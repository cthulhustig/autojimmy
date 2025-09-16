import app
import cartographer
import typing

_DarkStyles = [
    cartographer.MapStyle.Poster,
    cartographer.MapStyle.Candy,
    cartographer.MapStyle.Terminal
]

def isLightMapStyle(style: cartographer.MapStyle) -> bool:
    return style not in _DarkStyles

def isDarkMapStyle(style: cartographer.MapStyle) -> bool:
    return style in _DarkStyles

_MapOptionsToRenderOptions: typing.Dict[
    app.MapOption,
    cartographer.RenderOptions
    ] = {
        app.MapOption.SectorGrid: cartographer.RenderOptions.GridMask,
        app.MapOption.SelectedSectorNames: cartographer.RenderOptions.SectorsSelected,
        app.MapOption.AllSectorNames: cartographer.RenderOptions.SectorsAll,
        app.MapOption.Borders: cartographer.RenderOptions.BordersMask,
        app.MapOption.Routes: cartographer.RenderOptions.RoutesMask,
        app.MapOption.RegionNames: cartographer.RenderOptions.NamesMask,
        app.MapOption.ImportantWorlds: cartographer.RenderOptions.WorldsMask,
        app.MapOption.WorldColours: cartographer.RenderOptions.WorldColours,
        app.MapOption.FilledBorders: cartographer.RenderOptions.FilledBorders,
        app.MapOption.DimUnofficial: cartographer.RenderOptions.DimUnofficial,
        app.MapOption.ImportanceOverlay: cartographer.RenderOptions.ImportanceOverlay,
        app.MapOption.PopulationOverlay: cartographer.RenderOptions.PopulationOverlay,
        app.MapOption.CapitalsOverlay: cartographer.RenderOptions.CapitalOverlay,
        app.MapOption.MinorRaceOverlay: cartographer.RenderOptions.MinorHomeWorlds,
        app.MapOption.DroyneWorldOverlay: cartographer.RenderOptions.DroyneWorlds,
        app.MapOption.AncientSitesOverlay: cartographer.RenderOptions.AncientWorlds,
        app.MapOption.StellarOverlay: cartographer.RenderOptions.StellarOverlay
    }
def mapOptionsToRenderOptions(
        mapOptions: typing.Iterable[app.MapOption],
        ) -> cartographer.RenderOptions:
    renderOptions = 0
    for option in mapOptions:
        mask = _MapOptionsToRenderOptions.get(option)
        if mask is not None:
            renderOptions |= mask
    return renderOptions
