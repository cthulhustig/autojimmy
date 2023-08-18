import enum
import logging
import re
import typing

# https://en.wikipedia.org/wiki/Stellar_classification
# https://en.wikipedia.org/wiki/Main_sequence
# https://en.wikipedia.org/wiki/A-type_main-sequence_star

_SpectralClassDescriptionMap = {
    'O': 'Blue - >33,000 Kelvin',
    'B': 'Blue-White - 10,000-33,000 Kelvin',
    'A': 'White - 7,500-10,000K Kelvin', # Traveller Map says Blue-White but this says White https://en.wikipedia.org/wiki/Stellar_classification
    'F': 'Yellow-White - 6,000-7,500K Kelvin',
    'G': 'Yellow - 5,200-6,000 Kelvin',
    'K': 'Orange - 3,700-5,200 Kelvin',
    'M': 'Red - 2,000-3,700 Kelvin',
    '?': 'Unknown' # This was added my me
}

_SpectralScaleDescriptionMap = {
    '0': '0%',
    '1': '10%',
    '2': '20%',
    '3': '30%',
    '4': '40%',
    '5': '50%',
    '6': '60%',
    '7': '70%',
    '8': '80%',
    '9': '90%',
    '?': 'Unknown' # This was added my me
}

_LuminosityDescriptionMap = {
    'Ia': 'Bright Supergiant - 52-3,500 Sols Diameter',
    'Ib': 'Weak Supergiant - 30-3,000 Sols Diameter',
    'II': 'Bright Giant - 14-1,000 Sols Diameter',
    'III': 'Normal Giant - 4.6-360 Sols Diameter',
    'IV': 'Subgiant - 3.3-13 Sols Diameter',
    'V': 'Main Sequence Star - 0.2-10 Sols Diameter',
    'VI': 'Subdwarf - 0.1-1.2 Sols Diameter',
    'D': 'White Dwarf - 0.006-0.018 Sols Diameter',
    # These came from Traveller Map
    'BD': 'Brown Dwarf - Unknown Diameter',
    'BH': 'Black Hole - Unknown Diameter',
    'NS': 'Neutron Star - Unknown Diameter',
    'PSR': 'Pulsar - Unknown Diameter',
    '?': 'Unknown', # This was added my me
}

class Star(object):
    class Element(enum.Enum):
        SpectralClass = 0
        SpectralScale = 1
        LuminosityClass = 2

    _elementDescriptionMaps: typing.List[typing.Mapping[str, str]] = [
        _SpectralClassDescriptionMap,
        _SpectralScaleDescriptionMap,
        _LuminosityDescriptionMap
    ]

    def __init__(
            self,
            classification: str,
            spectralClass: str,
            spectralScale: str,
            luminosityClass: str
            ) -> None:
        self._classification = classification
        self._spectralClass = spectralClass
        self._spectralScale = spectralScale
        self._luminosityClass = luminosityClass

    def string(self) -> str:
        return self._classification

    def code(self, element: Element) -> str:
        if element == Star.Element.SpectralClass:
            return self._spectralClass
        elif element == Star.Element.SpectralScale:
            return self._spectralScale
        elif element == Star.Element.LuminosityClass:
            return self._luminosityClass
        raise ValueError('Invalid star element')

    def description(self, element: Element) -> str:
        return Star._elementDescriptionMaps[element.value][self.code(element)]

    @staticmethod
    def descriptionMap(element: Element) -> typing.Mapping[str, str]:
        return Star._elementDescriptionMaps[element.value]

class Stellar(object):
    # Details of the format of the stars string can be found here
    # https://travellermap.com/doc/secondsurvey#stellar
    # https://travellermap.com/doc/fileformats#legacy-sec-format
    _StellarPattern = re.compile(r'([OBAFGKM][0-9])\s*(D|Ia|Ib|III|II|IV|VII|VI|V||)|(DB|DA|DF|DG|DK|DM|D)|(BD|BH|NS|PSR)')

    def __init__(
            self,
            string: str
            ) -> None:
        self._string = string
        self._stars = self._parseString(self._string)

    def string(self) -> str:
        return self._string

    def stars(self) -> typing.Iterable[Star]:
        return self._stars

    def hasStars(self) -> bool:
        return len(self._stars) > 0

    def starCount(self) -> int:
        return len(self._stars)

    @staticmethod
    def _parseString(string) -> typing.List[Star]:
        stars = []
        for match in Stellar._StellarPattern.finditer(string):
            if match[1] and match[2]:
                stars.append(Star(
                    classification=match[0],
                    spectralClass=match[1][0],
                    spectralScale=match[1][1],
                    luminosityClass=match[2]))
            elif match[3]:
                stars.append(Star(
                    classification=match[0],
                    spectralClass='?' if len(match[3]) == 1 else match[3][1],
                    spectralScale='?',
                    luminosityClass=match[3][0]))
            elif match[4]:
                stars.append(Star(
                    classification=match[0],
                    spectralClass='?',
                    spectralScale='?',
                    luminosityClass=match[4]))
        return stars

    def __getitem__(self, index: int) -> Star:
        return self._stars.__getitem__(index)

    def __iter__(self) -> typing.Iterator[Star]:
        return self._stars.__iter__()

    def __next__(self) -> typing.Any:
        return self._stars.__next__()

    def __len__(self) -> int:
        return self._stars.__len__()
