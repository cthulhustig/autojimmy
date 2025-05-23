import logging
import requests
import time
import threading
import travellermap
import typing

class TileClient(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()
    _baseMapUrl = None
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
    def configure(baseMapUrl: str) -> None:
        if TileClient._instance:
            raise RuntimeError('You can\'t configure map proxy after the singleton has been initialised')
        TileClient._baseMapUrl = baseMapUrl

    def tile(
            self,
            milieu: travellermap.Milieu,
            style: travellermap.Style,
            hex: travellermap.HexPosition,
            options: typing.Iterable[travellermap.Option],
            linearScale: float = 64,
            width: int = 256,
            height: int = 256,
            timeout: typing.Optional[typing.Union[int, float]] = None,
            ) -> typing.Tuple[bytes, travellermap.MapFormat]:
        mapX, mapY = hex.mapSpace()

        # Calculate position to center tile on map position
        tilePosition = (
            (mapX * linearScale - (width / 2)) / width,
            (-mapY * linearScale - (height / 2)) / height)

        url = travellermap.formatTileUrl(
            baseMapUrl=TileClient._baseMapUrl,
            milieu=milieu,
            style=style,
            options=options,
            tilePosition=tilePosition,
            linearScale=linearScale,
            minimal=True)

        with self._lock:
            content = TileClient._cache.get(url)
        if content != None:
            logging.debug(f'Tile cache hit for {url}')
            return content

        content = TileClient._makeRequest(
            url=url,
            timeout=timeout)

        with self._lock:
            TileClient._cache[url] = content

        return content

    @staticmethod
    def _makeRequest(
            url: str,
            timeout: typing.Optional[typing.Union[int, float]] = None
            ) -> typing.Tuple[bytes, travellermap.MapFormat]:
        # Leave this enabled to catch bugs that are causing LOTS of requests
        logging.info(f'Downloading tile {url}')

        startTime = time.time()

        # Any exception that occurs here is just allowed to pass up to the caller
        try:
            with requests.get(
                    url=url,
                    timeout=timeout
                    ) as response:
                contentType = response.headers['content-type']
                mapFormat = travellermap.mimeTypeToMapFormat(contentType)
                if not mapFormat:
                    raise RuntimeError(f'Unknown format {contentType}')

                content = response.content
        except requests.Timeout as ex:
            raise TimeoutError(f'Tile request timeout for {url}') from ex
        except Exception as ex:
            raise RuntimeError(f'Tile request failed for {url} ({ex})') from ex

        downloadTime = time.time() - startTime
        logging.debug(f'Download of tile {url} took {downloadTime}s')

        return (content, mapFormat)
