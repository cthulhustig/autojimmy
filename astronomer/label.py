import enum
import typing

class Label(object):
    class Size(enum.Enum):
        Small = 0
        Large = 1

    def __init__(
            self,
            text: str,
            worldX: float,
            worldY: float,
            colour: typing.Optional[str],
            size: typing.Optional[Size],
            wrap: bool
            ) -> None:
        self._text = text
        self._worldX = worldX
        self._worldY = worldY
        self._colour = colour
        self._size = size
        self._wrap = wrap

    def text(self) -> str:
        return self._text

    # Offset from top left of sector in world coordinates
    def worldX(self) -> float:
        return self._worldX

    def worldY(self) -> float:
        return self._worldY

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def size(self) -> typing.Optional[Size]:
        return self._size

    def wrap(self) -> bool:
        return self._wrap