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

def _validateZone(
        name: str,
        value: str
        ) -> None:
    if value is not None and value not in _ValidZoneCodes:
        raise ValueError(f'{name} must be a valid zone code')

def validateZone(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        validationFn=lambda name, value: _validateZone(
            name=name,
            value=value))
