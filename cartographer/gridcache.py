import astronomer
import common
import cartographer

class GridCache(object):
    _Slop = 1

    def __init__(
            self,
            graphics: cartographer.AbstractGraphics,
            capacity: int
            ) -> None:
        self._graphics = graphics
        self._cache = common.LRUCache(capacity=capacity)

    def grid(
            self,
            parsecWidth: int,
            parsecHeight: int
            ) -> cartographer.AbstractPointList:
        key = (parsecWidth, parsecHeight)
        grid = self._cache.get(key)
        if grid:
            return grid

        points = []
        for px in range(-GridCache._Slop, parsecWidth + GridCache._Slop):
            yOffset = 0 if ((px % 2) != 0) else 0.5
            for py in range(-GridCache._Slop, parsecHeight + GridCache._Slop):
                point1 = cartographer.PointF(
                    x=px + -astronomer.HexWidthOffset,
                    y=py + 0.5 + yOffset)
                point2 = cartographer.PointF(
                    x=px + astronomer.HexWidthOffset,
                    y=py + 1.0 + yOffset)
                point3 = cartographer.PointF(
                    x=px + 1.0 - astronomer.HexWidthOffset,
                    y=py + 1.0 + yOffset)
                point4 = cartographer.PointF(
                    x=px + 1.0 + astronomer.HexWidthOffset,
                    y=py + 0.5 + yOffset)

                points.append(point1)
                points.append(point2)

                points.append(point2)
                points.append(point3)

                points.append(point3)
                points.append(point4)

        grid = self._graphics.createPointList(points=points)
        self._cache[key] = grid
        return grid

    def clear(self) -> None:
        self._cache.clear()
