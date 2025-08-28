import cartographer
import common
import travellermap
import typing

def makeAlphaColour(
        alpha: typing.Union[float, int],
        colour: str,
        isNormalised: bool = False
        ) -> str:
    red, green, blue, _ = common.parseHtmlColour(htmlColour=colour)

    if isNormalised:
        alpha *= 255

    alpha = int(round(alpha))
    if alpha < 0:
        alpha = 0
    if alpha > 255:
        alpha = 255

    return f'#{alpha:02X}{red:02X}{green:02X}{blue:02X}'


_MapOptionsToRenderOptions: typing.Dict[
    travellermap.MapOption,
    cartographer.RenderOptions
    ] = {
        travellermap.MapOption.SectorGrid: cartographer.RenderOptions.GridMask,
        travellermap.MapOption.SelectedSectorNames: cartographer.RenderOptions.SectorsSelected,
        travellermap.MapOption.SectorNames: cartographer.RenderOptions.SectorsAll,
        travellermap.MapOption.Borders: cartographer.RenderOptions.BordersMask,
        travellermap.MapOption.Routes: cartographer.RenderOptions.RoutesMask,
        travellermap.MapOption.RegionNames: cartographer.RenderOptions.NamesMask,
        travellermap.MapOption.ImportantWorlds: cartographer.RenderOptions.WorldsMask,
        travellermap.MapOption.WorldColours: cartographer.RenderOptions.WorldColours,
        travellermap.MapOption.FilledBorders: cartographer.RenderOptions.FilledBorders,
        travellermap.MapOption.DimUnofficial: cartographer.RenderOptions.DimUnofficial,
        travellermap.MapOption.ImportanceOverlay: cartographer.RenderOptions.ImportanceOverlay,
        travellermap.MapOption.PopulationOverlay: cartographer.RenderOptions.PopulationOverlay,
        travellermap.MapOption.CapitalsOverlay: cartographer.RenderOptions.CapitalOverlay,
        travellermap.MapOption.MinorRaceOverlay: cartographer.RenderOptions.MinorHomeWorlds,
        travellermap.MapOption.DroyneWorldOverlay: cartographer.RenderOptions.DroyneWorlds,
        travellermap.MapOption.AncientSitesOverlay: cartographer.RenderOptions.AncientWorlds,
        travellermap.MapOption.StellarOverlay: cartographer.RenderOptions.StellarOverlay
    }
def mapOptionsToRenderOptions(
        mapOptions: typing.Iterable[travellermap.MapOption],
        ) -> cartographer.RenderOptions:
    renderOptions = 0
    for option in mapOptions:
        mask = _MapOptionsToRenderOptions.get(option)
        if mask is not None:
            renderOptions |= mask
    return renderOptions
