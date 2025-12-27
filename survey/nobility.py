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

    # TODO: Need to check that this is always putting nobilities in alphabetical order
    return ''.join(sorted(validCodes))