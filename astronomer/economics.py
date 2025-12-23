import astronomer
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

    _ValueDescriptionsMap: typing.Dict[Element, typing.Mapping[str, str]] = {
        Element.Resources: _ResourcesDescriptionMap,
        Element.Labour: _LabourDescriptionMap,
        Element.Infrastructure: _InfrastructureDescriptionMap,
        Element.Efficiency: _EfficiencyDescriptionMap
    }

    def __init__(
            self,
            resources: typing.Optional[str] = None,
            labour: typing.Optional[str] = None,
            infrastructure: typing.Optional[str] = None,
            efficiency: typing.Optional[str] = None
            ) -> None:
        self._valueMap: typing.Dict[Economics.Element, str] = {}
        self._string = None

        if resources is not None:
            self._valueMap[Economics.Element.Resources] = resources
        if labour is not None:
            self._valueMap[Economics.Element.Labour] = labour
        if infrastructure is not None:
            self._valueMap[Economics.Element.Infrastructure] = infrastructure
        if efficiency is not None:
            self._valueMap[Economics.Element.Efficiency] = efficiency

    def string(self) -> str:
        if self._string is None:
            self._string = multiverse.formatSystemEconomicsString(
                resources=self._valueMap.get(Economics.Element.Resources),
                labour=self._valueMap.get(Economics.Element.Labour),
                infrastructure=self._valueMap.get(Economics.Element.Infrastructure),
                efficiency=self._valueMap.get(Economics.Element.Efficiency))
        return self._string

    def code(
            self,
            element: Element
            ) -> str:
        return self._valueMap.get(element, '?')

    def numeric(
            self,
            element: Element,
            default: int = -1
            ) -> int:
        code = self._valueMap.get(element)
        if code is None:
            return default
        return astronomer.ehexToInteger(code, default)

    def description(
            self,
            element: Element
            ) -> str:
        return Economics._ValueDescriptionsMap[element][self.code(element)]

    def isUnknown(self) -> bool:
        return len(self._valueMap) == 0

    @staticmethod
    def descriptionMap(element: Element) -> typing.Mapping[str, str]:
        return Economics._ValueDescriptionsMap[element]

