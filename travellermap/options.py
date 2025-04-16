import enum

class Option(enum.Enum):
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
