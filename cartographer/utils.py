import cartographer
import common
import multiverse
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
    multiverse.MapOption,
    cartographer.RenderOptions
    ] = {
        multiverse.MapOption.SectorGrid: cartographer.RenderOptions.GridMask,
        multiverse.MapOption.SelectedSectorNames: cartographer.RenderOptions.SectorsSelected,
        multiverse.MapOption.SectorNames: cartographer.RenderOptions.SectorsAll,
        multiverse.MapOption.Borders: cartographer.RenderOptions.BordersMask,
        multiverse.MapOption.Routes: cartographer.RenderOptions.RoutesMask,
        multiverse.MapOption.RegionNames: cartographer.RenderOptions.NamesMask,
        multiverse.MapOption.ImportantWorlds: cartographer.RenderOptions.WorldsMask,
        multiverse.MapOption.WorldColours: cartographer.RenderOptions.WorldColours,
        multiverse.MapOption.FilledBorders: cartographer.RenderOptions.FilledBorders,
        multiverse.MapOption.DimUnofficial: cartographer.RenderOptions.DimUnofficial,
        multiverse.MapOption.ImportanceOverlay: cartographer.RenderOptions.ImportanceOverlay,
        multiverse.MapOption.PopulationOverlay: cartographer.RenderOptions.PopulationOverlay,
        multiverse.MapOption.CapitalsOverlay: cartographer.RenderOptions.CapitalOverlay,
        multiverse.MapOption.MinorRaceOverlay: cartographer.RenderOptions.MinorHomeWorlds,
        multiverse.MapOption.DroyneWorldOverlay: cartographer.RenderOptions.DroyneWorlds,
        multiverse.MapOption.AncientSitesOverlay: cartographer.RenderOptions.AncientWorlds,
        multiverse.MapOption.StellarOverlay: cartographer.RenderOptions.StellarOverlay
    }
def mapOptionsToRenderOptions(
        mapOptions: typing.Iterable[multiverse.MapOption],
        ) -> cartographer.RenderOptions:
    renderOptions = 0
    for option in mapOptions:
        mask = _MapOptionsToRenderOptions.get(option)
        if mask is not None:
            renderOptions |= mask
    return renderOptions
