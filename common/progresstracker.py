import common
import threading
import typing
import weakref

class ProgressTracker(object):
    def __init__(
            self,
            weight: float,
            steps: int = 0,
            updateCallback: typing.Optional[typing.Callable[[float], typing.Any]] = None,
            ) -> None:
        common.validateInt(name='steps', value=steps, min=0)
        # TODO: Not sure how to validate the callback

        self._weight = weight
        self._steps = steps
        self._progress = 0
        self._updateCallback = updateCallback
        self._children: typing.List['ProgressTracker'] = []
        self._weakParent: typing.Optional[weakref.ReferenceType['ProgressTracker']] = None

        # Avoid a lot of repeated recursion by marking nodes as complete once
        # they AND their children have completed
        self._complete = False

        self._lock = threading.RLock()

    def weight(self) -> float:
        return self._weight

    def progress(self) -> float:  # In the range 0.0 -> 1.0
        with self._lock:
            if self._complete:
                return 1.0

            if not self._children:
                if self._steps == 0:
                    return 0
                return common.clamp(self._progress / self._steps, 0.0, 1.0)

            totalProgress = 0
            for child in self._children:
                totalProgress += child.progress() * child.weight()
            totalProgress = common.clamp(totalProgress, 0.0, 1.0)
            if totalProgress == 1.0:
                self._complete = True
            return common.clamp(totalProgress, 0.0, 1.0)

    def advance(self, increment: int = 1) -> None:
        common.validateFloat(name='increment', value=increment, min=0)
        if not increment:
            return

        with self._lock:
            self._progress += increment
            self._progress = min(self._progress, self._steps)
        self._doChangeNotification()

    def complete(self) -> None:
        self._complete = True

    def createChild(
            self,
            weight: float,
            steps: int = 0
            ) -> 'ProgressTracker':
        common.validateInt(name='steps', value=steps, min=0)

        child = ProgressTracker(weight=weight, steps=steps)
        child._setParent(self)

        with self._lock:
            self._children.append(child)

        # No need to notify parent as a new child never adds anything to progress
        # so the percentage complete hasn't changed
        #self._doChangeNotification()
        return child

    def _setParent(self, parent: 'ProgressTracker') -> None:
        self._weakParent = weakref.ref(parent)

    def _parent(self) -> typing.Optional['ProgressTracker']:
        return self._weakParent() if self._weakParent else None

    def _doChangeNotification(self) -> None:
        # Walk up to root to notify all ancestors
        parent = self._parent()
        if parent:
            parent._doChangeNotification()

        # Call our callback with current percentage if set
        if self._updateCallback:
            try:
                progress = self.progress()
                self._updateCallback(progress)
            except Exception:
                # callbacks should not raise to avoid breaking callers
                # TODO: Should probably log something
                pass