import enum
import multiverse
import typing

# Types and ehex mappings taken from Traveller Map source code (world_utils.js).

_ResourcesDescriptionMap = {
    '2': 'Very scarce',
    '3': 'Very scarce',
    '4': 'Scarce',
    '5': 'Scarce',
    '6': 'Few',
    '7': 'Few',
    '8': 'Moderate',
    '9': 'Moderate',
    'A': 'Abundant',
    'B': 'Abundant',
    'C': 'Very abundant',
    'D': 'Very abundant',
    'E': 'Extremely abundant',
    'F': 'Extremely abundant',
    'G': 'Extremely abundant',
    'H': 'Extremely abundant',
    'J': 'Extremely abundant',
    '?': 'Unknown'
}


# This is the same mapping as the UWP population values
_LabourDescriptionMap = {
    '0': 'Unpopulated',
    '1': 'Tens',
    '2': 'Hundreds',
    '3': 'Thousands',
    '4': 'Tens of thousands',
    '5': 'Hundreds of thousands',
    '6': 'Millions',
    '7': 'Tens of millions',
    '8': 'Hundreds of millions',
    '9': 'Billions',
    'A': 'Tens of billions',
    'B': 'Hundreds of billions',
    'C': 'Trillions',
    'D': 'Tens of trillions',
    'E': 'Hundreds of trillions',
    'F': 'Quadrillions',
    '?': 'Unknown'
}

_InfrastructureDescriptionMap = {
    '0': 'Non-existent',
    '1': 'Extremely limited',
    '2': 'Extremely limited',
    '3': 'Very limited',
    '4': 'Very limited',
    '5': 'Limited',
    '6': 'Limited',
    '7': 'Generally available',
    '8': 'Generally available',
    '9': 'Extensive',
    'A': 'Extensive',
    'B': 'Very extensive',
    'C': 'Very extensive',
    'D': 'Comprehensive',
    'E': 'Comprehensive',
    'F': 'Very comprehensive',
    'G': 'Very comprehensive',
    'H': 'Very comprehensive',
    '?': 'Unknown'
}

_EfficiencyDescriptionMap = {
    '-5': 'Extremely poor',
    '-4': 'Very poor',
    '-3': 'Poor',
    '-2': 'Fair',
    '-1': 'Average',
    '0': 'Average',
    '+1': 'Average',
    '+2': 'Good',
    '+3': 'Improved',
    '+4': 'Advanced',
    '+5': 'Very advanced',
    '?': 'Unknown'
}

class Economics(object):
    class Element(enum.Enum):
        # Enum values are the index into the UWP string
        Resources = 0
        Labour = 1
        Infrastructure = 2
        Efficiency = 3

    _elementDescriptionMaps: typing.List[typing.Mapping[str, str]] = [
        _ResourcesDescriptionMap,
        _LabourDescriptionMap,
        _InfrastructureDescriptionMap,
        _EfficiencyDescriptionMap
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
        if element == Economics.Element.Efficiency:
            return self._sanitised[element.value:]
        return self._sanitised[element.value]

    def description(
            self,
            element: Element
            ) -> str:
        return Economics._elementDescriptionMaps[element.value][self.code(element)]

    @staticmethod
    def codeList(element: Element) -> typing.Iterable[str]:
        return Economics._elementDescriptionMaps[element.value].keys()

    @staticmethod
    def descriptionMap(element: Element) -> typing.Mapping[str, str]:
        return Economics._elementDescriptionMaps[element.value]

    @staticmethod
    def _sanitise(culture: str) -> str:
        culture = culture.strip('()')
        sanitized = ''
        for index in range(4):
            sanitized += Economics._sanitiseElement(index, culture)
        return sanitized

    @staticmethod
    def _sanitiseElement(index: int, culture: str) -> str:
        if index >= len(culture):
            return '?'
        if index != Economics.Element.Efficiency.value:
            code = culture[index].upper()
        else:
            code = culture[index:]
        if code not in Economics._elementDescriptionMaps[index]:
            return '?'
        return code
