import common
import typing

_ValidNobilityCodes = set([
    'B', # Knight
    'c', # Baronet
    'C', # Baron
    'D', # Marquis
    'e', # Viscount
    'E', # Count
    'f', # Duke
    'F', # Subsector Duke
    'G', # Archduke
    'H', # Emperor
])

def parseSystemNobilityString(
        string: str,
        strict: bool = False
        ) -> typing.Generator[str, None, None]:
    for code in string:
        if code not in _ValidNobilityCodes:
            if not strict:
                # TODO: This should probably log
                continue
            raise ValueError(f'Nobility string "{string}" contains unrecognised value "{code}"')

        yield code

def formatSystemNobilityString(
        nobilities: typing.Iterable[str]
        ) -> str:
    validCodes = set()
    for code in nobilities:
        if code not in _ValidNobilityCodes:
            raise ValueError(f'Invalid nobility code "{code}"')
        validCodes.add(code)

    return ''.join(sorted(validCodes))

def _mandatoryNobilityValidator(
        name: str,
        value: str
        ) -> None:
    if value.upper() not in _ValidNobilityCodes:
        raise ValueError(f'{name} must be a valid nobility code')

def _optionalNobilityValidator(
        name: str,
        value: str
        ) -> None:
    if value is not None and value.upper() not in _ValidNobilityCodes:
        raise ValueError(f'{name} must be a valid nobility code or None')

def validateMandatoryNobility(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryNobilityValidator(
            name=name,
            value=value))

def validateOptionalNobility(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalNobilityValidator(
            name=name,
            value=value))