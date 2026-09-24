import cartographer
import typing

class _QuadTreeNode(object):
    def __init__(
            self,
            bounds: cartographer.RectangleF,
            maxObjects: int,
            maxDepth: int,
            depth: int = 0) -> None:
        self.bounds = cartographer.RectangleF(bounds)
        self.maxObjects = maxObjects
        self.maxDepth = maxDepth
        self.depth = depth
        self.objects: typing.List[typing.Tuple[object, cartographer.RectangleF]] = []
        self.children: typing.Optional[typing.List['_QuadTreeNode']] = None

    def add(self, obj: object, bounds: cartographer.RectangleF) -> None:
        if self.children is not None:
            child = self._containingChild(bounds)
            if child is not None:
                child.add(obj, bounds)
                return

        self.objects.append((obj, bounds))
        if len(self.objects) > self.maxObjects and self.depth < self.maxDepth:
            self._split()

    def remove(self, obj: object, bounds: typing.Optional[cartographer.RectangleF] = None) -> bool:
        for index, (storedObject, _) in enumerate(self.objects):
            if storedObject is obj:
                del self.objects[index]
                return True

        if self.children is not None:
            if bounds is None:
                for child in self.children:
                    if child.remove(obj):
                        return True
            else:
                # TODO: Need to check this path is working
                child = self._containingChild(bounds=bounds)
                if child is not None:
                    if child.remove(obj):
                        return  True
        return False

    def query(self, bounds: cartographer.RectangleF, results: typing.List[object]) -> None:
        if not self.bounds.intersects(bounds):
            return

        for obj, objectBounds in self.objects:
            if objectBounds.intersects(bounds):
                results.append(obj)

        if self.children is not None:
            for child in self.children:
                child.query(bounds, results)

    def makeChildren(self) -> None:
        if self.children is not None:
            return

        x, y, width, height = self.bounds.rect()
        halfWidth = width / 2
        halfHeight = height / 2
        self.children = [
            _QuadTreeNode(cartographer.RectangleF(x, y, halfWidth, halfHeight), self.maxObjects, self.maxDepth, self.depth + 1),
            _QuadTreeNode(cartographer.RectangleF(x + halfWidth, y, width - halfWidth, halfHeight), self.maxObjects, self.maxDepth, self.depth + 1),
            _QuadTreeNode(cartographer.RectangleF(x, y + halfHeight, halfWidth, height - halfHeight), self.maxObjects, self.maxDepth, self.depth + 1),
            _QuadTreeNode(cartographer.RectangleF(x + halfWidth, y + halfHeight, width - halfWidth, height - halfHeight), self.maxObjects, self.maxDepth, self.depth + 1)]

    def clear(self) -> None:
        self.objects.clear()
        self.children.clear()

    def _split(self) -> None:
        self.makeChildren()
        objects = self.objects
        self.objects = []
        for obj, bounds in objects:
            child = self._containingChild(bounds)
            if child is None:
                self.objects.append((obj, bounds))
            else:
                child.add(obj, bounds)

    def _containingChild(self, bounds: cartographer.RectangleF) -> typing.Optional['_QuadTreeNode']:
        for child in self.children or []:
            if child.bounds.contains(bounds):
                return child
        return None

class QuadTree(object):
    def __init__(
            self,
            bounds: cartographer.RectangleF,
            maxObjects: int = 10,
            maxDepth: int = 8) -> None:
        if maxObjects < 1:
            raise ValueError('maxObjects must be at least 1')
        if maxDepth < 0:
            raise ValueError('maxDepth must not be negative')
        if bounds.width() <= 0 or bounds.height() <= 0:
            raise ValueError('bounds must have positive width and height')

        self._maxObjects = maxObjects
        self._maxDepth = maxDepth
        self._root = _QuadTreeNode(bounds, maxObjects, maxDepth)

    def add(self, obj: object, bounds: cartographer.RectangleF) -> None:
        objectBounds = cartographer.RectangleF(bounds)
        self._expandRootToContain(objectBounds)
        self._root.add(obj, objectBounds)

    def insert(self, obj: object, bounds: cartographer.RectangleF) -> None:
        self.add(obj=obj, bounds=bounds)

    def remove(self, obj: object, bounds: typing.Optional[cartographer.RectangleF] = None) -> bool:
        return self._root.remove(obj, bounds)

    def query(self, bounds: cartographer.RectangleF) -> typing.List[object]:
        results: typing.List[object] = []
        self._root.query(bounds, results)
        return results

    def clear(self) -> None:
        self._root.clear()

    def _expandRootToContain(self, objectBounds: cartographer.RectangleF) -> None:
        while not self._root.bounds.contains(objectBounds):
            left, top, width, height = self._root.bounds.rect()
            expandLeft = objectBounds.left() < left
            expandTop = objectBounds.top() < top
            newLeft = left - width if expandLeft else left
            newTop = top - height if expandTop else top

            newRoot = _QuadTreeNode(
                cartographer.RectangleF(newLeft, newTop, width * 2, height * 2),
                self._maxObjects,
                self._maxDepth)
            newRoot.makeChildren()

            childIndex = 0
            if expandLeft:
                childIndex += 1
            if expandTop:
                childIndex += 2
            newRoot.children[childIndex] = self._root
            self._root = newRoot

