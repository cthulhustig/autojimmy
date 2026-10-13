import astronomer
import common
import enum
import typing

class VectorLayer(enum.Enum):
    Border = 0
    Rift = 1
    Route = 2

class MapVector(astronomer.Entity):
    def __init__(
            self,
            entityId: str,
            points: typing.Sequence[typing.Tuple[float, float]],
            layer: VectorLayer,
            closed: bool
            ) -> None:
        super().__init__(entityId=entityId)

        common.validateSequence(name='points', value=points, allowEmpty=False, validationFn=MapVector._validatePoint)
        common.validateObject(name='layer', value=layer, objectType=VectorLayer)
        common.validateBool(name='closed', value=closed)

        self._points = list(points)
        self._layer = layer
        self._closed = closed

    def points(self) -> typing.Sequence[typing.Tuple[float, float]]:
        return common.ConstSequenceRef(self._points)

    def layer(self) -> VectorLayer:
        return self._layer

    def closed(self) -> bool:
        return self._closed

    @staticmethod
    def _validatePoint(
            name: str,
            index: int,
            value: typing.Tuple[float, float]
            ) -> None:
        if not isinstance(value, tuple):
            raise TypeError(f'{name} element at index {index} must be a tuple')
        if len(value) != 2:
            raise TypeError(f'{name} element at index {index} must have 2 elements')
        if not isinstance(value[0], (float, int)):
            raise TypeError(f'{name} element at index {index} x value must be a float')
        if not isinstance(value[1], (float, int)):
            raise TypeError(f'{name} element at index {index} y value must be a float')