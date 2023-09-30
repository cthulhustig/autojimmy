import common
import threading
import travellermap
import typing

class TileClient(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()

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

    def tile(
            self,
            travellerMapUrl: str,
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

        # TODO: This should be pointed at the local proxy so tool tips also show custom sectors
        url = travellermap.formatMapUrl(
            #baseUrl=f'{travellerMapUrl}/api/tile',
            baseUrl='http://127.0.0.1:8002/', # TODO: Do this better
            milieu=milieu,
            style=style,
            options=options,
            position=position,
            minimal=True)

        return common.RequestCache.instance().makeRequest(
            url=url,
            timeout=timeout,
            cacheInMemory=True)
