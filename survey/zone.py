import common
import typing

_ValidZoneCodes = set(['A', 'R', 'B', 'U', 'F'])

def parseSystemZoneString(
        zone: str,
        strict: bool = False
        ) -> typing.Optional[str]:
    if zone == '?':
        return None

    if zone in _ValidZoneCodes:
        # TODO: This should log something and probably inform the user for custom sectors
        return zone

    if not strict:
        return None

    raise ValueError(f'Invalid zone code "{zone}"')

def formatSystemZoneString(
        zone: typing.Optional[str]
        ) -> str:
    if zone is None:
        return '?'
    if zone not in _ValidZoneCodes:
        raise ValueError(f'Invalid zone code "{zone}"')
    return zone

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