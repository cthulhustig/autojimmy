import aiohttp.web
import asyncio
import app
import collections
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

class _TileCache(object):
    def __init__(
            self,
            maxBytes: typing.Optional[int] # None means no max
            ) -> None:
        self._cache = collections.OrderedDict()
        self._maxBytes = maxBytes
        self._currentBytes = 0

    def add(self, key: str, image: travellermap.MapImage) -> None:
        size = image.size()

        startingBytes = self._currentBytes
        evictionCount = 0
        while self._cache and ((self._currentBytes + size) > self._maxBytes):
            # The item at the start of the cache is the one that was used longest ago
            oldKey, oldData = self._cache.popitem(last=False) # TODO: Double check last is correct (it's VERY important)
            evictionCount += 1
            self._currentBytes -= len(oldData)
            assert(self._currentBytes > 0)

        if evictionCount:
            evictionBytes = startingBytes - self._currentBytes
            logging.debug(f'Tile cache evicted {evictionCount} tiles for {evictionBytes} bytes')

        # Add the image to the cache, this will automatically add it at the end of the cache
        # to indicate it's the most recently used
        self._cache[key] = image
        self._currentBytes += size

    def lookup(self, key: str) -> typing.Optional[travellermap.MapImage]:
        data = self._cache.get(key)
        if not data:
            return None

        # Move most recently used item to end of cache so it will be evicted last
        self._cache.move_to_end(key, last=True)
        return data

class _HttpRequestHandler(object):
    # By default the aiohttp ClientSession connection pool seems to keep connections alive for ~15 seconds.
    # I'm overriding this to make navigation of the map more responsive
    _ConnectionKeepAliveSeconds = 60

    def __init__(
            self,
            travellerMapUrl: str,
            localFileStore: _LocalFileStore,
            tileCache: _TileCache,
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

    async def shutdown(self) -> None:
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
        cacheKey = self._generateCacheKey(request)

        tileImage = self._tileCache.lookup(key=cacheKey)
        if tileImage:
            logging.debug(f'Serving cached response for tile {request.query}')
            tileBytes = tileImage.bytes()
            contentType = travellermap.mapFormatToMimeType(tileImage.format())
        else:
            logging.debug(f'Creating tile for {request.query}')

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
                try:
                    if overlapType == proxy.Compositor.OverlapType.PartialOverlap:
                        tileImage = PIL.Image.open(io.BytesIO(tileBytes))

                        try:
                            await self._compositor.partialOverlapAsync(
                                tileImage=tileImage,
                                tileX=tileX,
                                tileY=tileY,
                                tileWidth=tileWidth,
                                tileHeight=tileHeight,
                                tileScale=tileScale,
                                milieu=milieu)
                            
                            newBytes = io.BytesIO() # New variable to prevent loss of bytes if save, seek or read throws
                            tileImage.save(newBytes, format=targetFormat.value)
                            newBytes.seek(0)
                            tileBytes = newBytes.read()
                        finally:
                            del tileImage
                    else:
                        assert(overlapType == proxy.Compositor.OverlapType.CompleteOverlap)
                        tileImage = await self._compositor.fullOverlapAsync(
                            tileX=tileX,
                            tileY=tileY,
                            tileScale=tileScale,
                            milieu=milieu)

                        if tileImage != None:
                            try:
                                tileBytes = io.BytesIO()
                                tileImage.save(tileBytes, format=targetFormat.value)
                                tileBytes.seek(0)
                                tileBytes = tileBytes.read()
                            finally:
                                del tileImage
                except Exception as ex:
                    # Log this at a low level as it could happen a LOT if something goes wrong
                    # TODO: This should be logging at debug as it could get very spammy
                    logging.info('Failed to composite tile', exc_info=ex)
            else:
                logging.debug(f'Serving live response for tile {request.query}')

            # Enable this to add a red boundary to all tiles in order to highlight where they are
            # TODO: When I add disk caching this overlay shouldn't be included in the image that is cached
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

            if not tileBytes:
                # If we get to here with no tile bytes it means something wen't wrong performing a simple
                # copy. In this situation the only real option is to request the tile from Traveller Map and
                # return that
                logging.debug(f'Requesting fallback tile for {request.query}')
                tileBytes, contentType, targetFormat = await self._makeTileRequestAsync(request)
                if not tileBytes:
                    # We're having a bad day, something also wen't wrong getting the tile from Traveller
                    # Map. Not much to do apart from bail
                    raise RuntimeError('Proxied tile request returned no data')

            # Add the tile to the cache. Depending on the logic above this could either be a tile
            # as-is from Traveller Map or a composite tile
            if tileBytes and targetFormat:
                tileImage = travellermap.MapImage(
                    bytes=tileBytes,
                    format=targetFormat)
                self._tileCache.add(key=cacheKey, image=tileImage)

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
            raise RuntimeError(f'Request for tile {request.query} filed (status: {status}, reason: {reason})')

        contentType = headers.get('Content-Type')
        tileFormat = travellermap.mimeTypeToMapFormat(contentType)
        if not tileFormat:
            # Log this at debug as it could happen a lot if something goes wrong
            logging.debug(f'Request for tile {request.query} returned unexpected Content-Type {contentType}')

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

    # The key used for the tile cache is based on the request options. Rather than just use the raw
    # request string, a new string is generated with the parameters arranged in alphabetic order.
    # This is done so that the order the options are specified in the URL don't mater when it comes
    # to checking for a cache hit.
    @staticmethod
    def _generateCacheKey(request: aiohttp.web.Request) -> str:
        options = []
        for key in request.query:
            values=request.query.getall(key)
            for value in values:
                options.append(key + '=' + value)
        options.sort()
        return request.path + '&'.join(options)
    
# TODO: I don't think this is working for errors due to internal exceptions
@aiohttp.web.middleware
async def _setServerHeaderAsync(
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
    _localFilesDir = None
    _installMapsDir = None
    _overlayMapsDir = None
    _customMapsDir = None
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
            localFilesDir: str,
            installMapsDir: str,
            overlayMapsDir: str,
            customMapsDir: str,
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
        MapProxy._localFilesDir = localFilesDir
        MapProxy._installMapsDir = installMapsDir
        MapProxy._overlayMapsDir = overlayMapsDir
        MapProxy._customMapsDir = customMapsDir
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
                    self._localFilesDir,
                    self._installMapsDir,
                    self._overlayMapsDir,
                    self._customMapsDir,
                    self._mainsMilieu,
                    self._logDir,
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
            localFilesDir: str,
            installMapsDir: str,
            overlayMapsDir: str,
            customMapsDir: str,
            mainsMilieu: travellermap.Milieu,
            logDir: str,
            logLevel: int,
            shutdownEvent: multiprocessing.Event,
            messageQueue: multiprocessing.Queue
            ) -> None:
        try:
            app.setupLogger(logDir=logDir, logFile='mapproxy.log')
            #app.setLogLevel(logLevel=logLevel) # TODO: Reinstate correct logging
            app.setLogLevel(logLevel=logging.WARNING)
        except Exception as ex:
            logging.error('Failed to set up map proxy logging', exc_info=ex)

        logging.info(f'Map proxy starting on port {listenPort}')

        try:
            travellermap.DataStore.setSectorDirs(
                installDir=installMapsDir,
                overlayDir=overlayMapsDir,
                customDir=customMapsDir)

            localFileStore = _LocalFileStore(localFileDir=localFilesDir)
            localFileStore.addAlias(route='/index.html', alias='/')

            tileCache = _TileCache(maxBytes=_MaxTileCacheBytes)
            
            loop = asyncio.get_event_loop()

            with proxy.Compositor(customMapsDir=customMapsDir) as compositor:
                # NOTE: This will block until the universe is loaded
                loop.run_until_complete(compositor.loadUniverseAsync())

                # TODO: Should load all mains files now to avoid consistency issues if the user was to add/remove
                # a custom sector before they've opened any traveller map widgets. The updated mains will be loaded
                # but it won't match the sector data

                # Clear out cached data from the data store now that things should have loaded the required data.
                # This is an attempt to keep the memory footprint of the proxy down
                # TODO: Would probably be better if you could disable caching of files when setting up the data store
                travellermap.DataStore.instance().clearCachedData()

                # Start web server
                requestHandler = _HttpRequestHandler(
                    travellerMapUrl=travellerMapUrl,
                    localFileStore=localFileStore,
                    tileCache=tileCache,
                    compositor=compositor,
                    mainsMilieu=mainsMilieu)
                webApp = aiohttp.web.Application(
                    middlewares=[_setServerHeaderAsync])
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
                    requestHandler=requestHandler))

                messageQueue.put((MapProxy.ServerStatus.Stopped, None))
                logging.info('Map proxy shutdown complete')
        except Exception as ex:
            logging.error('Exception occurred while running map proxy', exc_info=ex)
            messageQueue.put((MapProxy.ServerStatus.Error, str(ex)))

    async def _shutdownMonitorAsync(
            shutdownEvent: multiprocessing.Event,
            webApp: aiohttp.web.Application,
            requestHandler: _HttpRequestHandler
            ) -> None:
        while True:
            await asyncio.sleep(0.5)
            if shutdownEvent.is_set():
                await webApp.shutdown()
                await webApp.cleanup()
                await requestHandler.shutdown()
                return