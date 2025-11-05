import astronomer
import enum
import typing

# Types and ehex mappings taken from Traveller Map source code (world_utils.js).
# I've no idea why mappings have so many repeated values

_HeterogeneityDescriptionMap = {
    '0': 'N/A',
    '1': 'Monolithic',
    '2': 'Monolithic',
    '3': 'Monolithic',
    '4': 'Harmonious',
    '5': 'Harmonious',
    '6': 'Harmonious',
    '7': 'Discordant',
    '8': 'Discordant',
    '9': 'Discordant',
    'A': 'Discordant',
    'B': 'Discordant',
    'C': 'Fragmented',
    'D': 'Fragmented',
    'E': 'Fragmented',
    'F': 'Fragmented',
    'G': 'Fragmented',
    '?': 'Unknown'
}

_AcceptanceDescriptionMap = {
    '0': 'N/A',
    '1': 'Extremely xenophobic',
    '2': 'Very xenophobic',
    '3': 'Xenophobic',
    '4': 'Extremely aloof',
    '5': 'Very aloof',
    '6': 'Aloof',
    '7': 'Aloof',
    '8': 'Friendly',
    '9': 'Friendly',
    'A': 'Very friendly',
    'B': 'Extremely friendly',
    'C': 'Xenophilic',
    'D': 'Very xenophilic',
    'E': 'Extremely xenophilic',
    'F': 'Extremely xenophilic',
    '?': 'Unknown'
}

_StrangenessDescriptionMap = {
    '0': 'N/A',
    '1': 'Very typical',
    '2': 'Typical',
    '3': 'Somewhat typical',
    '4': 'Somewhat distinct',
    '5': 'Distinct',
    '6': 'Very distinct',
    '7': 'Confusing',
    '8': 'Very confusing',
    '9': 'Extremely confusing',
    'A': 'Incomprehensible',
    '?': 'Unknown'
}

_SymbolsDescriptionMap = {
    '0': 'Extremely concrete',
    '1': 'Extremely concrete',
    '2': 'Very concrete',
    '3': 'Very concrete',
    '4': 'Concrete',
    '5': 'Concrete',
    '6': 'Somewhat concrete',
    '7': 'Somewhat concrete',
    '8': 'Somewhat abstract',
    '9': 'Somewhat abstract',
    'A': 'Abstract',
    'B': 'Abstract',
    'C': 'Very abstract',
    'D': 'Very abstract',
    'E': 'Extremely abstract',
    'F': 'Extremely abstract',
    'G': 'Extremely abstract',
    'H': 'Incomprehensibly abstract',
    'J': 'Incomprehensibly abstract',
    'K': 'Incomprehensibly abstract',
    'L': 'Incomprehensibly abstract',
    '?': 'Unknown'
}

class Culture(object):
    class Element(enum.Enum):
        # Enum values are the index into the UWP string
        Heterogeneity = 0
        Acceptance = 1
        Strangeness = 2
        Symbols = 3

    _elementDescriptionMaps: typing.List[typing.Mapping[str, str]] = [
        _HeterogeneityDescriptionMap,
        _AcceptanceDescriptionMap,
        _StrangenessDescriptionMap,
        _SymbolsDescriptionMap
    ]

    def __init__(
            self,
            string: str
            ) -> None:
        self._string = string
        self._sanitised = self._sanitise(self._string)

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
        return Culture._elementDescriptionMaps[element.value][self.code(element)]

    @staticmethod
    def codeList(element: Element) -> typing.Iterable[str]:
        return Culture._elementDescriptionMaps[element.value].keys()

    @staticmethod
    def descriptionMap(element: Element) -> typing.Mapping[str, str]:
        return Culture._elementDescriptionMaps[element.value]

    @staticmethod
    def _sanitise(culture: str) -> str:
        culture = culture.strip('[]')
        sanitized = ''
        for index in range(4):
            sanitized += Culture._sanitiseElement(index, culture)
        return sanitized

    @staticmethod
    def _sanitiseElement(index: int, culture: str) -> str:
        if index >= len(culture):
            return '?'
        code = culture[index].upper()
        if code not in Culture._elementDescriptionMaps[index]:
            return '?'
        return code
