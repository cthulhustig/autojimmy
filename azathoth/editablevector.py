import astronomer
import typing

class EditableMapVector(astronomer.MapVector):
    def __init__(
            self,
            entityId: str,
            points: typing.Sequence[typing.Tuple[float, float]],
            layer: astronomer.VectorLayer,
            closed: bool
            ) -> None:
        super().__init__(
            entityId=entityId,
            points=points,
            layer=layer,
            closed=closed)
