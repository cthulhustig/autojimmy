import enum
import travellermap
import typing

class Label(object):
    class Size(enum.Enum):
        Small = 0
        Large = 1

    def __init__(
            self,
            text: str,
            hex: travellermap.HexPosition,
            colour: str,
            wrap: bool,
            size: typing.Optional[Size],
            offsetX: typing.Optional[float],
            offsetY: typing.Optional[float]
            ) -> None:
        self._text = text
        self._hex = hex
        self._colour = colour
        self._wrap = wrap
        self._size = size
        self._offsetX = offsetX
        self._offsetY = offsetY

    def text(self) -> str:
        return self._text

    def hex(self) -> travellermap.HexPosition:
        return self._hex

    def colour(self) -> str:
        return self._colour

    def wrap(self) -> bool:
        return self._wrap

    def size(self) -> typing.Optional[Size]:
        return self._size

    # TODO: Make it clear what units these are in
    def offsetX(self) -> typing.Optional[float]:
        return self._offsetX

    def offsetY(self) -> typing.Optional[float]:
        return self._offsetY
