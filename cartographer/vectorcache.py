import astronomer
import cartographer
import typing

class VectorCache(object):
    def __init__(
            self,
            universe: astronomer.Universe,
            graphics: cartographer.AbstractGraphics
            ):
        self._universe = universe
        self._graphics = graphics

        self.borders: typing.List[cartographer.AbstractPath] = []
        self.routes: typing.List[cartographer.AbstractPath] = []
        self._loadCache()

    def _loadCache(self) -> None:
        for vector in self._universe.vectors():
            if vector.layer() is astronomer.VectorLayer.Border:
                self.borders.append(self._graphics.createPath(
                    points=[cartographer.PointF(x, y) for x, y in vector.points()],
                    closed=vector.closed()))
            elif vector.layer() is astronomer.VectorLayer.Route:
                self.routes.append(self._graphics.createPath(
                    points=[cartographer.PointF(x, y) for x, y in vector.points()],
                    closed=vector.closed()))