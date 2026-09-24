import astronomer
import common
import numba
import typing

# This code isn't actually used for anything at the moment as I couldn't get it
# any faster than the current algorithm for radius checks when route planning,
# it was always fractionally slower. I've kept it as it's close and I might figure
# out a way to get it faster.
# If I do ever decide to use it, I'll need to add numba to the dependencies.

@numba.njit
def _parsecsBetween(
        x1: int, y1: int,
        x2: int, y2: int
        ) -> int:
    dx = x2 - x1
    dy = y2 - y1

    adx = dx if dx >= 0 else -dx

    ody = dy + (adx // 2)

    if ((x1 & 0b1) == 0) and ((x2 & 0b1) != 0):
        ody += 1

    max = ody if ody > adx else adx
    adx -= ody
    return adx if adx > max else max

class WorldTree(object):
    class _Node(object):
        # Used fixed array for attributes rather than dictionary for space
        # and faster access
        __slots__ = (
            'left',
            'top',
            'width',
            'height',
            'worlds',
            'children',
            'bucketSize',
            'minWidth',
            'minHeight',
            'centerX',
            'centerY'
        )

        def __init__(
                self,
                left: int,
                top: int,
                width: int,
                height: int,
                bucketSize: int,
                minWidth: int,
                minHeight: int,
                ) -> None:
            self.left = left
            self.top = top
            self.width = width
            self.height = height
            self.bucketSize = bucketSize
            self.minWidth = minWidth
            self.minHeight = minHeight
            self.worlds: typing.List[typing.Tuple[
                int, int, # Hex position
                astronomer.World]] = []
            self.children: typing.Optional[typing.List[WorldTree._Node]] = None

            self.centerX = left + (width // 2)
            self.centerY = top + (height // 2)

        def contains(self, x: int, y: int) -> bool:
            return self.left <= x < self.left + self.width and self.top <= y < self.top + self.height

        def childIndex(self, x: int, y: int) -> int:
            index = 0
            if x >= self.centerX:
                index += 1
            if y >= self.centerY:
                index += 2
            return index

        def makeChildren(self) -> None:
            if self.children is not None:
                return

            childWidth = self.width // 2
            childHeight = self.height // 2
            if childWidth < 1 or childHeight < 1:
                return

            self.children = [
                WorldTree._Node(self.left, self.top, childWidth, childHeight, self.bucketSize, self.minWidth, self.minHeight),
                WorldTree._Node(self.left + childWidth, self.top, childWidth, childHeight, self.bucketSize, self.minWidth, self.minHeight),
                WorldTree._Node(self.left, self.top + childHeight, childWidth, childHeight, self.bucketSize, self.minWidth, self.minHeight),
                WorldTree._Node(self.left + childWidth, self.top + childHeight, childWidth, childHeight, self.bucketSize, self.minWidth, self.minHeight)]

            for worldX, worldY, world in self.worlds:
                childIndex = self.childIndex(worldX, worldY)
                self.children[childIndex].worlds.append((worldX, worldY, world))

            self.worlds.clear()

        def shouldSubdivide(self) -> bool:
            return (
                len(self.worlds) > self.bucketSize and
                self.width > self.minWidth and (self.width & 1) == 0 and
                self.height > self.minHeight and (self.height & 1) == 0)

        def insert(self, world: astronomer.World) -> None:
            x, y = world.hex().absolute()
            if self.children is None:
                self.worlds.append((x, y, world))
                if self.shouldSubdivide():
                    self.makeChildren()
            else:
                childIndex = self.childIndex(x, y)
                self.children[childIndex].insert(world)

        def queryArea(self, left: int, top: int, right: int, bottom: int, out: typing.List[astronomer.World]) -> None:
            if self.children is None:
                for x, y, world in self.worlds:
                    if left <= x <= right and top <= y <= bottom:
                        out.append(world)
            else:
                if left < self.centerX:
                    if top < self.centerY:
                        self.children[0].queryArea(left, top, right, bottom, out)
                    if bottom >= self.centerY:
                        self.children[2].queryArea(left, top, right, bottom, out)

                if right >= self.centerX:
                    if top < self.centerY:
                        self.children[1].queryArea(left, top, right, bottom, out)
                    if bottom >= self.centerY:
                        self.children[3].queryArea(left, top, right, bottom, out)

        def queryRadius(
                self,
                left: int,
                top: int,
                right: int,
                bottom: int,
                centerX: int,
                centerY: int,
                radius: int,
                out: typing.List[astronomer.World]
                ) -> None:
            if self.children is None:
                for worldX, worldY, world in self.worlds:
                    if left <= worldX <= right and top <= worldY <= bottom and _parsecsBetween(worldX, worldY, centerX, centerY) <= radius:
                        out.append(world)
            else:
                if left < self.centerX:
                    if top < self.centerY:
                        self.children[0].queryRadius(left, top, right, bottom, centerX, centerY, radius, out)
                    if bottom >= self.centerY:
                        self.children[2].queryRadius(left, top, right, bottom, centerX, centerY, radius, out)

                if right >= self.centerX:
                    if top < self.centerY:
                        self.children[1].queryRadius(left, top, right, bottom, centerX, centerY, radius, out)
                    if bottom >= self.centerY:
                        self.children[3].queryRadius(left, top, right, bottom, centerX, centerY, radius, out)

        def remove(self, x: int, y: int) -> None:
            if self.children is None:
                for index in range(len(self.worlds) - 1, -1, -1):
                    worldX, worldY, _ = self.worlds[index]
                    if x == worldX and y == worldY:
                        del self.worlds[index]
                        break
            else:
                self.children[self.childIndex(x, y)].remove(x, y)

    def __init__(
            self,
            initLeft: int,
            initTop: int,
            initWidth: int,
            initHeight: int,
            bucketSize: int = 10,
            minNodeWidth: int = 4,
            minNodeHeight: int = 4
            ) -> None:
        self._bucketSize = bucketSize
        self._minNodeWidth = minNodeWidth
        self._minNodeHeight = minNodeHeight
        self._root = WorldTree._Node(initLeft, initTop, initWidth, initHeight, self._bucketSize, self._minNodeWidth, self._minNodeHeight)
        self._worlds: typing.Dict[typing.Tuple[int, int], astronomer.World] = {}

    def insert(self, world: astronomer.World) -> None:
        pos = world.hex().absolute()
        self._expandRootToContain(*pos)
        self._root.insert(world)
        self._worlds[pos] = world

    def remove(
            self,
            hex: astronomer.HexPosition
            ) -> None:
        pos = hex.absolute()
        self._root.remove(*pos)
        if pos in self._worlds:
            del self._worlds[pos]

    def worlds(self) -> typing.Collection[astronomer.World]:
        return common.ConstCollectionRef(self._worlds.values())

    def find(
            self,
            hex: astronomer.HexPosition
            ) -> typing.Optional[astronomer.World]:
        return self._worlds.get(hex.absolute())

    def queryArea(
            self,
            left: int,
            top: int,
            right: int,
            bottom: int,
            ) -> typing.List[astronomer.World]:
        if right < self._root.left or left >= self._root.left + self._root.width or bottom < self._root.top or top >= self._root.top + self._root.height:
            return []

        items: typing.List[astronomer.World] = []
        self._root.queryArea(left, top, right, bottom, items)
        return items

    def queryRadius(
            self,
            center: astronomer.HexPosition,
            radius: int
            ) -> typing.List[astronomer.World]:
        centerX, centerY = center.absolute()
        left = centerX - radius
        top = centerY - radius
        right = centerX + radius
        bottom = centerY + radius

        if right < self._root.left or left >= self._root.left + self._root.width or bottom < self._root.top or top >= self._root.top + self._root.height:
            return []

        results = []
        self._root.queryRadius(
            left,
            top,
            right,
            bottom,
            centerX,
            centerY,
            radius,
            results)
        return results

    def _expandRootToContain(self, x: int, y: int) -> None:
        while not self._root.contains(x, y):
            left = self._root.left
            top = self._root.top
            width = self._root.width
            height = self._root.height

            expandLeft = x < left
            expandTop = y < top
            newLeft = left - width if expandLeft else left
            newTop = top - height if expandTop else top
            newWidth = width * 2
            newHeight = height * 2

            newRoot = WorldTree._Node(newLeft, newTop, newWidth, newHeight, self._bucketSize, self._minNodeWidth, self._minNodeHeight)
            newRoot.makeChildren()

            childIndex = 0
            if expandLeft:
                childIndex += 1
            if expandTop:
                childIndex += 2

            newRoot.children[childIndex] = self._root
            self._root = newRoot

