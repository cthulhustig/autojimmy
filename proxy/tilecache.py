import aiofiles
import aiofiles.os
import aiosqlite
import asyncio
import collections
import common
import datetime
import logging
import os
import proxy
import sqlite3
import travellermap
import uuid
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
_LoadAllMetadataQuery = \
    'SELECT query, mime, size, overlap, created, used FROM tile_cache;'
_LoadTileDataQuery = \
    'SELECT data FROM tile_cache WHERE query = :query;'
_DeleteTileQuery = \
    'DELETE FROM tile_cache WHERE query = :query;'
_DeleteExpiredTilesQuery = \
    'DELETE FROM tile_cache WHERE created <= :expiry;'
# TODO: Implement clearing tile cache when custom sectors or snapshot change
_DeleteAllQuery = 'DELETE FROM tile_cache;'

class TileCache(object):
    class _DbEntry(object):
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

    _GarbageCollectInterval = datetime.timedelta(seconds=60)
    _MaxDiskCacheSizeBytes = 1 * 1024 * 1024 * 1024 # 1GiB
    _MinDiskCacheReapBytes = 10 * 1024 * 1024 # 10MiB
    _MaxDiskCacheExpiryAge = datetime.timedelta(days=30)
    _TimestampFormat = '%Y-%m-%d %H:%M:%f'
    _TileCacheFileExtension = '.dat'    

    def __init__(
            self,
            database: aiosqlite.Connection,
            maxBytes: typing.Optional[int] # None means no max
            ) -> None:
        self._database = database
        self._maxBytes = maxBytes
        self._memCache: typing.OrderedDict[str, travellermap.MapImage] = collections.OrderedDict()
        self._memTotalBytes = 0
        self._dbCache: typing.Dict[str, TileCache._DbEntry] = {}
        self._dbTotalBytes = 0
        self._dbPendingAdds: typing.Set[str] = set() # Tile query strings of adds that are pending
        self._backgroundTasks: typing.Set[asyncio.Task] = set()
        self._garbageCollectTask = None

    async def initAsync(self) -> None:
        # Creating the table will be a no-op if it already exists
        # TODO: If I have table creation here it means any future migration is going to need to be here
        # which in turn means I probably need to have a separate schema version just for the table
        async with self._database.execute(_CreateTableQuery):
            pass
        logging.debug('Created tile cache table')

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

                self._dbCache[tileQuery] = TileCache._DbEntry(
                    tileQuery=tileQuery,
                    mapFormat=mapFormat,
                    fileSize=fileSize,
                    overlapType=overlapType,
                    createdTime=createdTime,
                    usedTime=usedTime)
                self._dbTotalBytes += fileSize

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

        self._dbCache.clear()
        self._dbTotalBytes = 0

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

        # Add the image to the cache, this will automatically add it at the end of the cache
        # to indicate it's the most recently used
        self._memCache[tileQuery] = tileImage
        self._memTotalBytes += size

        if cacheToDisk and (tileQuery not in self._dbPendingAdds):
            # Writing to the disk cache is done as a future so as not to block
            # the caller
            dbEntry = TileCache._DbEntry(
                tileQuery=tileQuery,
                mapFormat=tileImage.format(),
                fileSize=tileImage.size(),
                overlapType=overlapType,
                createdTime=common.utcnow())
            self._dbPendingAdds.add(tileQuery)            
            self._startBackgroundJob(
                coro=self._storeTileAsync(
                    dbEntry=dbEntry,
                    tileData=tileImage.bytes()))

    async def lookupAsync(self, tileQuery: str) -> typing.Optional[travellermap.MapImage]:
        # Check the memory cache first
        data = self._memCache.get(tileQuery)
        if data:
            # Move most recently used item to end of cache so it will be evicted last
            self._memCache.move_to_end(tileQuery, last=True)
            return data
        
        # Not in memory so check the disk cache
        dbEntry = self._dbCache.get(tileQuery)
        if dbEntry == None:
            return None # Tile isn't in disk cache or is in the process of being removed
        
        # Load cached file from disk
        try:
            queryArgs = {'query': tileQuery}
            async with self._database.execute(_LoadTileDataQuery, queryArgs) as cursor:
                results = await cursor.fetchone()
                data = results[0]
        except Exception as ex:
            # Something wen't wrong with loading the file so delete remove the file from
            # the disk cache to prevent anything trying to load it again in the future.
            # The check that it's still in the cache is important as in theory it could
            # have already been removed by another async task
            logging.warning(
                f'Failed to load cached tile data for {tileQuery}',
                exc_info=ex)            
            if tileQuery in self._dbCache:
                del self._dbCache[tileQuery]
            return None
        
        # Mark the disk tile as used so it will be at the back of the queue if tiles need
        # to be purged for space. An background task is started to push the update to the
        # database
        dbEntry.markUsed()
        self._startBackgroundJob(
            coro=self._updateTileUsedAsync(dbEntry=dbEntry))

        # Add the cached file to the memory cache, removing other items if
        # required to make space. It's important to specify that it shouldn't
        # be added to the disk cache as we know it's already there
        image = travellermap.MapImage(bytes=data, format=dbEntry.mapFormat())
        await self.addAsync(
            tileQuery=dbEntry.tileQuery(),
            tileImage=image,
            overlapType=dbEntry.overlapType(),
            cacheToDisk=False)
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
        self._dbPendingAdds.clear()

        # Remove tiles from the database
        async with self._database.execute(_DeleteAllQuery):
            pass
        await self._database.commit()

        # Clear details of the disk cache from memory.
        self._dbCache.clear()
        self._dbTotalBytes = 0
    
    # NOTE: This function is intended to be fire and forget so whatever async
    # stream of execution adds something to the cache isn't blocked waiting
    # for the file to be written and database updated. It should be noted that
    # doing this (at least theoretically) introduces the possibility that two
    # independent requests for the same tile may cause this function to be called
    # in parallel for the same key but mapping to different images objects (but
    # images of the same tile)
    async def _storeTileAsync(
            self,
            dbEntry: _DbEntry,
            tileData: bytes
            ) -> None:
        try:
            queryArgs = {
                'query': dbEntry.tileQuery(),
                'mime': travellermap.mapFormatToMimeType(format=dbEntry.mapFormat()),
                'size': dbEntry.fileSize(),
                'overlap': str(dbEntry.overlapType().name),
                'created': TileCache._timestampToString(timestamp=dbEntry.createdTime()),
                'used': TileCache._timestampToString(timestamp=dbEntry.usedTime()),
                'data': sqlite3.Binary(tileData)}
        
            async with self._database.execute(_AddTileQuery, queryArgs):
                pass
            await self._database.commit()

            # It's important that the in memory copy of what disk cache tiles are
            # available is updated AFTER the database has been updated. It's only
            # at this point is it safe for something to use the cached entry.
            self._dbCache[dbEntry.tileQuery()] = dbEntry
            self._dbTotalBytes += dbEntry.fileSize()
            logging.debug(f'Added tile {dbEntry.tileQuery()} to disk cache')
        except asyncio.CancelledError:
            # Cancellation is expected at shutdown so only log at debug
            logging.debug(
                f'Adding tile {dbEntry.tileQuery()} to the disk cache was cancelled')
        except Exception as ex:           
            # Log the exception here rather than letting it be caught and logged by
            # the async loop running the fire and forget function.
            logging.error(
                f'An error occurred while adding tile {dbEntry.tileQuery()} to the disk cache',
                exc_info=ex)
        finally:
            # No mater what happens, make sure we remove this tile form the list of
            # pending adds
            if dbEntry.tileQuery() in self._dbPendingAdds:
                self._dbPendingAdds.remove(dbEntry.tileQuery())
            
    # NOTE: This function is intended to be fire and forget so whatever async
    # stream of execution adds something to the cache isn't blocked waiting
    # for the file to be written and database updated. 
    async def _updateTileUsedAsync(
            self,
            dbEntry: _DbEntry
            ) -> None:
        try:
            queryArgs = {
                'query': dbEntry.tileQuery(),
                'used': TileCache._timestampToString(dbEntry.usedTime())}

            async with self._database.execute(_UpdateTileUsedQuery, queryArgs):
                pass
            await self._database.commit()

            logging.debug(
                f'Update last used time for tile {dbEntry.tileQuery()} to {dbEntry.usedTime()}')
        except asyncio.CancelledError:
            # Cancellation is expected at shutdown so only log at debug
            logging.debug(
                f'Updating tile {dbEntry.tileQuery()} last used time was cancelled')
        except Exception as ex:           
            # Log the exception here rather than letting it be caught and logged by
            # the async loop running the fire and forget function.
            logging.error(
                f'An error occurred while updating last used time of tile {dbEntry.tileQuery()}',
                exc_info=ex)
            
    async def _purgeForSpaceAsync(
            self,
            requiredBytes: int
            ) -> None:
        requiredBytes = min(requiredBytes, self._MinDiskCacheReapBytes)
        # TODO: Should probably log at debug
        logging.info(
            f'Purging tile disk cache entries to free {requiredBytes} bytes')
    
        # Create list of all disk tiles ordered by usage time, starting with
        # the most recently used
        metadataList = sorted(
            self._dbCache.values(),
            key=lambda dbEntry: dbEntry.usedTime().timestamp(),
            reverse=True)
        purgeAge = None
        while requiredBytes > 0:
            # Remove the tile that was used longest ago
            dbEntry = metadataList.pop()
            del self._dbCache[dbEntry.tileQuery()]
            self._dbTotalBytes -= dbEntry.fileSize()
            purgeAge = dbEntry.createdTime()

        # TODO: Finish me

    async def _purgeByAgeAsync(self) -> None:
        expiryTime = common.utcnow() - TileCache._MaxDiskCacheExpiryAge
        logging.debug(
            f'Purging tile disk cache entries up to {expiryTime}')
        
        # Remove expired entries from the in memory copy of the disk cache
        # contents. This needs to be done first to prevent another task
        # trying to read the tile wile it's being deleted
        expiredEntries: typing.List[TileCache._DbEntry] = []
        for tileQuery in list(self._dbCache.keys()):
            dbEntry = self._dbCache[tileQuery]

            # Used created time for this checking for tile age rather than
            # used time. The intention is all tiles will eventually be
            # purged even if they are getting used
            if dbEntry.createdTime() <= expiryTime:
                # TODO: Should probably log at debug
                logging.warning(
                    f'Purging expired tile disk cache entry for {dbEntry.tileQuery()} from {dbEntry.createdTime()}')

                # Remove from cache, this will prevent any further lookups from
                # loading the tile from the cache
                del self._dbCache[tileQuery]
                self._dbTotalBytes -= dbEntry.fileSize()
                expiredEntries.append(dbEntry)

        # Remove expired entries from database
        queryArgs = {'expiry': TileCache._timestampToString(timestamp=expiryTime)}
        async with self._database.execute(_DeleteExpiredTilesQuery, queryArgs):
            pass
        await self._database.commit()

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

        if task.done(): # TODO: Remove debug code
            print('Hmmmmm, I guess this can happen!!!!!!!!!!!!!!!!!')

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
            TileCache._TimestampFormat)
        return datetime.datetime.fromtimestamp(
            timestamp.timestamp(),
            tz=datetime.timezone.utc)
    
    @staticmethod
    def _timestampToString(timestamp: datetime.datetime) -> str:
        return timestamp.strftime(TileCache._TimestampFormat)