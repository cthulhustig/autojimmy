import maprenderer
import travellermap
import typing

def makeAlphaColor(
        alpha: typing.Union[float, int],
        color: str
        ) -> str:
    red, green, blue, _ = travellermap.parseHtmlColor(htmlColor=color)

    alpha = int(alpha)
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
    maprenderer.MapOptions
    ] = {
        # There is no entry for GalacticDirections as it's not a render
        #travellermap.Option.GalacticDirections
        travellermap.Option.SectorGrid: maprenderer.MapOptions.GridMask,
        # TODO: There is currently no way to show all sector names as I don't have the
        # tri-state controls that Traveller Map has
        travellermap.Option.SectorNames: maprenderer.MapOptions.SectorsSelected,
        travellermap.Option.Borders: maprenderer.MapOptions.BordersMask,
        travellermap.Option.Routes: maprenderer.MapOptions.RoutesMask,
        travellermap.Option.RegionNames: maprenderer.MapOptions.NamesMask,
        travellermap.Option.ImportantWorlds: maprenderer.MapOptions.WorldsMask,
        travellermap.Option.WorldColours: maprenderer.MapOptions.WorldColors,
        travellermap.Option.FilledBorders: maprenderer.MapOptions.FilledBorders,
        travellermap.Option.DimUnofficial: maprenderer.MapOptions.DimUnofficial,
        travellermap.Option.ImportanceOverlay: maprenderer.MapOptions.ImportanceOverlay,
        travellermap.Option.PopulationOverlay: maprenderer.MapOptions.PopulationOverlay,
        travellermap.Option.CapitalsOverlay: maprenderer.MapOptions.CapitalOverlay,
        travellermap.Option.MinorRaceOverlay: maprenderer.MapOptions.MinorHomeWorlds,
        travellermap.Option.DroyneWorldOverlay: maprenderer.MapOptions.DroyneWorlds,
        travellermap.Option.AncientSitesOverlay: maprenderer.MapOptions.AncientWorlds,
        travellermap.Option.StellarOverlay: maprenderer.MapOptions.StellarOverlay,
        #travellermap.Option.EmpressWaveOverlay
        #travellermap.Option.QrekrshaZoneOverlay
        #travellermap.Option.MainsOverlay
    }
def mapOptionsToRenderOptions(
        mapOptions: typing.Iterable[travellermap.Option],
        ) -> maprenderer.MapOptions:
    renderOptions = 0
    for option in mapOptions:
        mask = _MapOptionsToRenderOptions.get(option)
        if mask is not None:
            renderOptions |= mask
    return renderOptions