import enum
import travellermap
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
for code, value in travellermap.ehexCodeMap().items():
    _PlanetoidBeltDescriptionMap[code] = str(value)
_PlanetoidBeltDescriptionMap['?'] = 'Unknown'

_GasGiantDescriptionMap = _PlanetoidBeltDescriptionMap

class PBG(object):
    class Element(enum.Enum):
        PopulationMultiplier = 0
        PlanetoidBelts = 1
        GasGiants = 2

    _elementDescriptionMaps: typing.List[typing.Mapping[str, str]] = [
        _PopulationMultiplierDescriptionMap,
        _PlanetoidBeltDescriptionMap,
        _GasGiantDescriptionMap
    ]

    def __init__(
            self,
            string
            ) -> None:
        self._string = string
        self._sanitised = PBG._sanitise(self._string)

    def string(self) -> str:
        return self._string

    def sanitised(self) -> str:
        return self._sanitised

    def code(
            self,
            element: Element
            ) -> str:
        return self._sanitised[element.value]

    def description(
            self,
            element: Element
            ) -> str:
        return PBG._elementDescriptionMaps[element.value][self.code(element)]

    @staticmethod
    def codeList(element: Element) -> typing.Iterable[str]:
        return PBG._elementDescriptionMaps[element.value].keys()

    @staticmethod
    def descriptionMap(element: Element) -> typing.Mapping[str, str]:
        return PBG._elementDescriptionMaps[element.value]

    @staticmethod
    def _sanitise(pbg: str) -> str:
        sanitized = ''
        for index in range(3):
            sanitized += PBG._sanitiseElement(index, pbg)
        return sanitized

    @staticmethod
    def _sanitiseElement(index: int, pbg: str) -> str:
        if index >= len(pbg):
            return '?'
        code = pbg[index].upper()
        value = travellermap.ehexToInteger(value=code, default=None)
        if value == None:
            return '?'

        if index == PBG.Element.PopulationMultiplier.value:
            # Some worlds use X as the population multiplier to indicate unknown. In reality a
            # multipliers over 9 doesn't make sense as it would push the world up another UWP
            # population code so it should be safe to ignore anything higher. No worlds currently
            # have a multiplier over 9
            if value > 9:
                return '?'
        elif index == PBG.Element.PlanetoidBelts.value or index == PBG.Element.GasGiants.value:
            # Some worlds use X as the planetoid belt and gas giant counts to indicate unknown.
            # In theory any ehex value could be a valid planetoid belt and gas giant count, however
            # in practice no worlds currently have more than 14 planetoid belts or 12 gas giants.
            # It seems safe to just replace any X with ? for unknown
            if code == 'X':
                return '?'

        return code
