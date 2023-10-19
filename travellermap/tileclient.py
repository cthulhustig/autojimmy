import logging
import time
import threading
import travellermap
import typing
import urllib.error
import urllib.parse
import urllib.request

class TileClient(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()
    _mapBaseUrl = travellermap.TravellerMapBaseUrl
    _mapProxyPort = 0 # Disabled by default
    _cache = {}

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

    # The Traveller Map URL specified here is only used if the map proxy isn't running
    @staticmethod
    def configure(
            mapBaseUrl: str,
            mapProxyPort: int
            ) -> None:
        if TileClient._instance:
            raise RuntimeError('You can\'t configure map proxy after the singleton has been initialised')
        TileClient._mapBaseUrl = mapBaseUrl
        TileClient._mapProxyPort = mapProxyPort

    def tile(
            self,
            milieu: travellermap.Milieu,
            style: travellermap.Style,
            absoluteX: int,
            absoluteY: int,
            options: typing.Iterable[travellermap.Option],
            linearScale: float = 64,
            width: int = 256,
            height: int = 256,
            timeout: typing.Optional[typing.Union[int, float]] = None,
            ) -> bytes:
        mapX, mapY = travellermap.absoluteHexToMapSpace(
            absoluteX=absoluteX,
            absoluteY=absoluteY)

        # Calculate position to center tile on map position
        tilePosition = (
            (mapX * linearScale - (width / 2)) / width,
            (-mapY * linearScale - (height / 2)) / height)

        if self._mapProxyPort:
            baseUrl = f'http://127.0.0.1:{self._mapProxyPort}'
        else:
            baseUrl = self._mapBaseUrl

        url = travellermap.formatTileUrl(
            baseMapUrl=baseUrl,
            milieu=milieu,
            style=style,
            options=options,
            tilePosition=tilePosition,
            linearScale=linearScale,
            minimal=True)

        with self._lock:
            content = self._cache.get(url)
        if content != None:
            logging.debug(f'Tile cache hit for {url}')
            return content

        content = TileClient._makeRequest(
            url=url,
            timeout=timeout)

        with self._lock:
            self._cache[url] = content

        return content

    @staticmethod
    def _makeRequest(
            url: str,
            timeout: typing.Optional[typing.Union[int, float]] = None
            ) -> bytes:
        # Leave this enabled to catch bugs that are causing LOTS of requests
        logging.info(f'Downloading tile {url}')

        startTime = time.time()

        # Any exception that occurs here is just allowed to pass up to the caller
        try:
            with urllib.request.urlopen(url=url, timeout=timeout) as response:
                content = response.read()
        except urllib.error.HTTPError as ex:
            raise RuntimeError(f'Tile request failed for {url} ({ex.reason})') from ex
        except urllib.error.URLError as ex:
            if isinstance(ex.reason, TimeoutError):
                raise TimeoutError(f'Tile request timeout for {url}') from ex
            raise RuntimeError(f'Tile request failed for {url} ({ex.reason})') from ex
        except Exception as ex:
            raise RuntimeError(f'Tile request failed for {url} ({ex})') from ex

        downloadTime = time.time() - startTime
        logging.debug(f'Download of tile {url} took {downloadTime}s')

        return content
