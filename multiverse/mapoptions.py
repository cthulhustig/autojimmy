import enum

# TODO: Once the datastore has been updated to not load map options
# for custom sectors. It should be possible to move this class into
# app\. Ideally it should probably go into gui\map\ but it's needed
# in app as it's used by app.Config. As part of this change the code
# that converts these map options to cartographer render options
# should be moved into gui\map

# NOTE: If I ever change the name of any of these enums I'll
# need to add a mapping to the code that loads CustomMapOptions
# from the custom universe.json format I use for custom sectors.
# TODO: The note above can be removed when I remove the web map
# as the options used when the sector was added aren't relevant
# for local rendering
class MapOption(enum.Enum):
    GalacticDirections = 'Galactic Directions'
    SectorGrid = 'Sector Grid'
    # Traveller Map supports showing no sector names, selected sector names or
    # all sector names. With the selected sectors being those around the center
    # of chartered space. I currently only have a single option for sector names
    # and it maps to showing all names. Adding a tri-state control to the UI to
    # support none/selected/all would be a bit of a faff and I don't think it's
    # worth the effort. Instead I've just gone with a single sector names options
    # that maps to all sector names
    SelectedSectorNames = 'Selected Sector Names'
    # TODO: This enum should really be called AllSectorNames but changing it
    # would cause pre-existing custom sectors that used it to fail to load
    # (see note above). When I remove the web map I can rename it.
    SectorNames = 'All Sector Names'
    Borders = 'Borders'
    Routes = 'Routes'
    RegionNames = 'Region Names'
    ImportantWorlds = 'Important Worlds'

    HideUI = 'Hide UI'
    WorldColours = 'More World Colours'
    FilledBorders = 'Filled Borders'
    DimUnofficial = 'Dim Unofficial Data'

    ImportanceOverlay = 'Importance'
    PopulationOverlay = 'Population'
    CapitalsOverlay = 'Capitals/Candidates'
    MinorRaceOverlay = 'Minor Race Homeworlds'
    DroyneWorldOverlay = 'Droyne Worlds'
    AncientSitesOverlay = 'Ancient Sites'
    StellarOverlay = 'Stellar'
    EmpressWaveOverlay = 'Empress Wave'
    QrekrshaZoneOverlay = 'Qrekrsha Zone'
    AntaresSupernovaOverlay = 'Antares Supernova'
    MainsOverlay = 'Mains'
