import math
import travellermap
import typing
from urllib import parse

_SectorGridOption = 0x0001
_SubsectorGridOption = 0x0002
_GridMaskOption = 0x0003
_SectorsSelectedOption = 0x0004
_SectorsAllOption = 0x0008
_SectorsMaskOption = 0x000C
_BordersMajorOption = 0x0010
_BordersMinorOption = 0x0020
_BordersMaskOption = 0x0030
_NamesMajorOption = 0x0040
_NamesMinorOption = 0x0080
_NamesMaskOption = 0x00C0 # aka Region Names
_WorldsCapitalsOption = 0x0100
_WorldsHomeworldsOption = 0x0200
_WorldsMaskOption = 0x0300 # aka Important Worlds
_ForceHexesOption = 0x2000
_WorldColorsOption = 0x4000
_FilledBordersOption = 0x8000

class MapPosition(object):
    def __init__(
            self,
            mapX: float,
            mapY: float,
            logScale: float
            ) -> None:
        self._mapX = mapX
        self._mapY = mapY
        self._logScale = logScale

    def mapX(self) -> float:
        return self._mapX

    def mapY(self) -> float:
        return self._mapY

    def logScale(self) -> float:
        return self._logScale

class TilePosition(object):
    def __init__(
            self,
            tileX: float,
            tileY: float,
            linearScale: float
            ) -> None:
        self._tileX = tileX
        self._tileY = tileY
        self._linearScale = linearScale

    def tileX(self) -> float:
        return self._tileX

    def tileY(self) -> float:
        return self._tileY

    def linearScale(self) -> float:
        return self._linearScale

def linearScaleToLogScale(linearScale: float) -> float:
    return 1 + math.log2(linearScale)

def logScaleToLinearScale(logScale: float) -> float:
    return math.pow(2, logScale - 1)

def formatMapUrl(
        baseUrl: str,
        milieu: travellermap.Milieu,
        style: travellermap.Style,
        options: typing.Optional[typing.Iterable[travellermap.Option]] = None,
        position: typing.Optional[typing.Union[MapPosition, TilePosition]] = None,
        minimal: bool = False
        ) -> str:
    url = f'{baseUrl}?milieu={milieu.value}&style={style.value}'

    optionBitMask = _ForceHexesOption # Always enabled
    if travellermap.Option.SectorGrid in options:
        optionBitMask |= _GridMaskOption
    if travellermap.Option.SectorNames in options:
        optionBitMask |= _SectorsAllOption
    if travellermap.Option.Borders in options:
        optionBitMask |= _BordersMaskOption
    if travellermap.Option.RegionNames in options:
        optionBitMask |= _NamesMaskOption
    if travellermap.Option.ImportantWorlds in options:
        optionBitMask |= _WorldsMaskOption
    if travellermap.Option.WorldColours in options:
        optionBitMask |= _WorldColorsOption
    if travellermap.Option.FilledBorders in options:
        optionBitMask |= _FilledBordersOption

    url += '&options=' + str(optionBitMask)

    if travellermap.Option.HideUI in options:
        url += '&hideui=1'
    elif not minimal:
        url += '&hideui=0'

    if travellermap.Option.GalacticDirections in options:
        url += '&galdir=1'
    elif not minimal:
        url += '&galdir=0'

    if travellermap.Option.Routes in options:
        url += '&routes=1'
    elif not minimal:
        url += '&routes=0'

    if travellermap.Option.DimUnofficial in options:
        url += '&dimunofficial=1'
    elif not minimal:
        url += '&dimunofficial=0'

    if travellermap.Option.ImportanceOverlay in options:
        url += '&im=1'
    elif not minimal:
        url += '&im=0'

    if travellermap.Option.PopulationOverlay in options:
        url += '&po=1'
    elif not minimal:
        url += '&po=0'

    if travellermap.Option.CapitalsOverlay in options:
        url += '&cp=1'
    elif not minimal:
        url += '&cp=0'

    if travellermap.Option.MinorRaceOverlay in options:
        url += '&mh=1'
    elif not minimal:
        url += '&mh=0'

    if travellermap.Option.DroyneWorldOverlay in options:
        url += '&dw=1'
    elif not minimal:
        url += '&dw=0'

    if travellermap.Option.AncientSitesOverlay in options:
        url += '&an=1'
    elif not minimal:
        url += '&an=0'

    if travellermap.Option.StellarOverlay in options:
        url += '&stellar=1'
    elif not minimal:
        url += '&stellar=0'

    if travellermap.Option.MainsOverlay in options:
        url += '&mains=1'
    elif not minimal:
        url += '&mains=0'

    # Note that ew and qz use an empty argument to clear rather than 0
    if travellermap.Option.EmpressWaveOverlay in options:
        url += '&ew=milieu' # Show for current milieu
    elif not minimal:
        url += '&ew=' # Empty to clear rather than 0

    if travellermap.Option.EmpressWaveOverlay in options:
        url += '&qz=1'
    elif not minimal:
        url += '&qz=' # Empty to clear rather than 0

    if isinstance(position, MapPosition):
        url += f'&p={position.mapX():.3f}!{position.mapY():.3f}!{position.logScale():.2f}'
    elif isinstance(position, TilePosition):
        url += f'&x={position.tileX():.4f}&y={position.tileY():.4f}&scale={position.linearScale()}'

    return url

def posFromMapUrl(url: str) -> typing.Optional[MapPosition]:
    paramMap = parse.parse_qs(parse.urlsplit(url).query)
    paramValues = paramMap.get('p')
    if not paramValues:
        return None
    tokens = paramValues[0].split('!')
    if len(tokens) != 3:
        return None
    return MapPosition(mapX=float(tokens[0]), mapY=float(tokens[1]), logScale=float(tokens[2]))
