import io
import json
import logging
import math
import os
import PIL.Image
import PIL.ImageDraw
import travellermap
import typing

# Rect format is (left, top, right, bottom)
# NOTE: This assumes that rects are valid (i.e. rect1.left <= rect1.right)
def _calculateIntersection(
        rect1: typing.Tuple[float, float, float, float],
        rect2: typing.Tuple[float, float, float, float]
        ) -> typing.Optional[typing.Tuple[float, float, float, float]]:
    left = max(rect1[0], rect2[0])
    right = min(rect1[2], rect2[2])
    if left >= right:
        return None

    top = max(rect1[1], rect2[1])
    bottom = min(rect1[3], rect2[3])
    if top >= bottom:
        return None
    
    return (left, top, right, bottom)

class _MipLevel(object):
    def __init__(
            self,
            filePath: str,
            scale: float
            ) -> None:
        self._filePath = filePath
        self._scale = scale
        with PIL.Image.open(self._filePath) as image:
            self._pixels = image.tobytes()
            self._size = (image.width, image.height)
            self._mode = image.mode

    def scale(self) -> float:
        return self._scale

    def pixels(self) -> bytes:
        return self._pixels

    def size(self) -> typing.Tuple[int, int]:
        return self._size

    def mode(self) -> str:
        return self._mode

    def __lt__(self, other: '_MipLevel') -> bool:
        if self.__class__ is other.__class__:
            return self.scale() > other.scale()
        return NotImplemented

class _CustomSector(object):
    def __init__(
            self,
            name: str,
            position: typing.Tuple[int, int],
            mipLevels: typing.Iterable[_MipLevel]
            ) -> None:
        self._name = name
        self._position = position
        self._mipLevels = sorted(mipLevels)

        absoluteRect = travellermap.sectorBoundingRect(position[0], position[1])
        mapSpaceUL = travellermap.absoluteHexToMapSpace(
            absoluteRect[0],
            absoluteRect[1] + absoluteRect[3])
        mapSpaceBR = travellermap.absoluteHexToMapSpace(
            absoluteRect[0] + absoluteRect[2],
            absoluteRect[1])
        self._mapSpaceRect = (
            mapSpaceUL[0], # Left
            mapSpaceUL[1], # Top
            mapSpaceBR[0], # Right
            mapSpaceBR[1]) # Bottom

    # Returned rect is (left, top, right, bottom)
    def mapSpaceRect(self) -> typing.Tuple[float, float, float, float]:
        return self._mapSpaceRect

    def findMipLevel(
            self,
            scale: float
            ) -> typing.Optional[_MipLevel]:
        bestLevel = None
        for level in self._mipLevels:
            if bestLevel and scale > level.scale():
                # We've got a possible best level and the one currently being looked at is for a
                # lower scale so use the current best. This works on the assumption that list is
                # ordered highest scale to lowest scale
                break
            bestLevel = level

        return bestLevel

class Compositor(object):
    _ManifestFileName = 'manifest.json'

    # This seems to be the point where things stop being that visible and Traveller Map starts showing
    # the galaxy overlay. If the requested tile has a scale lower than this then there isn't any point
    # in compositing.
    _MinCompositionScale = 1.4

    def __init__(
            self,
            customMapsDir: str
            ) -> None:
        self._customMapsDir = customMapsDir
        self._milieuSectorMap: typing.Dict[travellermap.Milieu, typing.List[_CustomSector]] = {}

        self._loadCustomUniverse()

    def composite(
            self,
            tileData: bytes,
            tileX: float,
            tileY: float,
            tileWidth: int,
            tileHeight: int,
            tileScale: float,
            milieu: travellermap.Milieu
            ) -> bytes:
        if tileScale < Compositor._MinCompositionScale:
            return tileData
        
        tileMapUL = travellermap.tileSpaceToMapSpace(
            tileX=tileX,
            tileY=tileY + 1,
            scale=tileScale)
        tileMapBR = travellermap.tileSpaceToMapSpace(
            tileX=tileX + 1,
            tileY=tileY,
            scale=tileScale)
        tileMapRect = (
            tileMapUL[0], # Left
            tileMapUL[1], # Top
            tileMapBR[0], # Right
            tileMapBR[1]) # Bottom        

        # TODO: There is an annoying graphics issue that can occur if two custom sectors
        # are horizontally next to each other. If the name of one of the edge worlds from
        # the first sector processed overlaps the hex from the adjacent sector. When the
        # adjacent sector is overlayed on the tile will be overwritten. The only solution 
        # I can see to that problem is switching so the custom sector mip levels have a
        # completely transparent background. However this introduces a load more problems
        # that are worse, such as issues with the * placeholders and things like trade
        # routes being rendered on the tile by Traveller Map and not overwritten
        # (especially if a custom sector was dropped over an existing populated sector).
        sectorList = self._milieuSectorMap.get(milieu)
        for sector in sectorList:
            sectorMapRect = sector.mapSpaceRect()
            intersection = _calculateIntersection(sectorMapRect, tileMapRect)
            if not intersection:
                continue # No intersection so just use base tile data
            
            # The custom sector overlaps the tile so copy the section that overlaps to
            # the tile

            mipLevel = sector.findMipLevel(scale=tileScale)
            if not mipLevel:
                continue

            # NOTE: Y-axis is flipped due to map space having a negative Y compared to other
            # coordinate systems
            srcPixelRect = (
                round((intersection[0] - sectorMapRect[0]) * mipLevel.scale()), # Left
                -round((intersection[3] - sectorMapRect[3]) * mipLevel.scale()), # Upper
                round((intersection[2] - sectorMapRect[0]) * mipLevel.scale()), # Right
                -round((intersection[1] - sectorMapRect[3]) * mipLevel.scale())) # Lower

            tgtPixelDim = (
                round((intersection[2] - intersection[0]) * tileScale),
                round((intersection[3] - intersection[1]) * tileScale))
            tgtPixelOffset = (
                math.ceil((intersection[0] * tileScale) - (float(tileX) * tileWidth)),
                -math.ceil((intersection[3] * tileScale) + (float(tileY) * tileHeight)))

            # Convert the mip level bytes to an image each time. The Image can't be shared between
            # threads as things like crop aren't thread safe
            # https://github.com/python-pillow/Pillow/issues/4848
            srcImage = PIL.Image.frombytes(
                mipLevel.mode(),
                mipLevel.size(),
                mipLevel.pixels())
            try:
                cropImage = srcImage.crop(srcPixelRect)
                del srcImage
                srcImage = cropImage

                # Scale the source image if required
                if (srcImage.width != tgtPixelDim[0]) or (srcImage.height != tgtPixelDim[1]):
                    resizedImage = srcImage.resize(
                        tgtPixelDim,
                        resample=PIL.Image.Resampling.BICUBIC)
                    del srcImage
                    srcImage = resizedImage

                # TODO: There is an optimisation here but care has to be taken. If the tile is
                # completely within the portion of the custom sector that doesn't contain any
                # masked out hexs from adjacent sectors then there is srcImage can be used to
                # generate tileData without the need to open the original tile. The best way
                # I can think to do this is to sectorBoundingRect so it can either return the
                # maximal bounds (what it currently returns) or the minimal bounds (where it
                # shrinks and offsets the rect)

                with PIL.Image.open(io.BytesIO(tileData)) as tgtImage:
                    tgtImage.paste(srcImage, tgtPixelOffset, srcImage)
                    tileData = io.BytesIO()
                    tgtImage.save(tileData, format='png')
                    tileData.seek(0)
                    tileData = tileData.read()
            finally:
                del srcImage

        return tileData

    def _loadCustomUniverse(self) -> None:
        self._milieuSectorMap.clear()

        manifestFilePath = os.path.join(self._customMapsDir, Compositor._ManifestFileName)
        if not os.path.isfile(manifestFilePath):
            return # Nothing to do

        with open(manifestFilePath, 'r') as file:
            data: typing.Mapping[str, typing.Any] = json.load(file)
            universeData = data.get('Universe')
            if not universeData:
                return # Nothing to do

            for milieuData in universeData:
                try:
                    self._loadMilieu(milieuData=milieuData)
                except Exception as ex:
                    logging.warning(f'Compositor skipping milieu due to parsing error')


    def _loadMilieu(
            self,
            milieuData: typing.Mapping[str, typing.Any]
            ) -> None:
        milieu = milieuData.get('Milieu')
        if milieu == None:
            raise RuntimeError('Milieu data is missing the Milieu element')
        if milieu not in travellermap.Milieu.__members__:
            raise RuntimeError(f'Milieu element has an invalid value "{milieu}"')
        milieu = travellermap.Milieu.__members__[milieu]

        sectors = milieuData.get('Sectors')
        if not sectors:
            logging.warning(f'Compositor skipping milieu {milieu.value} as it has no sectors')
            return

        self._milieuSectorMap[milieu] = self._loadSectors(
            sectorsData=sectors,
            milieu=milieu)

    def _loadSectors(
            self,
            sectorsData: typing.Iterable[typing.Mapping[str, typing.Any]],
            milieu: travellermap.Milieu
            ) -> typing.List[_CustomSector]:
        sectors = []
        for sectorData in sectorsData:
            try:
                sectors.append(self._loadSector(
                    sectorData=sectorData,
                    milieu=milieu))
            except Exception as ex:
                logging.warning(
                    f'Compositor skipping sector from {milieu.value} due to parsing error',
                    exc_info=ex)
        return sectors

    def _loadSector(
            self,
            sectorData: typing.Mapping[str, typing.Any],
            milieu: travellermap.Milieu     
            ) -> typing.Optional[_CustomSector]:
        name = sectorData.get('Name')
        if name == None:
            raise RuntimeError(f'Sector data from {milieu.value} is missing the Name element')

        sectorX = sectorData.get('SectorX')
        if sectorX == None:
            raise RuntimeError(f'Sector data for {name} from {milieu.value} is missing the SectorX element')
        if not isinstance(sectorX, int):
            raise RuntimeError(f'SectorX element for {name} from {milieu.value} has non integer value')

        sectorY = sectorData.get('SectorY')
        if sectorY == None:
            raise RuntimeError(f'Sector data for {name} from {milieu.value} is missing the SectorY element')
        if not isinstance(sectorY, int):
            raise RuntimeError(f'SectorY element for {name} from {milieu.value} has non integer value')

        mipLevels = sectorData.get('MipLevels')
        if not mipLevels:
            raise RuntimeError(f'Sector data  for {name} from {milieu.value} is missing the MipLevels element')

        return _CustomSector(
            name=name,
            position=(sectorX, sectorY),
            mipLevels=self._loadMipLevels(
                mipLevelsData=mipLevels,
                milieu=milieu,
                sectorName=name))

    def _loadMipLevels(
            self,
            mipLevelsData: typing.Iterable[typing.Mapping[str, typing.Any]],
            milieu: travellermap.Milieu,
            sectorName: str
            ) -> typing.List[_MipLevel]:
        levels = []
        for mipLevelData in mipLevelsData:
            try:
                levels.append(self._loadMipLevel(
                    mipLevelData=mipLevelData,
                    milieu=milieu,
                    sectorName=sectorName))
            except Exception as ex:
                logging.warning(
                    f'Compositor skipping mip level for {sectorName} from {milieu.value} due to parsing error',
                    exc_info=ex)
        return levels

    def _loadMipLevel(
            self,
            mipLevelData: typing.Mapping[str, typing.Any],
            milieu: travellermap.Milieu,
            sectorName: str
            ) -> _MipLevel:
        fileName = mipLevelData.get('FileName')
        if fileName == None:
            raise RuntimeError(f'MipLevel data for {sectorName} from {milieu.value} is missing the FileName element')

        scale = mipLevelData.get('Scale')
        if scale == None:
            raise RuntimeError(f'MipLevel data for {sectorName} from {milieu.value} is missing the Scale element')
        if not isinstance(scale, (int, float)):
            raise RuntimeError(f'MipLevel element for {sectorName} from {milieu.value}  has non numeric value')

        return _MipLevel(
            filePath=os.path.join(self._customMapsDir, 'milieu', milieu.value, fileName),
            scale=scale)
