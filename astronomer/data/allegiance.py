import astronomer
import typing

class Allegiance(object):
    def __init__(
            self,
            code: str,
            name: str,
            legacyCode: typing.Optional[str] = None,
            baseCode: typing.Optional[str] = None,
            routeColour: typing.Optional[str] = None,
            routeStyle: typing.Optional[astronomer.LineStyle] = None,
            routeWidth: typing.Optional[float] = None,
            borderColour: typing.Optional[str] = None,
            borderStyle: typing.Optional[astronomer.LineStyle] = None
            ) -> None:
        self._code = code
        self._name = name
        self._legacyCode = legacyCode
        self._baseCode = baseCode
        self._routeColour = routeColour
        self._routeStyle = routeStyle
        self._routeWidth = routeWidth
        self._borderColour = borderColour
        self._borderStyle = borderStyle

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def legacyCode(self) -> typing.Optional[str]:
        return self._legacyCode

    # The base code is used in cases where a region has an allegiance that's a
    # subgroup of a larger allegiance. For example the Sylean Worlds in Core
    # have the allegiance ImSy but are still part of the Imperium so those
    # worlds have the base allegiance Im
    def baseCode(self) -> typing.Optional[str]:
        return self._baseCode

    def routeColour(self) -> typing.Optional[str]:
        return self._routeColour

    def routeStyle(self) -> typing.Optional[astronomer.LineStyle]:
        return self._routeStyle

    def routeWidth(self) -> typing.Optional[str]:
        return self._routeWidth

    def borderColour(self) -> typing.Optional[str]:
        return self._borderColour

    def borderStyle(self) -> typing.Optional[astronomer.LineStyle]:
        return self._borderStyle
