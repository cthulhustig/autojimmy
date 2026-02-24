import common
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
_IntegerToExtendedHexMap = {v: k for k, v in _ExtendedHexToIntegerMap.items()}

def ehexToInteger(
        value: str,
        default: typing.Optional[typing.Any] = -1
        ) -> typing.Union[int, typing.Any]:
    if not value:
        return default
    return _ExtendedHexToIntegerMap.get(value.upper(), default)

def ehexFromInteger(
        value: int,
        default: typing.Optional[typing.Any] = None
        ) -> typing.Union[str, typing.Any]:
    return _IntegerToExtendedHexMap.get(value, default)

def ehexCodeMap() -> typing.Mapping[str, int]:
    return _ExtendedHexToIntegerMap

def _mandatoryExtendedHexValidator(
        name: str,
        value: str
        ) -> None:
    if value not in _ExtendedHexToIntegerMap:
        raise ValueError(f'{name} must be a valid eHex code')

def _optionalExtendedHexValidator(
        name: str,
        value: str
        ) -> None:
    if value is not None and value not in _ExtendedHexToIntegerMap:
        raise ValueError(f'{name} must be a valid eHex code or None')

def validateMandatoryExtendedHex(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryExtendedHexValidator(
            name=name,
            value=value))

def validateOptionalExtendedHex(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalExtendedHexValidator(
            name=name,
            value=value))