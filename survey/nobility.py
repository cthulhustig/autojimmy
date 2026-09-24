import common
import typing

# NOTE: Use ordered set to hold valid strings as they may get listed in
# error messages a validate* function fails
_ValidNobilityCodes = common.OrderedSet([
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

def validateNobility(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        allowedValues=_ValidNobilityCodes)
