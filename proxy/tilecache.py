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
import travellermap
import uuid
import typing

_CreateTableQuery = \
"""
CREATE TABLE IF NOT EXISTS tile_cache (
    query TEXT PRIMARY KEY,
    mime TEXT,
    file TEXT,
    size INTEGER,
    overlap TEXT,
    created DATETIME,
    used DATETIME);
"""
_AddTileQuery = \
"""
INSERT OR REPLACE INTO tile_cache(query, mime, file, size, overlap, created, used) VALUES (
    "{0}", "{1}", "{2}", "{3}", "{4}", "{5}", "{6}");
"""
_UpdateTileUsedQuery = \
"""
UPDATE tile_cache SET used="{1}" WHERE query = "{0}" AND used < "{1}";
"""
_LoadTilesQuery = \
"""
SELECT * FROM tile_cache;
"""
_DeleteTileQuery = \
"""
DELETE FROM tile_cache WHERE query = "{0}";
"""
_DeleteExpiredTilesQuery = \
"""
DELETE FROM tile_cache WHERE created <= "{0}";
"""
# TODO: Implement clearing tile cache when custom sectors or snapshot change
_DeleteAllTilesQuery = \
"""
DELETE FROM tile_cache;
"""

class TileCache(object):
    class _DiskTile(object):
        def __init__(
                self,
                tileQuery: str,
                mapFormat: travellermap.MapFormat,
                fileName: str,
                fileSize: int,
                overlapType: proxy.Compositor.OverlapType,
                createdTime: datetime.datetime,
                usedTime: typing.Optional[datetime.datetime] = None
                ) -> None:
            self._tileQuery = tileQuery
            self._mapFormat = mapFormat
            self._fileName = fileName
            self._fileSize = fileSize
            self._overlapType = overlapType
            self._createdTimestamp = createdTime
            self._usedTimestamp = usedTime if usedTime != None else createdTime

        def tileQuery(self) -> str:
            return self._tileQuery
        
        def mapFormat(self) -> str:
            return self._mapFormat
        
        def fileName(self) -> str:
            return self._fileName
        
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
            cacheDir: str,
            maxBytes: typing.Optional[int] # None means no max
            ) -> None:
        self._database = database
        self._cacheDir = cacheDir
        self._maxBytes = maxBytes
        self._memCache: typing.OrderedDict[str, travellermap.MapImage] = collections.OrderedDict()
        self._memTotalBytes = 0
        self._diskCache: typing.Dict[str, TileCache._DiskTile] = {}
        self._diskTotalBytes = 0
        self._diskPendingAdds: typing.Set[str] = set() # Tile query strings of adds that are pending
        self._backgroundTasks: typing.Set[asyncio.Task] = set()
        self._garbageCollectTask = None

    async def initAsync(self) -> None:
        # Creating the table will be a no-op if it already exists
        # TODO: If I have table creation here it means any future migration is going to need to be here
        # which in turn means I probably need to have a separate schema version just for the table
        async with self._database.executescript(_CreateTableQuery) as cursor:
            logging.debug('Created tile cache table')

        startTime = common.utcnow() # TODO: Remove debug code

        # Get a list of all files in the cache directory
        cacheFiles = set(await aiofiles.os.listdir(self._cacheDir))

        # TODO: Remove debug code once I've tried with a LOT of files
        finishTime = common.utcnow()
        print(f'Cache file list took {finishTime - startTime}!!!!!!!!!!!!!!!!!!!!!')

        logging.debug('Loading tile cache table contents')
        invalidEntries = []
        referencedFiles = set()
        async with self._database.execute(_LoadTilesQuery) as cursor:
            results = await cursor.fetchall()
            for tileQuery, mimeType, fileName, fileSize, overlapType, createdTime, usedTime in results:
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

                if fileName not in cacheFiles:
                    logging.warning(
                        f'Found invalid tile cache entry for {tileQuery} (Cache file {fileName} doesn\'t exist)')
                    invalidEntries.append(tileQuery)
                    continue                

                self._diskCache[tileQuery] = TileCache._DiskTile(
                    tileQuery=tileQuery,
                    mapFormat=mapFormat,
                    fileName=fileName,
                    fileSize=fileSize,
                    overlapType=overlapType,
                    createdTime=createdTime,
                    usedTime=usedTime)
                self._diskTotalBytes += fileSize
                referencedFiles.add(fileName)

        # Remove invalid entries from the database
        for tileQuery in invalidEntries:
            try:
                query = _DeleteTileQuery.format(tileQuery)
                async with self._database.executescript(query) as cursor:
                    pass
                # TODO: Should be logged at info or debug
                logging.warning(f'Deleted the invalid tile cache entry for {tileQuery}')                             
            except Exception as ex:
                # Log and continue
                logging.error(
                    f'An error occurred while deleting the invalid tile cache entry for {tileQuery}',
                    exc_info=ex)
                
        # Remove cache files not referenced by the database
        for fileName in cacheFiles:
            if fileName in referencedFiles:
                continue # File is referenced by database so nothing to do
            _, extension = os.path.splitext(fileName)
            if extension == TileCache._TileCacheFileExtension:
                continue # Not a cache file so ignore it
            filePath = os.path.join(self._cacheDir, fileName)
            try:
                await aiofiles.os.rename(filePath)
                # TODO: Should be logged at info or debug
                logging.warning(f'Deleted the unreferenced tile cache file {fileName}')                    
            except:
                # Log and continue
                logging.error(
                    f'An error occurred while deleting the unreferenced tile cache file {fileName}',
                    exc_info=ex)
                                
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

        # Add the image to the cache, this will automatically add it at the end of the cache
        # to indicate it's the most recently used
        self._memCache[tileQuery] = tileImage
        self._memTotalBytes += size

        if cacheToDisk and (tileQuery not in self._diskPendingAdds):
            # Writing to the disk cache is done as a future so as not to block
            # the caller
            diskTile = TileCache._DiskTile(
                tileQuery=tileQuery,
                mapFormat=tileImage.format(),
                fileName=str(uuid.uuid4()) + TileCache._TileCacheFileExtension,
                fileSize=tileImage.size(),
                overlapType=overlapType,
                createdTime=common.utcnow())
            self._diskPendingAdds.add(tileQuery)            
            self._startBackgroundJob(
                coro=self._storeTileAsync(
                    diskTile=diskTile,
                    tileData=tileImage.bytes()))

    async def lookupAsync(self, tileQuery: str) -> typing.Optional[travellermap.MapImage]:
        # Check the memory cache first
        data = self._memCache.get(tileQuery)
        if data:
            # Move most recently used item to end of cache so it will be evicted last
            self._memCache.move_to_end(tileQuery, last=True)
            return data
        
        # Not in memory so check the disk cache
        diskTile = self._diskCache.get(tileQuery)
        if diskTile == None:
            return None # Tile isn't in disk cache or is in the process of being removed
        
        # Load cached file from disk
        cacheFilePath = os.path.join(self._cacheDir, diskTile.fileName())
        try:
            async with aiofiles.open(cacheFilePath, 'rb') as file:
                data = await file.read()
        except Exception as ex:
            # Something wen't wrong with loading the file so delete remove the file from
            # the disk cache to prevent anything trying to load it again in the future.
            # The check that it's still in the cache is important as in theory it could
            # have already been removed by another async task
            logging.warning(
                f'Failed to load cached tile file {diskTile.fileName()} for {tileQuery}',
                exc_info=ex)            
            if tileQuery in self._diskCache:
                del self._diskCache[tileQuery]
            return None
        
        # Mark the disk tile as used so it will be at the back of the queue if tiles need
        # to be purged for space. An background task is started to push the update to the
        # database
        diskTile.markUsed()
        self._startBackgroundJob(
            coro=self._updateTileUsedAsync(diskTile=diskTile))

        # Add the cached file to the memory cache, removing other items if
        # required to make space. It's important to specify that it shouldn't
        # be added to the disk cache as we know it's already there
        image = travellermap.MapImage(bytes=data, format=diskTile.mapFormat())
        await self.addAsync(
            tileQuery=diskTile.tileQuery(),
            tileImage=image,
            overlapType=diskTile.overlapType(),
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
        self._diskPendingAdds.clear()

        # Remove tiles from the database
        async with self._database.executescript(_DeleteAllTilesQuery) as cursor:
            pass

        # Clear details of the disk cache from memory. This prevents other tasks
        # performing lookups trying to read the file while this task is trying
        # to delete it
        cacheEntries = list(self._diskCache.values())
        self._diskCache.clear()
        self._diskTotalBytes = 0
    
        # Remove tiles from disk
        for diskTile in cacheEntries:
            filePath = os.path.join(self._cacheDir, diskTile.fileName())
            try:
                await aiofiles.os.remove(filePath)
            except Exception as ex:
                # Log and continue if an error occurs
                logging.error(
                    f'Failed to delete tile file {diskTile.fileName()}',
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
            diskTile: _DiskTile,
            tileData: bytes
            ) -> None:
        try:
            filePath = os.path.join(self._cacheDir, diskTile.fileName())
            query = _AddTileQuery.format(
                diskTile.tileQuery(),
                travellermap.mapFormatToMimeType(format=diskTile.mapFormat()),
                diskTile.fileName(),
                diskTile.fileSize(),
                str(diskTile.overlapType().name),
                TileCache._timestampToString(timestamp=diskTile.createdTime()),
                TileCache._timestampToString(timestamp=diskTile.usedTime()))
            
            # Write the tile image to disk
            async with aiofiles.open(filePath, 'wb') as file:
                await file.write(tileData)
        
            # Only update the database once the file has successfully been written
            # to disk
            async with self._database.executescript(query) as cursor:
                pass

            # It's important that the in memory copy of what disk cache tiles are
            # available is updated AFTER the file has been written to disk and the
            # database has been updated. It's only at this point is it safe for
            # something to use the cached entry.
            self._diskCache[diskTile.tileQuery()] = diskTile
            self._diskTotalBytes += diskTile.fileSize()
            logging.debug(f'Added tile {diskTile.tileQuery()} to disk cache')
        except asyncio.CancelledError:
            # Cancellation is expected at shutdown so only log at debug
            logging.debug(
                f'Adding tile {diskTile.tileQuery()} to the disk cache was cancelled')
        except Exception as ex:           
            # Log the exception here rather than letting it be caught and logged by
            # the async loop running the fire and forget function.
            logging.error(
                f'An error occurred while adding tile {diskTile.tileQuery()} to the disk cache',
                exc_info=ex)
        finally:
            # No mater what happens, make sure we remove this tile form the list of
            # pending adds
            if diskTile.tileQuery() in self._diskPendingAdds:
                self._diskPendingAdds.remove(diskTile.tileQuery())
            
    # NOTE: This function is intended to be fire and forget so whatever async
    # stream of execution adds something to the cache isn't blocked waiting
    # for the file to be written and database updated. 
    async def _updateTileUsedAsync(
            self,
            diskTile: _DiskTile
            ) -> None:
        try:
            query = _UpdateTileUsedQuery.format(
                diskTile.tileQuery(),
                TileCache._timestampToString(diskTile.usedTime()))
            
            async with self._database.executescript(query) as cursor:
                pass

            logging.debug(
                f'Update last used time for tile {diskTile.tileQuery()} to {diskTile.usedTime()}')
        except asyncio.CancelledError:
            # Cancellation is expected at shutdown so only log at debug
            logging.debug(
                f'Updating tile {diskTile.tileQuery()} last used time was cancelled')
        except Exception as ex:           
            # Log the exception here rather than letting it be caught and logged by
            # the async loop running the fire and forget function.
            logging.error(
                f'An error occurred while updating last used time of tile {diskTile.tileQuery()}',
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
        diskTiles = sorted(
            self._diskCache.values(),
            key=lambda diskTile: diskTile.usedTime().timestamp(),
            reverse=True)
        purgeAge = None
        while requiredBytes > 0:
            # Remove the tile that was used longest ago
            diskTile = diskTiles.pop()
            del self._diskCache[diskTile.tileQuery()]
            self._diskTotalBytes -= diskTile.fileSize()
            purgeAge = diskTile.createdTime()

        # TODO: Finish me

    async def _purgeByAgeAsync(self) -> None:
        expiryTime = common.utcnow() - TileCache._MaxDiskCacheExpiryAge
        logging.debug(
            f'Purging tile disk cache entries up to {expiryTime}')
        
        # Remove expired entries from the in memory copy of the disk cache
        # contents. This needs to be done first to prevent another task
        # trying to read the tile wile it's being deleted
        expiredEntries: typing.List[TileCache._DiskTile] = []
        for tileQuery in list(self._diskCache.keys()):
            diskTile = self._diskCache[tileQuery]

            # Used created time for this checking for tile age rather than
            # used time. The intention is all tiles will eventually be
            # purged even if they are getting used
            if diskTile.createdTime() <= expiryTime:
                # TODO: Should probably log at debug
                logging.warning(
                    f'Purging expired tile disk cache entry for {diskTile.tileQuery()} from {diskTile.createdTime()}')

                # Remove from cache, this will prevent any further lookups from
                # loading the tile from the cache
                del self._diskCache[tileQuery]
                self._diskTotalBytes -= diskTile.fileSize()
                expiredEntries.append(diskTile)

        # Remove expired entries from database
        query = _DeleteExpiredTilesQuery.format(
            TileCache._timestampToString(timestamp=expiryTime))
        async with self._database.executescript(query) as cursor:
            pass

        # Remove expired tile files from disk
        for diskTile in expiredEntries:
            filePath = os.path.join(self._cacheDir, diskTile.fileName())
            try:
                await aiofiles.os.remove(filePath)
            except Exception as ex:
                # Log and continue if an error occurs
                logging.error(
                    f'Failed to purge expired tile disk cache file {diskTile.fileName()} for {diskTile.tileQuery()}',
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