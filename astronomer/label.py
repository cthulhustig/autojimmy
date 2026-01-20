import enum
import typing

class Label(object):
    class Size(enum.Enum):
        Small = 0
        Large = 1

    def __init__(
            self,
            text: str,
            x: float,
            y: float,
            colour: typing.Optional[str],
            size: typing.Optional[Size],
            wrap: bool
            ) -> None:
        self._text = text
        self._x = x
        self._y = y
        self._colour = colour
        self._size = size
        self._wrap = wrap

    def text(self) -> str:
        return self._text

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def size(self) -> typing.Optional[Size]:
        return self._size

    def wrap(self) -> bool:
        return self._wrap