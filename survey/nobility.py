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
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.List[str]:
    nobilities = []
    for code in string:
        if code not in _ValidNobilityCodes:
            if reporter:
                reporter.addMessage(f'Ignoring invalid Nobility code "{code}"')
            continue
        nobilities.append(code)
    return nobilities

def formatSystemNobilityString(
        nobilities: typing.Iterable[str],
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    validCodes = set()
    for code in nobilities:
        if code not in _ValidNobilityCodes:
            reporter.addMessage(f'Ignoring invalid Nobility code "{code}"')
            continue
        validCodes.add(code)

    # NOTE: This slightly odd sorting is to maintain the canonical ordering
    # when it comes to things like 'c' vs 'C'. The primary sort is done on
    # the case insensitive character so ('B' is before 'c') and the secondary
    # sort is done on the upper/lower case-ness (so 'c' is before 'C')
    return ''.join(sorted(validCodes, key=lambda c: (c.lower(), c.isupper())))

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