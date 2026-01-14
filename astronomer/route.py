import astronomer
import typing

class Route(object):
    def __init__(
            self,
            startHex: astronomer.HexPosition,
            endHex: astronomer.HexPosition,
            allegiance: typing.Optional[astronomer.Allegiance],
            type: typing.Optional[str],
            style: typing.Optional[astronomer.LineStyle],
            colour: typing.Optional[str],
            width: typing.Optional[float]
            ) -> None:
        self._startHex = startHex
        self._endHex = endHex
        self._allegiance = allegiance
        self._type = type
        self._style = style
        self._colour = colour
        self._width = width

    def startHex(self) -> astronomer.HexPosition:
        return self._startHex

    def endHex(self) -> astronomer.HexPosition:
        return self._endHex

    def allegiance(self) -> typing.Optional[astronomer.Allegiance]:
        return self._allegiance

    def type(self) -> typing.Optional[str]:
        return self._type

    def style(self) -> typing.Optional[astronomer.LineStyle]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def width(self) -> typing.Optional[float]:
        return self._width
