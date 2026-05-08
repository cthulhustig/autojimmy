import astronomer
import typing

class Route(astronomer.Entity):
    def __init__(
            self,
            entityId: str,
            startHex: astronomer.HexPosition,
            endHex: astronomer.HexPosition,
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            routeType: typing.Optional[str] = None,
            style: typing.Optional[astronomer.LineStyle] = None,
            colour: typing.Optional[str] = None,
            width: typing.Optional[float] = None
            ) -> None:
        super().__init__(entityId=entityId)
        self._startHex = startHex
        self._endHex = endHex
        self._allegiance = allegiance
        self._routeType = routeType
        self._style = style
        self._colour = colour
        self._width = width

    def startHex(self) -> astronomer.HexPosition:
        return self._startHex

    def endHex(self) -> astronomer.HexPosition:
        return self._endHex

    def allegiance(self) -> typing.Optional[astronomer.Allegiance]:
        return self._allegiance

    def routeType(self) -> typing.Optional[str]:
        return self._routeType

    def style(self) -> typing.Optional[astronomer.LineStyle]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def width(self) -> typing.Optional[float]:
        return self._width
