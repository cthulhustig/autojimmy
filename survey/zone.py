import common
import typing

# NOTE: Use ordered set to hold valid strings as they may get listed in
# error messages a validate* function fails
_ValidZoneCodes = common.OrderedSet(['G', 'A', 'R', 'B', 'U', 'F'])

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

def validateZone(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False
        ) -> typing.Optional[str]:
    return common.validateStr(
        name=name,
        value=value,
        allowNone=allowNone,
        allowedValues=_ValidZoneCodes)
