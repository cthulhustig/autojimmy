import astronomer
import enum
import typing

class Label(object):
    class Size(enum.Enum):
        Small = 0
        Large = 1

    def __init__(
            self,
            text: str,
            hex: astronomer.HexPosition,
            colour: typing.Optional[str],
            size: typing.Optional[Size],
            offsetX: typing.Optional[float],
            offsetY: typing.Optional[float]
            ) -> None:
        self._text = text
        self._hex = hex
        self._colour = colour
        self._size = size
        self._offsetX = offsetX
        self._offsetY = offsetY

    def text(self) -> str:
        return self._text

    def hex(self) -> astronomer.HexPosition:
        return self._hex

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def size(self) -> typing.Optional[Size]:
        return self._size

    # Offset in world coordinates
    def offsetX(self) -> typing.Optional[float]:
        return self._offsetX

    def offsetY(self) -> typing.Optional[float]:
        return self._offsetY
