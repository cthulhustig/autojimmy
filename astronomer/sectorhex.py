
import re
import typing

_SectorHexPattern = re.compile(r'^(.+)\s+([0-9]{2})([0-9]{2})$')

def splitSectorHex(
        sectorHex: str
        ) -> typing.Tuple[str, int, int]:
    result = _SectorHexPattern.match(sectorHex)
    if not result:
        raise ValueError(f'Invalid sector hex string "{sectorHex}"')
    return (result.group(1), int(result.group(2)), int(result.group(3)))

def formatSectorHex(
        sectorName: str,
        offsetX: typing.Union[int, str],
        offsetY: typing.Union[int, str]
        ) -> str:
    return f'{sectorName} {int(offsetX):02d}{int(offsetY):02d}'
