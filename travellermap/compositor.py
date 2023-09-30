import io
import json
import math
import os
import PIL.Image
import PIL.ImageDraw
import travellermap
import typing
from PyQt5 import QtCore # TODO: Need to do something to remove this dependency

class MipLevel(object):
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

    def mode(self): # TODO: Figure out what type this should return
        return self._mode

    def __lt__(self, other: 'MipLevel') -> bool:
        if self.__class__ is other.__class__:
            return self.scale() < other.scale() # TODO: Check this is the correct order
        return NotImplemented

class CustomSector(object):
    def __init__(
            self,
            name: str,
            position: typing.Tuple[int, int],
            mipLevels: typing.Iterable[MipLevel]
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
        self._mapSpaceRect = QtCore.QRectF(
            mapSpaceUL[0], # Left
            mapSpaceUL[1], # Top
            mapSpaceBR[0] - mapSpaceUL[0], # Width
            mapSpaceBR[1] - mapSpaceUL[1]) # Height

    def mapSpaceRect(self) -> QtCore.QRectF:
        return self._mapSpaceRect

    def findMipLevel(
            self,
            scale: float
            ) -> typing.Optional[MipLevel]:
        """
        bestLevel = None
        bestDiff = float('inf')

        for level in self._mipLevels:
            diff = abs(level.scale() - scale)
            if diff > bestDiff:
                # Mip levels are sorted be scale so we can bail if we ever start seeing
                # the diff getting worse (as we're getting further away)
                break
            bestLevel = level
            bestDiff = diff
        """
        bestLevel = None
        for level in self._mipLevels:
            bestLevel = level
            if level.scale() >= scale:
                break
        return bestLevel

class Compositor(object):
    _ManifestFileName = 'manifest.json'

    def __init__(
            self,
            customMapsDir: str
            ) -> None:
        self._customMapsDir = customMapsDir
        self._milieuSectorMap: typing.Dict[travellermap.Milieu, typing.List[CustomSector]] = {}

        self._loadCustomUniverse()

    def composite(
            self,
            tileData: bytes,
            tileX: float,
            tileY: float,
            tileWidth: int,
            tileHeight: int,
            scale: float,
            milieu: travellermap.Milieu
            ) -> bytes:
        if scale < 1.4: # TODO: Pull this out as a constant
            # This seems to be the point where things stop being that visible
            # and Traveller Map starts showing the galaxy overlay
            return tileData

        # TODO: Need to handle multiple custom sectors overlapping the same tile
        customSectors = self._milieuSectorMap.get(milieu)
        if not customSectors:
            return tileData
        sector = customSectors[0]

        mipLevel = sector.findMipLevel(scale=scale)
        if not mipLevel:
            return tileData

        # TODO: Update to use mip level. Need to switch to having intersect done in map space with
        # CustomSector storing the sector rect in map space. Tile will need converted to map space.
        # I think pretty much everything should be possible in map space (more y flipping fun)

        tileMapUL = travellermap.tileSpaceToMapSpace(
            tileX=tileX,
            tileY=tileY + 1,
            scale=scale)
        tileMapBR = travellermap.tileSpaceToMapSpace(
            tileX=tileX + 1,
            tileY=tileY,
            scale=scale)
        tileMapRect = QtCore.QRectF(
            tileMapUL[0], # Left
            tileMapUL[1], # Top
            tileMapBR[0] - tileMapUL[0], # Width
            tileMapBR[1] - tileMapUL[1]) # Height

        sectorMapRect = sector.mapSpaceRect()
        intersection = sectorMapRect.intersected(tileMapRect)
        if intersection.isEmpty():
            return tileData # No intersection so just use base tile data

        # The custom sector overlaps the tile so copy the section that overlaps to
        # the tile

        srcPixelRect = (
            round((intersection.left() - sectorMapRect.left()) * mipLevel.scale()), # Left
            -round((intersection.bottom() - sectorMapRect.bottom()) * mipLevel.scale()), # Upper
            round((intersection.right() - sectorMapRect.left()) * mipLevel.scale()), # Right
            -round((intersection.top() - sectorMapRect.bottom()) * mipLevel.scale())) # Lower

        tgtPixelDim = (
            round(intersection.width() * scale),
            round(intersection.height() * scale))
        tgtPixelOffset = (
            math.ceil((intersection.left() * scale) - (float(tileX) * tileWidth)),
            -math.ceil((intersection.bottom() * scale) + (float(tileY) * tileHeight)))

        # TODO: I think the bytes need to be converted to an image each time as things
        # like crop aren't thread safe so the image can't be shared
        # https://github.com/python-pillow/Pillow/issues/4848
        # TODO: Do I need to call close on this???
        srcImage = PIL.Image.frombytes(
            mipLevel.mode(),
            mipLevel.size(),
            mipLevel.pixels())
        try:
            cropImage = srcImage.crop(srcPixelRect)
            srcImage.close()
            srcImage = cropImage

            # TODO: This shouldn't use nearest (as it looks crap) but doing it for speed as when zoomed
            # way out resizing the entire custom sector image down to the size of a tile takes multiple
            # seconds. The better thing to do would be have lower res versions of the custom sector image,
            # ideally independently generate posters but possibly could just pre-process the high res
            # image to pre-create smaller versions at a few different lower resolutions
            if (srcImage.width != tgtPixelDim[0]) or (srcImage.height != tgtPixelDim[1]):
                resizedImage = srcImage.resize(
                    tgtPixelDim,
                    #resample=PIL.Image.Resampling.NEAREST)
                    resample=PIL.Image.Resampling.BICUBIC)
                srcImage.close()
                srcImage = resizedImage

            # TODO: There is an optimisation here but care has to be taken. If the tile is
            # completely within the portion of the custom sector that doesn't contain any
            # masked out hexs from adjacent sectors then there is srcImage can be used to
            # generate tileData without the need to open the original tile. The best way
            # I can think to do this is to sectorBoundingRect so it can either return the
            # maximal bounds (what it currently returns) or the minimal bounds (where it
            # shrinks and offsets the rect)

            with PIL.Image.open(tileData if isinstance(tileData, io.BytesIO) else io.BytesIO(tileData)) as tgtImage:
                tgtImage.paste(srcImage, tgtPixelOffset, srcImage)
                tileData = io.BytesIO()
                tgtImage.save(tileData, format='png')
                tileData.seek(0)
        finally:
            srcImage.close()

        return tileData

    def _loadCustomUniverse(self) -> None:
        self._milieuSectorMap.clear()

        manifestFilePath = os.path.join(self._customMapsDir, Compositor._ManifestFileName)
        with open(manifestFilePath, 'r') as file:
            data: typing.Mapping[str, typing.Any] = json.load(file)
            universeData = data.get('Universe')
            if not universeData:
                return # Nothing to do

            for milieuData in universeData:
                self._loadMilieu(milieuData=milieuData)

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
            # TODO: Could log a warning at this as it's an indication of a mistake
            return # No sectors so nothing to do

        self._milieuSectorMap[milieu] = self._loadSectors(
            mipPath=os.path.join(self._customMapsDir, 'milieu', milieu.value),
            sectorsData=sectors)

    def _loadSectors(
            self,
            mipPath: str,
            sectorsData: typing.Iterable[typing.Mapping[str, typing.Any]]
            ) -> typing.List[CustomSector]:
        sectors = []
        for sectorData in sectorsData:
            sectors.append(self._loadSector(
                mipPath=mipPath,
                sectorData=sectorData))
        return sectors

    def _loadSector(
            self,
            mipPath: str,
            sectorData: typing.Mapping[str, typing.Any]
            ) -> typing.Optional[CustomSector]:
        name = sectorData.get('Name')
        if name == None:
            raise RuntimeError('Sector data is missing the Name element')

        sectorX = sectorData.get('SectorX')
        if sectorX == None:
            raise RuntimeError('Sector data is missing the SectorX element')
        if not isinstance(sectorX, int):
            raise RuntimeError('SectorX element has non integer value')

        sectorY = sectorData.get('SectorY')
        if sectorY == None:
            raise RuntimeError('Sector data is missing the SectorY element')
        if not isinstance(sectorY, int):
            raise RuntimeError('SectorY element has non integer value')

        mipLevels = sectorData.get('MipLevels')
        if not mipLevels:
            raise RuntimeError('Sector data is missing the MipLevels element')

        return CustomSector(
            name=name,
            position=(sectorX, sectorY),
            mipLevels=self._loadMipLevels(
                mipPath=mipPath,
                mipLevelsData=mipLevels))

    def _loadMipLevels(
            self,
            mipPath: str,
            mipLevelsData: typing.Iterable[typing.Mapping[str, typing.Any]]
            ) -> typing.List[MipLevel]:
        levels = []
        for mipLevelData in mipLevelsData:
            levels.append(self._loadMipLevel(
                mipPath=mipPath,
                mipLevelData=mipLevelData))
        return levels

    def _loadMipLevel(
            self,
            mipPath: str,
            mipLevelData: typing.Mapping[str, typing.Any]
            ) -> MipLevel:
        fileName = mipLevelData.get('FileName')
        if fileName == None:
            raise RuntimeError('MipLevel data is missing the FileName element')

        scale = mipLevelData.get('Scale')
        if scale == None:
            raise RuntimeError('MipLevel data is missing the Scale element')
        if not isinstance(scale, (int, float)):
            raise RuntimeError('SectorY element has non numeric value')

        return MipLevel(
            filePath=os.path.join(mipPath, fileName),
            scale=scale)
