# TODO: Need to handle cairo dll not being found
import cairosvg
import cairosvg.parser
import cairosvg.surface
import enum
import io
import logging
import math
import numpy
import PIL.Image
import travellermap
import typing
import threading
import xml.etree.ElementTree

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
    def __init__(
            self,
            mapImage: travellermap.MapImage,
            scale: int
            ) -> None:
        self._scale = scale
        self._mainImage = None
        self._textImage = None

        mapBytes = mapImage.bytes()
        mapFormat = mapImage.format()
        if mapFormat == travellermap.MapFormat.SVG:    
            self._mainImage = CompositorImage._createImage(
                mapBytes=mapBytes,
                mapFormat=mapFormat)     

            textSvg = CompositorImage._createTextSvg(mapBytes=mapBytes)            
            self._textImage = CompositorImage._createImage(
                mapBytes=textSvg,
                mapFormat=mapFormat)
        else:
            self._mainImage = CompositorImage._createImage(
                mapBytes=mapBytes,
                mapFormat=mapFormat)
            
    def mainImage(self) -> PIL.Image.Image:
        return self._mainImage

    def textImage(self) -> PIL.Image.Image:
        return self._textImage
    
    def scale(self) -> int:
        return self._scale
    
    def __lt__(self, other: 'CompositorImage') -> bool:
        if self.__class__ is other.__class__:
            return self.scale() > other.scale()
        return NotImplemented
    
    def __del__(self):
        if self._mainImage:
            self._mainImage.close()
            del self._mainImage

        if self._textImage:
            self._textImage.close()
            del self._textImage

    @staticmethod
    def _createTextSvg(mapBytes: bytes) -> bytes:
        root = xml.etree.ElementTree.fromstring(mapBytes)
        element = root.find('{http://www.w3.org/2000/svg}g')
        CompositorImage._recursiveRemoveGraphics(element)
        return xml.etree.ElementTree.tostring(element=root)

    @staticmethod
    def _recursiveRemoveGraphics(
            element: xml.etree.ElementTree.Element
            ) -> None:
        for child in reversed(element):
            if child.tag == '{http://www.w3.org/2000/svg}g':
                CompositorImage._recursiveRemoveGraphics(child)
                if len(child) == 0:
                    element.remove(child)
            elif child.tag != '{http://www.w3.org/2000/svg}text':
                element.remove(child)    

    # I found that when having cairosvg render from multiple threads simultaneously (on Windows) it
    # could result in it throwing an GDI exception. I assume it's got some kind of shared resource
    # or resource limit somewhere
    _cairoLock = threading.Lock()

    @staticmethod
    def _createImage(
            mapBytes: bytes,
            mapFormat: travellermap.MapFormat
            ) -> PIL.Image.Image:
        if mapFormat != travellermap.MapFormat.SVG:
            # The map image is something other than SVG so use PIL to load it

            # Image.load isn't thread safe so make sure to call it now so it doesn't get called
            # when cropping the image during composition
            # https://github.com/python-pillow/Pillow/issues/4848
            image = PIL.Image.open(io.BytesIO(mapBytes))
            try:
                image.load()
            except:
                image.close()
                raise
            return image
        
        # The image is an SVG so generate two images, one containing the full tile and the other
        # containing just the text on a transparent background
        width, height = _extractSvgSize(mapBytes)
        output = io.BytesIO()
        
        with CompositorImage._cairoLock:
            surface = cairosvg.surface.PNGSurface(
                tree=cairosvg.parser.Tree(bytestring=mapBytes),
                output=output,
                output_width=width,
                output_height=height,
                dpi=96.0)
            try:
                bgra = numpy.frombuffer(
                    buffer=bytes(surface.cairo.get_data()),
                    dtype=numpy.uint8)
                surface.finish()
            finally:
                del surface

        # Convert cairo BGRA pixels to PIL RGBA
        bgra.shape = (height, width, 4) # for RGBA
        b, g, r, a = bgra[:,:,0], bgra[:,:,1], bgra[:,:,2], bgra[:,:,3]
        rgba = numpy.zeros(
            shape=(height, width, 4),
            dtype=numpy.uint8)
        rgba[:,:,0] = r
        rgba[:,:,1] = g
        rgba[:,:,2] = b
        rgba[:,:,3] = a

        return PIL.Image.frombytes('RGBA', (width, height), rgba.tobytes())

class _CustomSector(object):
    def __init__(
            self,
            name: str,
            position: typing.Tuple[int, int],
            mapPosters: typing.Iterable[CompositorImage]
            ) -> None:
        self._name = name
        self._position = position
        self._mapPosters = sorted(mapPosters)

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

    # Returned rect is in map space and ordered (left, top, right, bottom)
    def boundingRect(self) -> typing.Tuple[float, float, float, float]:
        return self._boundingRect
    
    # Returned rect is in map space and ordered (left, top, right, bottom)
    def interiorRect(self) -> typing.Tuple[float, float, float, float]:
        return self._interiorRect    

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

    # This seems to be the point where things stop being that visible and Traveller Map starts showing
    # the galaxy overlay. If the requested tile has a scale lower than this then there isn't any point
    # in compositing.
    _MinCompositionScale = 4

    def __init__(
            self,
            customMapsDir: str
            ) -> OverlapType:
        self._customMapsDir = customMapsDir
        self._milieuSectorMap: typing.Dict[travellermap.Milieu, typing.List[_CustomSector]] = {}

        self._loadCustomUniverse()

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
            tileText: typing.Optional[PIL.Image.Image],
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
            Compositor._overlayCustomSector(
                srcImage=mapPoster.mainImage(),
                srcPixelRect=srcPixelRect,
                tgtPixelDim=tgtPixelDim,
                tgtPixelOffset=tgtPixelOffset,
                tgtImage=tileImage)
            
        # Overlay custom sector text on tile
        for mapPoster, srcPixelRect, tgtPixelDim, tgtPixelOffset in overlappedSectors:
            textImage = mapPoster.textImage()
            if textImage:
                Compositor._overlayCustomSector(
                    srcImage=textImage,
                    srcPixelRect=srcPixelRect,
                    tgtPixelDim=tgtPixelDim,
                    tgtPixelOffset=tgtPixelOffset,
                    tgtImage=tileImage)

        if tileText and overlappedSectors:
            # Overlay original tile text layer over the top of the tile to fill in any text that
            # was overwritten by custom sector tiles
            tileImage.paste(tileText, (0, 0), tileText)

        return tileImage
    
    def fullOverlap(
            self,
            tileX: float,
            tileY: float,
            tileScale: float,
            milieu: travellermap.Milieu
            ) -> PIL.Image.Image:
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
            tileImage = Compositor._overlayCustomSector(
                srcImage=mapPoster.mainImage(),
                srcPixelRect=srcPixelRect,
                tgtPixelDim=tgtPixelDim,
                tgtPixelOffset=(0, 0))
            
            # Overlay custom sector text on tile
            textImage = mapPoster.textImage()
            if textImage:
                Compositor._overlayCustomSector(
                    srcImage=textImage,
                    srcPixelRect=srcPixelRect,
                    tgtPixelDim=tgtPixelDim,
                    tgtPixelOffset=(0, 0),
                    tgtImage=tileImage)
                
            return tileImage

        return None

    # TODO: Loading this stuff takes to long, it's still going after the main app has finished loading and
    # the user is ready to start loading the map widget
    def _loadCustomUniverse(self) -> None:
        self._milieuSectorMap.clear()

        for milieu in travellermap.Milieu:
            sectors = []
            for sectorInfo in travellermap.DataStore.instance().sectors(milieu=milieu):
                if not sectorInfo.isCustomSector():
                    continue # Only interested in custom sectors

                mapLevels = sectorInfo.customMapLevels()
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
                        mapImages.append(CompositorImage(mapImage=mapImage, scale=scale))
                    except Exception as ex:
                        logging.warning(f'Compositor failed to load scale {scale} map image for {sectorInfo.canonicalName()}', exc_info=ex)
                        continue

                sectors.append(_CustomSector(
                    name=sectorInfo.canonicalName(),
                    position=(sectorInfo.x(), sectorInfo.y()),
                    mapPosters=mapImages))

            self._milieuSectorMap[milieu] = sectors

    @staticmethod
    def _overlayCustomSector(
            srcImage: PIL.Image.Image,
            srcPixelRect: typing.Tuple[int, int, int, int],
            tgtPixelDim: typing.Tuple[int, int],
            tgtPixelOffset: typing.Tuple[int, int],
            tgtImage: typing.Optional[PIL.Image.Image] = None
            ) -> PIL.Image.Image: # Returns the target if specified otherwise returns the cropped and resized section of the source image  
        overlayImage = srcImage
        srcPixelDim = (
            srcPixelRect[2] - srcPixelRect[0],
            srcPixelRect[3] - srcPixelRect[1])
        croppedImage = None
        resizedImage = None
        try:
            # Crop the source image if required
            if ((overlayImage.width != srcPixelDim[0]) or (overlayImage.height != srcPixelDim[1])):
                croppedImage = overlayImage.crop(srcPixelRect)
                overlayImage = croppedImage

            # Scale the source image if required
            if (overlayImage.width != tgtPixelDim[0]) or (overlayImage.height != tgtPixelDim[1]):
                resizedImage = overlayImage.resize(
                    tgtPixelDim,
                    resample=PIL.Image.Resampling.BICUBIC)
                overlayImage = resizedImage

            if tgtImage == None:
                # No target was specified to overlay the custom sector on so just return the
                # cropped and resized section of the source image.
                # NOTE: If no cropping or resizing performed a copy MUST be made as the source
                # image shouldn't be returned as something may delete it
                # NOTE: It's important to set tgtImage to srcImage to prevent it being deleted
                # in the finally clause
                tgtImage = overlayImage if overlayImage is not srcImage else overlayImage.copy()
            else:
                # Copy custom sector section over current tile using it's alpha channel as a mask
                tgtImage.paste(overlayImage, tgtPixelOffset, overlayImage)
        finally:
            if (croppedImage != None) and (croppedImage is not tgtImage):
                croppedImage.close()
                del croppedImage
            if (resizedImage != None) and (resizedImage is not tgtImage):
                resizedImage.close()
                del resizedImage

        return tgtImage