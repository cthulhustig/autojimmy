import collections
import functools
import http.server
import io
import logging
import multiprocessing
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
            while self._cache and ((self._currentBytes + size) > self._maxBytes):
                # The item at the start of the cache is the one that was used longest ago
                oldKey, oldData = self._cache.popitem(last=False)
                self._currentBytes -= len(oldData)
                assert(self._currentBytes > 0)

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
            # https://stackoverflow.com/questions/10085996/shutdown-socketserver-serve-forever-in-one-thread-python-application
            self._BaseServer__shutdown_request = True

class _HttpGetRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(
            self,
            tileCache: _TileCache,
            compositor: typing.Optional[travellermap.Compositor],
            *args,
            **kwargs
            ) -> None:
        self._tileCache = tileCache
        self._compositor = compositor

        # BaseHTTPRequestHandler calls do_GET **inside** __init__ !!!
        # So we have to call super().__init__ after setting attributes.
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        # TODO: This should be a debug level option
        pass # Don't write requests to terminal

    # NOTE: It's important that this function tries it's best to return something. If compositing
    # fails it should return the default tile
    def do_GET(self):
        parsedUrl = urllib.parse.urlparse(self.path)

        data = self._tileCache.lookup(key=parsedUrl.query)
        if data == None:
            #requestUrl = f'https://travellermap.com/api/tile?{parsed.query}'
            requestUrl = f'http://localhost:50103/api/tile?{parsedUrl.query}' # TODO: Remove local Traveller Map instance
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
                parsedQuery = urllib.parse.parse_qs(parsedUrl.query)
                tileX = float(parsedQuery['x'][0])
                tileY = float(parsedQuery['y'][0])
                scale = float(parsedQuery['scale'][0])
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
                        scale=scale,
                        milieu=milieu)
                except Exception as ex:
                    # TODO: Do something better
                    print(str(ex))

            self._tileCache.add(parsedUrl.query, data)

        # TODO: Remove debug tile highlight
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
        self.end_headers()
        # send the body of the response
        self.wfile.write(data.read() if isinstance(data, io.BytesIO) else data)

class TileProxy(object):
    def __init__(
            self,
            port: int,
            customMapDir: str
            ) -> None:
        self._port = port
        self._customMapsDir = customMapDir
        self._service = None
        self._shutdownEvent = None

    def run(self) -> None:
        self._shutdownEvent = multiprocessing.Event()
        self._service = multiprocessing.Process(
            target=TileProxy._serviceCallback,
            args=[self._port, self._customMapsDir, self._shutdownEvent])
        self._service.daemon = True
        self._service.start()

    def shutdown(self) -> None:
        if not self._service:
            return
        self._shutdownEvent.set()
        self._service.join()
        self._service = None
        self._shutdownEvent = None

    # NOTE: This runs in a separate process
    @staticmethod
    def _serviceCallback(
            port: int,
            customMapsDir: str,
            shutdownEvent: multiprocessing.Event
            ) -> None:
        try:
            tileCache = _TileCache(maxBytes=_MaxTileCacheBytes)

            # If creation of the compositor fails (e.g. if it fails to parse the custom sector data)
            # then it's important that we continue setting up the proxy so it can at least return the
            # default tiles to the client
            compositor = None
            try:
                compositor = travellermap.Compositor(customMapsDir=customMapsDir)
            except Exception as ex:
                print(ex) # TODO: Log something

            handler = functools.partial(_HttpGetRequestHandler, tileCache, compositor)

            # Only listen on loopback for security. Allow address reuse to prevent issues if the
            # app is restarted
            httpd = _HTTPServer(
                serverAddress=('127.0.0.1', port),
                requestHandlerClass=handler,
                shutdownEvent=shutdownEvent)
            httpd.allow_reuse_address = True
            httpd.serve_forever(poll_interval=0.5)

            print('Proxy Shutdown Complete') # TODO: Should log something at info level
        except Exception as ex:
            # TODO: Need to somehow pass this back to main process so an error can be displayed
            logging.error('Exception occurred while running web server', exc_info=ex)
