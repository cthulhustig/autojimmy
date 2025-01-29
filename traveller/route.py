import enum
import travellermap
import typing

class Route(object):
    class Style(enum.Enum):
        Solid = 0
        Dashed = 1
        Dotted = 2

    def __init__(
            self,
            startHex: travellermap.HexPosition,
            endHex: travellermap.HexPosition,
            allegiance: typing.Optional[str],
            type: typing.Optional[str],
            style: typing.Optional[Style],
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

    def startHex(self) -> travellermap.HexPosition:
        return self._startHex

    def endHex(self) -> travellermap.HexPosition:
        return self._endHex

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

    def type(self) -> typing.Optional[str]:
        return self._type

    def style(self) -> typing.Optional[Style]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def width(self) -> typing.Optional[float]:
        return self._width