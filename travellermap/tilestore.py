import common
import math
import threading
import travellermap
import typing

class TileStore(object):
    _ParsecScaleX = math.cos(math.pi / 6) # cosine 30°
    _ParsecScaleY = 1

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
            worldX: int,
            worldY: int,
            options: typing.Iterable[travellermap.Option],
            linearScale: float = 64,
            width: int = 256,
            height: int = 256,
            timeout: typing.Optional[typing.Union[int, float]] = None,
            ) -> bytes:
        mapX, mapY = TileStore._worldSpaceToMapSpace(
            worldX=worldX,
            worldY=worldY)

        # Calculate position to center tile on map position
        position = travellermap.TilePosition(
            tileX=(mapX * linearScale - (width / 2)) / width,
            tileY=(-mapY * linearScale - (height / 2)) / height,
            linearScale=linearScale)

        url = travellermap.formatMapUrl(
            baseUrl=f'{travellerMapUrl}/api/tile',
            milieu=milieu,
            style=style,
            options=options,
            position=position,
            minimal=True)

        return common.RequestCache.instance().makeRequest(
            url=url,
            timeout=timeout,
            cacheInMemory=True)

    @staticmethod
    def _worldSpaceToMapSpace(
            worldX: int,
            worldY: int
            ) -> typing.Tuple[float, float]:
        ix = worldX - 0.5
        iy = worldY - 0.5 if (worldX % 2) == 0 else worldY
        x = ix * TileStore._ParsecScaleX
        y = iy * -TileStore._ParsecScaleY
        return x, y
