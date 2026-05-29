import common
import survey
import typing

def parseSystemWorldCountString(
        string: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[int]:
    if not string:
        return None

    try:
        result = int(string)
    except:
        # The number of system worlds should be an integer but wasn't
        # so try parsing it as ehex
        result = survey.ehexToInteger(value=string, default=None)

    if result is None or result < 0:
        if reporter:
            reporter.addMessage(f'Ignoring invalid World Count "{string}"')
        return None

    return result

def formatSystemWorldCountString(
        count: int,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    return str(count)

def validateMandatoryWorldCount(name: str, value: int) -> int:
    return common.validateMandatoryInt(name=name, value=value, min=0)

def validateOptionalWorldCount(name: str, value: typing.Optional[int]) -> typing.Optional[int]:
    return common.validateOptionalInt(name=name, value=value, min=0)