import cartographer
import travellermap
import typing

def makeAlphaColor(
        alpha: typing.Union[float, int],
        color: str,
        isNormalised: bool = False
        ) -> str:
    red, green, blue, _ = travellermap.parseHtmlColor(htmlColor=color)

    if isNormalised:
        alpha *= 255

    alpha = int(round(alpha))
    if alpha < 0:
        alpha = 0
    if alpha > 255:
        alpha =255

    return f'#{alpha:02X}{red:02X}{green:02X}{blue:02X}'


# TODO: Handle other option mappings
# TODO: This feels hacky, I need to consolidate it down to a single
# representation of the options.
_MapOptionsToRenderOptions: typing.Dict[
    travellermap.Option,
    cartographer.MapOptions
    ] = {
        # There is no entry for GalacticDirections as it's not a render
        #travellermap.Option.GalacticDirections
        travellermap.Option.SectorGrid: cartographer.MapOptions.GridMask,
        # TODO: There is currently no way to show all sector names as I don't have the
        # tri-state controls that Traveller Map has
        travellermap.Option.SectorNames: cartographer.MapOptions.SectorsSelected,
        travellermap.Option.Borders: cartographer.MapOptions.BordersMask,
        travellermap.Option.Routes: cartographer.MapOptions.RoutesMask,
        travellermap.Option.RegionNames: cartographer.MapOptions.NamesMask,
        travellermap.Option.ImportantWorlds: cartographer.MapOptions.WorldsMask,
        travellermap.Option.WorldColours: cartographer.MapOptions.WorldColors,
        travellermap.Option.FilledBorders: cartographer.MapOptions.FilledBorders,
        travellermap.Option.DimUnofficial: cartographer.MapOptions.DimUnofficial,
        travellermap.Option.ImportanceOverlay: cartographer.MapOptions.ImportanceOverlay,
        travellermap.Option.PopulationOverlay: cartographer.MapOptions.PopulationOverlay,
        travellermap.Option.CapitalsOverlay: cartographer.MapOptions.CapitalOverlay,
        travellermap.Option.MinorRaceOverlay: cartographer.MapOptions.MinorHomeWorlds,
        travellermap.Option.DroyneWorldOverlay: cartographer.MapOptions.DroyneWorlds,
        travellermap.Option.AncientSitesOverlay: cartographer.MapOptions.AncientWorlds,
        travellermap.Option.StellarOverlay: cartographer.MapOptions.StellarOverlay,
        #travellermap.Option.EmpressWaveOverlay
        #travellermap.Option.QrekrshaZoneOverlay
        #travellermap.Option.MainsOverlay
    }
def mapOptionsToRenderOptions(
        mapOptions: typing.Iterable[travellermap.Option],
        ) -> cartographer.MapOptions:
    renderOptions = 0
    for option in mapOptions:
        mask = _MapOptionsToRenderOptions.get(option)
        if mask is not None:
            renderOptions |= mask
    return renderOptions