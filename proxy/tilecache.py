import aiofiles
import aiosqlite
import asyncio
import collections
import logging
import os
import proxy
import travellermap
import uuid
import typing

_TileCacheFileExtension = '.dat'

_CreateTileCacheTableQuery = \
"""
CREATE TABLE IF NOT EXISTS tile_cache (
    query TEXT PRIMARY KEY,
    mime TEXT,
    file TEXT,
    size INTEGER,
    overlap TEXT,
    timestamp DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')));
"""
_AddToTileCacheQuery = \
"""
INSERT INTO tile_cache(query, mime, file, size, overlap) VALUES (
    "{0}", "{1}", "{2}", "{3}", "{4}");
"""
_LoadTileCacheQuery = \
"""
SELECT query, mime, file, size, overlap FROM tile_cache;
"""
# TODO: Implement clearing tile cache when custom sectors or snapshot change
_ClearTileCacheQuery = \
"""
DELETE FROM tile_cache;
"""

class TileCache(object):
    class _DbEntry(object):
        def __init__(
                self,
                tileQuery: str,
                mapFormat: travellermap.MapFormat,
                fileName: str,
                fileSize: int,
                overlapType: proxy.Compositor.OverlapType
                ) -> None:
            self._tileQuery = tileQuery
            self._mapFormat = mapFormat
            self._fileName = fileName
            self._fileSize = fileSize
            self._overlapType = overlapType

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
        self._currentMemBytes = 0
        self._dbCache: typing.Dict[str, TileCache._DbEntry] = {}
        self._dbPendingAdds: typing.Set[str] = set() # Set of keys of entries waiting to written to the DB

    async def initAsync(self) -> None:
        # Creating the table will be a no-op if it already exists
        # TODO: If I have table creation here it means any future migration is going to need to be here
        # which in turn means I probably need to have a separate schema version just for the table
        async with self._database.executescript(_CreateTileCacheTableQuery) as cursor:
            logging.debug('Created tile cache table')

        logging.debug('Loading tile cache table contents')
        async with self._database.execute(_LoadTileCacheQuery) as cursor:
            results = await cursor.fetchall()
            for tileQuery, mimeType, fileName, fileSize, overlapType in results:
                mapFormat = travellermap.mimeTypeToMapFormat(mimeType=mimeType)
                if not mapFormat:
                    logging.warning(f'Skipping tile cache entry for {tileQuery} (Unsupported mime type {mimeType})')
                    continue

                if overlapType not in proxy.Compositor.OverlapType.__members__:
                    logging.warning(f'Skipping tile cache entry for {tileQuery} (Unknown overlap type {overlapType})')
                    continue
                overlapType = proxy.Compositor.OverlapType.__members__[overlapType]

                self._dbCache[tileQuery] = TileCache._DbEntry(
                    tileQuery=tileQuery,
                    mapFormat=mapFormat,
                    fileName=fileName,
                    fileSize=fileSize,
                    overlapType=overlapType)

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

        startingBytes = self._currentMemBytes
        evictionCount = 0
        while self._memCache and ((self._currentMemBytes + size) > self._maxBytes):
            # The item at the start of the cache is the one that was used longest ago
            _, oldData = self._memCache.popitem(last=False) # TODO: Double check last is correct (it's VERY important)
            evictionCount += 1
            self._currentMemBytes -= len(oldData)
            assert(self._currentMemBytes > 0)

        if evictionCount:
            evictionBytes = startingBytes - self._currentMemBytes
            logging.debug(f'Tile cache evicted {evictionCount} tiles for {evictionBytes} bytes')

        # Add the image to the cache, this will automatically add it at the end of the cache
        # to indicate it's the most recently used
        self._memCache[tileQuery] = tileImage
        self._currentMemBytes += size

        if cacheToDisk and (tileQuery not in self._dbPendingAdds):
            # Writing to the disk cache is fire and forget
            self._dbPendingAdds.add(tileQuery)
            asyncio.ensure_future(self._updateDiskCacheAsync(
                key=tileQuery, image=tileImage,
                overlapType=overlapType))

    async def lookupAsync(self, tileQuery: str) -> typing.Optional[travellermap.MapImage]:
        # Check the memory cache first
        data = self._memCache.get(tileQuery)
        if data:
            # Move most recently used item to end of cache so it will be evicted last
            self._memCache.move_to_end(tileQuery, last=True)
            return data
        
        # Not in memory so check the database cache
        dbEntry = self._dbCache.get(tileQuery)
        if dbEntry == None:
            return None # Tile isn't in database cache
        
        # Load cached file from disk
        cacheFilePath = os.path.join(self._cacheDir, dbEntry.fileName())
        async with aiofiles.open(cacheFilePath, 'rb') as file:
            data = await file.read()

        # TODO: Handle unknown mime type
        image = travellermap.MapImage(bytes=data, format=dbEntry.mapFormat())

        # Add the cached file to the memory cache, removing other items if
        # required to make space. It's important to specify that it shouldn't
        # be added to the disk cache as we know it's already there
        await self.addAsync(
            tileQuery=dbEntry.tileQuery(),
            tileImage=image,
            overlapType=dbEntry.overlapType(),
            cacheToDisk=False)
        return image
    
    # NOTE: This function is intended to be fire and forget so whatever async
    # stream of execution adds something to the cache isn't blocked waiting
    # for the file to be written and database updated. It should be noted that
    # doing this (at least theoretically) introduces the possibility that two
    # independent requests for the same tile may cause this function to be called
    # in parallel for the same key but mapping to different images objects (but
    # images of the same tile)
    async def _updateDiskCacheAsync(
            self,
            key: str, # TODO: Should I hash this?
            image: travellermap.MapImage,
            overlapType: proxy.Compositor.OverlapType,
            ) -> None:
        dbEntry = TileCache._DbEntry(
            tileQuery=key,
            mapFormat=image.format(),
            fileName=str(uuid.uuid4()) + _TileCacheFileExtension,
            fileSize=image.size(),
            overlapType=overlapType)
        mimeType = travellermap.mapFormatToMimeType(format=image.format())
        filePath = os.path.join(self._cacheDir, dbEntry.fileName())

        try:
            async with aiofiles.open(filePath, 'wb') as file:
                await file.write(image.bytes())
        
            # Only update the database once the file has successfully been written
            # to disk
            query = _AddToTileCacheQuery.format(
                dbEntry.tileQuery(),
                mimeType,
                dbEntry.fileName(),
                dbEntry.fileSize(),
                str(overlapType.name))
            async with self._database.executescript(query) as cursor:
                pass # TODO: Do something?????

            # It's important that the entry is added to the database cache and
            # removed from the pending list AFTER the file has been written to
            # disk and the database has been updated. It's only at this point
            # is it safe for something to use the cached entry. The order the
            # entry is added to the cache and removed from the pending list isn't
            # important as they're not async so are effectively atomic from the
            # point of view of other async tasks.
            self._dbCache[key] = dbEntry
            self._dbPendingAdds.remove(dbEntry.tileQuery())
        except Exception as ex:
            print('EX ' + str(ex)) # TODO: Do something, should log here rather than letting the async loop log it

            