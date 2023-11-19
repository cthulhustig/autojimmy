import aiohttp.web
import aiosqlite
import asyncio
import app
import enum
import io
import logging
import multidict
import multiprocessing
import os
import PIL.Image
import PIL.ImageDraw
import proxy
import travellermap
import urllib.error
import urllib.parse
import urllib.request
import threading
import typing

_MaxTileCacheBytes = 256 * 1024 * 1024 # 256MiB

_ExtensionToContentTypeMap = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css'
}

_DatabaseFileName = 'map_proxy.db'
_TileCacheDirName = 'tile_cache'

_DatabaseSchemaVersion = 1
_DatabaseCacheKiB = 51200 # 50MiB

_ReadSchemaVersionQuery = 'PRAGMA user_version;'
_SetSchemaVersionQuery = f'PRAGMA user_version = {_DatabaseSchemaVersion};'

_ConfigureDatabaseQuery = \
f"""
PRAGMA synchronous = NORMAL;
PRAGMA journal_mode = WAL;
PRAGMA cache_size = -{_DatabaseCacheKiB};
"""

# This is an extremely crude in memory cache of all the locally served files. It assumes
# files don't change during run time and doesn't support files in sub-directories
# TODO: This should probably be flattened into _HttpRequestHandler
class _LocalFileStore(object):
    def __init__(
            self,
            localFileDir: str
            ) -> None:
        self._cache = {}

        for fileName in os.listdir(localFileDir):
            filePath = os.path.join(localFileDir, fileName)
            if not os.path.isfile(filePath):
                continue

            _, extension = os.path.splitext(filePath)
            mimeType = _ExtensionToContentTypeMap.get(extension)
            if not mimeType:
                logging.warning(f'Local file store ignoring {filePath} as it has an unknown extension {extension}')
                continue

            try:
                self.addFile(filePath=filePath, route='/' + fileName, mimeType=mimeType)
            except Exception as ex:
                logging.error(f'Local file store failed to add {filePath}', exc_info=ex)
                continue

    def addFile(self, filePath: str, route: str, mimeType: str) -> None:
        with open(filePath, 'rb') as file:
            data = file.read()

        self._cache[route] = (data, mimeType)
        logging.debug(f'Local file store cached {filePath} for {route}')

    def addFileData(
            self,
            data: typing.Union[bytes, str],
            route: str,
            mimeType: str
            ) -> None:
        self._cache[route] = (data, mimeType)
        logging.debug(f'Local file store cached data for {route}')

    def addAlias(self, route: str, alias: str) -> None:
        if not route in self._cache:
            raise RuntimeError(f'Unable to create alias for unknown route {route}')
        self._cache[alias] = self._cache[route]            
        logging.debug(f'Local file store aliased {route} to {alias}')

    def contains(self, filePath: str) -> bool:
        return filePath in self._cache

    def lookup(
            self,
            filePath: str
            ) -> typing.Tuple[typing.Optional[typing.Union[bytes, str]], typing.Optional[str]]: # File Data, Mime Type
        return self._cache.get(filePath, (None, None))

class _HttpRequestHandler(object):
    # By default the aiohttp ClientSession connection pool seems to keep connections alive for ~15 seconds.
    # I'm overriding this to make navigation of the map more responsive
    _ConnectionKeepAliveSeconds = 60

    def __init__(
            self,
            travellerMapUrl: str,
            localFileStore: _LocalFileStore,
            tileCache: proxy.TileCache,
            compositor: typing.Optional[proxy.Compositor],
            mainsMilieu: typing.Optional[travellermap.Milieu]
            ) -> None:
        super().__init__()
        self._travellerMapUrl = travellerMapUrl
        self._localFileStore = localFileStore
        self._tileCache = tileCache
        self._compositor = compositor
        self._mainsMilieu = mainsMilieu

        # As far as I can tell connection reuse requires HTTP/2 which in turns requires
        # SSL (https://caniuse.com/http2). I was seeing exceptions when using my local
        # Traveller Map over HTTP but not when accessing the main site over HTTPS.
        parsedUrl = urllib.parse.urlparse(travellerMapUrl)
        if parsedUrl.scheme.lower() == 'https':
            self._connector = aiohttp.TCPConnector(
                keepalive_timeout=_HttpRequestHandler._ConnectionKeepAliveSeconds)
        else:            
            self._connector = aiohttp.TCPConnector(force_close=True)

        self._session = aiohttp.ClientSession(connector=self._connector)

    async def shutdownAsync(self) -> None:
        if self._session:
            await self._session.close()

    async def handleRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> aiohttp.web.Response:
        # TODO: I should probably use the local copies of sophont and allegiance files for those requests
        if self._localFileStore.contains(request.path):
            return await self._handleLocalFileRequestAsync(request)
        elif request.path == '/api/tile':
            return await self._handleTileRequestAsync(request)
        elif request.path == '/res/mains.json':
            return await self._handleMainsRequestAsync(request)
        else:
            # Act as a proxy for all other requests and just forward them to the
            # configured Traveller Map instance
            return await self._handleProxyRequestAsync(request)

    async def _handleLocalFileRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> aiohttp.web.Response:
        logging.debug(f'Serving local data for {request.path}')

        body, contentType = self._localFileStore.lookup(request.path)
        if body == None or contentType == None:
            raise RuntimeError(f'Unknown local file {request.path}')        

        headers = {
            'Content-Length': str(len(body)),
            'Cache-Control': 'no-store, no-cache', # Don't cache locally served files
            'Content-Type': contentType}

        return aiohttp.web.Response(
            status=200,
            headers=headers,
            body=body) 

    # NOTE: It's important that this function tries it's best to return something. If compositing
    # fails it should return the default tile
    async def _handleTileRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> aiohttp.web.Response:
        tileImage = None
        try:
            tileImage = await self._tileCache.lookupAsync(tileQuery=request.query_string)
        except Exception as ex:
            # Log this at a low level as it could happen a LOT if something goes wrong
            # TODO: This should be logging at debug as it could get very spammy
            logging.info(
                f'Error occurred when looking up tile {request.query_string} in tile cache',
                exc_info=ex)
            # Continue so tile is still generated

        shouldCacheTile = True
        overlapType = None
        if tileImage:
            logging.debug(f'Serving cached response for tile {request.query_string}')
            tileBytes = tileImage.bytes()
            contentType = travellermap.mapFormatToMimeType(tileImage.format())
            shouldCacheTile = False # Already in the cache so no need to add
        else:
            logging.debug(f'Creating tile for {request.query_string}')

            tileX = float(request.query['x'])
            tileY = float(request.query['y'])
            tileScale = float(request.query['scale'])
            tileWidth = int(request.query.get('w', 256))
            tileHeight = int(request.query.get('h', 256))
            milieu = str(request.query.get('milieu', 'M1105'))
            style = str(request.query.get('style', 'poster'))
            if milieu.upper() in travellermap.Milieu.__members__:
                milieu = travellermap.Milieu.__members__[milieu]
            else:
                milieu = travellermap.Milieu.M1105

            if self._compositor:
                overlapType = self._compositor.overlapType(
                    tileX=tileX,
                    tileY=tileY,
                    tileScale=tileScale,
                    milieu=milieu)
            else:
                overlapType = proxy.Compositor.OverlapType.NoOverlap

            if overlapType != proxy.Compositor.OverlapType.CompleteOverlap:
                # Request the tile from Traveller Map. If it's a partial overlap request an SVG so
                # the text can be processed to avoid truncation by overlaid sectors
                tileBytes, contentType, sourceFormat = await self._makeTileRequestAsync(request)

                # Set the target format, by default the source format is used, this can be None if we
                # got something unexpected back from Traveller Map. In that case the tile will be
                # returned as is (using the content type string returned with the tile). If the tile
                # is an SVG set the target format to the best type for the style and update the content
                # type string to match
                targetFormat = sourceFormat
                if sourceFormat == travellermap.MapFormat.SVG:
                    targetFormat = travellermap.MapFormat.JPEG if style == 'candy' else travellermap.MapFormat.PNG
                    contentType = travellermap.mapFormatToMimeType(targetFormat)

                # No tile data shouldn't really happen and there's nothing we can do to return something
                # usable. Making this check is important as, if it was to happen, it prevents code later
                # from re-making the request
                if not tileBytes:
                    raise RuntimeError('Proxied tile request returned no data')
            else:
                # The tile is completely overlapped by a custom sector so there is no need to request the tile
                # from Traveller Map. This also means there is no source format. Set the target format to the
                # best type for the style and update the content string accordingly
                tileBytes = None
                sourceFormat = None
                targetFormat = travellermap.MapFormat.JPEG if style == 'candy' else travellermap.MapFormat.PNG
                contentType = travellermap.mapFormatToMimeType(targetFormat)

            if targetFormat and (overlapType != proxy.Compositor.OverlapType.NoOverlap):
                tileImage = None
                try:
                    if overlapType == proxy.Compositor.OverlapType.PartialOverlap:
                        tileImage = PIL.Image.open(io.BytesIO(tileBytes))
                        await self._compositor.partialOverlapAsync(
                            tileImage=tileImage,
                            tileX=tileX,
                            tileY=tileY,
                            tileWidth=tileWidth,
                            tileHeight=tileHeight,
                            tileScale=tileScale,
                            milieu=milieu)
                    else:
                        assert(overlapType == proxy.Compositor.OverlapType.CompleteOverlap)
                        tileImage = await self._compositor.fullOverlapAsync(
                            tileX=tileX,
                            tileY=tileY,
                            tileScale=tileScale,
                            milieu=milieu)

                    if tileImage != None:
                        if (targetFormat == travellermap.MapFormat.JPEG) and (tileImage.mode == 'RGBA'):
                            # JPEG doesn't support alpha and Image.save doesn't just ignore it :(
                            rgbImage = tileImage.convert('RGB')
                            del tileImage
                            tileImage = rgbImage

                        newBytes = io.BytesIO()
                        tileImage.save(newBytes, format=targetFormat.value)
                        newBytes.seek(0)
                        tileBytes = newBytes.read()
                except Exception as ex:
                    # Log this at a low level as it could happen a LOT if something goes wrong
                    # TODO: This should be logging at debug as it could get very spammy
                    logging.warning('Failed to composite tile', exc_info=ex)
                    shouldCacheTile = False # Don't cache tiles if they failed to generate
                finally:
                    if tileImage:
                        del tileImage
            else:
                logging.debug(f'Serving live response for tile {request.query_string}')

            if not tileBytes:
                # If we get to here with no tile bytes it means something wen't wrong performing a simple
                # copy. In this situation the only real option is to request the tile from Traveller Map and
                # return that
                logging.debug(f'Requesting fallback tile for {request.query_string}')
                tileBytes, contentType, targetFormat = await self._makeTileRequestAsync(request)
                shouldCacheTile = False # Don't cache tile when using a fallback tile
                if not tileBytes:
                    # We're having a bad day, something also wen't wrong getting the tile from Traveller
                    # Map. Not much to do apart from bail
                    raise RuntimeError(f'Proxied tile request returned no data for tile {request.query_string}')

            # Add the tile to the cache. Depending on the logic above this could either be a tile
            # as-is from Traveller Map or a composite tile
            if shouldCacheTile and tileBytes and targetFormat and overlapType:
                tileImage = travellermap.MapImage(
                    bytes=tileBytes,
                    format=targetFormat)
                await self._tileCache.addAsync(
                    tileQuery=request.query_string,
                    tileImage=tileImage,
                    overlapType=overlapType)

            # Enable this to add a red boundary to all tiles in order to highlight where they are
            # NOTE: This code should always be after tiles are added to the cache as we don't want
            # to write tiles with the border to the disk cache
            """
            if targetFormat:
                colour = 'red'
                with PIL.Image.open(tileBytes if isinstance(tileBytes, io.BytesIO) else io.BytesIO(tileBytes)) as image:
                    draw = PIL.ImageDraw.Draw(image)
                    draw.line([(0, 0), (0, image.height - 1)], fill=colour, width=0)
                    draw.line([(0, image.height - 1), (image.width - 1, image.height - 1)], fill=colour, width=0)
                    draw.line([(image.width - 1, image.height - 1), (image.width - 1, 0)], fill=colour, width=0)
                    draw.line([(image.width - 1, 0), (0, 0)], fill=colour, width=0)
                    tileBytes = io.BytesIO()
                    image.save(tileBytes, format=targetFormat.value)
                    tileBytes.seek(0)
                    tileBytes = tileBytes.read()
            """                

        headers = {
            'Content-Length': str(len(tileBytes) if tileBytes else 0),
            # Tell the client not to cache tiles. Assuming the browser respects the request, it
            # should prevent stale tiles being displayed if the user modifies data
            'Cache-Control': 'no-store, no-cache'}
        if contentType:
            headers['Content-Type'] = contentType

        return aiohttp.web.Response(
            status=200,
            headers=headers,
            body=tileBytes)

    async def _handleMainsRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> aiohttp.web.Response:
        mainsData = None
        if self._mainsMilieu:
            try:
                # TODO: This should be an async read
                mainsData = travellermap.DataStore.instance().mainsData(
                    milieu=self._mainsMilieu)
                if not mainsData:
                    raise RuntimeError('Empty mains data returned')
            except Exception as ex:
                logging.error(f'Failed to retrieve mains data from data store', exc_info=ex)
                # Continue to fall back to traveller map

        if not mainsData:
            return await self._handleProxyRequestAsync(
                request=request,
                # Allow browser to cache it for the session but not store it on disk
                forceCacheControl='no-store')
        mainsData = mainsData.encode()

        logging.debug(f'Serving local mains data')

        headers = {
            'Content-Type': 'application/json',
            'Content-Length': str(len(mainsData)),
            # Tell the client not to cache tiles. Assuming the browser respects the request, it
            # should prevent stale tiles being displayed if the user modifies data
            'Cache-Control': 'no-store, no-cache'}

        return aiohttp.web.Response(
            status=200,
            headers=headers,
            body=mainsData)        

    _ProxyRequestCopyHeaders = [
        'Content-Type',
        'Cache-Control'
    ]
    async def _handleProxyRequestAsync(
            self,
            request: aiohttp.web.Request,
            forceCacheControl: typing.Optional[str] = None
            ) -> aiohttp.web.Response:
        status, reason, headers, body = await self._makeProxyRequestAsync(request)

        responseHeaders = {'Content-Length': str(len(body))}
        for header in _HttpRequestHandler._ProxyRequestCopyHeaders:
            if header in headers:
                responseHeaders[header] = headers[header]

        if forceCacheControl: # if forceCacheControl is an empty string, don't add the header
            responseHeaders['Cache-Control'] = forceCacheControl            

        return aiohttp.web.Response(
            status=status,
            reason=reason,
            headers=responseHeaders,
            body=body)

    async def _makeTileRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> typing.Tuple[bytes, str, typing.Optional[travellermap.MapFormat]]:
        status, reason, headers, body = await self._makeProxyRequestAsync(request)
        if status != 200:
            raise RuntimeError(f'Request for tile {request.query_string} filed (status: {status}, reason: {reason})')

        contentType = headers.get('Content-Type')
        tileFormat = travellermap.mimeTypeToMapFormat(contentType)
        if not tileFormat:
            # Log this at debug as it could happen a lot if something goes wrong
            logging.debug(f'Request for tile {request.query_string} returned unexpected Content-Type {contentType}')

        return body, contentType, tileFormat

    async def _makeProxyRequestAsync(
            self,
            request: aiohttp.web.Request
            ) -> typing.Tuple[
                int, # Status code
                str, # Reason
                multidict.CIMultiDict, # Headers
                bytes: # Body
                ]:
        targetUrl = urllib.parse.urljoin(self._travellerMapUrl, request.path)
        query = request.query
        body = await request.read()

        # The headers from the incoming request are used as the headers for the outgoing request.
        # The Host header should be removed if present as, if it's passed on, Traveller Map doesn't
        # like the fact it's set to the address of the proxy
        headers = request.headers
        if 'Host' in headers:
            headers = headers.copy()
            del headers['Host']

        async with self._session.request(request.method, targetUrl, headers=headers, params=query, data=body) as response:
            body = await response.read()
            headers = response.headers.copy()
            if response.content_type:
                headers['Content-Type'] = response.content_type
            return (response.status, response.reason, headers, body)
    
# TODO: I don't think this is working for errors due to internal exceptions
@aiohttp.web.middleware
async def _serverHeaderMiddlewareAsync(
    request: aiohttp.web.Request,
    handler: typing.Callable[[aiohttp.web.Request], aiohttp.web.Response]
    ):
    response: aiohttp.web.Response = await handler(request)
    response.headers['Server'] = f'{app.AppName} Map Proxy {app.AppVersion}'
    return response

class MapProxy(object):
    class ServerStatus(enum.Enum):
        Stopped = 0
        Starting = 1
        Started = 2
        Error = 3

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _listenPort = None
    _travellerMapUrl = None
    _installDir = None
    _appDir = None
    _mainsMilieu = None
    _logDir = None
    _logLevel = logging.INFO
    _service = None
    _shutdownEvent = None
    _currentState = ServerStatus.Stopped
    _mpContext = None # Multiprocessing context
    _messageQueue = None

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    # Setting up multiprocessing stuff should be protected by __main__ so
                    # shouldn't be done when initialising the rest of the static class
                    # variables. A context is used so we can force processes to be spawned,
                    # this keeps the behaviour the same on all OS and avoids issues with
                    # singletons when using fork
                    cls._mpContext = multiprocessing.get_context('spawn')
                    cls._messageQueue = cls._mpContext.Queue()

                    cls._instance = cls.__new__(cls)
        return cls._instance

    @staticmethod
    def configure(
            listenPort: int,
            travellerMapUrl: str,
            installDir: str,
            appDir: str,
            mainsMilieu: travellermap.Milieu,
            logDir: str,
            logLevel: int
            ) -> None:
        if MapProxy._instance:
            raise RuntimeError('You can\'t configure map proxy after the singleton has been initialised')
        if MapProxy._listenPort == 0:
            raise RuntimeError('Map proxy listen port can\'t be 0')
        MapProxy._listenPort = listenPort
        MapProxy._travellerMapUrl = travellerMapUrl
        MapProxy._installDir = installDir
        MapProxy._appDir = appDir
        MapProxy._mainsMilieu = mainsMilieu
        MapProxy._logDir = logDir
        MapProxy._logLevel = logLevel

    def run(self) -> None:
        if self._service:
            self.shutdown()

        self._currentState = MapProxy.ServerStatus.Starting
        try:
            self._shutdownEvent = self._mpContext.Event()
            self._service = self._mpContext.Process(
                target=MapProxy._serviceCallback,
                args=[
                    self._listenPort,
                    self._travellerMapUrl,
                    self._installDir,
                    self._appDir,
                    self._mainsMilieu,
                    self._logLevel,
                    self._shutdownEvent,
                    self._messageQueue])
            self._service.daemon = False
            self._service.start()
        except Exception:
            self._currentState = MapProxy.ServerStatus.Error
            raise

    def shutdown(self) -> None:
        if not self._service:
            return
        self._shutdownEvent.set()
        self._service.join()
        self._service = None
        self._shutdownEvent = None
        self._currentState = MapProxy.ServerStatus.Stopped

    def status(self) -> 'MapProxy.ServerStatus':
        self._updateState()
        return self._currentState

    def _updateState(self) -> None:
        while not self._messageQueue.empty():
            message = self._messageQueue.get(block=False)
            if message and (len(message) == 2):
                status = message[0]
                data = message[1]
                assert(isinstance(status, MapProxy.ServerStatus))
                self._currentState = status

    # NOTE: This runs in a separate process
    @staticmethod
    def _serviceCallback(
            listenPort: int,
            travellerMapUrl: str,
            installDir: str,
            appDir: str,
            mainsMilieu: travellermap.Milieu,
            logLevel: int,
            shutdownEvent: multiprocessing.Event,
            messageQueue: multiprocessing.Queue
            ) -> None:
        try:
            app.setupLogger(
                logDir=os.path.join(appDir, 'logs'),
                logFile='mapproxy.log')
            #app.setLogLevel(logLevel=logLevel) # TODO: Reinstate correct logging
            app.setLogLevel(logLevel=logging.WARNING)
        except Exception as ex:
            logging.error('Failed to set up map proxy logging', exc_info=ex)

        logging.info(f'Map proxy starting on port {listenPort}')

        try:
            # TODO: This is duplicated from the app and should probably be shared
            installMapsDir = os.path.join(installDir, 'data', 'map')
            overlayMapsDir = os.path.join(appDir, 'map')
            customMapsDir = os.path.join(appDir, 'custom_map')            
            travellermap.DataStore.setSectorDirs(
                installDir=installMapsDir,
                overlayDir=overlayMapsDir,
                customDir=customMapsDir)

            localFileStore = _LocalFileStore(
                localFileDir=os.path.join(installDir, 'data', 'web'))
            localFileStore.addAlias(route='/index.html', alias='/')
            
            loop = asyncio.get_event_loop()

            with proxy.Compositor(customMapsDir=customMapsDir) as compositor:
                # TODO: Check what is logged if this fails
                dbConnection = loop.run_until_complete(MapProxy._connectToDatabase(
                    os.path.join(appDir, _DatabaseFileName)))

                # NOTE: This will block until the universe is loaded
                loop.run_until_complete(compositor.loadUniverseAsync())

                # TODO: Should load all mains files now to avoid consistency issues if the user was to add/remove
                # a custom sector before they've opened any traveller map widgets. The updated mains will be loaded
                # but it won't match the sector data

                # Clear out cached data from the data store now that things should have loaded the required data.
                # This is an attempt to keep the memory footprint of the proxy down
                # TODO: Would probably be better if you could disable caching of files when setting up the data store
                travellermap.DataStore.instance().clearCachedData()

                tileCacheDir = os.path.join(appDir, _TileCacheDirName)
                os.makedirs(tileCacheDir, exist_ok=True)
                    
                tileCache = proxy.TileCache(
                    database=dbConnection,
                    cacheDir=tileCacheDir,
                    maxBytes=_MaxTileCacheBytes)
                loop.run_until_complete(tileCache.initAsync())

                # Start web server
                requestHandler = _HttpRequestHandler(
                    travellerMapUrl=travellerMapUrl,
                    localFileStore=localFileStore,
                    tileCache=tileCache,
                    compositor=compositor,
                    mainsMilieu=mainsMilieu)
                webApp = aiohttp.web.Application(
                    middlewares=[_serverHeaderMiddlewareAsync])
                webApp.router.add_route('*', '/{path:.*?}', requestHandler.handleRequestAsync)

                webServer = loop.create_server(
                    protocol_factory=webApp.make_handler(),
                    host='127.0.0.1', # Only listen on loopback for security
                    port=app.Config.instance().mapProxyPort())
                loop.run_until_complete(webServer)

                messageQueue.put((MapProxy.ServerStatus.Started, None))
                loop.run_until_complete(MapProxy._shutdownMonitorAsync(
                    shutdownEvent=shutdownEvent,
                    webApp=webApp,
                    requestHandler=requestHandler,
                    tileCache=tileCache,
                    dbConnection=dbConnection))

                messageQueue.put((MapProxy.ServerStatus.Stopped, None))
                logging.info('Map proxy shutdown complete')
        except Exception as ex:
            logging.error('Exception occurred while running map proxy', exc_info=ex)
            messageQueue.put((MapProxy.ServerStatus.Error, str(ex)))

    async def _connectToDatabase(
            databasePath: str
            ) -> aiosqlite.Connection:
        connection = await aiosqlite.connect(databasePath)
        try:
            logging.info('Connected to map proxy database')
            async with connection.execute(_ReadSchemaVersionQuery) as cursor:
                data = await cursor.fetchone()
                schemaVersion = int(data[0])

            if schemaVersion < _DatabaseSchemaVersion:
                async with connection.executescript(_ConfigureDatabaseQuery)as cursor:
                    logging.debug('Configured map proxy database')

                async with connection.executescript(_SetSchemaVersionQuery) as cursor:
                    logging.info('Completed initialisation of map proxy database')
            elif schemaVersion > _DatabaseSchemaVersion:
                # TODO: Not sure what to do here? Delete the db? but then what about the
                # files in the cache? Will also making switching between versions more
                # difficult.
                pass
        except:
            await connection.close()
            raise

        return connection

    async def _shutdownMonitorAsync(
            shutdownEvent: multiprocessing.Event,
            webApp: aiohttp.web.Application,
            requestHandler: _HttpRequestHandler,
            tileCache: proxy.TileCache,
            dbConnection: aiosqlite.Connection
            ) -> None:
        while True:
            await asyncio.sleep(0.5)
            if shutdownEvent.is_set():
                # Disable aiohttp logging during shutdown as it can get quite noisy if requests
                # are in progress due. The errors that are generated are expected due to closing
                # the async session used for outgoing connections
                logging.getLogger('aiohttp').setLevel(logging.CRITICAL)

                await requestHandler.shutdownAsync()
                await webApp.shutdown()
                await webApp.cleanup()
                await tileCache.shutdownAsync()
                await dbConnection.close()
                return