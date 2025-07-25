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
    travellermap.Option,
    cartographer.RenderOptions
    ] = {
        travellermap.Option.SectorGrid: cartographer.RenderOptions.GridMask,
        travellermap.Option.SelectedSectorNames: cartographer.RenderOptions.SectorsSelected,
        travellermap.Option.SectorNames: cartographer.RenderOptions.SectorsAll,
        travellermap.Option.Borders: cartographer.RenderOptions.BordersMask,
        travellermap.Option.Routes: cartographer.RenderOptions.RoutesMask,
        travellermap.Option.RegionNames: cartographer.RenderOptions.NamesMask,
        travellermap.Option.ImportantWorlds: cartographer.RenderOptions.WorldsMask,
        travellermap.Option.WorldColours: cartographer.RenderOptions.WorldColours,
        travellermap.Option.FilledBorders: cartographer.RenderOptions.FilledBorders,
        travellermap.Option.DimUnofficial: cartographer.RenderOptions.DimUnofficial,
        travellermap.Option.ImportanceOverlay: cartographer.RenderOptions.ImportanceOverlay,
        travellermap.Option.PopulationOverlay: cartographer.RenderOptions.PopulationOverlay,
        travellermap.Option.CapitalsOverlay: cartographer.RenderOptions.CapitalOverlay,
        travellermap.Option.MinorRaceOverlay: cartographer.RenderOptions.MinorHomeWorlds,
        travellermap.Option.DroyneWorldOverlay: cartographer.RenderOptions.DroyneWorlds,
        travellermap.Option.AncientSitesOverlay: cartographer.RenderOptions.AncientWorlds,
        travellermap.Option.StellarOverlay: cartographer.RenderOptions.StellarOverlay
    }
def mapOptionsToRenderOptions(
        mapOptions: typing.Iterable[travellermap.Option],
        ) -> cartographer.RenderOptions:
    renderOptions = 0
    for option in mapOptions:
        mask = _MapOptionsToRenderOptions.get(option)
        if mask is not None:
            renderOptions |= mask
    return renderOptions
