import typing

_ExtendedHexToIntegerMap = {
    '0': 0,
    '1': 1,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,
    'A': 10,
    'B': 11,
    'C': 12,
    'D': 13,
    'E': 14,
    'F': 15,
    'G': 16,
    'H': 17,
    # There is no I in extended hex
    'J': 18,
    'K': 19,
    'L': 20,
    'M': 21,
    'N': 22,
    # There is no O in extended hex
    'P': 23,
    'Q': 24,
    'R': 25,
    'S': 26,
    'T': 27,
    'U': 28,
    'V': 29,
    'W': 30,
    'X': 31,
    'Y': 32,
    'Z': 33,
}

def ehexToInteger(
        value: str,
        default: typing.Optional[typing.Any] = -1
        ) -> typing.Union[int, typing.Any]:
    return _ExtendedHexToIntegerMap.get(value.upper(), default)

def ehexCodeMap() -> typing.Mapping[str, int]:
    return _ExtendedHexToIntegerMap
