import common
import re
import typing

_InvalidSophontNameCharacters = '\n'

# NOTE: It's important that this pattern is kept in sync with the patterns
# that match T5 & legacy sophont population in remarks.py (remember there
# are four patterns in total)
# NOTE: This needs to support T5 4 character codes and legacy 1 character
# codes
_SophontCodePattern = re.compile(r'^\s*([0-9A-Za-z\-\']{4}|[ACDFHIMVXZ])\s*$')

def parseSophontNameString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    stripped = string.strip()
    if not stripped:
        return None

    for c in stripped:
        if c in _InvalidSophontNameCharacters:
            if reporter:
                reporter.addMessage(f'Ignoring Sophont Name {stripped!r} as it contains invalid character {c!r}')
            return None

    return stripped

def formatSophontNameString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    # Formatting has the same restrictions as parsing
    return parseSophontNameString(string=string, reporter=reporter)

def parseSophontCodeString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    result = _SophontCodePattern.match(string)
    if not result:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Sophont Code {string}')
        return None

    return result[1]

def formatSophontCodeString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    # Formatting has the same restrictions as parsing
    return parseSophontCodeString(string=string, reporter=reporter)

def _validateSophontName(
        attributeName: str,
        sophontName: typing.Optional[str]
        ) -> None:
    if sophontName is None:
        return

    for c in sophontName:
        if c in _InvalidSophontNameCharacters:
            raise ValueError(f'{attributeName} can\'t contain {_InvalidSophontNameCharacters!r}')

def validateMandatorySophontName(
        name: str,
        value: str
        ) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        allowEmpty=False,
        validationFn=_validateSophontName)

def validateOptionalSophontName(
        name: str,
        value: typing.Optional[str]
        ) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        allowEmpty=False,
        validationFn=_validateSophontName)

def _validateSophontCode(
        attributeName: str,
        sophontCode: typing.Optional[str]
        ) -> None:
    if sophontCode is None:
        return

    result = _SophontCodePattern.match(sophontCode)
    if not result:
        raise ValueError(f'{attributeName} is not a valid Sophont Code')

def validateMandatorySophontCode(
        name: str,
        value: str
        ) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        allowEmpty=False,
        validationFn=_validateSophontCode)

def validateOptionalSophontCode(
        name: str,
        value: typing.Optional[str]
        ) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        allowEmpty=False,
        validationFn=_validateSophontCode)