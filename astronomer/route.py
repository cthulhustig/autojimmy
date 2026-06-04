import astronomer
import common
import survey
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

        common.validateMandatoryObject(name='startHex', value=startHex, objectType=astronomer.HexPosition)
        common.validateMandatoryObject(name='endHex', value=endHex, objectType=astronomer.HexPosition)
        common.validateOptionalObject(name='allegiance', value=allegiance, objectType=astronomer.Allegiance)
        common.validateOptionalStr(name='routeType', value=routeType, allowEmpty=False)
        common.validateOptionalObject(name='style', value=style, objectType=astronomer.LineStyle)
        survey.validateOptionalHtmlColour(name='colour', value=colour)
        survey.validateOptionalLineWidth(name='width', value=width)

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
