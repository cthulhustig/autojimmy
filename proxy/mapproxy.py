import app
import collections
import enum
import functools
import http.server
import io
import logging
import multiprocessing
import os
import PIL.Image
import PIL.ImageDraw
import proxy
import socketserver
import travellermap
import urllib.error
import urllib.parse
import urllib.request
import threading
import typing

_MultiThreaded = True

_MaxTileCacheBytes = 256 * 1024 * 1024 # 256MiB

_ExtensionToContentTypeMap = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css'
}

# This is an extremely crude in memory cache of all the locally served files. It assumes
# files don't change during run time and doesn't support files in sub-directories
class _LocalFileStore(object):
    def __init__(
            self,
            localFileDir: str
            ) -> None:
        self._lock = threading.Lock()
        self._cache = {}

        for fileName in os.listdir(localFileDir):
            filePath = os.path.join(localFileDir, fileName)
            if not os.path.isfile(filePath):
                continue
            try:
                with open(filePath, 'rb') as file:
                    data = file.read()
            except Exception as ex:
                logging.error(f'Local file store failed to load {filePath}', exc_info=ex)
                continue

            logging.debug(f'Local file store loaded {filePath}')
            self._cache['/' + fileName] = data # Add '/' to the key for easier mapping later

    def lookup(self, filePath: str) -> bytes:
        with self._lock:
            return self._cache.get(filePath)

class _TileCache(object):
    def __init__(
            self,
            maxBytes: typing.Optional[int] # None means no max
            ) -> None:
        self._lock = threading.Lock()
        self._cache = collections.OrderedDict()
        self._maxBytes = maxBytes
        self._currentBytes = 0

    def add(self, key: str, image: travellermap.MapImage) -> None:
        with self._lock:
            size = image.size()

            startingBytes = self._currentBytes
            evictionCount = 0
            while self._cache and ((self._currentBytes + size) > self._maxBytes):
                # The item at the start of the cache is the one that was used longest ago
                oldKey, oldData = self._cache.popitem(last=False)
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
        with self._lock:
            data = self._cache.get(key)
            if not data:
                return None

            # Move most recently used item to end of cache so it will be evicted last
            self._cache.move_to_end(key, last=True)
            return data


if _MultiThreaded:
    class _HTTPServerBase(socketserver.ThreadingMixIn, http.server.HTTPServer):
        pass
else:
    class _HTTPServerBase(http.server.HTTPServer):
        pass

class _HTTPServer(_HTTPServerBase):
    def __init__(
            self,
            serverAddress: str,
            requestHandlerClass: typing.Type[http.server.BaseHTTPRequestHandler],
            shutdownEvent: multiprocessing.Event
            ) -> None:
        super().__init__(serverAddress, requestHandlerClass)
        self._shutdownEvent = shutdownEvent

    def service_actions(self) -> None:
        super().service_actions()
        if self._shutdownEvent.is_set():
            logging.debug('Tile map shutdown event received')
            # https://stackoverflow.com/questions/10085996/shutdown-socketserver-serve-forever-in-one-thread-python-application
            self._BaseServer__shutdown_request = True

class _HttpGetRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(
            self,
            travellerMapUrl: str,
            localFileStore: _LocalFileStore,
            tileCache: _TileCache,
            compositor: typing.Optional[proxy.Compositor],
            mainsMilieu: typing.Optional[travellermap.Milieu],
            *args,
            **kwargs
            ) -> None:
        self._travellerMapUrl = travellerMapUrl
        self._localFileStore = localFileStore
        self._tileCache = tileCache
        self._compositor = compositor
        self._mainsMilieu = mainsMilieu

        # BaseHTTPRequestHandler calls do_GET **inside** __init__ !!!
        # So we have to call super().__init__ after setting attributes.
        super().__init__(*args, **kwargs)

    def log_error(self, format: str, *args: typing.Any) -> None:
        logging.error('{address}: {message}'.format(
            address=self.address_string(),
            message=format % args))

    def log_request(
            self,
            code: typing.Union[int, str, http.HTTPStatus] = "-",
            size: typing.Union[int, str] = "-"
            ) -> None:
        if isinstance(code, http.HTTPStatus):
            code = code.value
        logging.debug('{address}: "{request}" {code} {size}'.format(
            address=self.address_string(),
            request=self.requestline,
            code=str(code),
            size=str(size)))

    def log_message(self, format, *args):
        logging.info('{address}: {message}'.format(
            address=self.address_string(),
            message=format % args))

    # This is the string the gets returned as the Server HTTP header
    def version_string(self) -> str:
        return f'Traveller Map Proxy {app.AppVersion}'

    def do_GET(self) -> None:
        try:
            parsedUrl = urllib.parse.urlparse(self.path)

            path = parsedUrl.path
            if path == '' or path == '/':
                path = '/index.html'

            # TODO: I should probably use the local copies of sophont and allegiance files for those requests
            localFileData = self._localFileStore.lookup(path)
            if localFileData:
                self._handleLocalFileRequest(
                    filePath=path,
                    fileData=localFileData)
            elif path == '/api/tile':
                self._handleTileRequest(parsedUrl=parsedUrl)
            elif path == '/res/mains.json':
                self._handleMainsRequest(parsedUrl=parsedUrl)
            else:
                # Act as a proxy for all other requests and just forward them to the
                # configured Traveller Map instance
                self._handleProxyRequest(parsedUrl=parsedUrl)
        except urllib.error.HTTPError as ex:
            logging.error(f'HTTP Error {ex.code} when handling GET request for {self.path}')
            self.send_response(ex.code)
            self.end_headers()
        except urllib.error.URLError as ex:
            logging.error(f'URL Error {ex.reason} when handling GET request for {self.path}')
            if hasattr(ex, 'code'):
                code = ex.code
            else:
                code = 500
            self.send_response(code)
            self.end_headers()
        except ConnectionAbortedError as ex:
            # Log this at debug as it's expected that it can happen if the client closes
            # the connection while the proxy is handling the request
            logging.debug(f'Connection aborted when handling GET request for {self.path}', exc_info=ex)
        except Exception as ex:
            logging.error(f'Exception occurred when handling GET request for {self.path}', exc_info=ex)
            self.send_response(500)
            self.end_headers()

    def _handleLocalFileRequest(
            self,
            filePath: urllib.parse.ParseResult,
            fileData: str
            ) -> None:
        logging.debug(f'Serving local data for {filePath}')

        _, extension = os.path.splitext(filePath)
        contentType = _ExtensionToContentTypeMap.get(extension)

        self.send_response(200)
        if contentType:
            self.send_header('Content-Type', contentType)
        self.send_header('Content-Length', len(fileData))
        self.end_headers()
        self.wfile.write(fileData)

    # NOTE: It's important that this function tries it's best to return something. If compositing
    # fails it should return the default tile
    def _handleTileRequest(
            self,
            parsedUrl: urllib.parse.ParseResult
            ) -> None:
        parsedQuery = urllib.parse.parse_qs(parsedUrl.query)
        cacheKey = self._generateCacheKey(queryMap=parsedQuery)

        tileImage = self._tileCache.lookup(key=cacheKey)
        if tileImage:
            logging.debug(f'Serving cached response for tile {parsedUrl.query}')
            tileBytes = tileImage.bytes()
            contentType = travellermap.mapFormatToMimeType(tileImage.format())
        else:
            logging.debug(f'Creating tile for {parsedUrl.query}')

            tileX = float(parsedQuery['x'][0])
            tileY = float(parsedQuery['y'][0])
            tileScale = float(parsedQuery['scale'][0])
            tileWidth = int(parsedQuery.get('w', [256])[0])
            tileHeight = int(parsedQuery.get('h', [256])[0])
            milieu = str(parsedQuery.get('milieu', ['M1105'])[0])
            style = str(parsedQuery.get('style', 'poster'))
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

                # TODO: I suspect this is creating a new TCP connection for each request. If so it
                # would be better to use a connection pull if possible

                tileBytes, contentType, sourceFormat = self._makeTileRequest(parsedUrl=parsedUrl)

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
                        # TODO: This could be simplified now that I've dropped support for SVG tiles
                        tile = self._compositor.createCompositorImage(
                            mapImage=travellermap.MapImage(bytes=tileBytes, format=sourceFormat),
                            scale=tileScale)

                        try:
                            self._compositor.partialOverlap(
                                tileImage=tile.mainImage(),
                                tileText=tile.textImage(),
                                tileX=tileX,
                                tileY=tileY,
                                tileWidth=tileWidth,
                                tileHeight=tileHeight,
                                tileScale=tileScale,
                                milieu=milieu)

                            tileImage = tile.mainImage()
                            tileBytes = io.BytesIO()
                            tileImage.save(tileBytes, format=targetFormat.value)
                            tileBytes.seek(0)
                            tileBytes = tileBytes.read()
                        finally:
                            del tile
                    else:
                        assert(overlapType == proxy.Compositor.OverlapType.CompleteOverlap)
                        tileImage = self._compositor.fullOverlap(
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
                    logging.debug('Failed to composite tile', exc_info=ex)
            else:
                logging.debug(f'Serving live response for tile {parsedUrl.query}')

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
                logging.debug(f'Requesting fallback tile for {parsedUrl.query}')
                tileBytes, contentType, targetFormat = self._makeTileRequest(parsedUrl=parsedUrl)
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

        self.send_response(200)
        if contentType:
            self.send_header('Content-Type', contentType)
        self.send_header('Content-Length', len(tileBytes) if tileBytes else 0)
        # Tell the client not to cache tiles. Assuming the browser respects the request, it
        # should prevent stale tiles being displayed if the user modifies data
        self.send_header('Cache-Control', 'no-store, no-cache')
        self.end_headers()
        if tileBytes:
            self.wfile.write(tileBytes.read() if isinstance(tileBytes, io.BytesIO) else tileBytes)

    def _handleMainsRequest(
            self,
            parsedUrl: urllib.parse.ParseResult
            ) -> None:
        mainsData = None
        if self._mainsMilieu:
            try:
                mainsData = travellermap.DataStore.instance().mainsData(
                    milieu=self._mainsMilieu)
                if not mainsData:
                    raise RuntimeError('Empty mains data returned')
            except Exception as ex:
                logging.error(f'Failed to retrieve mains data from data store', exc_info=ex)
                # Continue to fall back to traveller map

        if not mainsData:
            self._handleProxyRequest(
                parsedUrl=parsedUrl,
                # Allow browser to cache it for the session but not store it on disk
                forceCacheControl='no-store')
            return
        mainsData = mainsData.encode()

        logging.debug(f'Serving local mains data')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(mainsData))
        # Tell the client not to cache tiles. Assuming the browser respects the request, it
        # should prevent stale tiles being displayed if the user modifies data
        self.send_header('Cache-Control', 'no-store, no-cache') # Served locally so never cache
        self.end_headers()
        self.wfile.write(mainsData)

    def _handleProxyRequest(
            self,
            parsedUrl: urllib.parse.ParseResult,
            forceCacheControl: typing.Optional[str] = None
            ) -> None:
        content, headers = self._makeProxyRequest(parsedUrl=parsedUrl)

        self.send_response(200)
        for header, value in headers.items():
            if (forceCacheControl != None) and (header.lower() == 'cache-control'):
                continue # Don't proxy cache setting
            self.send_header(header, value)
        if forceCacheControl: # if forceCacheControl is an empty string, don't add the header
            self.send_header('Cache-Control', forceCacheControl)
        self.end_headers()
        self.wfile.write(content)

    def _makeTileRequest(
            self,
            parsedUrl: urllib.parse.ParseResult
            ) -> typing.Tuple[bytes, str, typing.Optional[travellermap.MapFormat]]:
        tileBytes, headers = self._makeProxyRequest(parsedUrl=parsedUrl)

        contentType = headers.get('Content-Type') # TODO: Is this check case sensitive?
        tileFormat = travellermap.mimeTypeToMapFormat(contentType)
        if not tileFormat:
            # Log this at debug as it could happen a lot if something goes wrong
            logging.debug(f'Unexpected Content-Type {contentType} for tile {parsedUrl.query}')

        return tileBytes, contentType, tileFormat

    def _makeProxyRequest(
            self,
            parsedUrl: urllib.parse.ParseResult,
            headers: typing.Optional[typing.Mapping[str, str]] = None
            ) -> typing.Tuple[bytes, typing.Dict[str, str]]:
        requestUrl = urllib.parse.urljoin(self._travellerMapUrl, parsedUrl.path)
        if parsedUrl.query:
            requestUrl += '?' + parsedUrl.query
        logging.debug(f'Making proxied request for {requestUrl}')

        request = urllib.request.Request(requestUrl)
        if headers:
            for key, value in headers.items():
                request.add_header(key, value)

        with urllib.request.urlopen(request) as response:
            return (response.read(), response.info())

    # The key used for the tile cache is based on the request options. Rather than just use the raw
    # request string, a new string is generated with the parameters arranged in alphabetic order.
    # This is done so that the order the options are specified in the URL don't mater when it comes
    # to checking for a cache hit. This makes the assumption the parameter order doesn't mater make
    # a difference to the response that is being cached. This is the case for the Traveller Map API.
    @staticmethod
    def _generateCacheKey(queryMap: typing.Dict[str, typing.List[str]]) -> str:
        options = []
        for key, values in queryMap.items():
            for value in values:
                options.append(key + '=' + value)
        options.sort()
        return '&'.join(options)

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
            app.setLogLevel(logLevel=logLevel)
        except Exception as ex:
            logging.error('Failed to set up map proxy logging', exc_info=ex)

        logging.info(f'Map proxy starting on port {listenPort}')

        try:
            localFileStore = _LocalFileStore(localFileDir=localFilesDir)
            tileCache = _TileCache(maxBytes=_MaxTileCacheBytes)

            travellermap.DataStore.setSectorDirs(
                installDir=installMapsDir,
                overlayDir=overlayMapsDir,
                customDir=customMapsDir)

            
            # Create the compositor if there are custom sectors for any milieu, not just the one that
            # is currently selected in the main app.
            compositor = None            
            if travellermap.DataStore.instance().hasCustomSectors():
                # If creation of the compositor fails (e.g. if it fails to parse the custom sector data)
                # then it's important that we continue setting up the proxy so it can at least return the
                # default tiles to the client
                try:
                    compositor = proxy.Compositor(customMapsDir=customMapsDir)
                except Exception as ex:
                    logging.error('Exception occurred while compositing tile', exc_info=ex)

            handler = functools.partial(
                _HttpGetRequestHandler,
                travellerMapUrl,
                localFileStore,
                tileCache,
                compositor,
                mainsMilieu)

            # Only listen on loopback for security. Allow address reuse to prevent issues if the
            # app is restarted
            httpd = _HTTPServer(
                serverAddress=('127.0.0.1', listenPort),
                requestHandlerClass=handler,
                shutdownEvent=shutdownEvent)
            httpd.allow_reuse_address = True

            messageQueue.put((MapProxy.ServerStatus.Started, None))
            httpd.serve_forever(poll_interval=0.5)

            messageQueue.put((MapProxy.ServerStatus.Stopped, None))
            logging.info('Map proxy shutdown complete')
        except Exception as ex:
            logging.error('Exception occurred while running map proxy', exc_info=ex)
            messageQueue.put((MapProxy.ServerStatus.Error, str(ex)))
