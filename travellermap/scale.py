import math
import typing

def linearScaleToLogScale(linearScale: float) -> float:
    return 1 + math.log2(linearScale)

def logScaleToLinearScale(logScale: float) -> float:
    return math.pow(2, logScale - 1)

class Scale(object):
    @typing.overload
    def __init__(self, other: 'Scale') -> None: ...
    @typing.overload
    def __init__(self, value: float, linear: bool) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        argCount = len(args) + len(kwargs)
        if argCount == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, Scale):
                raise TypeError('The other parameter must be a Scale')
            self._linear = other._linear
            self._log = other._log
        elif argCount == 2:
            value = float(args[0] if len(args) > 0 else kwargs['value'])
            linear = bool(args[1] if len(args) > 1 else kwargs['linear'])
            self._linear = value if linear else None
            self._log = value if not linear else None
        else:
            raise ValueError('Invalid number of arguments')

    @property
    def linear(self) -> float:
        if self._linear is None:
            self._linear = logScaleToLinearScale(self._log)
        return self._linear

    @linear.setter
    def linear(self, value: float) -> None:
        if value == self._linear:
            return # Nothing to do
        self._linear = value
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
        self._log = value
        if self._linear is not None:
            self._linear = None
