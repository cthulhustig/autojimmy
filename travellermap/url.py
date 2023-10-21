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
        options: typing.Optional[typing.Collection[travellermap.Option]] = None,
        mapPosition: typing.Optional[typing.Tuple[float, float]] = None,
        linearScale: typing.Optional[float] = None, # Pixels per parsec
        minimal: bool = False
        ) -> str:
    # It's important the file name doesn't start with a slash as, in the case of a file url,
    # it will cause it to be take as the located in the root of the filesystem and any part
    # in baseMapUrl will be deleted
    url = urllib.parse.urljoin(baseMapUrl, 'index.html')

    queryList = _createCommonQueryList(
        milieu=milieu,
        style=style,
        options=options,
        minimal=minimal)
    if (mapPosition != None) and (linearScale != None):
        logScale = linearScaleToLogScale(linearScale=linearScale)
        queryList.append(f'p={mapPosition[0]:.3f}!{mapPosition[1]:.3f}!{logScale:.2f}')

    if queryList:
        url += '?' + ('&'.join(queryList))
    return url

def formatTileUrl(
        baseMapUrl: str,
        tilePosition: typing.Tuple[float, float],
        milieu: travellermap.Milieu,
        style: travellermap.Style,
        options: typing.Optional[typing.Collection[travellermap.Option]] = None,
        linearScale: typing.Optional[float] = None, # Pixels per parsec
        minimal: bool = False
        ) -> str:
    url = urllib.parse.urljoin(baseMapUrl, 'api/tile')

    queryList = _createCommonQueryList(
        milieu=milieu,
        style=style,
        options=options,
        minimal=minimal)
    queryList.append(f'x={tilePosition[0]:.4f}')
    queryList.append(f'y={tilePosition[1]:.4f}')
    if linearScale != None:
        queryList.append('scale=' + str(linearScale))

    if queryList:
        url += '?' + ('&'.join(queryList))
    return url

# NOTE: This only supports generating full sector posters from custom sector data, it doesn't
# support generating posters from standard sector data or subsector/quadrant posters of
# custom sectors as those features aren't used by the app
def formatPosterUrl(
        baseMapUrl: str,
        style: travellermap.Style,
        options: typing.Optional[typing.Collection[travellermap.Option]] = None,
        linearScale: typing.Optional[float] = None, # Pixels per parsec
        compositing: bool = True,
        minimal: bool = False
        ) -> str:
    url = urllib.parse.urljoin(baseMapUrl, 'api/poster')

    queryList = _createCommonQueryList(
        style=style,
        options=options,
        minimal=minimal)
    if linearScale != None:
        queryList.append(f'scale=' + str(linearScale))
    queryList.append(f'compositing=' + ('1' if compositing else '0'))

    if queryList:
        url += '?' + ('&'.join(queryList))
    return url

def formatPosterLintUrl(baseMapUrl: str) -> str:
    return urllib.parse.urljoin(baseMapUrl, 'api/poster?lint=1')

def formatMetadataLintUrl(baseMapUrl: str) -> str:
    return urllib.parse.urljoin(baseMapUrl, 'api/metadata?lint=1')

def _createCommonQueryList(
        milieu: typing.Optional[travellermap.Milieu] = None,
        style: typing.Optional[travellermap.Style] = None,
        options: typing.Optional[typing.Collection[travellermap.Option]] = None,
        minimal: bool = False
        ) -> typing.List[str]:
    optionList = []
    if milieu != None:
        optionList.append('milieu=' + str(milieu.value))
    if style != None:
        optionList.append('style=' + str(style.value))

    optionBitMask = _ForceHexesOption # Always enabled
    if options:
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
    optionList.append('options=' + str(optionBitMask)) # Always add this as ForcedHexes is always set

    if options:
        if travellermap.Option.HideUI in options:
            optionList.append('hideui=1')
        elif not minimal:
            optionList.append('hideui=0')

        if travellermap.Option.GalacticDirections in options:
            optionList.append('galdir=1')
        elif not minimal:
            optionList.append('galdir=0')

        if travellermap.Option.Routes in options:
            optionList.append('routes=1')
        elif not minimal:
            optionList.append('routes=0')

        if travellermap.Option.DimUnofficial in options:
            optionList.append('dimunofficial=1')
        elif not minimal:
            optionList.append('dimunofficial=0')

        if travellermap.Option.ImportanceOverlay in options:
            optionList.append('im=1')
        elif not minimal:
            optionList.append('im=0')

        if travellermap.Option.PopulationOverlay in options:
            optionList.append('po=1')
        elif not minimal:
            optionList.append('po=0')

        if travellermap.Option.CapitalsOverlay in options:
            optionList.append('cp=1')
        elif not minimal:
            optionList.append('cp=0')

        if travellermap.Option.MinorRaceOverlay in options:
            optionList.append('mh=1')
        elif not minimal:
            optionList.append('mh=0')

        if travellermap.Option.DroyneWorldOverlay in options:
            optionList.append('dw=1')
        elif not minimal:
            optionList.append('dw=0')

        if travellermap.Option.AncientSitesOverlay in options:
            optionList.append('an=1')
        elif not minimal:
            optionList.append('an=0')

        if travellermap.Option.StellarOverlay in options:
            optionList.append('stellar=1')
        elif not minimal:
            optionList.append('stellar=0')

        if travellermap.Option.MainsOverlay in options:
            optionList.append('mains=1')
        elif not minimal:
            optionList.append('mains=0')

        # Note that ew and qz use an empty argument to clear rather than 0
        if travellermap.Option.EmpressWaveOverlay in options:
            optionList.append('ew=milieu') # Show for current milieu
        elif not minimal:
            optionList.append('ew=') # Empty to clear rather than 0

        if travellermap.Option.EmpressWaveOverlay in options:
            optionList.append('qz=1')
        elif not minimal:
            optionList.append('qz=') # Empty to clear rather than 0

    return optionList

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
