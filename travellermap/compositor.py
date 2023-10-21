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

class _MapTile(object):
    def __init__(
            self,
            image: travellermap.MapImage,
            scale: int
            ) -> None:
        self._scale = scale
        with PIL.Image.open(io.BytesIO(image.bytes())) as pixelData:
            self._pixels = pixelData.tobytes()
            self._size = (pixelData.width, pixelData.height)
            self._mode = pixelData.mode

    def scale(self) -> int:
        return self._scale

    def pixels(self) -> bytes:
        return self._pixels

    def size(self) -> typing.Tuple[int, int]:
        return self._size

    def mode(self) -> str:
        return self._mode

    def __lt__(self, other: '_MapTile') -> bool:
        if self.__class__ is other.__class__:
            return self.scale() > other.scale()
        return NotImplemented

class _CustomSector(object):
    def __init__(
            self,
            name: str,
            position: typing.Tuple[int, int],
            mapImages: typing.Iterable[_MapTile]
            ) -> None:
        self._name = name
        self._position = position
        self._mapImages = sorted(mapImages)

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

    def findMapImage(
            self,
            scale: typing.Union[int, float]
            ) -> typing.Optional[_MapTile]:
        bestLevel = None
        for level in self._mapImages:
            if bestLevel and scale > level.scale():
                # We've got a possible best level and the one currently being looked at is for a
                # lower scale so use the current best. This works on the assumption that list is
                # ordered highest scale to lowest scale
                break
            bestLevel = level

        return bestLevel

class Compositor(object):
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

    def needsComposition(
            self,
            tileX: float,
            tileY: float,
            tileScale: float,
            milieu: travellermap.Milieu
            ) -> bool:
        if tileScale < Compositor._MinCompositionScale:
            return False

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

        for sector in self._milieuSectorMap.get(milieu):
            sectorMapRect = sector.mapSpaceRect()
            intersection = _calculateIntersection(sectorMapRect, tileMapRect)
            if intersection:
                return True
            
        return False

    def composite(
            self,
            tileData: bytes,
            tileX: float,
            tileY: float,
            tileWidth: int,
            tileHeight: int,
            tileScale: float,
            milieu: travellermap.Milieu,
            outputFormat: travellermap.MapFormat
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

            mapImage = sector.findMapImage(scale=tileScale)
            if not mapImage:
                continue

            # NOTE: Y-axis is flipped due to map space having a negative Y compared to other
            # coordinate systems
            srcPixelRect = (
                round((intersection[0] - sectorMapRect[0]) * mapImage.scale()), # Left
                -round((intersection[3] - sectorMapRect[3]) * mapImage.scale()), # Upper
                round((intersection[2] - sectorMapRect[0]) * mapImage.scale()), # Right
                -round((intersection[1] - sectorMapRect[3]) * mapImage.scale())) # Lower

            tgtPixelDim = (
                round((intersection[2] - intersection[0]) * tileScale),
                round((intersection[3] - intersection[1]) * tileScale))
            tgtPixelOffset = (
                math.ceil((intersection[0] * tileScale) - (float(tileX) * tileWidth)),
                -math.ceil((intersection[3] * tileScale) + (float(tileY) * tileHeight)))

            # Convert the map image bytes to an image each time. The Image can't be shared between
            # threads as things like crop aren't thread safe
            # https://github.com/python-pillow/Pillow/issues/4848
            srcImage = PIL.Image.frombytes(
                mapImage.mode(),
                mapImage.size(),
                mapImage.pixels())
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
                # shrinks and offsets the rect). The main issue is it would mean the compositor
                # would have to (possibly indirectly) initiate the request for the tile from
                # Traveller Map (if it's not in the cache).
                # TODO: There is another optimisation as if the tile overlaps multiple custom
                # sectors it will repeatedly decode and re-encode the image. This will also
                # cause repeated quality loss if using jpeg

                with PIL.Image.open(io.BytesIO(tileData)) as tgtImage:
                    tgtImage.paste(srcImage, tgtPixelOffset, srcImage)
                    tileData = io.BytesIO()
                    tgtImage.save(tileData, format=outputFormat.value)
                    tileData.seek(0)
                    tileData = tileData.read()
            finally:
                del srcImage

        return tileData

    def _loadCustomUniverse(self) -> None:
        self._milieuSectorMap.clear()

        for milieu in travellermap.Milieu:
            sectors = []
            for sectorInfo in travellermap.DataStore.instance().sectors(milieu=milieu):
                if not sectorInfo.isCustomSector():
                    continue # Only interested in custom sectors

                mapLevels = sectorInfo.mapLevels()
                if not mapLevels:
                    logging.warning(f'Compositor skipping custom sector {sectorInfo.canonicalName()} as it has no map levels')
                    continue

                mapImages = []
                for scale in mapLevels.keys():
                    try:
                        mapImage = travellermap.DataStore.instance().sectorMapImage(
                            sectorName=sectorInfo.canonicalName(),
                            milieu=milieu,
                            scale=scale)
                        mapImages.append(_MapTile(image=mapImage, scale=scale))
                    except Exception as ex:
                        logging.warning(f'Compositor failed to load scale {scale} map image for {sectorInfo.canonicalName()}', exc_info=ex)
                        continue

                sectors.append(_CustomSector(
                    name=sectorInfo.canonicalName(),
                    position=(sectorInfo.x(), sectorInfo.y()),
                    mapImages=mapImages))

            self._milieuSectorMap[milieu] = sectors
