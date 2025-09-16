import math
import typing

def linearScaleToLogScale(linearScale: float) -> float:
    return 1 + math.log2(linearScale)

def logScaleToLinearScale(logScale: float) -> float:
    return math.pow(2, logScale - 1)

class MapScale(object):
    @typing.overload
    def __init__(self, linear: 'float') -> None: ...
    @typing.overload
    def __init__(self, log: 'float') -> None: ...
    @typing.overload
    def __init__(self, other: 'MapScale') -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        argCount = len(args) + len(kwargs)
        if argCount != 1:
            raise ValueError('Invalid number of arguments')

        if args:
            other = args[0]
        else:
            other = kwargs.get('other')

        if other is not None:
            if not isinstance(other, MapScale):
                raise TypeError('The other parameter must be a MapScale')
            self._linear = other._linear
            self._log = other._log
        else:
            linear = kwargs.get('linear')
            log = kwargs.get('log')
            if linear is None and log is None:
                raise ValueError('Invalid arguments')

            self._linear = float(linear) if linear is not None else None
            self._log = float(log) if log is not None else None

    @property
    def linear(self) -> float:
        if self._linear is None:
            self._linear = logScaleToLinearScale(self._log)
        return self._linear

    @linear.setter
    def linear(self, value: float) -> None:
        if value == self._linear:
            return # Nothing to do
        self._linear = float(value)
        if self._log is not None:
            self._log = None

    @property
    def log(self) -> float:
        if self._log is None:
            self._log = linearScaleToLogScale(self._linear)
        return self._log

    @log.setter
    def log(self, value: float) -> None:
        if value == self._log:
            return # Nothing to do
        self._log = float(value)
        if self._linear is not None:
            self._linear = None

    def __eq__(self, other) -> bool:
        if isinstance(other, MapScale):
            return self.log == other.log
        return NotImplemented

    def __lt__(self, other) -> bool:
        if isinstance(other, MapScale):
            return self.log < other.log
        return NotImplemented

    def __gt__(self, other) -> bool:
        if isinstance(other, MapScale):
            return self.log > other.log
        return NotImplemented

    def __le__(self, other) -> bool:
        if isinstance(other, MapScale):
            return self.log <= other.log
        return NotImplemented

    def __ge__(self, other) -> bool:
        if isinstance(other, MapScale):
            return self.log >= other.log
        return NotImplemented

    def __ne__(self, other) -> bool:
        if isinstance(other, MapScale):
            return self.log != other.log
        return NotImplemented