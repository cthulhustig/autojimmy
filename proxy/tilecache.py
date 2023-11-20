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

# TODO: Not sure if overlap can be defined to only have specific values
# TODO: I don't like the fact I'm using the enum names as the overlap value, should have table specific values that get mapped
_CreateTableQuery = \
"""
CREATE TABLE IF NOT EXISTS tile_cache (
    query TEXT PRIMARY KEY,
    mime TEXT,
    size INTEGER,
    overlap TEXT,
    created DATETIME,
    used DATETIME,
    data BLOB);
"""
_AddTileQuery = \
    'INSERT OR REPLACE INTO tile_cache VALUES (:query, :mime, :size, :overlap, :created, :used, :data);'
_UpdateTileUsedQuery = \
    'UPDATE tile_cache SET used = :used WHERE query = :query AND used < :used;'
# When loading the metadata have it sorted by used time (oldest to newest) as it makes it
# easier to initialise the memory cache which is also kept in usage order
_LoadAllMetadataQuery = \
    'SELECT query, mime, size, overlap, created, used FROM tile_cache ORDER BY used ASC;'
_LoadTileDataQuery = \
    'SELECT data FROM tile_cache WHERE query = :query;'
_DeleteTileQuery = \
    'DELETE FROM tile_cache WHERE query = :query;'
_DeleteExpiredTilesQuery = \
    'DELETE FROM tile_cache WHERE created <= :expiry;'
# TODO: Implement clearing tile cache when custom sectors or snapshot change
_DeleteAllQuery = 'DELETE FROM tile_cache;'

class TileCache(object):
    class _DiskEntry(object):
        def __init__(
                self,
                tileQuery: str,
                mapFormat: travellermap.MapFormat,
                fileSize: int,
                overlapType: proxy.Compositor.OverlapType,
                createdTime: datetime.datetime,
                usedTime: typing.Optional[datetime.datetime] = None
                ) -> None:
            self._tileQuery = tileQuery
            self._mapFormat = mapFormat
            self._fileSize = fileSize
            self._overlapType = overlapType
            self._createdTimestamp = createdTime
            self._usedTimestamp = usedTime if usedTime != None else createdTime

        def tileQuery(self) -> str:
            return self._tileQuery
        
        def mapFormat(self) -> str:
            return self._mapFormat
        
        def fileSize(self) -> str:
            return self._fileSize
        
        def overlapType(self) -> proxy.Compositor.OverlapType:
            return self._overlapType
        
        def createdTime(self) -> datetime.datetime:
            return self._createdTimestamp

        def usedTime(self) -> datetime.datetime:
            return self._usedTimestamp
        
        def markUsed(self) -> None:
            self._usedTimestamp = common.utcnow()

    # TODO: Restore correct values
    _MaxDbCacheSizeBytes = 1 * 1024 * 1024 * 1024 # 1GiB
    _MaxDbCacheExpiryAge = datetime.timedelta(days=7)
    _DbTimestampFormat = '%Y-%m-%d %H:%M:%f'
    _GarbageCollectInterval = datetime.timedelta(seconds=60)

    def __init__(
            self,
            database: aiosqlite.Connection,
            maxBytes: typing.Optional[int] # None means no max
            ) -> None:
        self._database = database
        self._maxBytes = maxBytes
        self._memCache: typing.OrderedDict[str, travellermap.MapImage] = collections.OrderedDict()
        self._memTotalBytes = 0
        self._diskCache: typing.OrderedDict[str, TileCache._DiskEntry] = collections.OrderedDict()
        self._diskTotalBytes = 0
        self._diskPendingAdds: typing.Set[str] = set() # Tile query strings of adds that are pending
        self._backgroundTasks: typing.Set[asyncio.Task] = set()
        self._garbageCollectTask = None

    # TODO: This should probably periodically compact the database to save space
    async def initAsync(self) -> None:
        # Creating the table will be a no-op if it already exists
        # TODO: If I have table creation here it means any future migration is going to need to be here
        # which in turn means I probably need to have a separate schema version just for the table
        logging.debug('Setting up tile cache table')
        async with self._database.execute(_CreateTableQuery):
            pass

        logging.debug('Loading tile cache table contents')
        invalidEntries = []
        async with self._database.execute(_LoadAllMetadataQuery) as cursor:
            results = await cursor.fetchall()
            for tileQuery, mimeType, fileSize, overlapType, createdTime, usedTime in results:
                mapFormat = travellermap.mimeTypeToMapFormat(mimeType=mimeType)
                if not mapFormat:
                    logging.warning(f'Found invalid tile cache entry for {tileQuery} (Unsupported mime type {mimeType})')
                    invalidEntries.append(tileQuery)
                    continue

                if overlapType not in proxy.Compositor.OverlapType.__members__:
                    logging.warning(f'Found invalid tile cache entry for {tileQuery} (Unknown overlap type {overlapType})')
                    invalidEntries.append(tileQuery)
                    continue
                overlapType = proxy.Compositor.OverlapType.__members__[overlapType]

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
                    overlapType=overlapType,
                    createdTime=createdTime,
                    usedTime=usedTime)
                self._diskTotalBytes += fileSize

        # Remove invalid entries from the database
        if invalidEntries:
            for tileQuery in invalidEntries:
                try:
                    queryArgs = {'query': tileQuery}
                    async with self._database.execute(_DeleteTileQuery, queryArgs):
                        pass
                    # TODO: Should be logged at info or debug
                    logging.warning(f'Deleted the invalid tile cache entry for {tileQuery}')                             
                except Exception as ex:
                    # Log and continue
                    logging.error(
                        f'An error occurred while deleting the invalid tile cache entry for {tileQuery}',
                        exc_info=ex)
            await self._database.commit()

        self._garbageCollectTask = asyncio.ensure_future(self._garbageCollectAsync())
                
    async def shutdownAsync(self) -> None:
        # TODO: Not sure if this should close tasks or await them
        while self._backgroundTasks:
            task = next(iter(self._backgroundTasks))
            try:
                await task
            except Exception as ex:
                print(str(ex)) # TODO: Not sure if this should log or just ignore
        """
        for task in self._backgroundTasks:
            task.cancel()
        self._backgroundTasks.clear()
        self._diskPendingAdds.clear()
        """

        if self._garbageCollectTask:
            self._garbageCollectTask.cancel()

        self._memCache.clear()
        self._memTotalBytes = 0

        self._diskCache.clear()
        self._diskTotalBytes = 0

    async def addAsync(
            self,
            tileQuery: str,
            tileImage: travellermap.MapImage,
            overlapType: proxy.Compositor.OverlapType,
            cacheToDisk: bool = True
            ) -> None:
        if tileQuery in self._memCache:
            # The tile is already cached so nothing to do
            return

        size = tileImage.size()

        startingBytes = self._memTotalBytes
        evictionCount = 0
        while self._memCache and ((self._memTotalBytes + size) > self._maxBytes):
            # The item at the start of the cache is the one that was used longest ago
            _, oldData = self._memCache.popitem(last=False) # TODO: Double check last is correct (it's VERY important)
            evictionCount += 1
            self._memTotalBytes -= len(oldData)
            assert(self._memTotalBytes > 0)

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
            async with self._database.execute(_LoadTileDataQuery, queryArgs) as cursor:
                results = await cursor.fetchone()
                data = results[0]
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
            overlapType=diskEntry.overlapType(),
            cacheToDisk=False) # Already on disk
        
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
        async with self._database.execute(_DeleteAllQuery):
            pass
        await self._database.commit()

        # Clear details of the database cache from memory.
        self._diskCache.clear()
        self._diskTotalBytes = 0
    
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
                'overlap': str(diskEntry.overlapType().name),
                'created': TileCache._timestampToString(timestamp=diskEntry.createdTime()),
                'used': TileCache._timestampToString(timestamp=diskEntry.usedTime()),
                'data': sqlite3.Binary(tileData)}
                    
            async with self._database.execute(_AddTileQuery, queryArgs):
                pass
            await self._database.commit()

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

            async with self._database.execute(_UpdateTileUsedQuery, queryArgs):
                pass
            await self._database.commit()

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
        # TODO: Should probably log at debug
        logging.warning('Purging tile disk cache entries to free space')

        # Remove expired tiles from the disk cache. This assumes the disk cache
        # is maintained in order of last usage (oldest to newest).
        queryArgs = []
        while self._diskTotalBytes > TileCache._MaxDbCacheSizeBytes:
            _, diskEntry = self._diskCache.popitem(last=False) # TODO: Double check last is correct (it's VERY important)
            self._diskTotalBytes -= diskEntry.fileSize()
            queryArgs.append({'query': diskEntry.tileQuery()})

            # TODO: Should log at debug
            logging.warning(
                f'Purged tile disk cache entry for {diskEntry.tileQuery()} to free {diskEntry.fileSize()} bytes')   

        if not queryArgs:
            return # Nothing was purged so nothing more to do

        # Remove expired tiles from the database
        try:
            async with self._database.executemany(_DeleteTileQuery, queryArgs):
                pass
            await self._database.commit()
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
            async with self._database.execute(_DeleteExpiredTilesQuery, queryArgs):
                pass
            await self._database.commit()
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
            TileCache._DbTimestampFormat)
        return datetime.datetime.fromtimestamp(
            timestamp.timestamp(),
            tz=datetime.timezone.utc)
    
    @staticmethod
    def _timestampToString(timestamp: datetime.datetime) -> str:
        return timestamp.strftime(TileCache._DbTimestampFormat)