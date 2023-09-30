import functools
import http.server
import io
import logging
import multiprocessing
import socketserver
import PIL.Image
import PIL.ImageDraw
import travellermap
import urllib.error
import urllib.parse
import urllib.request
import typing

# TODO: Make sure threaded server is enabled
_MultiThreaded = False

if _MultiThreaded:
    class _HTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        pass
else:
    class _HTTPServer(http.server.HTTPServer):
        pass

class _HttpGetRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(
            self,
            tileCache: typing.Dict[str, typing.Any], # TODO: Work out what type it is
            compositor: travellermap.Compositor,
            *args,
            **kwargs
            ) -> None:
        self._tileCache = tileCache
        self._compositor = compositor

        # BaseHTTPRequestHandler calls do_GET **inside** __init__ !!!
        # So we have to call super().__init__ after setting attributes.
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        pass # Don't write requests to terminal

    def do_GET(self):
        parsedUrl = urllib.parse.urlparse(self.path)

        # TODO: Need to ask Joshua if I can get a flag added to the poster api that doesn't
        # add any padding around the generated image (basically disable the "Account for
        # jagged hexes" code in the poster handler).

        data = self._tileCache.get(parsedUrl.query)
        if data == None:
            #requestUrl = f'https://travellermap.com/api/tile?{parsed.query}'
            requestUrl = f'http://localhost:50103/api/tile?{parsedUrl.query}' # TODO: Remove local Traveller Map instance
            with urllib.request.urlopen(requestUrl) as response:
                data = response.read()

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
                milieu = None

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
                print(ex)

            self._tileCache[parsedUrl.query] = data

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

    def run(self) -> None:
        self._service = multiprocessing.Process(target=TileProxy._serviceCallback, args=[self._port, self._customMapsDir])
        self._service.daemon = True
        self._service.start()

    @staticmethod
    def _serviceCallback(
            port: int,
            customMapsDir: str
            ) -> None:
        try:
            tileCache = {}
            compositor = travellermap.Compositor(customMapsDir=customMapsDir)

            handler = functools.partial(_HttpGetRequestHandler, tileCache, compositor)

            # Only listen on loopback for security. Allow address reuse to prevent issues if the
            # app is restarted
            httpd = _HTTPServer(('127.0.0.1', port), handler)
            httpd.allow_reuse_address = True

            # TODO: Need some way to cleanly stop this from the main process
            httpd.serve_forever(poll_interval=0.5)
        except Exception as ex:
            # TODO: Need to somehow pass this back to main process so an error can be displayed
            logging.error('Exception occurred while running web server', exc_info=ex)
