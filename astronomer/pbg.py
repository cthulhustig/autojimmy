import enum
import survey
import typing

_PopulationMultiplierDescriptionMap = {
    '0': '0',
    '1': '1',
    '2': '2',
    '3': '3',
    '4': '4',
    '5': '5',
    '6': '6',
    '7': '7',
    '8': '8',
    '9': '9',
    '?': 'Unknown'
}

# There can be any number of planetoid belts or gas giants up to the max allowed by ehex.
# The mapping shouldn't be modified so the same mapping can be used for both.
_PlanetoidBeltDescriptionMap = {}
for code, value in survey.ehexCodeMap().items():
    _PlanetoidBeltDescriptionMap[code] = str(value)
_PlanetoidBeltDescriptionMap['?'] = 'Unknown'

_GasGiantDescriptionMap = _PlanetoidBeltDescriptionMap

class PBG(object):
    class Element(enum.Enum):
        PopulationMultiplier = 0
        PlanetoidBelts = 1
        GasGiants = 2

    _ValueDescriptionsMap: typing.Dict[Element, typing.Mapping[str, str]] = {
        Element.PopulationMultiplier: _PopulationMultiplierDescriptionMap,
        Element.PlanetoidBelts: _PlanetoidBeltDescriptionMap,
        Element.GasGiants: _GasGiantDescriptionMap
    }

    def __init__(
            self,
            populationMultiplier: typing.Optional[str] = None,
            planetoidBelts: typing.Optional[str] = None,
            gasGiants: typing.Optional[str] = None
            ) -> None:
        self._valueMap: typing.Dict[PBG.Element, str] = {}
        self._string = None

        if populationMultiplier is not None:
            self._valueMap[PBG.Element.PopulationMultiplier] = populationMultiplier
        if planetoidBelts is not None:
            self._valueMap[PBG.Element.PlanetoidBelts] = planetoidBelts
        if gasGiants is not None:
            self._valueMap[PBG.Element.GasGiants] = gasGiants

    def string(self) -> str:
        if self._string is None:
            self._string = survey.formatSystemPBGString(
                populationMultiplier=self._valueMap.get(PBG.Element.PopulationMultiplier),
                planetoidBelts=self._valueMap.get(PBG.Element.PlanetoidBelts),
                gasGiants=self._valueMap.get(PBG.Element.GasGiants))
        return self._string

    def code(
            self,
            element: Element
            ) -> str:
        return self._valueMap.get(element, '?')

    def numeric(
            self,
            element: Element,
            default: typing.Any = -1
            ) -> int:
        code = self._valueMap.get(element)
        if code is None:
            return default
        return survey.ehexToInteger(code, default)

    def description(
            self,
            element: Element
            ) -> str:
        return PBG._ValueDescriptionsMap[element][self.code(element)]

    def isUnknown(self) -> bool:
        return len(self._valueMap) == 0

    @staticmethod
    def descriptionMap(element: Element) -> typing.Mapping[str, str]:
        return PBG._ValueDescriptionsMap[element]

