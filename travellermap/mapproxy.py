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
import socketserver
import travellermap
import urllib.error
import urllib.parse
import urllib.request
import threading
import typing

# TODO: Make sure threaded server is enabled
_MultiThreaded = True

# TODO: This should be configurable
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

    def add(self, key: str, data: bytes) -> None:
        with self._lock:
            size = len(data)

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

            # Add the data to the cache, this will automatically add it at the end of the cache
            # to indicate it's the most recently used
            self._cache[key] = data
            self._currentBytes += size

    def lookup(self, key: str) -> typing.Optional[bytes]:
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
            compositor: typing.Optional[travellermap.Compositor],
            *args,
            **kwargs
            ) -> None:
        self._travellerMapUrl = travellerMapUrl
        self._localFileStore = localFileStore
        self._tileCache = tileCache
        self._compositor = compositor

        # BaseHTTPRequestHandler calls do_GET **inside** __init__ !!!
        # So we have to call super().__init__ after setting attributes.
        super().__init__(*args, **kwargs)

    def log_error(self, format: str, *args: typing.Any) -> None:
        logging.error('{address}: {message}'.format(
            address=self.address_string(),
            message=format%args))
        
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
            message=format%args))

    # NOTE: It's important that this function tries it's best to return something. If compositing
    # fails it should return the default tile
    def do_GET(self):
        try:
            parsedUrl = urllib.parse.urlparse(self.path)

            path = parsedUrl.path
            if path == '' or path == '/':
                path = '/index.html'

            localFileData = self._localFileStore.lookup(path)
            if localFileData:
                self._handleLocalFileRequest(
                    filePath=path,
                    fileData=localFileData)
            elif path == '/api/tile':
                self._handleTileRequest(parsedUrl=parsedUrl)
            else:
                # Act as a proxy for all other requests, pulling data from the configured
                # Traveller Map instance
                self._handleProxyRequest(parsedUrl=parsedUrl)
        except urllib.error.HTTPError as ex:
            logging.error(f'HTTP Error {ex.code} when handling request for {self.path}')
            self.send_response(ex.code)
            self.end_headers()
        except urllib.error.URLError as ex:
            logging.error(f'URL Error {ex.reason} when handling request for {self.path}')
            if hasattr(ex, 'code'):
                code = ex.code
            else:
                code = 500
            self.send_response(code)
            self.end_headers()
        except Exception as ex:
            logging.error(f'Exception occurred when handling request for {self.path}', exc_info=ex)
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

    def _handleTileRequest(
            self,
            parsedUrl: urllib.parse.ParseResult
            ) -> None:
        parsedQuery = urllib.parse.parse_qs(parsedUrl.query)
        cacheKey = self._generateCacheKey(queryMap=parsedQuery)

        data = self._tileCache.lookup(key=cacheKey)
        if data == None:
            logging.debug(f'Proxying request for tile {parsedUrl.query}')

            requestUrl = urllib.parse.urljoin(self._travellerMapUrl, '/api/tile?' + parsedUrl.query)
            with urllib.request.urlopen(requestUrl) as response:
                data = response.read()

            # TODO: Remove debug code
            """
            with PIL.Image.open(data if isinstance(data, io.BytesIO) else io.BytesIO(data)) as image:
                draw = PIL.ImageDraw.Draw(image)
                draw.rectangle([(0, 0), (255, 255)], fill="green", width=0)
                data = io.BytesIO()
                image.save(data, format='PNG')
                data.seek(0)
                data = data.read()
            """

            if self._compositor:
                tileX = float(parsedQuery['x'][0])
                tileY = float(parsedQuery['y'][0])
                tileScale = float(parsedQuery['scale'][0])
                tileWidth = int(parsedQuery.get('w', [256])[0])
                tileHeight = int(parsedQuery.get('h', [256])[0])
                milieu = str(parsedQuery.get('milieu', ['M1105'])[0])
                if milieu.upper() in travellermap.Milieu.__members__:
                    milieu = travellermap.Milieu.__members__[milieu]
                else:
                    milieu = travellermap.Milieu.M1105

                try:
                    data = self._compositor.composite(
                        tileData=data,
                        tileX=tileX,
                        tileY=tileY,
                        tileWidth=tileWidth,
                        tileHeight=tileHeight,
                        tileScale=tileScale,
                        milieu=milieu)
                except Exception as ex:
                    logging.error('Failed to composite tile', exc_info=ex)

            self._tileCache.add(key=cacheKey, data=data)
        else:
            logging.debug(f'Serving cached response for tile {parsedUrl.query}')

        # Enable this to add a red boundary to all tiles in order to highlight where they are
        """
        with PIL.Image.open(data if isinstance(data, io.BytesIO) else io.BytesIO(data)) as image:
            draw = PIL.ImageDraw.Draw(image)
            draw.line([(0, 0), (0, image.height - 1)], fill="red", width=0)
            draw.line([(0, image.height - 1), (image.width - 1, image.height - 1)], fill="red", width=0)
            draw.line([(image.width - 1, image.height - 1), (image.width - 1, 0)], fill="red", width=0)
            draw.line([(image.width - 1, 0), (0, 0)], fill="red", width=0)
            data = io.BytesIO()
            image.save(data, format='PNG')
            data.seek(0)
            data = data.read()
        """

        self.send_response(200)
        self.send_header('Content-Type', 'image/png')
        self.send_header('Content-Length', len(data))
        # This is copied from Traveller Map (public not local). Worth pointing
        # out that this proxy is ignoring the max-age request
        self.send_header('Cache-Control', 'public, max-age=3600')
        self.end_headers()
        self.wfile.write(data.read() if isinstance(data, io.BytesIO) else data)

    def _handleProxyRequest(
            self,
            parsedUrl: urllib.parse.ParseResult
            ) -> None:
        requestUrl = urllib.parse.urljoin(self._travellerMapUrl, parsedUrl.path)
        logging.debug(f'Proxying request to {requestUrl}')

        if parsedUrl.query:
            requestUrl += '?' + parsedUrl.query
        with urllib.request.urlopen(requestUrl) as response:
            info = response.info()
            data = response.read()

        self.send_response(200)
        for header, value in info.items():
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(data)            

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

# TODO: Rename this to MapProxy
class MapProxy(object):
    class ServerStatus(enum.Enum):
        Stopped = 0
        Starting = 1
        Started = 2
        Error = 3

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _travellerMapUrl = None
    _localFilesDir = None
    _customMapsDir = None
    _logDir = None
    _logLevel = logging.INFO
    _service = None
    _shutdownEvent = None
    _currentState = ServerStatus.Stopped
    _messageQueue = multiprocessing.Queue()
    _port = None

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
        return cls._instance

    @staticmethod
    def configure(
            travellerMapUrl: str,
            localFilesDir: str,
            customMapsDir: str,
            logDir: str,
            logLevel: int
            ) -> None:
        if MapProxy._instance:
            raise RuntimeError('You can\'t configure map proxy after the singleton has been initialised')
        MapProxy._travellerMapUrl = travellerMapUrl
        MapProxy._localFilesDir = localFilesDir
        MapProxy._customMapsDir = customMapsDir
        MapProxy._logDir = logDir
        MapProxy._logLevel = logLevel         

    def run(self) -> None:
        if self._service:
            self.shutdown()

        self._currentState = MapProxy.ServerStatus.Starting
        try:
            self._shutdownEvent = multiprocessing.Event()
            self._service = multiprocessing.Process(
                target=MapProxy._serviceCallback,
                args=[
                    self._travellerMapUrl,
                    self._localFilesDir,
                    self._customMapsDir,
                    self._logDir,
                    self._logLevel,
                    self._shutdownEvent,
                    self._messageQueue])
            self._service.daemon = True
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
        self._currentState =  MapProxy.ServerStatus.Stopped
        self._port = None

    def port(self) -> typing.Optional[int]:
        self._updateState()
        return self._port

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

                if self._currentState == MapProxy.ServerStatus.Started:
                    assert(isinstance(data, int))
                    self._port = data
                elif self._currentState == MapProxy.ServerStatus.Error:
                    self._port = None

    # NOTE: This runs in a separate process
    @staticmethod
    def _serviceCallback(
            travellerMapUrl: str,
            localFilesDir: str,
            customMapsDir: str,
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

        logging.info('Map proxy starting')

        try:
            localFileStore = _LocalFileStore(localFileDir=localFilesDir)
            tileCache = _TileCache(maxBytes=_MaxTileCacheBytes)

            # If creation of the compositor fails (e.g. if it fails to parse the custom sector data)
            # then it's important that we continue setting up the proxy so it can at least return the
            # default tiles to the client
            compositor = None
            try:
                compositor = travellermap.Compositor(customMapsDir=customMapsDir)
            except Exception as ex:
                logging.error('Exception occurred while compositing tile', exc_info=ex)

            handler = functools.partial(
                _HttpGetRequestHandler,
                travellerMapUrl,
                localFileStore,
                tileCache,
                compositor)

            # Only listen on loopback for security. Allow address reuse to prevent issues if the
            # app is restarted
            httpd = _HTTPServer(
                serverAddress=('127.0.0.1', 0),
                requestHandlerClass=handler,
                shutdownEvent=shutdownEvent)
            httpd.allow_reuse_address = True

            logging.info(f'Map proxy listening on port {httpd.server_port}')
            messageQueue.put((MapProxy.ServerStatus.Started, httpd.server_port))
            httpd.serve_forever(poll_interval=0.5)

            messageQueue.put((MapProxy.ServerStatus.Stopped, None))
            logging.info('Map proxy shutdown complete')
        except Exception as ex:
            logging.error('Exception occurred while running map proxy', exc_info=ex)
            messageQueue.put((MapProxy.ServerStatus.Error, str(ex)))
