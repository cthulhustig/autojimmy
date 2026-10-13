import astronomer
import common
import survey
import typing

class Allegiance(astronomer.Entity):
    def __init__(
            self,
            entityId: str,
            name: str,
            code: str,
            legacyCode: typing.Optional[str] = None,
            baseCode: typing.Optional[str] = None,
            routeColour: typing.Optional[str] = None,
            routeStyle: typing.Optional[astronomer.LineStyle] = None,
            routeWidth: typing.Optional[float] = None,
            borderColour: typing.Optional[str] = None,
            borderStyle: typing.Optional[astronomer.LineStyle] = None
            ) -> None:
        super().__init__(entityId=entityId)

        survey.validateAllegianceName(name='name', value=name)
        survey.validateAllegianceCode(name='code', value=code)
        survey.validateAllegianceCode(name='legacyCode', value=legacyCode, allowNone=True)
        survey.validateAllegianceCode(name='baseCode', value=baseCode, allowNone=True)
        survey.validateHtmlColour(name='routeColour', value=routeColour, allowNone=True)
        common.validateObject(name='routeStyle', value=routeStyle, objectType=astronomer.LineStyle, allowNone=True)
        survey.validateLineWidth(name='routeWidth', value=routeWidth, allowNone=True)
        survey.validateHtmlColour(name='borderColour', value=borderColour, allowNone=True)
        common.validateObject(name='borderStyle', value=borderStyle, objectType=astronomer.LineStyle, allowNone=True)

        self._name = name
        self._code = code
        self._legacyCode = legacyCode
        self._baseCode = baseCode
        self._routeColour = routeColour
        self._routeStyle = routeStyle
        self._routeWidth = routeWidth
        self._borderColour = borderColour
        self._borderStyle = borderStyle

    def name(self) -> str:
        return self._name

    def code(self) -> str:
        return self._code

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
