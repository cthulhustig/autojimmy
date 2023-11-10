_HasSvgSupport = True
try:
    import cairosvg
    import cairosvg.parser
    import cairosvg.surface
except Exception as ex:
    _HasSvgSupport = False

import enum
import io
import logging
import math
import multiprocessing
import numpy
import PIL.Image
import travellermap
import typing
import xml.etree.ElementTree

_FullSvgRendering = False

# Returns true if rect1 is completely contained within rect2
# Rect format is (left, top, right, bottom)
# NOTE: This assumes that rects are valid (i.e. rect1.left <= rect1.right)
def _isContained(
        rect1: typing.Tuple[float, float, float, float],
        rect2: typing.Tuple[float, float, float, float]
        ) -> bool:
    return (rect1[0] >= rect2[0]) and (rect1[1] >= rect2[1]) and \
        (rect1[2] <= rect2[2]) and (rect1[3] <= rect2[3])

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

def _extractSvgSize(
        svgData: typing.Union[str, bytes],
        ) -> typing.Tuple[int, int]:
    if isinstance(svgData, bytes):
        svgData = svgData.decode()

    root = xml.etree.ElementTree.fromstring(svgData)

    return (
        int(root.attrib.get('width')),
        int(root.attrib.get('height')))

class CompositorImage(object):
    class ImageType(enum.Enum):
        Bitmap = 0,
        SVG = 1

    def __init__(
            self,
            imageType: ImageType,
            mainImage: typing.Union[PIL.Image.Image, bytes],
            textMask: typing.Optional[typing.Union[PIL.Image.Image, bytes]],
            scale: int
            ) -> None:
        self._imageType = imageType
        self._mainImage = mainImage
        self._textMask = textMask
        self._scale = scale

    def imageType(self) -> ImageType:
        return self._imageType

    def mainImage(self) -> typing.Union[PIL.Image.Image, bytes]:
        return self._mainImage

    def textMask(self) -> typing.Optional[typing.Union[PIL.Image.Image, bytes]]:
        return self._textMask
    
    def scale(self) -> int:
        return self._scale

    def __lt__(self, other: 'CompositorImage') -> bool:
        if self.__class__ is other.__class__:
            return self.scale() > other.scale()
        return NotImplemented

    def __del__(self):
        if self._imageType == CompositorImage.ImageType.Bitmap:
            if self._mainImage:
                self._mainImage.close()

            if self._textMask:
                self._textMask.close()

class _CustomSector(object):
    def __init__(
            self,
            name: str,
            position: typing.Tuple[int, int],
            mapPosters: typing.Optional[typing.Iterable[CompositorImage]] = None
            ) -> None:
        self._name = name
        self._position = position
        self._mapPosters = list(mapPosters) if mapPosters else []
        self._mapPosters.sort() # Sorting is important for map selection algorithm

        absoluteRect = travellermap.sectorBoundingRect(position[0], position[1])
        mapSpaceUL = travellermap.absoluteHexToMapSpace(
            absoluteRect[0],
            absoluteRect[1] + absoluteRect[3])
        mapSpaceBR = travellermap.absoluteHexToMapSpace(
            absoluteRect[0] + absoluteRect[2],
            absoluteRect[1])
        self._boundingRect = (
            mapSpaceUL[0], # Left
            mapSpaceUL[1], # Top
            mapSpaceBR[0], # Right
            mapSpaceBR[1]) # Bottom

        absoluteRect = travellermap.sectorInteriorRect(position[0], position[1])
        mapSpaceUL = travellermap.absoluteHexToMapSpace(
            absoluteRect[0],
            absoluteRect[1] + absoluteRect[3])
        mapSpaceBR = travellermap.absoluteHexToMapSpace(
            absoluteRect[0] + absoluteRect[2],
            absoluteRect[1])
        self._interiorRect = (
            mapSpaceUL[0], # Left
            mapSpaceUL[1], # Top
            mapSpaceBR[0], # Right
            mapSpaceBR[1]) # Bottom
        
    def name(self) -> str:
        return self._name
    
    def position(self) -> typing.Tuple[int, int]:
        return self._position

    # Returned rect is in map space and ordered (left, top, right, bottom)
    def boundingRect(self) -> typing.Tuple[float, float, float, float]:
        return self._boundingRect

    # Returned rect is in map space and ordered (left, top, right, bottom)
    def interiorRect(self) -> typing.Tuple[float, float, float, float]:
        return self._interiorRect
    
    def addMapPoster(
            self,
            poster: CompositorImage
            ) -> None:
        self._mapPosters.append(poster)
        self._mapPosters.sort() # Sorting is important for map selection algorithm

    def findMapPoster(
            self,
            scale: typing.Union[int, float]
            ) -> typing.Optional[CompositorImage]:
        bestPoster = None
        for poster in self._mapPosters:
            if bestPoster and scale > poster.scale():
                # We've got a possible best poster and the one currently being looked at is for a
                # lower scale so use the current best. This works on the assumption that list is
                # ordered highest scale to lowest scale
                break
            bestPoster = poster

        return bestPoster

class Compositor(object):
    class OverlapType(enum.Enum):
        # The tile doesn't overlap any custom sectors so the required tile is just the source tile
        # that is generated by Traveller Map and no composition is required
        NoOverlap = 0

        # The tile partially overlaps at least one custom sector so the custom sector(s) need to
        # be composited onto the source tile from Traveller. Note this is a partial overlap of the
        # _tile_, the tile may contain part or all of the custom sector.
        PartialOverlap = 1

        # The tile is completely contained within a single custom sector so the required tile  can
        # be generated simply by copying from the (i.e. the Traveller Map tile isn't required)
        CompleteOverlap = 2

    # This is the point that Traveller Map stops rendering the sector data and starts rendering
    # the galaxy image. It stops rendering sector detail at a scale of 4, however the sector name
    # is still rendered so composition is still required.
    _MinCompositionScale = 1

    def __init__(
            self,
            customMapsDir: str
            ) -> OverlapType:
        self._customMapsDir = customMapsDir
        self._milieuSectorMap: typing.Dict[travellermap.Milieu, typing.List[_CustomSector]] = {}
        self._processPool = None # Make sure variable exists for destructor in case creation fails

        # Construct the pool of processes that can be used for SVG rendering (or other long jobs).
        # A context is used so we can force processes to be spawned, this keeps the behaviour
        # the same on all OS and avoids issues with singletons when using fork
        self._mpContext = multiprocessing.get_context('spawn')
        self._processPool = self._mpContext.Pool()

        self._loadCustomUniverse()

    def __del__(self):
        if self._processPool:
            self._processPool.close()

    def createCompositorImage(
            self,
            mapImage: travellermap.MapImage,
            scale: int
            ) -> CompositorImage:
        mapBytes = mapImage.bytes()
        mapFormat = mapImage.format()
        if mapFormat == travellermap.MapFormat.SVG:
            if _FullSvgRendering:
                imageType = CompositorImage.ImageType.SVG
                mainImage = mapBytes
                textMask = Compositor._createTextSvg(mapBytes=mapBytes)
            else:
                imageType = CompositorImage.ImageType.Bitmap
                width, height = _extractSvgSize(mapBytes)

                result = self._processPool.apply(
                    Compositor._renderSvgTask,
                    args=[mapBytes])
                if isinstance(result, Exception):
                    raise RuntimeError('Worker process exception when render map SVG') from result                
                mainImage = PIL.Image.frombytes('RGBA', (width, height), result)

                textSvg = Compositor._createTextSvg(mapBytes=mapBytes)
                result = self._processPool.apply(
                    Compositor._renderSvgTask,
                    args=[textSvg])
                if isinstance(result, Exception):
                    raise RuntimeError('Worker process exception when render text SVG') from result
                textImage = PIL.Image.frombytes('RGBA', (width, height), result)
                textMask = textImage.split()[-1] # Extract alpha channel as Image
                del textImage
        else:
            imageType = CompositorImage.ImageType.Bitmap
            # Image.load isn't thread safe so make sure to call it now so it doesn't get called
            # when cropping the image during composition
            # https://github.com/python-pillow/Pillow/issues/4848
            mainImage = PIL.Image.open(io.BytesIO(mapBytes))
            try:
                mainImage.load()
            except:
                mainImage.close()
                raise
            textMask = None

        return CompositorImage(
            imageType=imageType,
            mainImage=mainImage,
            textMask=textMask,
            scale=scale)

    def overlapType(
            self,
            tileX: float,
            tileY: float,
            tileScale: float,
            milieu: travellermap.Milieu
            ) -> OverlapType:
        if tileScale < Compositor._MinCompositionScale:
            return Compositor.OverlapType.NoOverlap

        # Calculate tile rect in map space
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

        sectorList = self._milieuSectorMap.get(milieu)

        for sector in sectorList:
            sectorMapRect = sector.interiorRect()
            if _isContained(tileMapRect, sectorMapRect):
                return Compositor.OverlapType.CompleteOverlap

        for sector in sectorList:
            sectorMapRect = sector.boundingRect()
            intersection = _calculateIntersection(sectorMapRect, tileMapRect)
            if intersection:
                return Compositor.OverlapType.PartialOverlap

        return Compositor.OverlapType.NoOverlap

    def partialOverlap(
            self,
            tileImage: PIL.Image.Image,
            tileX: float,
            tileY: float,
            tileWidth: int,
            tileHeight: int,
            tileScale: float,
            milieu: travellermap.Milieu
            ) -> None:
        if tileScale < Compositor._MinCompositionScale:
            return # Nothing to do (shouldn't happen if correctly checking which operation to use)

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

        # Determine which custom sector(s) overlap the tile how they should be overlaid.
        overlappedSectors: typing.List[typing.Tuple[
            CompositorImage, # Map poster for custom sector that overlaps tile
            typing.Tuple[int, int, int, int], # Custom sector rect to copy
            typing.Tuple[int, int], # Size to scale section of custom sector to
            typing.Tuple[int, int], # Tile offset to place scaled section of custom sector
            ]] = []
        for sector in self._milieuSectorMap.get(milieu):
            sectorMapRect = sector.boundingRect()
            intersection = _calculateIntersection(sectorMapRect, tileMapRect)
            if not intersection:
                continue # No intersection so just use base tile data

            # The custom sector overlaps the tile so copy the section that overlaps to
            # the tile

            mapPoster = sector.findMapPoster(scale=tileScale)
            if not mapPoster:
                continue

            # NOTE: Y-axis is flipped due to map space having a negative Y compared to other
            # coordinate systems
            srcPixelRect = (
                round((intersection[0] - sectorMapRect[0]) * mapPoster.scale()), # Left
                -round((intersection[3] - sectorMapRect[3]) * mapPoster.scale()), # Upper
                round((intersection[2] - sectorMapRect[0]) * mapPoster.scale()), # Right
                -round((intersection[1] - sectorMapRect[3]) * mapPoster.scale())) # Lower

            tgtPixelDim = (
                round((intersection[2] - intersection[0]) * tileScale),
                round((intersection[3] - intersection[1]) * tileScale))
            tgtPixelOffset = (
                math.ceil((intersection[0] * tileScale) - (float(tileX) * tileWidth)),
                -math.ceil((intersection[3] * tileScale) + (float(tileY) * tileHeight)))

            overlappedSectors.append((mapPoster, srcPixelRect, tgtPixelDim, tgtPixelOffset))

        # Overlay custom sector graphics on tile
        for mapPoster, srcPixelRect, tgtPixelDim, tgtPixelOffset in overlappedSectors:
            if mapPoster.imageType() == CompositorImage.ImageType.SVG:
                self._overlaySvgCustomSector(
                    svgData=mapPoster.mainImage(),
                    srcPixelRect=srcPixelRect,
                    tgtPixelDim=tgtPixelDim,
                    tgtPixelOffset=tgtPixelOffset,
                    tgtImage=tileImage)
            else:
                self._overlayBitmapCustomSector(
                    srcImage=mapPoster.mainImage(),
                    srcPixelRect=srcPixelRect,
                    tgtPixelDim=tgtPixelDim,
                    tgtPixelOffset=tgtPixelOffset,
                    tgtImage=tileImage)

        # Overlay custom sector text on tile
        for mapPoster, srcPixelRect, tgtPixelDim, tgtPixelOffset in overlappedSectors:
            textMask = mapPoster.textMask()
            if textMask:            
                if mapPoster.imageType() == CompositorImage.ImageType.SVG:
                    self._overlaySvgCustomSector(
                        svgData=textMask,
                        srcPixelRect=srcPixelRect,
                        tgtPixelDim=tgtPixelDim,
                        tgtPixelOffset=tgtPixelOffset,
                        tgtImage=tileImage)
                else:
                    self._overlayBitmapCustomSector(
                        srcImage=mapPoster.mainImage(),
                        srcPixelRect=srcPixelRect,
                        tgtPixelDim=tgtPixelDim,
                        tgtPixelOffset=tgtPixelOffset,
                        tgtImage=tileImage,
                        maskImage=textMask)

    def fullOverlap(
            self,
            tileX: float,
            tileY: float,
            tileScale: float,
            milieu: travellermap.Milieu
            ) -> typing.Optional[PIL.Image.Image]:
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

        sectorList = self._milieuSectorMap.get(milieu)
        for sector in sectorList:
            if not _isContained(tileMapRect, sector.interiorRect()):
                continue

            sectorMapRect = sector.boundingRect()

            # The tile is completely contained within the custom sector so copy the section of
            # the custom sector that it covers

            mapPoster = sector.findMapPoster(scale=tileScale)
            if not mapPoster:
                continue

            # NOTE: Y-axis is flipped due to map space having a negative Y compared to other
            # coordinate systems
            srcPixelRect = (
                round((tileMapRect[0] - sectorMapRect[0]) * mapPoster.scale()), # Left
                -round((tileMapRect[3] - sectorMapRect[3]) * mapPoster.scale()), # Upper
                round((tileMapRect[2] - sectorMapRect[0]) * mapPoster.scale()), # Right
                -round((tileMapRect[1] - sectorMapRect[3]) * mapPoster.scale())) # Lower

            tgtPixelDim = (
                round((tileMapRect[2] - tileMapRect[0]) * tileScale),
                round((tileMapRect[3] - tileMapRect[1]) * tileScale))

            # Overlay custom sector poster on tile
            if mapPoster.imageType() == CompositorImage.ImageType.SVG:
                tileImage = self._overlaySvgCustomSector(
                    svgData=mapPoster.mainImage(),
                    srcPixelRect=srcPixelRect,
                    tgtPixelDim=tgtPixelDim,
                    tgtPixelOffset=(0, 0))
            else:
                tileImage = self._overlayBitmapCustomSector(
                    srcImage=mapPoster.mainImage(),
                    srcPixelRect=srcPixelRect,
                    tgtPixelDim=tgtPixelDim,
                    tgtPixelOffset=(0, 0))

            # Overlay custom sector text on tile
            textMask = mapPoster.textMask()
            if textMask:
                if mapPoster.imageType() == CompositorImage.ImageType.SVG:
                    self._overlaySvgCustomSector(
                        svgData=textMask,
                        srcPixelRect=srcPixelRect,
                        tgtPixelDim=tgtPixelDim,
                        tgtPixelOffset=(0, 0),
                        tgtImage=tileImage)
                else:
                    self._overlayBitmapCustomSector(
                        srcImage=mapPoster.mainImage(),
                        srcPixelRect=srcPixelRect,
                        tgtPixelDim=tgtPixelDim,
                        tgtPixelOffset=(0, 0),
                        tgtImage=tileImage,
                        maskImage=textMask)

            return tileImage

        return None

    def _loadCustomUniverse(self) -> None:
        self._milieuSectorMap.clear()
        
        svgMapData: typing.List[typing.Tuple[
            travellermap.Milieu,
            _CustomSector,
            travellermap.MapImage,
            int]] = []        

        for milieu in travellermap.Milieu:
            milieuSectors = []
            for sectorInfo in travellermap.DataStore.instance().sectors(milieu=milieu):
                if not sectorInfo.isCustomSector():
                    continue # Only interested in custom sectors

                mapLevels = sectorInfo.customMapLevels()
                if not mapLevels:
                    logging.warning(f'Compositor skipping custom sector {sectorInfo.canonicalName()} in {milieu.value} as it has no map levels')
                    continue

                mapImages: typing.List[typing.Tuple[travellermap.MapImage, int]] = []
                for scale in mapLevels.keys():
                    try:
                        mapImage = travellermap.DataStore.instance().sectorMapImage(
                            sectorName=sectorInfo.canonicalName(),
                            milieu=milieu,
                            scale=scale)
                        if (mapImage.format() == travellermap.MapFormat.SVG) and (not _HasSvgSupport):
                            logging.warning(f'Compositor ignoring {scale} map image for {sectorInfo.canonicalName()} in {milieu.value} as SVG support is disabled')
                            continue

                        mapImages.append((mapImage, scale))
                    except Exception as ex:
                        logging.warning(f'Compositor failed to load scale {scale} map image for {sectorInfo.canonicalName()} in {milieu.value}', exc_info=ex)
                        continue

                if not mapImages:
                    logging.warning(f'Compositor skipping custom sector {sectorInfo.canonicalName()} in {milieu.value} as it has no usable map levels')
                    continue

                customSector = _CustomSector(
                    name=sectorInfo.canonicalName(),
                    position=(sectorInfo.x(), sectorInfo.y()))
                milieuSectors.append(customSector)

                for mapImage, scale in mapImages:
                    mapFormat = mapImage.format()
                    if (mapFormat == travellermap.MapFormat.SVG) and not _FullSvgRendering:
                        svgMapData.append((milieu, customSector, mapImage, scale))
                    else:
                        try:       
                            customSector.addMapPoster(self.createCompositorImage(
                                mapImage=mapImage,
                                scale=scale))
                        except Exception as ex:
                            logging.warning(f'Compositor failed to generate {scale} composition image for {sectorInfo.canonicalName()} in {milieu.value}', exc_info=ex)
                            continue

            if milieuSectors:
                self._milieuSectorMap[milieu] = milieuSectors
    
        if not svgMapData:
            return # Nothing more to do
        
        svgTaskData = []
        for index, (milieu, customSector, mapImage, scale) in enumerate(svgMapData):
            try:
                svgMapBytes = mapImage.bytes()
                svgTextBytes = Compositor._createTextSvg(mapBytes=svgMapBytes)

                svgTaskData.append((svgMapBytes, ))
                svgTaskData.append((svgTextBytes, ))
            except:
                logging.warning(f'Compositor failed to set up SVG task for {scale} composition image for {customSector.name()} in {milieu.value}', exc_info=ex)
                continue

        logging.info(f'Compositor converting {len(svgTaskData)} SVG maps')
        svgTaskResults = self._processPool.starmap(
            Compositor._renderSvgTask,
            iterable=svgTaskData)

        for index, (milieu, customSector, mapImage, scale) in enumerate(svgMapData):
            try:
                mapResult = svgTaskResults[index * 2]
                if isinstance(mapResult, Exception):
                    raise RuntimeError('Worker process exception when render map SVG') from mapResult

                textResult = svgTaskResults[(index * 2) + 1]
                if isinstance(textResult, Exception):
                    raise RuntimeError('Worker process exception when render text SVG') from textResult

                svgDim = _extractSvgSize(svgData=mapImage.bytes())
                mainImage = PIL.Image.frombytes('RGBA', svgDim, mapResult)
                textImage = PIL.Image.frombytes('RGBA', svgDim, textResult)
                textMask = textImage.split()[-1] # Extract alpha channel as Image
                del textImage

                customSector.addMapPoster(CompositorImage(
                    imageType=CompositorImage.ImageType.Bitmap,
                    mainImage=mainImage,
                    textMask=textMask,
                    scale=scale))
            except Exception as ex:
                logging.warning(f'Compositor failed to generate {scale} composition image for {customSector.name()} in {milieu.value}', exc_info=ex)
                continue

    def _overlayBitmapCustomSector(
            self,
            srcImage: PIL.Image.Image,
            srcPixelRect: typing.Tuple[int, int, int, int],
            tgtPixelDim: typing.Tuple[int, int],
            tgtPixelOffset: typing.Tuple[int, int],
            tgtImage: typing.Optional[PIL.Image.Image] = None,
            maskImage: typing.Optional[PIL.Image.Image] = None # NOTE: Must be the same size as srcImage and tgtImage must not be None
            ) -> PIL.Image.Image: # Returns the target if specified otherwise returns the cropped and resized section of the source image
        overlayImage = srcImage
        srcPixelDim = (
            srcPixelRect[2] - srcPixelRect[0],
            srcPixelRect[3] - srcPixelRect[1])
        croppedImage = None
        resizedImage = None
        croppedMask = None
        resizedMask = None
        try:
            # Crop the source image if required
            if ((overlayImage.width != srcPixelDim[0]) or (overlayImage.height != srcPixelDim[1])):
                croppedImage = overlayImage.crop(srcPixelRect)
                overlayImage = croppedImage

                if maskImage is not None:
                    croppedMask = maskImage.crop(srcPixelRect)
                    maskImage = croppedMask


            # Scale the source image if required
            if (overlayImage.width != tgtPixelDim[0]) or (overlayImage.height != tgtPixelDim[1]):
                resizedImage = overlayImage.resize(
                    tgtPixelDim,
                    resample=PIL.Image.Resampling.BICUBIC)
                overlayImage = resizedImage

                if maskImage is not None:
                    resizedMask = maskImage.resize(
                        tgtPixelDim,
                        resample=PIL.Image.Resampling.BICUBIC)
                    maskImage = resizedMask

            if tgtImage is None:
                # No target was specified to overlay the custom sector on so just return the
                # cropped and resized section of the source image.
                # NOTE: If no cropping or resizing performed a copy MUST be made as the source
                # image shouldn't be returned as something may delete it
                # NOTE: It's important to set tgtImage to srcImage to prevent it being deleted
                # in the finally clause
                tgtImage = overlayImage if overlayImage is not srcImage else overlayImage.copy()
            else:
                # Overlay custom sector section on current tile
                if maskImage is None:
                    maskImage = overlayImage
                tgtImage.paste(overlayImage, tgtPixelOffset, maskImage)
        finally:
            if (croppedImage is not None) and (croppedImage is not tgtImage):
                croppedImage.close()
                del croppedImage
            if (resizedImage is not None) and (resizedImage is not tgtImage):
                resizedImage.close()
                del resizedImage
            if croppedMask is not None:
                croppedMask.close()
                del croppedMask
            if resizedMask is not None:
                resizedMask.close()
                del resizedMask

        return tgtImage

    def _overlaySvgCustomSector(
            self,
            svgData: bytes,
            srcPixelRect: typing.Tuple[int, int, int, int],
            tgtPixelDim: typing.Tuple[int, int],
            tgtPixelOffset: typing.Tuple[int, int],
            tgtImage: typing.Optional[PIL.Image.Image] = None
            ) -> PIL.Image.Image: # Returns the target if specified otherwise returns the cropped and resized section of the source image
        overlayImage = None
        try:
            result = self._processPool.apply(
                Compositor._renderSvgRegionTask,
                args=[svgData, srcPixelRect, tgtPixelDim])
            if isinstance(result, Exception):
                raise RuntimeError('Worker process encountered an exception when render SVG region') from result
                
            overlayImage = PIL.Image.frombytes('RGBA', tgtPixelDim, result)

            if tgtImage == None:
                # No target was specified to overlay the custom sector on so just return the
                # cropped and resized section of the source image.
                # NOTE: If no cropping or resizing performed a copy MUST be made as the source
                # image shouldn't be returned as something may delete it
                # NOTE: It's important to set tgtImage to srcImage to prevent it being deleted
                # in the finally clause
                tgtImage = overlayImage
            else:
                # Copy custom sector section over current tile using it's alpha channel as a mask
                tgtImage.paste(overlayImage, tgtPixelOffset, overlayImage)
        finally:
            if (overlayImage is not None) and (overlayImage is not tgtImage):
                del overlayImage

        return tgtImage

    @staticmethod
    def _createTextSvg(mapBytes: bytes) -> bytes:
        root = xml.etree.ElementTree.fromstring(mapBytes)
        element = root.find('{http://www.w3.org/2000/svg}g')
        Compositor._recursiveRemoveGraphics(element)
        return xml.etree.ElementTree.tostring(element=root)

    @staticmethod
    def _recursiveRemoveGraphics(
            element: xml.etree.ElementTree.Element
            ) -> None:
        for child in reversed(element):
            if child.tag == '{http://www.w3.org/2000/svg}g':
                Compositor._recursiveRemoveGraphics(child)
                if len(child) == 0:
                    element.remove(child)
            elif child.tag != '{http://www.w3.org/2000/svg}text':
                element.remove(child)

    # This function is executed in a worker process
    @staticmethod
    def _renderSvgTask(
        svgData: bytes
        ) -> typing.Union[bytes, Exception]:
        try:
            tree = cairosvg.parser.Tree(bytestring=svgData)
            width = int(tree['width'])
            height = int(tree['height'])

            output = io.BytesIO()
            surface = cairosvg.surface.PNGSurface(
                tree=tree,
                output=output,
                output_width=width,
                output_height=height,
                dpi=96.0)
            try:
                result = Compositor._convertBGRAToRGBA(
                    bgra=bytes(surface.cairo.get_data()),
                    width=width,
                    height=height)
                surface.finish()
            finally:
                del surface
        except Exception as ex:
            return ex

        return result

    # This function is executed in a worker process
    @staticmethod
    def _renderSvgRegionTask(
            svgData: bytes,
            srcPixelRect: typing.Tuple[int, int, int, int],
            tgtPixelDim: typing.Tuple[int, int],
            ) -> typing.Union[bytes, Exception]:
        try:
            tree = cairosvg.parser.Tree(bytestring=svgData)
            tree['viewBox'] = \
                f'{srcPixelRect[0]}, {srcPixelRect[1]}, {srcPixelRect[2] - srcPixelRect[0]}, {srcPixelRect[3] - srcPixelRect[1]}'

            output = io.BytesIO()
            surface = cairosvg.surface.PNGSurface(
                tree=tree,
                output=output,
                output_width=tgtPixelDim[0],
                output_height=tgtPixelDim[1],
                dpi=96.0)

            try:
                result = Compositor._convertBGRAToRGBA(
                    bgra=bytes(surface.cairo.get_data()),
                    width=tgtPixelDim[0],
                    height=tgtPixelDim[1])
                surface.finish()
            finally:
                del surface
        except Exception as ex:
            return ex

        return result

    @staticmethod
    def _convertBGRAToRGBA(
            bgra: bytes,
            width: int,
            height: int
            ) -> bytes:
        bgra = numpy.frombuffer(
            buffer=bgra,
            dtype=numpy.uint8)
        bgra.shape = (height, width, 4) # for RGBA
        b, g, r, a = bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2], bgra[:, :, 3]
        rgba = numpy.zeros(shape=bgra.shape, dtype=numpy.uint8)
        rgba[:, :, 0] = r
        rgba[:, :, 1] = g
        rgba[:, :, 2] = b
        rgba[:, :, 3] = a
        return rgba.tobytes()
