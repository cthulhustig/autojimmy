import common
import typing
import weakref

P = typing.ParamSpec("P")

class ObserverSet(typing.Generic[P]):
    def __init__(self):
        super().__init__()
        self._observers = common.OrderedSet()

    def register(self, callback: typing.Callable[P, None]) -> None:
        if not callable(callback):
            raise ValueError('Callback is not callable')

        self._observers.add(self._createObserver(callback=callback))

    def unregister(self, callback: typing.Callable[P, None]) -> None:
        if not callable(callback):
            raise ValueError('Callback is not callable')

        self._observers.discard(self._createObserver(callback=callback))

    @typing.overload
    def notify(self, *args: P.args, **kwargs: P.kwargs) -> None: ...
    @typing.overload
    def notify(
        self,
        *args: P.args,
        exceptionCallback: typing.Optional[typing.Callable[[Exception], None]] = None) -> None: ...

    def notify(
            self,
            *args: P.args,
            exceptionCallback: typing.Optional[typing.Callable[[Exception], None]] = None,
            # NOTE: Named arguments other than exceptionCallback aren't supported
            # as they don't make sense for a callback as there is no guarantee
            # what the arguments are called. However, it needs to be here otherwise
            # typing breaks.
            **kwargs: P.kwargs
            ) -> None:
        if kwargs:
            raise ValueError('Named arguments aren\'t supported when notifying observers')

        # NOTE: Create a copy of the observers to ovoid issues if notifying
        # an observer causes a change in the registered observers
        for observer in list(self._observers):
            if isinstance(observer, weakref.WeakMethod):
                method = observer()
            else:
                method = observer

            if method:
                try:
                    method(*args)
                except Exception as ex:
                    if exceptionCallback:
                        exceptionCallback(ex)

    def _createObserver(
            self,
            callback: typing.Callable[P, None]
            ) -> typing.Union[typing.Callable[P, None], weakref.WeakMethod]:
        if hasattr(callback, '__self__'):
            return weakref.WeakMethod(callback, self._removeObserver)
        else:
            return callback

    def _removeObserver(
            self,
            observer: typing.Union[typing.Callable[P, None], weakref.WeakMethod]
            ) -> None:
        self._observers.discard(observer)

    @typing.overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None: ...
    @typing.overload
    def __call__(
        self,
        *args: P.args,
        exceptionCallback: typing.Optional[typing.Callable[[Exception], None]] = None) -> None: ...

    def __call__(
            self,
            *args: P.args,
            exceptionCallback: typing.Optional[typing.Callable[[Exception], None]] = None,
            # NOTE: Named arguments other than exceptionCallback aren't supported
            # as they don't make sense for a callback as there is no guarantee
            # what the arguments are called. However, it needs to be here otherwise
            # typing breaks.
            **kwargs: P.kwargs
            ) -> None:
        if kwargs:
            raise ValueError('Named arguments aren\'t supported when notifying observers')
        self.notify(*args, exceptionCallback=exceptionCallback)

    def __len__(self) -> int:
        return len(self._observers)

    def __contains__(self, item: object) -> bool:
        if not callable(item):
            return False

        testObserver = self._createObserver(callback=item)
        return testObserver in self._observers