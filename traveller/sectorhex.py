
import re
import typing

_SectorHexPattern = re.compile('^(.*) ([0-9]{2})([0-9]{2})$')

def splitSectorHex(
        sectorHex: str
        ) -> typing.Tuple[str, str]:
    result = _SectorHexPattern.match(sectorHex)
    if not result:
        raise ValueError(f'Invalid sector hex string "{sectorHex}"')
    return (result.group(1), int(result.group(2)), int(result.group(3)))

def formatSectorHex(
        sectorName: str,
        worldX: typing.Union[int, str],
        worldY: typing.Union[int, str]
        ) -> str:
    return f'{sectorName} {int(worldX):02d}{int(worldY):02d}'
