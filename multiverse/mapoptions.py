import enum

# TODO: Once the datastore has been updated to not load map options
# for custom sectors. It should be possible to move this class into
# app\. Ideally it should probably go into gui\map\ but it's needed
# in app as it's used by app.Config. As part of this change the code
# that converts these map options to cartographer render options
# should be moved into gui\map

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
    AllSectorNames = 'All Sector Names'
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
