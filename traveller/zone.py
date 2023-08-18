import enum
import typing

class ZoneType(enum.Enum):
    AmberZone = 1
    RedZone = 2


_ZoneTypeToCodeMap = {
    ZoneType.AmberZone: 'A',
    ZoneType.RedZone: 'R'
}

_ZoneCodeToTypeMap = {v: k for k, v in _ZoneTypeToCodeMap.items()}

_ZoneTypeToNameMap = {
    ZoneType.AmberZone: 'Amber Zone',
    ZoneType.RedZone: 'Red Zone'
}

# This returns a list rather than a set in order to preserve order of least to most significant
def parseZoneString(zoneString: str) -> typing.Optional[ZoneType]:
    return _ZoneCodeToTypeMap.get(zoneString)

def zoneTypeCode(zoneType: ZoneType) -> str:
    return _ZoneTypeToCodeMap.get(zoneType, '')

def zoneTypeName(zoneType: ZoneType) -> str:
    return _ZoneTypeToNameMap.get(zoneType, '')

def zoneTypeNameMap() -> typing.Mapping[ZoneType, str]:
    return _ZoneTypeToNameMap
