import aiosqlite
import asyncio
import collections
import common
import datetime
import logging
import proxy
import sqlite3
import travellermap
import typing

_SqliteCacheKiB = 51200 # 50MiB
# This is the best page size based on the average size of tile blobs
# https://www.sqlite.org/intern-v-extern-blob.html
_SqlitePageSizeBytes = 8192

_DatabaseSchemaVersion = 1

_ConfigTableName = 'config'
_TilesTableName = 'tiles'

_SchemaConfigKey = 'schema'
_UniverseTimestampConfigKey = 'universe_timestamp'
_CustomSectorTimestampConfigKey = 'custom_timestamp'
_MapUrlConfigKey = 'map_url'

# NOTE: Setting the page_size needs to be done before setting the journal_mode as
# it can't be changed after entering WAL mode
_SetDatabasePragmaScript = \
    f"""
PRAGMA cache_size = -{_SqliteCacheKiB};
PRAGMA page_size = {_SqlitePageSizeBytes};
PRAGMA synchronous = NORMAL;
PRAGMA journal_mode = WAL;
"""

_CreateConfigTableQuery = \
    f"""
CREATE TABLE IF NOT EXISTS {_ConfigTableName} (
    key TEXT NOT NULL PRIMARY KEY,
    value TEXT NOT NULL);
"""
_CreateTileTableQuery = \
    f"""
CREATE TABLE IF NOT EXISTS {_TilesTableName} (
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
_ReadConfigValue = \
    f'SELECT value FROM {_ConfigTableName} WHERE key = :key;'
_WriteConfigValue = \
    f'INSERT OR REPLACE INTO {_ConfigTableName} VALUES (:key, :value);'
_DeleteConfigValue = \
    f'DELETE FROM {_ConfigTableName} WHERE key = :key;'

_AddTileQuery = \
    f"""
    INSERT OR REPLACE INTO {_TilesTableName} VALUES (
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
_DropTilesTable = f'DROP TABLE {_TilesTableName};'
_UpdateTileUsedQuery = \
    f'UPDATE {_TilesTableName} SET used = :used WHERE query = :query AND used < :used;'
# When loading the metadata have it sorted by used time (oldest to newest) as it makes it
# easier to initialise the memory cache which is also kept in usage order
_LoadAllMetadataQuery = \
    f"""
    SELECT query, mime, size, milieu, x, y, width, height, scale, overlap, created, used
    FROM {_TilesTableName} ORDER BY used ASC;
"""
_LoadTileDataQuery = \
    f'SELECT data FROM {_TilesTableName} WHERE query = :query;'
_DeleteTileQuery = \
    f'DELETE FROM {_TilesTableName} WHERE query = :query;'
_DeleteExpiredTilesQuery = \
    f'DELETE FROM {_TilesTableName} WHERE created <= :expiry;'
_DeleteUniverseTilesQuery = \
    f'DELETE FROM {_TilesTableName} WHERE overlap != "complete"'
_DeleteAllTilesQuery = f'DELETE FROM {_TilesTableName};'

_OverlapTypeToDatabaseStringMap = {
    proxy.Compositor.OverlapType.NoOverlap: 'none',
    proxy.Compositor.OverlapType.PartialOverlap: 'partial',
    proxy.Compositor.OverlapType.CompleteOverlap: 'complete',
}
_DatabaseStringToOverlapTypeMap = {v: k for k, v in _OverlapTypeToDatabaseStringMap.items()}

_DatabaseTimestampFormat = '%Y-%m-%d %H:%M:%S.%f'

class TileCache(object):
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

    # TODO: Some of these should be configurable
    _MaxDbCacheSizeBytes = 1 * 1024 * 1024 * 1024 # 1GiB
    _MaxDbCacheExpiryAge = datetime.timedelta(days=7)
    _GarbageCollectInterval = datetime.timedelta(seconds=60)

    def __init__(
            self,
            travellerMapUrl: str,
            dbPath: str,
            maxMemBytes: typing.Optional[int] # None means no max
            ) -> None:
        self._travellerMapUrl = travellerMapUrl
        self._dbPath = dbPath
        self._dbConnection = None
        self._memCache: typing.OrderedDict[str, travellermap.MapImage] = collections.OrderedDict()
        self._memTotalBytes = 0
        self._memMaxBytes = maxMemBytes
        self._diskCache: typing.OrderedDict[str, TileCache._DiskEntry] = collections.OrderedDict()
        self._diskTotalBytes = 0
        self._diskPendingAdds: typing.Set[str] = set() # Tile query strings of adds that are pending
        self._backgroundTasks: typing.Set[asyncio.Task] = set()
        self._garbageCollectTask = None

    async def initAsync(self) -> None:
        logging.info(f'Connecting to tile cache database {self._dbPath}')

        try:
            self._dbConnection = await aiosqlite.connect(self._dbPath)

            async with self._dbConnection.executescript(_SetDatabasePragmaScript):
                pass

            if not await proxy.checkIfTableExistsAsync(
                    table=_ConfigTableName,
                    connection=self._dbConnection):
                logging.debug('Creating tile cache config table')
                async with self._dbConnection.execute(_CreateConfigTableQuery):
                    pass
                await self._writeConfigValueAsync(
                    key=_SchemaConfigKey,
                    value=_DatabaseSchemaVersion)
            else:
                schemaVersion = await self._readConfigValueAsync(
                    key=_SchemaConfigKey,
                    type=int)
                if schemaVersion != _DatabaseSchemaVersion:
                    logging.info(
                        'Recreating tile cache due to schema version change from {old} to {new})'.format(
                            old=schemaVersion,
                            new=_DatabaseSchemaVersion))
                    # The database schema doesn't match the expected schema. Drop the tiles
                    # table so it will be recreated with the correct structure
                    async with self._dbConnection.execute(_DropTilesTable):
                        pass

                    # Write the new schema version to the database
                    await self._writeConfigValueAsync(_SchemaConfigKey, _DatabaseSchemaVersion)

            if not await proxy.checkIfTableExistsAsync(
                    table=_TilesTableName,
                    connection=self._dbConnection):
                logging.debug('Creating tile cache table')
                async with self._dbConnection.execute(_CreateTileTableQuery):
                    pass

            logging.debug('Checking tile cache validity')
            await self._checkCacheValidityAsync()

            logging.debug('Loading tile cache table contents')
            invalidEntries = []
            async with self._dbConnection.execute(_LoadAllMetadataQuery) as cursor:
                results = await cursor.fetchall()
                for row in results:
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
                        createdTime = TileCache._stringToTimestamp(string=createdTime)
                    except Exception as ex:
                        logging.warning(
                            f'Found invalid tile cache entry for {tileQuery} (Error while parsing created timestamp)',
                            exc_info=ex)
                        invalidEntries.append(tileQuery)
                        continue

                    try:
                        usedTime = TileCache._stringToTimestamp(string=usedTime)
                    except Exception as ex:
                        logging.warning(
                            f'Found invalid tile cache entry for {tileQuery} (Error while parsing used timestamp)',
                            exc_info=ex)
                        invalidEntries.append(tileQuery)
                        continue

                    # NOTE: In order for items to be inserted into the ordered dict cache in the correct
                    # order, this assumes that the database query returns the rows ordered by used time
                    # (oldest to newest)
                    self._diskCache[tileQuery] = TileCache._DiskEntry(
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

            # Remove invalid entries from the database
            for tileQuery in invalidEntries:
                try:
                    queryArgs = {'query': tileQuery}
                    async with self._dbConnection.execute(_DeleteTileQuery, queryArgs):
                        pass
                    logging.debug(f'Deleted the invalid tile cache entry for {tileQuery}')
                except Exception as ex:
                    # Log and continue
                    logging.error(
                        f'An error occurred while deleting the invalid tile cache entry for {tileQuery}',
                        exc_info=ex)

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

        if cacheToDisk and (tileQuery not in self._diskPendingAdds):
            # Writing to the database is done as a future so as not to block the caller
            diskEntry = TileCache._DiskEntry(
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

    async def clearCacheAsync(self) -> None:
        logging.info('Clearing tile cache')

        # Clear the memory cache
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
        self._diskCache.clear()
        self._diskTotalBytes = 0

    async def _readConfigValueAsync(
            self,
            key: str,
            type: typing.Type[typing.Any],
            default: typing.Any = None
            ) -> None:
        queryArgs = {'key': key}
        async with self._dbConnection.execute(_ReadConfigValue, queryArgs) as cursor:
            row = await cursor.fetchone()
            if row == None:
                return default

            if type == datetime.datetime:
                return TileCache._stringToTimestamp(row[0])
            return type(row[0])

    async def _writeConfigValueAsync(
            self,
            key: str,
            value: typing.Any
            ) -> None:
        if isinstance(value, datetime.datetime):
            value = TileCache._timestampToString(timestamp=value)

        queryArgs = {'key': key, 'value': str(value)}
        async with self._dbConnection.execute(_WriteConfigValue, queryArgs):
            pass

    async def _deleteConfigValueAsync(
            self,
            key: str
            ) -> None:
        queryArgs = {'key': key}
        async with self._dbConnection.execute(_DeleteConfigValue, queryArgs):
            pass

    async def _checkCacheValidityAsync(self) -> None:
        # If the universe timestamp has changed then delete tiles that aren't
        # completely within a custom sector
        await self._checkKeyValidityAsync(
            configKey=_UniverseTimestampConfigKey,
            currentValueFn=travellermap.DataStore.instance().universeTimestamp,
            valueType=datetime.datetime,
            deleteQuery=_DeleteUniverseTilesQuery,
            identString='universe timestamp')

        # If the custom sector timestamp has changed then delete all tiles.
        # TODO: Ideally this would be more selective but it's not trivial
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

    async def _checkKeyValidityAsync(
            self,
            configKey: str,
            currentValueFn: typing.Callable[[], typing.Optional[typing.Any]],
            valueType: typing.Type[typing.Any],
            deleteQuery: str,
            identString: str
            ) -> None:
        try:
            cacheValue = await self._readConfigValueAsync(
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
        if (not cacheValue) or (not currentValue) or \
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

                if currentValue:
                    await self._writeConfigValueAsync(key=configKey, value=currentValue)
                else:
                    await self._deleteConfigValueAsync(key=configKey)
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
                'created': TileCache._timestampToString(timestamp=diskEntry.createdTime()),
                'used': TileCache._timestampToString(timestamp=diskEntry.usedTime()),
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
                'used': TileCache._timestampToString(diskEntry.usedTime())}

            async with self._dbConnection.execute(_UpdateTileUsedQuery, queryArgs):
                pass
            await self._dbConnection.commit()

            logging.debug(
                f'Update last used time for tile {diskEntry.tileQuery()} to {diskEntry.usedTime()}')
        except asyncio.CancelledError:
            # Cancellation is expected at shutdown so only log at debug
            logging.debug(
                f'Updating tile {diskEntry.tileQuery()} last used time was cancelled')
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
        while self._diskTotalBytes > TileCache._MaxDbCacheSizeBytes:
            _, diskEntry = self._diskCache.popitem(last=False)
            self._diskTotalBytes -= diskEntry.fileSize()
            queryArgs.append({'query': diskEntry.tileQuery()})

            # TODO: Should log at debug
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
        expiryTime = common.utcnow() - TileCache._MaxDbCacheExpiryAge
        logging.debug(
            f'Purging tile disk cache entries up to {expiryTime}')

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
            if diskEntry.createdTime() > expiryTime:
                continue # The entry hasn't expired

            # Remove entry from disk cache, this will prevent any further lookups from
            # loading the tile from the cache
            del self._diskCache[tileQuery]
            self._diskTotalBytes -= diskEntry.fileSize()
            purged += 1

            # TODO: This should be logged at debug
            logging.warning(
                f'Purged expired tile disk cache entry for {diskEntry.tileQuery()} from {diskEntry.createdTime()}')

        if not purged:
            return # Nothing was purged so nothing more to do

        # Remove expired tiles from the database
        try:
            queryArgs = {'expiry': TileCache._timestampToString(timestamp=expiryTime)}
            async with self._dbConnection.execute(_DeleteExpiredTilesQuery, queryArgs):
                pass
            await self._dbConnection.commit()
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            logging.error(
                f'An error occurred when purging disk cache entries up to {expiryTime}',
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

    @staticmethod
    def _stringToTimestamp(string: str) -> datetime.datetime:
        timestamp = datetime.datetime.strptime(
            string,
            _DatabaseTimestampFormat)
        return datetime.datetime.fromtimestamp(
            timestamp.timestamp(),
            tz=datetime.timezone.utc)

    @staticmethod
    def _timestampToString(timestamp: datetime.datetime) -> str:
        return timestamp.strftime(_DatabaseTimestampFormat)
