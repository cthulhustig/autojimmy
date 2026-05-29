import common
import typing

_ValidZoneCodes = set(['G', 'A', 'R', 'B', 'U', 'F'])

def parseSystemZoneString(
        zone: str,
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    if zone == '?':
        return None

    checkZone = zone.upper()
    if checkZone not in _ValidZoneCodes:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Zone code "{zone}"')
        return None

    return checkZone

def formatSystemZoneString(
        zone: typing.Optional[str],
        reporter: typing.Optional[common.Reporter] = None
        ) -> str:
    if zone is None:
        return ''

    checkZone = zone.upper()
    if checkZone not in _ValidZoneCodes:
        if reporter:
            reporter.addMessage(f'Ignoring invalid zone code "{zone}"')
        return ''

    return checkZone

def _mandatoryZoneValidator(
        name: str,
        value: str
        ) -> None:
    if value not in _ValidZoneCodes:
        raise ValueError(f'{name} must be a valid zone code')

def _optionalZoneValidator(
        name: str,
        value: str
        ) -> None:
    if value is not None and value not in _ValidZoneCodes:
        raise ValueError(f'{name} must be a valid zone code or None')

def validateMandatoryZone(name: str, value: str) -> str:
    return common.validateMandatoryStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _mandatoryZoneValidator(
            name=name,
            value=value))

def validateOptionalZone(name: str, value: typing.Optional[str]) -> typing.Optional[str]:
    return common.validateOptionalStr(
        name=name,
        value=value,
        validationFn=lambda name, value: _optionalZoneValidator(
            name=name,
            value=value))