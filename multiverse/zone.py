import enum
import typing

class ZoneType(enum.Enum):
    AmberZone = 1 # Imperial
    RedZone = 2 # Imperial
    Balkanized = 3
    Unabsorbed = 4 # Zhodani (based on Traveller Map code this is equivalent of a Amber Zone)
    Forbidden = 5 # Zhodani (based on Traveller Map code this is equivalent of a Red Zone)


_ZoneTypeToCodeMap = {
    ZoneType.AmberZone: 'A',
    ZoneType.RedZone: 'R',
    ZoneType.Balkanized: 'B',
    ZoneType.Unabsorbed: 'U',
    ZoneType.Forbidden: 'F',
}

_ZoneCodeToTypeMap = {v: k for k, v in _ZoneTypeToCodeMap.items()}

_ZoneTypeToNameMap = {
    ZoneType.AmberZone: 'Amber Zone',
    ZoneType.RedZone: 'Red Zone',
    ZoneType.Balkanized: 'Balkanized Zone',
    ZoneType.Unabsorbed: 'Unabsorbed Zone',
    ZoneType.Forbidden: 'Forbidden Zone',
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
