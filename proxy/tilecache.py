import asyncio
import collections
import common
import depschecker
import datetime
import logging
import proxy
import sqlite3
import travellermap
import typing

# v1 = Initial version
# v2 = SVG unicode font fix (not really a schema change but need to force regeneration)
# v3 = More selective splitting of text layer (not really a schema change but need to force regeneration)
_TileTableSchema = 3

_TileTableName = 'tile_cache'

_UniverseTimestampConfigKey = 'tile_cache_universe_timestamp'
_CustomSectorTimestampConfigKey = 'tile_cache_custom_timestamp'
_MapUrlConfigKey = 'tile_cache_map_url'
_SvgCompositionConfigKey = 'tile_cache_svg_composition'
_LibCairoSupportConfigKey = 'tile_cache_libcairo_support'
_SqliteCacheKiB = 51200 # 50MiB

_SetConnectionPragmaScript = \
    f"""
PRAGMA cache_size = -{_SqliteCacheKiB};
PRAGMA synchronous = NORMAL;
"""

_CreateTileTableQuery = \
    f"""
CREATE TABLE IF NOT EXISTS {_TileTableName} (
    query TEXT NOT NULL PRIMARY KEY,
    mime TEXT NOT NULL,
    size INTEGER NOT NULL,
    milieu TEXT NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    scale INTEGER NOT NULL,
    overlap TEXT NOT NULL CHECK(overlap IN ("none", "partial", "complete")),
    created DATETIME NOT NULL,
    used DATETIME NOT NULL,
    data BLOB NOT NULL);
"""

_AddTileQuery = \
    f"""
INSERT OR REPLACE INTO {_TileTableName} VALUES (
    :query,
    :mime,
    :size,
    :milieu,
    :x,
    :y,
    :width,
    :height,
    :scale,
    :overlap,
    :created,
    :used,
    :data);
"""

_UpdateTileUsedQuery = \
    f'UPDATE {_TileTableName} SET used = :used WHERE query = :query AND used < :used;'

# When loading the metadata have it sorted by used time (oldest to newest) as it makes it
# easier to initialise the memory cache which is also kept in usage order
_LoadAllMetadataQuery = \
    f"""
SELECT query, mime, size, milieu, x, y, width, height, scale, overlap, created, used
FROM {_TileTableName} ORDER BY used ASC;
"""

_LoadTileDataQuery = \
    f'SELECT data FROM {_TileTableName} WHERE query = :query;'

_DeleteTileQuery = \
    f'DELETE FROM {_TileTableName} WHERE query = :query;'

_DeleteExpiredTilesQuery = \
    f'DELETE FROM {_TileTableName} WHERE created <= :expiry;'

_DeleteStockTilesQuery = \
    f'DELETE FROM {_TileTableName} WHERE overlap != "complete"'

_DeleteCustomSectorTilesQuery = \
    f'DELETE FROM {_TileTableName} WHERE overlap != "none"'

_DeleteAllTilesQuery = f'DELETE FROM {_TileTableName};'

_OverlapTypeToDatabaseStringMap = {
    proxy.Compositor.OverlapType.NoOverlap: 'none',
    proxy.Compositor.OverlapType.PartialOverlap: 'partial',
    proxy.Compositor.OverlapType.CompleteOverlap: 'complete',
}
_DatabaseStringToOverlapTypeMap = {v: k for k, v in _OverlapTypeToDatabaseStringMap.items()}

class _DiskEntry(object):
    def __init__(
            self,
            tileQuery: str,
            mapFormat: travellermap.MapFormat,
            fileSize: int,
            tileMilieu: travellermap.milieu,
            tilePosition: typing.Tuple[int, int],
            tileDimensions: typing.Tuple[int, int],
            tileScale: int,
            overlapType: proxy.Compositor.OverlapType,
            createdTime: datetime.datetime,
            usedTime: typing.Optional[datetime.datetime] = None
            ) -> None:
        self._tileQuery = tileQuery
        self._mapFormat = mapFormat
        self._fileSize = fileSize
        self._tileMilieu = tileMilieu
        self._tilePosition = tilePosition
        self._tileDimensions = tileDimensions
        self._tileScale = tileScale
        self._overlapType = overlapType
        self._createdTimestamp = createdTime
        self._usedTimestamp = usedTime if usedTime != None else createdTime

    def tileQuery(self) -> str:
        return self._tileQuery

    def mapFormat(self) -> str:
        return self._mapFormat

    def fileSize(self) -> str:
        return self._fileSize

    def tileMilieu(self) -> travellermap.Milieu:
        return self._tileMilieu

    def tileX(self) -> int:
        return self._tilePosition[0]

    def tileY(self) -> int:
        return self._tilePosition[1]

    def tilePosition(self) -> typing.Tuple[int, int]:
        return self._tilePosition

    def tileWidth(self) -> int:
        return self._tileDimensions[0]

    def tileHeight(self) -> int:
        return self._tileDimensions[1]

    def tileDimensions(self) -> typing.Tuple[int, int]:
        return self._tileDimensions

    def tileScale(self) -> int:
        return self._tileScale

    def overlapType(self) -> proxy.Compositor.OverlapType:
        return self._overlapType

    def createdTime(self) -> datetime.datetime:
        return self._createdTimestamp

    def usedTime(self) -> datetime.datetime:
        return self._usedTimestamp

    def markUsed(self) -> None:
        self._usedTimestamp = common.utcnow()

class TileCache(object):
    _GarbageCollectInterval = datetime.timedelta(seconds=60)

    _TilesPerProgressStep = 100

    def __init__(
            self,
            travellerMapUrl: str,
            mapDatabase: proxy.Database,
            maxMemBytes: int,
            maxDiskBytes: int, # A value of 0 disables the disk cache
            tileLifetime: int, # A value of 0 disables eviction
            svgComposition: bool
            ) -> None:
        self._travellerMapUrl = travellerMapUrl
        self._mapDatabase = mapDatabase
        self._dbConnection = None
        self._memCache: typing.OrderedDict[str, travellermap.MapImage] = collections.OrderedDict()
        self._memTotalBytes = 0
        self._memMaxBytes = maxMemBytes
        self._diskCache: typing.OrderedDict[str, _DiskEntry] = collections.OrderedDict()
        self._diskTotalBytes = 0
        self._diskMaxBytes = maxDiskBytes
        self._diskPendingAdds: typing.Set[str] = set() # Tile query strings of adds that are pending
        self._tileLifetime = datetime.timedelta(days=tileLifetime) if tileLifetime != 0 else None
        self._svgComposition = svgComposition
        self._backgroundTasks: typing.Set[asyncio.Task] = set()
        self._garbageCollectTask = None

    async def initAsync(
            self,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        logging.info(f'Tile cache connecting to database')

        try:
            self._dbConnection = await self._mapDatabase.connectAsync(
                pragmaQuery=_SetConnectionPragmaScript)

            await proxy.createSchemaTableAsync(
                connection=self._dbConnection,
                tableName=_TileTableName,
                requiredSchema=_TileTableSchema,
                createTableQuery=_CreateTileTableQuery)

            logging.debug('Checking tile cache validity')
            await self._checkCacheValidityAsync()

            logging.debug('Loading tile cache table contents')
            invalidEntries = []
            async with self._dbConnection.execute(_LoadAllMetadataQuery) as cursor:
                results = await cursor.fetchall()
                progressStage = 'Loading Tile Cache'
                for progress, row in enumerate(results):
                    tileQuery = row[0]
                    mimeType = row[1]
                    fileSize = row[2]
                    tileMilieu = row[3]
                    tileX = row[4]
                    tileY = row[5]
                    tileWidth = row[6]
                    tileHeight = row[7]
                    tileScale = row[8]
                    overlapType = row[9]
                    createdTime = row[10]
                    usedTime = row[11]

                    if progressCallback and ((progress % TileCache._TilesPerProgressStep) == 0):
                        progressCallback(progressStage, progress, len(results))

                    mapFormat = travellermap.mimeTypeToMapFormat(mimeType=mimeType)
                    if not mapFormat:
                        logging.warning(f'Found invalid tile cache entry for {tileQuery} (Unsupported mime type {mimeType})')
                        invalidEntries.append(tileQuery)
                        continue

                    if overlapType not in _DatabaseStringToOverlapTypeMap:
                        logging.warning(f'Found invalid tile cache entry for {tileQuery} (Unknown overlap type {overlapType})')
                        invalidEntries.append(tileQuery)
                        continue
                    overlapType = _DatabaseStringToOverlapTypeMap[overlapType]

                    try:
                        createdTime = proxy.stringToDbTimestamp(string=createdTime)
                    except Exception as ex:
                        logging.warning(
                            f'Found invalid tile cache entry for {tileQuery} (Error while parsing created timestamp)',
                            exc_info=ex)
                        invalidEntries.append(tileQuery)
                        continue

                    try:
                        usedTime = proxy.stringToDbTimestamp(string=usedTime)
                    except Exception as ex:
                        logging.warning(
                            f'Found invalid tile cache entry for {tileQuery} (Error while parsing used timestamp)',
                            exc_info=ex)
                        invalidEntries.append(tileQuery)
                        continue

                    # NOTE: In order for items to be inserted into the ordered dict cache in the correct
                    # order, this assumes that the database query returns the rows ordered by used time
                    # (oldest to newest)
                    self._diskCache[tileQuery] = _DiskEntry(
                        tileQuery=tileQuery,
                        mapFormat=mapFormat,
                        fileSize=fileSize,
                        tileMilieu=tileMilieu,
                        tilePosition=(tileX, tileY),
                        tileDimensions=(tileWidth, tileHeight),
                        tileScale=tileScale,
                        overlapType=overlapType,
                        createdTime=createdTime,
                        usedTime=usedTime)
                    self._diskTotalBytes += fileSize

                if progressCallback:
                    progressCallback(progressStage, len(results), len(results))

            # Remove invalid entries from the database
            if invalidEntries:
                progressStage = 'Purging Tile Cache'
                for progress, tileQuery in enumerate(invalidEntries):
                    try:
                        if progressCallback and ((progress % TileCache._TilesPerProgressStep) == 0):
                            progressCallback(progressStage, progress, len(invalidEntries))

                        queryArgs = {'query': tileQuery}
                        async with self._dbConnection.execute(_DeleteTileQuery, queryArgs):
                            pass
                        logging.debug(f'Deleted the invalid tile cache entry for {tileQuery}')
                    except Exception as ex:
                        # Log and continue
                        logging.error(
                            f'An error occurred while deleting the invalid tile cache entry for {tileQuery}',
                            exc_info=ex)

                if progressCallback:
                    # Force 100% progress notification
                    progressCallback('Complete', len(invalidEntries), len(invalidEntries))

            # Commit all changes to the database
            await self._dbConnection.commit()

            self._garbageCollectTask = asyncio.ensure_future(self._garbageCollectAsync())
        except:
            # If something goes wrong call shutdown to tidy up. This is important as something
            # needs to close the database connection (if it exists) otherwise the process won't
            # exit causing the main app to lock up on shutdown
            await self.shutdownAsync()
            raise

    async def shutdownAsync(self) -> None:
        # Wait for all background tasks to finish
        while self._backgroundTasks:
            task = next(iter(self._backgroundTasks))
            try:
                await task
            except Exception as ex:
                logging.error(
                    'An error occurred while waiting for tile cache background tasks to complete',
                    exc_info=ex)

        if self._garbageCollectTask:
            self._garbageCollectTask.cancel()
            self._garbageCollectTask = None

        if self._dbConnection:
            await self._dbConnection.close()
            self._dbConnection = None

        self._memCache.clear()
        self._memTotalBytes = 0

        self._diskCache.clear()
        self._diskTotalBytes = 0

    async def addAsync(
            self,
            tileQuery: str,
            tileImage: travellermap.MapImage,
            tileMilieu: str,
            tilePosition: typing.Tuple[int, int],
            tileDimensions: typing.Tuple[int, int],
            tileScale: int,
            overlapType: proxy.Compositor.OverlapType,
            cacheToDisk: bool = True
            ) -> None:
        if tileQuery in self._memCache:
            # The tile is already cached so nothing to do
            return

        size = tileImage.size()

        startingBytes = self._memTotalBytes
        evictionCount = 0
        while self._memCache and ((self._memTotalBytes + size) > self._memMaxBytes):
            # The item at the start of the cache is the one that was used longest ago
            _, oldData = self._memCache.popitem(last=False)
            evictionCount += 1
            self._memTotalBytes -= len(oldData)
            assert(self._memTotalBytes >= 0)

        if evictionCount:
            evictionBytes = startingBytes - self._memTotalBytes
            logging.debug(f'Tile cache evicted {evictionCount} tiles for {evictionBytes} bytes')

        # Add the image to the cache, this will automatically add it at the end of the ordered dict
        # to indicate it's the most recently used
        self._memCache[tileQuery] = tileImage
        self._memTotalBytes += size

        if cacheToDisk and (self._diskMaxBytes > 0) and (tileQuery not in self._diskPendingAdds):
            # Writing to the database is done as a future so as not to block the caller
            diskEntry = _DiskEntry(
                tileQuery=tileQuery,
                mapFormat=tileImage.format(),
                fileSize=tileImage.size(),
                tileMilieu=tileMilieu,
                tilePosition=tilePosition,
                tileDimensions=tileDimensions,
                tileScale=tileScale,
                overlapType=overlapType,
                createdTime=common.utcnow())
            self._diskPendingAdds.add(tileQuery)
            self._startBackgroundJob(
                coro=self._storeTileAsync(
                    diskEntry=diskEntry,
                    tileData=tileImage.bytes()))

    async def lookupAsync(self, tileQuery: str) -> typing.Optional[travellermap.MapImage]:
        # Check the memory cache first
        data = self._memCache.get(tileQuery)
        if data:
            # Move most recently used item to end of cache so it will be evicted last
            self._memCache.move_to_end(tileQuery, last=True)
            return data

        if self._diskMaxBytes <= 0:
            return None # Disk cache is disabled

        # Not in memory so check the database cache
        diskEntry = self._diskCache.get(tileQuery)
        if diskEntry == None:
            return None # Tile isn't in database cache

        # Load cached file from disk
        try:
            queryArgs = {'query': tileQuery}
            async with self._dbConnection.execute(_LoadTileDataQuery, queryArgs) as cursor:
                row = await cursor.fetchone()
                data = row[0]
        except Exception as ex:
            # Something went wrong with loading the tile from the disk cache. Remove the
            # entry from memory to prevent anything trying to load it again in the future.
            # The check that it's still in the cache is important as in theory it could
            # have already been removed by another async task
            logging.warning(
                f'Failed to load cached tile data for {tileQuery}',
                exc_info=ex)
            if tileQuery in self._diskCache:
                del self._diskCache[tileQuery]
            return None

        # Add the cached file to the memory cache, removing other items if
        # required to make space.
        image = travellermap.MapImage(bytes=data, format=diskEntry.mapFormat())
        await self.addAsync(
            tileQuery=diskEntry.tileQuery(),
            tileImage=image,
            tileMilieu=diskEntry.tileMilieu(),
            tilePosition=diskEntry.tilePosition(),
            tileDimensions=diskEntry.tileDimensions(),
            tileScale=diskEntry.tileScale(),
            overlapType=diskEntry.overlapType(),
            cacheToDisk=False) # Already on disk so no need to add it

        # Mark the disk entry as used and kick of a background job to push the update
        # to the database
        diskEntry.markUsed()
        self._startBackgroundJob(
            coro=self._updateTileUsedAsync(diskEntry=diskEntry))

        # Move the disk entry to the end of the cache so it will be purged last if
        # space is required
        self._diskCache.move_to_end(tileQuery, last=True)

        return image

    async def clearCacheAsync(
            self
            ) -> (int, int): # (Memory Tile Count, Disk Tile Count)
        logging.info('Clearing tile cache')

        # Clear the memory cache
        memTileCount = len(self._memCache)
        self._memCache.clear()
        self._memTotalBytes = 0

        # Cancel any background operations
        for task in self._backgroundTasks:
            task.cancel()
        self._backgroundTasks.clear()
        self._diskPendingAdds.clear()

        # Remove tiles from the database
        async with self._dbConnection.execute(_DeleteAllTilesQuery):
            pass
        await self._dbConnection.commit()

        # Clear details of the database cache from memory.
        diskTileCount = len(self._diskCache)
        self._diskCache.clear()
        self._diskTotalBytes = 0

        return (memTileCount, diskTileCount)

    async def _checkCacheValidityAsync(self) -> None:
        # If the universe timestamp has changed then delete tiles that aren't
        # completely within a custom sector
        await self._checkKeyValidityAsync(
            configKey=_UniverseTimestampConfigKey,
            currentValueFn=travellermap.DataStore.instance().universeTimestamp,
            valueType=datetime.datetime,
            deleteQuery=_DeleteStockTilesQuery,
            identString='universe timestamp')

        # If the custom sector timestamp has changed then delete all tiles.
        # TODO: Ideally this would only delete tiles that touch custom sectors
        # that have changed (added, deleted, modified) but it's not trivial
        await self._checkKeyValidityAsync(
            configKey=_CustomSectorTimestampConfigKey,
            currentValueFn=travellermap.DataStore.instance().customSectorsTimestamp,
            valueType=datetime.datetime,
            deleteQuery=_DeleteAllTilesQuery,
            identString='custom sector timestamp')

        # If the map host has changed delete all tiles
        await self._checkKeyValidityAsync(
            configKey=_MapUrlConfigKey,
            currentValueFn=lambda: self._travellerMapUrl,
            valueType=str,
            deleteQuery=_DeleteAllTilesQuery,
            identString='map url')

        # If the SVG composition setting has changed, delete all tiles that overlap
        # a custom sector
        await self._checkKeyValidityAsync(
            configKey=_SvgCompositionConfigKey,
            currentValueFn=lambda: self._svgComposition,
            valueType=bool,
            deleteQuery=_DeleteCustomSectorTilesQuery,
            identString='SVG composition')

        # If the state of Cairo support has changed:
        # - if cairo is working, delete all tiles that intersect stock sectors,
        # this removes any tiles that were cached while SVG support wasn't
        # available but should now be rendered using custom sectors.
        # - If cairo is not working, delete all tiles that intersect custom
        # sectors, this prevents inconsistencies where old tiles have been
        # rendered with SVG support but new tiles are not.
        #
        # This whole check is a bit of a corner case for situations where cairo
        # is working, then not working then working again.
        cairoEnabled = depschecker.DetectedCairoSvgState == \
            depschecker.CairoSvgState.Working
        if cairoEnabled:
            deleteQuery = _DeleteStockTilesQuery
        else:
            deleteQuery = _DeleteCustomSectorTilesQuery
        await self._checkKeyValidityAsync(
            configKey=_LibCairoSupportConfigKey,
            currentValueFn=lambda: cairoEnabled,
            valueType=bool,
            deleteQuery=deleteQuery,
            identString='libcairo status')

    async def _checkKeyValidityAsync(
            self,
            configKey: str,
            currentValueFn: typing.Callable[[], typing.Optional[typing.Any]],
            valueType: typing.Type[typing.Any],
            deleteQuery: str,
            identString: str
            ) -> None:
        try:
            cacheValue = await proxy.readDbMetadataAsync(
                connection=self._dbConnection,
                key=configKey,
                type=valueType)
        except Exception as ex:
            # Log and continue if unable to read map timestamp. Assume that cache is invalid
            logging.error(
                'An exception occurred when reading the {key} entry from the tile cache config'.format(
                    key=configKey),
                exc_info=ex)
            cacheValue = None

        try:
            # TODO: Ideally this would be async
            currentValue = currentValueFn()
        except Exception as ex:
            # Log and continue if unable to read the current un
            logging.error(
                'An exception occurred when reading the current {ident}'.format(
                    ident=identString),
                exc_info=ex)
            currentValue = None

        # Delete tiles from the the disk cache if either of the values couldn't
        # be read or the value stored in the database is not an exact match for
        # the current value
        if (cacheValue is None) or (currentValue is None) or \
                (cacheValue != currentValue):
            logging.info(
                'Tile cache detected {ident} change (Current: {current}, Cached: {cached})'.format(
                    ident=identString,
                    current=currentValue,
                    cached=cacheValue))

            try:
                async with self._dbConnection.execute(deleteQuery) as cursor:
                    if cursor.rowcount:
                        logging.info(
                            'Purged {count} tiles from the tile cache due to {ident} change'.format(
                                count=cursor.rowcount,
                                ident=identString))

                if currentValue is not None:
                    await proxy.writeDbMetadataAsync(
                        connection=self._dbConnection,
                        key=configKey,
                        value=currentValue)
                else:
                    await proxy.deleteDbMetadataAsync(
                        connection=self._dbConnection,
                        key=configKey)
            except Exception as ex:
                logging.error(
                    'An exception occurred when purging tiles from tile cache due to {ident} change'.format(
                        ident=identString),
                    exc_info=ex)

    # NOTE: This function is intended to be fire and forget so whatever async
    # stream of execution adds something to the cache isn't blocked waiting
    # for the file to be written and database updated. It should be noted that
    # doing this (at least theoretically) introduces the possibility that two
    # independent requests for the same tile may cause this function to be called
    # in parallel for the same key but mapping to different images objects (but
    # images of the same tile)
    async def _storeTileAsync(
            self,
            diskEntry: _DiskEntry,
            tileData: bytes
            ) -> None:
        try:
            queryArgs = {
                'query': diskEntry.tileQuery(),
                'mime': travellermap.mapFormatToMimeType(format=diskEntry.mapFormat()),
                'size': diskEntry.fileSize(),
                'milieu': diskEntry.tileMilieu().value,
                'x': diskEntry.tileX(),
                'y': diskEntry.tileY(),
                'width': diskEntry.tileWidth(),
                'height': diskEntry.tileHeight(),
                'scale': diskEntry.tileScale(),
                'overlap': _OverlapTypeToDatabaseStringMap[diskEntry.overlapType()],
                'created': proxy.dbTimestampToString(timestamp=diskEntry.createdTime()),
                'used': proxy.dbTimestampToString(timestamp=diskEntry.usedTime()),
                'data': sqlite3.Binary(tileData)}

            async with self._dbConnection.execute(_AddTileQuery, queryArgs):
                pass
            await self._dbConnection.commit()

            # It's important that the database cache is only updated AFTER the tile has
            # been written to the database. It's not until that point that it's safe for
            # a lookup to try and load the tile
            self._diskCache[diskEntry.tileQuery()] = diskEntry
            self._diskTotalBytes += diskEntry.fileSize()
            logging.debug(f'Added tile {diskEntry.tileQuery()} to disk cache')
        except asyncio.CancelledError:
            # Cancellation is expected at shutdown so only log at debug
            logging.debug(
                f'Adding tile {diskEntry.tileQuery()} to the disk cache was cancelled')
            raise
        except Exception as ex:
            # Log the exception here rather than letting it be caught and logged by
            # the async loop running the fire and forget function.
            logging.error(
                f'An error occurred while adding tile {diskEntry.tileQuery()} to the disk cache',
                exc_info=ex)
        finally:
            # No mater what happens, make sure we remove this tile form the list of
            # pending adds
            if diskEntry.tileQuery() in self._diskPendingAdds:
                self._diskPendingAdds.remove(diskEntry.tileQuery())

    # NOTE: This function is intended to be fire and forget so whatever async
    # stream of execution adds something to the cache isn't blocked waiting
    # for the file to be written and database updated.
    async def _updateTileUsedAsync(
            self,
            diskEntry: _DiskEntry
            ) -> None:
        try:
            queryArgs = {
                'query': diskEntry.tileQuery(),
                'used': proxy.dbTimestampToString(diskEntry.usedTime())}

            async with self._dbConnection.execute(_UpdateTileUsedQuery, queryArgs):
                pass
            await self._dbConnection.commit()

            logging.debug(
                f'Update last used time for tile {diskEntry.tileQuery()} to {diskEntry.usedTime()}')
        except asyncio.CancelledError:
            # Cancellation is expected at shutdown so only log at debug
            logging.debug(
                f'Updating tile {diskEntry.tileQuery()} last used time was cancelled')
            raise
        except Exception as ex:
            # Log the exception here rather than letting it be caught and logged by
            # the async loop running the fire and forget function.
            logging.error(
                f'An error occurred while updating last used time of tile {diskEntry.tileQuery()}',
                exc_info=ex)

    async def _purgeForSpaceAsync(self) -> None:
        logging.debug('Purging tile disk cache entries to free space')

        # Remove expired tiles from the disk cache. This assumes the disk cache
        # is maintained in order of last usage (oldest to newest).
        queryArgs = []
        while self._diskTotalBytes > self._diskMaxBytes:
            _, diskEntry = self._diskCache.popitem(last=False)
            self._diskTotalBytes -= diskEntry.fileSize()
            queryArgs.append({'query': diskEntry.tileQuery()})

            logging.warning(
                f'Purged tile disk cache entry for {diskEntry.tileQuery()} to free {diskEntry.fileSize()} bytes')

        if not queryArgs:
            return # Nothing was purged so nothing more to do

        # Remove expired tiles from the database
        try:
            async with self._dbConnection.executemany(_DeleteTileQuery, queryArgs):
                pass
            await self._dbConnection.commit()
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            logging.error(
                'An error occurred when purging tile cache entries to free space',
                exc_info=ex)

    async def _purgeByAgeAsync(self) -> None:
        if self._tileLifetime is None:
            logging.debug(
                f'Purging tile disk cache entries by age is disabled')
            return

        purgeTime = common.utcnow() - self._tileLifetime
        logging.debug(
            f'Purging tile disk cache entries up to {purgeTime}')

        # Remove expired tiles from the disk cache
        purged = 0
        for tileQuery in list(self._diskCache.keys()):
            diskEntry = self._diskCache.get(tileQuery)
            if not diskEntry:
                # Something else must have removed the entry while this task
                # was running
                continue

            # Check if the disk entry has expired. The creation time is used
            # for this as the intention is all entries should be purged eventually
            if diskEntry.createdTime() > purgeTime:
                continue # The entry hasn't expired

            # Remove entry from disk cache, this will prevent any further lookups from
            # loading the tile from the cache
            del self._diskCache[tileQuery]
            self._diskTotalBytes -= diskEntry.fileSize()
            purged += 1

            logging.debug(
                f'Purged expired tile disk cache entry for {diskEntry.tileQuery()} from {diskEntry.createdTime()}')

        if not purged:
            return # Nothing was purged so nothing more to do

        # Remove expired tiles from the database
        try:
            queryArgs = {'expiry': proxy.dbTimestampToString(timestamp=purgeTime)}
            async with self._dbConnection.execute(_DeleteExpiredTilesQuery, queryArgs):
                pass
            await self._dbConnection.commit()
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            logging.error(
                f'An error occurred when purging disk cache entries up to {purgeTime}',
                exc_info=ex)

    async def _garbageCollectAsync(self) -> None:
        nextRunTime = common.utcnow() + TileCache._GarbageCollectInterval

        while True:
            logging.debug('Running garbage collection')

            try:
                await self._purgeByAgeAsync()
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                logging.warning(
                    'Garbage collector failed to purge expired cache entries',
                    exc_info=ex)

            try:
                await self._purgeForSpaceAsync()
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                logging.warning(
                    'Garbage collector failed to purge change entries for space',
                    exc_info=ex)

            sleepTime = nextRunTime.timestamp() - common.utcnow().timestamp()
            if sleepTime > 0:
                await asyncio.sleep(sleepTime)
            nextRunTime += TileCache._GarbageCollectInterval

    def _startBackgroundJob(
            self,
            coro: typing.Coroutine[typing.Any, typing.Any, typing.Any]
            ) -> None:
        task = asyncio.ensure_future(self._doBackgroundJobAsync(coro))
        self._backgroundTasks.add(task)

    async def _doBackgroundJobAsync(
            self,
            routine: typing.Coroutine[typing.Any, typing.Any, typing.Any]
            ) -> None:
        try:
            await routine
        finally:
            # Mo mater what happens, make sure the task is removed from the
            # list of background tasks
            currentTask = asyncio.current_task()
            if currentTask in self._backgroundTasks:
                self._backgroundTasks.remove(currentTask)
