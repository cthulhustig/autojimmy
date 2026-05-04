import enum
import survey
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
    '?': 'Unknown' # This was added my me
}

class Star(object):
    class Element(enum.Enum):
        SpectralClass = 0
        SpectralScale = 1
        LuminosityClass = 2

    _ValueDescriptionsMap: typing.Dict[Element, typing.Mapping[str, str]] = {
        Element.SpectralClass: _SpectralClassDescriptionMap,
        Element.SpectralScale: _SpectralScaleDescriptionMap,
        Element.LuminosityClass: _LuminosityDescriptionMap
    }

    def __init__(
            self,
            luminosityClass: str,
            spectralClass: typing.Optional[str] = None,
            spectralScale: typing.Optional[str] = None
            ) -> None:
        self._valueMap: typing.Dict[Star.Element, str] = {}
        self._string = None

        if luminosityClass not in _LuminosityDescriptionMap:
            raise ValueError(f'Invalid stellar luminosity class "{luminosityClass}"')
        self._valueMap[Star.Element.LuminosityClass] = luminosityClass

        if spectralClass is not None and spectralClass not in _SpectralClassDescriptionMap:
            raise ValueError(f'Invalid stellar spectral class "{spectralClass}"')
        self._valueMap[Star.Element.SpectralClass] = spectralClass

        if spectralScale is not None and spectralScale not in _SpectralScaleDescriptionMap:
            raise ValueError(f'Invalid stellar spectral scale "{spectralScale}"')
        self._valueMap[Star.Element.SpectralScale] = spectralScale

    @typing.overload
    def code(self, element: typing.Literal[Element.LuminosityClass]) -> str: ...
    @typing.overload
    def code(self, element: typing.Literal[Element.SpectralClass]) -> typing.Optional[str]: ...
    @typing.overload
    def code(self, element: typing.Literal[Element.SpectralScale]) -> typing.Optional[str]: ...

    def code(self, element: Element) -> typing.Optional[str]:
        return self._valueMap.get(element)

    def string(self) -> str:
        if self._string is None:
            self._string = survey.formatSystemStellarString(stars=[(
                self._valueMap.get(Star.Element.LuminosityClass),
                self._valueMap.get(Star.Element.SpectralClass),
                self._valueMap.get(Star.Element.SpectralScale))])
        return self._string

    def description(self, element: Element) -> str:
        return Star._ValueDescriptionsMap[element][self.code(element)]

    @staticmethod
    def descriptionMap(element: Element) -> typing.Mapping[str, str]:
        return Star._ValueDescriptionsMap[element]

class Stellar(object):
    def __init__(
            self,
            stars: typing.Optional[typing.Collection[Star]] = None
            ) -> None:
        self._stars = list(stars) if stars else []
        self._string = None

    def isEmpty(self) -> bool:
        return not self._stars

    def stars(self) -> typing.List[Star]:
        return list(self._stars)

    def yieldStars(self) -> typing.Generator[Star, None, None]:
        for star in self._stars:
            yield star

    def starCount(self) -> int:
        return len(self._stars)

    def string(self) -> str:
        if self._string is None:
            self._string = survey.formatSystemStellarString(
                stars=[(s.code(Star.Element.LuminosityClass), s.code(Star.Element.SpectralClass), s.code(Star.Element.SpectralScale)) for s in self._stars])
        return self._string

    def __getitem__(self, index: int) -> Star:
        return self._stars.__getitem__(index)

    def __iter__(self) -> typing.Iterator[Star]:
        return self._stars.__iter__()

    def __next__(self) -> typing.Any:
        return self._stars.__next__()

    def __len__(self) -> int:
        return self._stars.__len__()
