_HasSvgSupport = True
try:
    import cairosvg
    import cairosvg.parser
    import cairosvg.surface
except Exception as ex:
    _HasSvgSupport = False

import aiosqlite
import asyncio
import common
import concurrent.futures
import datetime
import enum
import io
import logging
import math
import multiprocessing
import PIL.Image
import proxy
import re
import sqlite3
import travellermap
import typing
import xml.etree.ElementTree

_LayersTableSchema = 1
_LayersTableName = 'layers_cache'

_CustomSectorTimestampConfigKey = 'layers_cache_custom_timestamp'

_SetConnectionPragmaScript = \
"""
PRAGMA synchronous = NORMAL;
"""

_CreateLayersTableQuery = \
f"""
CREATE TABLE IF NOT EXISTS {_LayersTableName} (
    name TEXT NOT NULL,
    milieu TEXT NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    scale INTEGER NOT NULL,
    created DATETIME NOT NULL,
    map BLOB NOT NULL,
    text BLOB NOT NULL);
"""

_LoadLayersQuery = \
f"""
SELECT map, text
FROM {_LayersTableName}
WHERE milieu = :milieu AND x = :x AND y = :y AND scale = :scale;
"""

_AddLayersQuery = \
f"""
INSERT INTO {_LayersTableName} VALUES (
    :name,
    :milieu,
    :x,
    :y,
    :scale,
    :created,
    :map,
    :text);
"""

_DeleteAllLayersQuery = f'DELETE FROM {_LayersTableName};'

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

class _CompositorImage(object):
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

    def __lt__(self, other: '_CompositorImage') -> bool:
        if self.__class__ is other.__class__:
            return self.scale() > other.scale()
        return NotImplemented

    def __del__(self):
        if self._imageType == _CompositorImage.ImageType.Bitmap:
            if self._mainImage:
                self._mainImage.close()

            if self._textMask:
                self._textMask.close()

class _CustomSector(object):
    def __init__(
            self,
            name: str,
            position: typing.Tuple[int, int],
            mapPosters: typing.Optional[typing.Iterable[_CompositorImage]] = None
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
            poster: _CompositorImage
            ) -> None:
        self._mapPosters.append(poster)
        self._mapPosters.sort() # Sorting is important for map selection algorithm

    def findMapPoster(
            self,
            scale: typing.Union[int, float]
            ) -> typing.Optional[_CompositorImage]:
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
            svgComposition: bool,
            customMapsDir: str,
            mapDatabase: proxy.Database
            ) -> OverlapType:
        self._svgComposition = svgComposition
        self._customMapsDir = customMapsDir
        self._mapDatabase = mapDatabase
        self._milieuSectorMap: typing.Dict[travellermap.Milieu, typing.List[_CustomSector]] = {}
        self._processExecutor = None

        if _HasSvgSupport:
            # Construct the pool of processes that can be used for SVG rendering.
            # A context is used so we can force processes to be spawned, this keeps the behaviour
            # the same on all OS and avoids issues with singletons when using fork
            mpContext = multiprocessing.get_context('spawn')
            self._processExecutor = concurrent.futures.ProcessPoolExecutor(
                mp_context=mpContext)

    async def initAsync(
            self,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        self._milieuSectorMap.clear()

        logging.info(f'Compositor connecting to database')
        connection = await self._mapDatabase.connectAsync(
            pragmaQuery=_SetConnectionPragmaScript)
        
        futureList: typing.List[asyncio.Future] = []
        try:
            await proxy.createSchemaTableAsync(
                connection=connection,
                tableName=_LayersTableName,
                requiredSchema=_LayersTableSchema,
                createTableQuery=_CreateLayersTableQuery)
            
            logging.debug('Checking compositor layers validity')
            await self._checkCacheValidityAsync(connection=connection)            

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
                            # TODO: Ideally this would by async
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
                        future = asyncio.ensure_future(self._addSectorImageAsync(
                            customSector=customSector,
                            milieu=milieu,
                            scale=scale,
                            mapImage=mapImage,
                            connection=connection))
                        futureList.append(future)

                if milieuSectors:
                    self._milieuSectorMap[milieu] = milieuSectors

            # Wait for futures adding compositor images to the sectors to complete
            progressStage = 'Processing Custom Sectors'
            completeCount = 0

            if progressCallback:
                progressCallback(progressStage, completeCount, len(futureList))

            for future in asyncio.as_completed(futureList):
                await future
                completeCount += 1
                if progressCallback:
                    progressCallback(progressStage, completeCount, len(futureList))

            # Commit any changes made to the database
            await connection.commit()
        except:
            # Cancel any futures that have been created
            for future in futureList:
                future.cancel()
        finally:
            await connection.close()

            # If full SVG rendering is disabled the process poll won't be used any more so may
            # as well shut it down
            if not self._svgComposition:
                self._processExecutor.shutdown(wait=True, cancel_futures=True)
                self._processExecutor = None

    # NOTE: Shutting down the executor is important as otherwise the app hangs on shutdown
    async def shutdownAsync(self):
        if self._processExecutor:
            self._processExecutor.shutdown(wait=True, cancel_futures=True)
            self._processExecutor = None

    def overlapType(
            self,
            tileX: float,
            tileY: float,
            tileScale: float,
            milieu: travellermap.Milieu
            ) -> OverlapType:
        if tileScale < Compositor._MinCompositionScale:
            return Compositor.OverlapType.NoOverlap

        sectorList = self._milieuSectorMap.get(milieu)
        if not sectorList:
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

        for sector in sectorList:
            sectorMapRect = sector.interiorRect()
            if _isContained(tileMapRect, sectorMapRect):
                return Compositor.OverlapType.CompleteOverlap

        for sector in sectorList:
            sectorMapRect = sector.boundingRect()
            intersection = _calculateIntersection(sectorMapRect, tileMapRect)
            if intersection is None:
                continue

            pixelWidth = round((intersection[2] - intersection[0]) * tileScale)
            pixelHeight = round((intersection[3] - intersection[1]) * tileScale)    
            if pixelWidth > 0 and pixelHeight > 0:
                return Compositor.OverlapType.PartialOverlap

        return Compositor.OverlapType.NoOverlap

    async def partialOverlapAsync(
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

        sectorList = self._milieuSectorMap.get(milieu)
        if not sectorList:
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
            _CompositorImage, # Map poster for custom sector that overlaps tile
            typing.Tuple[int, int, int, int], # Custom sector rect to copy
            typing.Tuple[int, int], # Size to scale section of custom sector to
            typing.Tuple[int, int], # Tile offset to place scaled section of custom sector
            ]] = []
        for sector in sectorList:
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
            if mapPoster.imageType() == _CompositorImage.ImageType.SVG:
                await self._overlaySvgCustomSectorAsync(
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
                if mapPoster.imageType() == _CompositorImage.ImageType.SVG:
                    await self._overlaySvgCustomSectorAsync(
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

    async def fullOverlapAsync(
            self,
            tileX: float,
            tileY: float,
            tileScale: float,
            milieu: travellermap.Milieu
            ) -> typing.Optional[PIL.Image.Image]:
        if tileScale < Compositor._MinCompositionScale:
            return None # Nothing to do (shouldn't happen if correctly checking which operation to use)

        sectorList = self._milieuSectorMap.get(milieu)
        if not sectorList:
            return None # Nothing to do (shouldn't happen if correctly checking which operation to use)

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
            if mapPoster.imageType() == _CompositorImage.ImageType.SVG:
                tileImage = await self._overlaySvgCustomSectorAsync(
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
                if mapPoster.imageType() == _CompositorImage.ImageType.SVG:
                    await self._overlaySvgCustomSectorAsync(
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
    
    async def _checkCacheValidityAsync(
            self,
            connection: aiosqlite.Connection
            ) -> None:
        # If the custom sector timestamp has changed then delete all tiles.
        # TODO: Ideally this would only delete tiles that touch custom sectors
        # that have changed (added, deleted, modified) but it's not trivial
        await self._checkKeyValidityAsync(
            connection=connection,
            configKey=_CustomSectorTimestampConfigKey,
            currentValueFn=travellermap.DataStore.instance().customSectorsTimestamp,
            valueType=datetime.datetime,
            deleteQuery=_DeleteAllLayersQuery,
            identString='custom sector timestamp')

    async def _checkKeyValidityAsync(
            self,
            connection: aiosqlite.Connection,
            configKey: str,
            currentValueFn: typing.Callable[[], typing.Optional[typing.Any]],
            valueType: typing.Type[typing.Any],
            deleteQuery: str,
            identString: str
            ) -> None:
        try:
            cacheValue = await proxy.readDbMetadataAsync(
                connection=connection,
                key=configKey,
                type=valueType)
        except Exception as ex:
            # Log and continue if unable to read map timestamp. Assume that cache is invalid
            logging.error(
                'An exception occurred when the compositor was reading the {key} entry layers cache config'.format(
                    key=configKey),
                exc_info=ex)
            cacheValue = None

        try:
            # TODO: Ideally this would be async
            currentValue = currentValueFn()
        except Exception as ex:
            # Log and continue if unable to read the current un
            logging.error(
                'An exception occurred when the compositor was reading the current {ident}'.format(
                    ident=identString),
                exc_info=ex)
            currentValue = None

        # Delete tiles from the the disk cache if either of the values couldn't
        # be read or the value stored in the database is not an exact match for
        # the current value
        if (not cacheValue) or (not currentValue) or \
                (cacheValue != currentValue):
            logging.info(
                'Compositor detected {ident} change (Current: {current}, Cached: {cached})'.format(
                    ident=identString,
                    current=currentValue,
                    cached=cacheValue))

            try:
                async with connection.execute(deleteQuery) as cursor:
                    if cursor.rowcount:
                        logging.info(
                            'Compositor purged {count} entries from the layers cache due to {ident} change'.format(
                                count=cursor.rowcount,
                                ident=identString))

                if currentValue:
                    await proxy.writeDbMetadataAsync(
                        connection=connection,
                        key=configKey,
                        value=currentValue)
                else:
                    await proxy.deleteDbMetadataAsync(
                        connection=connection,
                        key=configKey)
            except Exception as ex:
                logging.error(
                    'An exception occurred when the compositor was purging the layers cache due to {ident} change'.format(
                        ident=identString),
                    exc_info=ex)
                
    async def _addSectorImageAsync(
            self,
            customSector: _CustomSector,
            milieu: travellermap.Milieu,
            scale: int,
            mapImage: travellermap.MapImage,
            connection: aiosqlite.Connection
            ) -> None:
        try:
            mapBytes = mapImage.bytes()
            mapFormat = mapImage.format()

            if mapFormat == travellermap.MapFormat.SVG:
                if self._svgComposition:
                    customSector.addMapPoster(_CompositorImage(
                        imageType=_CompositorImage.ImageType.SVG,
                        mainImage=mapBytes,
                        textMask=Compositor._createTextSvg(mapBytes=mapBytes),
                        scale=scale))
                else:
                    sectorPosition = customSector.position()
                    queryArgs = {
                        'milieu': milieu.value,
                        'x': sectorPosition[0],
                        'y': sectorPosition[1],
                        'scale': scale}
                    async with connection.execute(_LoadLayersQuery, queryArgs) as cursor:
                        row = await cursor.fetchone()
                        if row:
                            mapBytes = row[0]
                            maskBytes = row[1]
                            customSector.addMapPoster(_CompositorImage(
                                imageType=_CompositorImage.ImageType.Bitmap,
                                mainImage=PIL.Image.open(io.BytesIO(mapBytes)),
                                textMask=PIL.Image.open(io.BytesIO(maskBytes)),
                                scale=scale))
                            return

                    svgMapBytes = mapImage.bytes()
                    svgTextBytes = Compositor._createTextSvg(mapBytes=svgMapBytes)

                    loop = asyncio.get_running_loop()
                    mapTask = loop.run_in_executor(
                        self._processExecutor,
                        Compositor._renderSvgTask,
                        svgMapBytes)
                    textTask = loop.run_in_executor(
                        self._processExecutor,
                        Compositor._renderSvgTask,
                        svgTextBytes)

                    await asyncio.gather(mapTask, textTask)

                    mapBytes = mapTask.result()
                    if isinstance(mapBytes, Exception):
                        raise RuntimeError('Worker process exception when render map SVG') from mapBytes

                    textBytes = textTask.result()
                    if isinstance(textBytes, Exception):
                        raise RuntimeError('Worker process exception when render text SVG') from textBytes

                    mainImage = PIL.Image.open(io.BytesIO(mapBytes))
                    textImage = PIL.Image.open(io.BytesIO(textBytes))
                    textMask = textImage.split()[-1] # Extract alpha channel as Image
                    del textImage

                    customSector.addMapPoster(_CompositorImage(
                        imageType=_CompositorImage.ImageType.Bitmap,
                        mainImage=mainImage,
                        textMask=textMask,
                        scale=scale))
                    
                    sectorPosition = customSector.position()
                    queryArgs = {
                        'name': customSector.name(),
                        'milieu': milieu.value,
                        'x': sectorPosition[0],
                        'y': sectorPosition[1],
                        'scale': scale,
                        'created': proxy.dbTimestampToString(timestamp=common.utcnow()),
                        'map': sqlite3.Binary(mapBytes),
                        'text': sqlite3.Binary(textBytes)}
                    async with connection.execute(_AddLayersQuery, queryArgs):
                        pass                           
            else:
                customSector.addMapPoster(_CompositorImage(
                    imageType=_CompositorImage.ImageType.Bitmap,
                    mainImage=PIL.Image.open(io.BytesIO(mapBytes)),
                    textMask=None,
                    scale=scale))
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            logging.warning(f'Compositor failed to generate {scale} composition image for {customSector.name()} in {milieu.value}', exc_info=ex)

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

    async def _overlaySvgCustomSectorAsync(
            self,
            svgData: bytes,
            srcPixelRect: typing.Tuple[int, int, int, int],
            tgtPixelDim: typing.Tuple[int, int],
            tgtPixelOffset: typing.Tuple[int, int],
            tgtImage: typing.Optional[PIL.Image.Image] = None
            ) -> PIL.Image.Image: # Returns the target if specified otherwise returns the cropped and resized section of the source image
        overlayImage = None
        try:
            assert(self._processExecutor)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                self._processExecutor,
                Compositor._renderSvgRegionTask,
                svgData,
                srcPixelRect,
                tgtPixelDim)
            if isinstance(result, Exception):
                raise RuntimeError('Worker process encountered an exception when render SVG region') from result

            overlayImage = PIL.Image.open(io.BytesIO(result))

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
                tgtImage.paste(overlayImage, tgtPixelOffset, overlayImage if overlayImage.mode == 'RGBA' else None)
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
            result = Compositor._renderSvgTree(
                svgTree=tree,
                tgtPixelDim=(width, height))
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
            Compositor._clipSvgTree(svgTree=tree, srcPixelRect=srcPixelRect)

            tree['viewBox'] = \
                f'{srcPixelRect[0]}, {srcPixelRect[1]}, {srcPixelRect[2] - srcPixelRect[0]}, {srcPixelRect[3] - srcPixelRect[1]}'
            tree['clip'] = \
                f'{srcPixelRect[0]} {srcPixelRect[1]} {srcPixelRect[2]} {srcPixelRect[3]}'
            
            result = Compositor._renderSvgTree(
                svgTree=tree,
                tgtPixelDim=tgtPixelDim)
        except Exception as ex:
            return ex

        return result

    # NOTE: Clipping assumes the tree is for a 32x40 hex poster image
    _TranslationRegex = re.compile(r'translate\((.+),\s*(.+)\)\s+scale\(1.1547 1\)')
    @staticmethod
    def _clipSvgTree(
            svgTree: cairosvg.parser.Tree,
            srcPixelRect: typing.Tuple[int, int, int, int]
            ) -> None:
        hexWidth = int(svgTree['width']) / 32
        hexHeight = int(svgTree['height']) / 40

        # Calculate the rect to use when clip world groups. The rect is in a local hex
        # coordinate system used by the SVGs generated by Traveller Map. The rect is
        # expanded by 2 hexes horizontally in each direction to avoid clipping adjacent
        # worlds with long names where the start/end of the text extends over the area
        # being rendered. It's expanded by 1 hex vertically in each direction to avoid
        # things getting clipped due to rounding errors and floating point comparisons
        clipMinX = (srcPixelRect[0] / hexWidth) - 2
        clipMinY = ((srcPixelRect[1] / hexHeight) - 40) - 1
        clipMaxX = (srcPixelRect[2] / hexWidth) + 2
        clipMaxY = ((srcPixelRect[3] / hexHeight) - 40) + 1

        for child in svgTree.children:
            if child.tag != 'g':
                continue
            newChildren = []
            for possible in child.children:
                if possible.tag != 'g':
                    newChildren.append(possible)
                    continue

                transform = possible.get('transform')
                if transform is None:
                    newChildren.append(possible)
                    continue

                translation = re.match(Compositor._TranslationRegex, transform)
                if not translation:
                    newChildren.append(possible)
                    continue

                try:
                    translationX = float(translation.group(1))
                    translationY = float(translation.group(2))
                except:
                    newChildren.append(possible)
                    continue

                if (translationX < clipMinX) or (translationX > clipMaxX) or \
                    (translationY < clipMinY) or (translationY > clipMaxY):
                    continue

                newChildren.append(possible)

            child.children = newChildren

    @staticmethod
    def _renderSvgTree(
            svgTree: cairosvg.parser.Tree,
            tgtPixelDim: typing.Tuple[int, int],
            ) -> bytes:
        # Usa a PNGSurface to render the SVG to a bitmap of the required size
        output = io.BytesIO()
        surface = cairosvg.surface.PNGSurface(
            tree=svgTree,
            output=output,
            output_width=tgtPixelDim[0],
            output_height=tgtPixelDim[1],
            dpi=96.0,
            map_rgba=Compositor._mapColour)

        # Use a PIL Image to convert the bitmap to a PNG. This is done rather than
        # using PNGSurface to generate the PNG as I found using it resulted in a 
        # green tint around text at some zoom levels. Using PIL also appears to be
        # slightly faster (at least on my machine)
        image = PIL.Image.frombytes(
            'RGBA',
            tgtPixelDim,
            surface.cairo.get_data())
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.read()
    
    @staticmethod
    def _mapColour(
            colour: typing.Tuple[int, int, int, int]
            ) -> typing.Tuple[int, int, int, int]:
        return (colour[2], colour[1], colour[0], colour[3])