import math
import travellermap
import typing
import urllib.parse

# TODO: The majority of this should be removed as part of the current
# work. I'll still need to format linter URLs but that could probably
# be moved into whichever code is currently calling it

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
_WorldColoursOption = 0x4000
_FilledBordersOption = 0x8000

_StyleOptionMap = {
    travellermap.MapStyle.Poster: 'poster',
    travellermap.MapStyle.Print: 'print',
    travellermap.MapStyle.Atlas: 'atlas',
    travellermap.MapStyle.Candy: 'candy',
    travellermap.MapStyle.Draft: 'draft',
    travellermap.MapStyle.Fasa: 'fasa',
    travellermap.MapStyle.Terminal: 'terminal',
    travellermap.MapStyle.Mongoose: 'mongoose'
}

# NOTE: This only supports generating full sector posters from custom sector data, it doesn't
# support generating posters from standard sector data or subsector/quadrant posters of
# custom sectors as those features aren't used by the app
def formatPosterUrl(
        baseMapUrl: str,
        style: travellermap.MapStyle,
        options: typing.Optional[typing.Collection[travellermap.MapOption]] = None,
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
        style: typing.Optional[travellermap.MapStyle] = None,
        options: typing.Optional[typing.Collection[travellermap.MapOption]] = None,
        minimal: bool = False
        ) -> typing.List[str]:
    optionList = []
    if milieu != None:
        optionList.append('milieu=' + str(milieu.value))
    style = _StyleOptionMap.get(style)
    if style != None:
        optionList.append('style=' + style)

    if options == None:
        # Always have a valid list of options as it makes the following code simpler
        options = []

    optionBitMask = _ForceHexesOption # Always enabled
    if travellermap.MapOption.SectorGrid in options:
        optionBitMask |= _GridMaskOption

    if travellermap.MapOption.SectorNames in options:
        optionBitMask |= _SectorsAllOption
    elif travellermap.MapOption.SelectedSectorNames in options:
        optionBitMask |= _SectorsSelectedOption

    if travellermap.MapOption.Borders in options:
        optionBitMask |= _BordersMaskOption

    if travellermap.MapOption.RegionNames in options:
        optionBitMask |= _NamesMaskOption

    if travellermap.MapOption.ImportantWorlds in options:
        optionBitMask |= _WorldsMaskOption

    if travellermap.MapOption.WorldColours in options:
        optionBitMask |= _WorldColoursOption

    if travellermap.MapOption.FilledBorders in options:
        optionBitMask |= _FilledBordersOption

    optionList.append('options=' + str(optionBitMask)) # Always add this as ForcedHexes is always set

    if travellermap.MapOption.HideUI in options:
        optionList.append('hideui=1')
    elif not minimal:
        optionList.append('hideui=0')

    # Galactic directors are on by default so this logic is different to most other options
    if travellermap.MapOption.GalacticDirections not in options:
        optionList.append('galdir=0')
    elif not minimal:
        optionList.append('galdir=1')

    # Routes are on by default so this logic is different to most other options
    if travellermap.MapOption.Routes not in options:
        optionList.append('routes=0')
    elif not minimal:
        optionList.append('routes=1')

    if travellermap.MapOption.DimUnofficial in options:
        optionList.append('dimunofficial=1')
    elif not minimal:
        optionList.append('dimunofficial=0')

    if travellermap.MapOption.ImportanceOverlay in options:
        optionList.append('im=1')
    elif not minimal:
        optionList.append('im=0')

    if travellermap.MapOption.PopulationOverlay in options:
        optionList.append('po=1')
    elif not minimal:
        optionList.append('po=0')

    if travellermap.MapOption.CapitalsOverlay in options:
        optionList.append('cp=1')
    elif not minimal:
        optionList.append('cp=0')

    if travellermap.MapOption.MinorRaceOverlay in options:
        optionList.append('mh=1')
    elif not minimal:
        optionList.append('mh=0')

    if travellermap.MapOption.DroyneWorldOverlay in options:
        optionList.append('dw=1')
    elif not minimal:
        optionList.append('dw=0')

    if travellermap.MapOption.AncientSitesOverlay in options:
        optionList.append('an=1')
    elif not minimal:
        optionList.append('an=0')

    if travellermap.MapOption.StellarOverlay in options:
        optionList.append('stellar=1')
    elif not minimal:
        optionList.append('stellar=0')

    if travellermap.MapOption.MainsOverlay in options:
        optionList.append('mains=1')
    elif not minimal:
        optionList.append('mains=0')

    # Note that ew and qz use an empty argument to clear rather than 0
    if travellermap.MapOption.EmpressWaveOverlay in options:
        optionList.append('ew=milieu') # Show for current milieu
    elif not minimal:
        optionList.append('ew=') # Empty to clear rather than 0

    if travellermap.MapOption.QrekrshaZoneOverlay in options:
        optionList.append('qz=1')
    elif not minimal:
        optionList.append('qz=') # Empty to clear rather than 0

    if travellermap.MapOption.AntaresSupernovaOverlay in options:
        optionList.append('as=milieu') # Show for current milieu
    elif not minimal:
        optionList.append('as=') # Empty to clear rather than 0

    return optionList
