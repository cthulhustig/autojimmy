import enum
import survey
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

    _ValueDescriptionsMap: typing.Dict[Element, typing.Mapping[str, str]] = {
        Element.Heterogeneity: _HeterogeneityDescriptionMap,
        Element.Acceptance: _AcceptanceDescriptionMap,
        Element.Strangeness: _StrangenessDescriptionMap,
        Element.Symbols: _SymbolsDescriptionMap
    }

    def __init__(
            self,
            heterogeneity: typing.Optional[str] = None,
            acceptance: typing.Optional[str] = None,
            strangeness: typing.Optional[str] = None,
            symbols: typing.Optional[str] = None
            ) -> None:
        self._valueMap: typing.Dict[Culture.Element, str] = {}
        self._string = None

        if heterogeneity is not None:
            if heterogeneity not in _HeterogeneityDescriptionMap:
                raise ValueError(f'Invalid culture heterogeneity code "{heterogeneity}"')
            self._valueMap[Culture.Element.Heterogeneity] = heterogeneity
        if acceptance is not None:
            if acceptance not in _AcceptanceDescriptionMap:
                raise ValueError(f'Invalid culture acceptance code "{acceptance}"')
            self._valueMap[Culture.Element.Acceptance] = acceptance
        if strangeness is not None:
            if strangeness not in _StrangenessDescriptionMap:
                raise ValueError(f'Invalid culture strangeness code "{strangeness}"')
            self._valueMap[Culture.Element.Strangeness] = strangeness
        if symbols is not None:
            if symbols not in _SymbolsDescriptionMap:
                raise ValueError(f'Invalid culture symbols code "{symbols}"')
            self._valueMap[Culture.Element.Symbols] = symbols

    def string(self) -> str:
        if self._string is None:
            self._string = survey.formatSystemCultureString(
                heterogeneity=self._valueMap.get(Culture.Element.Heterogeneity),
                acceptance=self._valueMap.get(Culture.Element.Acceptance),
                strangeness=self._valueMap.get(Culture.Element.Strangeness),
                symbols=self._valueMap.get(Culture.Element.Symbols))
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
        return Culture._ValueDescriptionsMap[element][self.code(element)]

    def isUnknown(self) -> bool:
        return len(self._valueMap) == 0

    @staticmethod
    def descriptionMap(element: Element) -> typing.Mapping[str, str]:
        return Culture._ValueDescriptionsMap[element]

