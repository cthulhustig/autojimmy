import common
import threading
import travellermap
import typing
import urllib.parse

class TileClient(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()
    _travellerMapBaseUrl = travellermap.TravellerMapBaseUrl

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
    
    # The Traveller Map URL specified here is only used if the tile proxy isn't running
    @staticmethod
    def configure(travellerMapBaseUrl: str) -> None:
        if TileClient._instance:
            raise RuntimeError('You can\'t configure tile proxy after the singleton has been initialised')        
        TileClient._travellerMapBaseUrl = travellerMapBaseUrl

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
        position = travellermap.TilePosition(
            tileX=(mapX * linearScale - (width / 2)) / width,
            tileY=(-mapY * linearScale - (height / 2)) / height,
            linearScale=linearScale)
        
        tileProxyPort = travellermap.TileProxy.instance().port()
        if tileProxyPort:
            assert(isinstance(tileProxyPort, int))
            baseUrl = f'http://127.0.0.1:{tileProxyPort}/api/tile'
        else:
            baseUrl = urllib.parse.urljoin(self._travellerMapBaseUrl, '/api/tile')
            
        url = travellermap.formatMapUrl(
            baseUrl=baseUrl,
            milieu=milieu,
            style=style,
            options=options,
            position=position,
            minimal=True)

        return common.RequestCache.instance().makeRequest(
            url=url,
            timeout=timeout,
            cacheInMemory=True)
