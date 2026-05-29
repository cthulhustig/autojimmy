import common
import re
import typing

# This regex allows the following
# - Matches with and without {}
# - Matches with empty brackets or brackets that only contain white space
# - Ignores leading/trailing white space
# - Doesn't match strings that are only white space
# - Allows for optional +/- preceding number
# - Allows multi-digit numbers
_ImportancePattern = re.compile(r'^\s*(?:\{\s*([+-]?\d+)?\s*\}|([+-]?\d+))\s*$')

def parseSystemImportanceString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[int]:
    result = _ImportancePattern.match(string)
    if not result:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Importance string "{string}"')
        return None

    if not result[1]:
        # The input string is just an empty set of brackets. This is
        # classed as valid so doesn't generate a report message
        return None

    return int(result[1])

def formatSystemImportanceString(
        importance: int,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    return f'{{{importance}}}'

def validateMandatoryImportance(name: str, value: int) -> int:
    return common.validateMandatoryInt(name=name, value=value)

def validateOptionalImportance(name: str, value: typing.Optional[int]) -> typing.Optional[int]:
    return common.validateOptionalInt(name=name, value=value)