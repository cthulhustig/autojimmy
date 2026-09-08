import common
import re
import typing

_InvalidAllegianceNameCharacters = '\n'

# NOTE: It's important that this pattern is kept in sync with the patterns
# that match Military Rule in remarks.py
# NOTE: This needs to support T5 4 character codes and legacy 1 and 2
# character codes. I've chosen to also support 3 character codes.
_AllegianceCodePattern = re.compile(r'^\s*([0-9A-Za-z\-\']{1,4})\s*$')

def parseAllegianceNameString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    stripped = string.strip()
    if not stripped:
        return None

    for c in stripped:
        if c in _InvalidAllegianceNameCharacters:
            if reporter:
                reporter.addMessage(f'Ignoring Allegiance Name {stripped!r} as it contains invalid character {c!r}')
            return None

    return stripped

def formatAllegianceNameString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    # Formatting has the same restrictions as parsing
    return parseAllegianceNameString(string=string, reporter=reporter)

def parseAllegianceCodeString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    # A LOT of second survey data uses ?? or -- to represent no allegiance
    isNoAllegiance = all(c == '?' for c in string) or all(c == '-' for c in string)
    if isNoAllegiance:
        return None

    result = _AllegianceCodePattern.match(string)
    if not result:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Allegiance Code {string}')
        return None

    return result[1]

def formatAllegianceCodeString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    # Formatting has the same restrictions as parsing
    return parseAllegianceCodeString(string=string, reporter=reporter)

def _validateAllegianceName(
        attributeName: str,
        allegianceName: typing.Optional[str]
        ) -> None:
    if allegianceName is None:
        return

    for c in allegianceName:
        if c in _InvalidAllegianceNameCharacters:
            raise ValueError(f'{attributeName} can\'t contain {_InvalidAllegianceNameCharacters!r}')

def validateAllegianceName(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        allowEmpty=False,
        validationFn=_validateAllegianceName)

def _validateAllegianceCode(
        attributeName: str,
        allegianceCode: typing.Optional[str]
        ) -> None:
    if allegianceCode is None:
        return

    result = _AllegianceCodePattern.match(allegianceCode)
    if not result:
        raise ValueError(f'{attributeName} is not a valid Allegiance Code')

def validateAllegianceCode(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        allowEmpty=False,
        validationFn=_validateAllegianceCode)
