import math
import travellermap
import typing
import urllib.parse

TravellerMapBaseUrl = 'https://travellermap.com'

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

def linearScaleToLogScale(linearScale: float) -> float:
    return 1 + math.log2(linearScale)

def logScaleToLinearScale(logScale: float) -> float:
    return math.pow(2, logScale - 1)

def formatMapUrl(
        baseMapUrl: str,
        milieu: travellermap.Milieu,
        style: travellermap.Style,
        options: typing.Optional[typing.Iterable[travellermap.Option]] = None,
        mapPosition: typing.Optional[typing.Tuple[float, float]] = None,
        linearScale: typing.Optional[float] = None, # Pixels per parsec
        minimal: bool = False
        ) -> str:
    urlOptions = formatCommonUrlOptions(
        milieu=milieu,
        style=style,
        options=options,
        minimal=minimal)
    
    if (mapPosition != None) and (linearScale != None):
        logScale = linearScaleToLogScale(linearScale=linearScale)
        urlOptions += f'&p={mapPosition[0]:.3f}!{mapPosition[1]:.3f}!{logScale:.2f}'
    
    # It's important the file name doesn't start with a slash as, in the case of a file url,
    # it will cause it to be take as the located in the root of the filesystem and any part
    # in baseMapUrl will be deleted
    return urllib.parse.urljoin(baseMapUrl, 'index.html?' + urlOptions)

def formatTileUrl(
        baseMapUrl: str,
        tilePosition: typing.Tuple[float, float],
        milieu: travellermap.Milieu,
        style: travellermap.Style,
        options: typing.Optional[typing.Iterable[travellermap.Option]] = None,
        linearScale: typing.Optional[float] = None, # Pixels per parsec
        minimal: bool = False
        ) -> str:
    urlOptions = formatCommonUrlOptions(
        milieu=milieu,
        style=style,
        options=options,
        minimal=minimal)
    urlOptions += f'&x={tilePosition[0]:.4f}&y={tilePosition[1]:.4f}'
    if linearScale != None:
        urlOptions += f'&scale={linearScale}'
    return urllib.parse.urljoin(baseMapUrl, 'api/tile?' + urlOptions)

def formatCommonUrlOptions(
        milieu: travellermap.Milieu,
        style: travellermap.Style,
        options: typing.Optional[typing.Iterable[travellermap.Option]] = None,
        minimal: bool = False
        ) -> str:
    urlOptions = f'milieu={milieu.value}&style={style.value}'

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

    urlOptions += '&options=' + str(optionBitMask)

    if travellermap.Option.HideUI in options:
        urlOptions += '&hideui=1'
    elif not minimal:
        urlOptions += '&hideui=0'

    if travellermap.Option.GalacticDirections in options:
        urlOptions += '&galdir=1'
    elif not minimal:
        urlOptions += '&galdir=0'

    if travellermap.Option.Routes in options:
        urlOptions += '&routes=1'
    elif not minimal:
        urlOptions += '&routes=0'

    if travellermap.Option.DimUnofficial in options:
        urlOptions += '&dimunofficial=1'
    elif not minimal:
        urlOptions += '&dimunofficial=0'

    if travellermap.Option.ImportanceOverlay in options:
        urlOptions += '&im=1'
    elif not minimal:
        urlOptions += '&im=0'

    if travellermap.Option.PopulationOverlay in options:
        urlOptions += '&po=1'
    elif not minimal:
        urlOptions += '&po=0'

    if travellermap.Option.CapitalsOverlay in options:
        urlOptions += '&cp=1'
    elif not minimal:
        urlOptions += '&cp=0'

    if travellermap.Option.MinorRaceOverlay in options:
        urlOptions += '&mh=1'
    elif not minimal:
        urlOptions += '&mh=0'

    if travellermap.Option.DroyneWorldOverlay in options:
        urlOptions += '&dw=1'
    elif not minimal:
        urlOptions += '&dw=0'

    if travellermap.Option.AncientSitesOverlay in options:
        urlOptions += '&an=1'
    elif not minimal:
        urlOptions += '&an=0'

    if travellermap.Option.StellarOverlay in options:
        urlOptions += '&stellar=1'
    elif not minimal:
        urlOptions += '&stellar=0'

    if travellermap.Option.MainsOverlay in options:
        urlOptions += '&mains=1'
    elif not minimal:
        urlOptions += '&mains=0'

    # Note that ew and qz use an empty argument to clear rather than 0
    if travellermap.Option.EmpressWaveOverlay in options:
        urlOptions += '&ew=milieu' # Show for current milieu
    elif not minimal:
        urlOptions += '&ew=' # Empty to clear rather than 0

    if travellermap.Option.EmpressWaveOverlay in options:
        urlOptions += '&qz=1'
    elif not minimal:
        urlOptions += '&qz=' # Empty to clear rather than 0

    return urlOptions

def parsePosFromMapUrl(
        url: str
        ) -> typing.Optional[typing.Tuple[float, float]]:
    paramMap = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    paramValues = paramMap.get('p')
    if not paramValues:
        return None
    tokens = paramValues[0].split('!')
    if len(tokens) != 3:
        return None
    return (float(tokens[0]), float(tokens[1]))

def parseScaleFromMapUrl(
        url: str
        ) -> typing.Optional[float]: # Pixels per parsec
    paramMap = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    paramValues = paramMap.get('p')
    if not paramValues:
        return None
    tokens = paramValues[0].split('!')
    if len(tokens) != 3:
        return None
    return logScaleToLinearScale(float(tokens[2]))
