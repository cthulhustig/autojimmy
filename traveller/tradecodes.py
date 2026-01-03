import enum
import survey
import typing

# This covers the trade remarks from the core rules and https://wiki.travellerrpg.com/Trade_classification
# I've taken a bit of a liberty and added amber and red zone to the TradeCode enum as it makes
# code elsewhere a lot simpler as the can just be included in the availability, purchase and
# sale lists when defining and using trade goods

class TradeCode(enum.Enum):
    # MGT2 rule trade remarks
    AgriculturalWorld = 0
    AsteroidBelt = 1
    BarrenWorld = 2
    DesertWorld = 3
    FluidWorld = 4
    GardenWorld = 5
    HighPopulationWorld = 6
    HighTechWorld = 7
    IceCappedWorld = 8
    IndustrialWorld = 9
    LowPopulationWorld = 10
    LowTechWorld = 11
    NonAgriculturalWorld = 12
    NonIndustrialWorld = 13
    PoorWorld = 14
    RichWorld = 15
    VacuumWorld = 16
    WaterWorld = 17
    # Auto-jimmy custom zone trade remarks
    AmberZone = 18
    RedZone = 19
    # https://wiki.travellerrpg.com/Trade_classification
    ColdWorld = 20,
    FrozenWorld = 21,
    HotWorld = 22,
    TropicWorld = 23,
    TundraWorld = 24,
    PreAgriculturalWorld = 25,
    PreIndustrialWorld = 26,
    PreRichWorld = 27,
    HellWorld = 28,
    LockedWorld = 29,
    OceanWorld = 30,
    TwilightZoneWorld = 31,
    SubsectorCapital = 32,
    SectorCapital = 33,
    ImperialCapital = 34,
    ColonyWorld = 35,
    DieBackWorld = 36,
    PreHighPopulationWorld = 37,
    FarmingWorld = 38,
    MiningWorld = 39,
    MilitaryRule = 40,
    PenalColony = 41,
    PrisonCamp = 42,
    Reserve = 43,
    DataRepositoryWorld = 44,
    AncientsSiteWorld = 45,
    ConstructWorld = 46,
    DangerousWorld = 47,
    ForbiddenWorld = 48,
    PuzzleWorld = 49,
    ResearchStation = 50,
    SatelliteWorld = 51,
    XBoatStation = 52


_StringToTradeCodeMap = {
    'Ag': TradeCode.AgriculturalWorld,
    'As': TradeCode.AsteroidBelt,
    'Ba': TradeCode.BarrenWorld,
    'De': TradeCode.DesertWorld,
    'Fl': TradeCode.FluidWorld,
    'Ga': TradeCode.GardenWorld,
    'Hi': TradeCode.HighPopulationWorld,
    'Ht': TradeCode.HighTechWorld,
    'Ic': TradeCode.IceCappedWorld, # Note: Traveller core rules has Ie but I think it's wrong
    'In': TradeCode.IndustrialWorld,
    'Lo': TradeCode.LowPopulationWorld,
    'Lt': TradeCode.LowTechWorld,
    'Na': TradeCode.NonAgriculturalWorld,
    'Ni': TradeCode.NonIndustrialWorld, # Note: Traveller core rules has NI but I think it's wrong
    'Po': TradeCode.PoorWorld,
    'Ri': TradeCode.RichWorld,
    'Va': TradeCode.VacuumWorld,
    'Wa': TradeCode.WaterWorld,
    'Az': TradeCode.AmberZone, # Note: This was created by me, see comment at top of file
    'Rz': TradeCode.RedZone, # Note: This was created by me, see comment at top of file
    'Co': TradeCode.ColdWorld,
    'Fr': TradeCode.FrozenWorld,
    'Ho': TradeCode.HotWorld,
    'Tr': TradeCode.TropicWorld,
    'Tu': TradeCode.TundraWorld,
    'Pa': TradeCode.PreAgriculturalWorld,
    'Pi': TradeCode.PreIndustrialWorld,
    'Pr': TradeCode.PreRichWorld,
    'He': TradeCode.HellWorld,
    'Lk': TradeCode.LockedWorld,
    'Oc': TradeCode.OceanWorld,
    'Tz': TradeCode.TwilightZoneWorld,
    'Cp': TradeCode.SubsectorCapital,
    'Cs': TradeCode.SectorCapital,
    'Cx': TradeCode.ImperialCapital,
    'Cy': TradeCode.ColonyWorld,
    'Di': TradeCode.DieBackWorld,
    'Ph': TradeCode.PreHighPopulationWorld,
    'Fa': TradeCode.FarmingWorld,
    'Mi': TradeCode.MiningWorld,
    'Mr': TradeCode.MilitaryRule,
    'Pe': TradeCode.PenalColony,
    'Px': TradeCode.PrisonCamp,
    'Re': TradeCode.Reserve,
    'Ab': TradeCode.DataRepositoryWorld,
    'An': TradeCode.AncientsSiteWorld,
    'Ax': TradeCode.ConstructWorld,
    'Da': TradeCode.DangerousWorld,
    'Fo': TradeCode.ForbiddenWorld,
    'Pz': TradeCode.PuzzleWorld,
    'Rs': TradeCode.ResearchStation,
    'Sa': TradeCode.SatelliteWorld,
    'Xb': TradeCode.XBoatStation,
}

_TradeCodeStringMap = {v: k for k, v in _StringToTradeCodeMap.items()}

_TradeCodeNameMap = {
    TradeCode.AgriculturalWorld: 'Agricultural World',
    TradeCode.AsteroidBelt: 'Asteroid Belt',
    TradeCode.BarrenWorld: 'Barren World',
    TradeCode.DesertWorld: 'Desert World',
    TradeCode.FluidWorld: 'Fluid World',
    TradeCode.GardenWorld: 'Garden World',
    TradeCode.HighPopulationWorld: 'High Population',
    TradeCode.HighTechWorld: 'High Tech World',
    TradeCode.IceCappedWorld: 'Ice-Capped World',
    TradeCode.IndustrialWorld: 'Industrial World',
    TradeCode.LowPopulationWorld: 'Low Population',
    TradeCode.LowTechWorld: 'Low Tech World',
    TradeCode.NonAgriculturalWorld: 'Non-agricultural World',
    TradeCode.NonIndustrialWorld: 'Non-industrial World',
    TradeCode.PoorWorld: 'Poor World',
    TradeCode.RichWorld: 'Rich World',
    TradeCode.VacuumWorld: 'Vacuum World',
    TradeCode.WaterWorld: 'Water World',
    TradeCode.AmberZone: 'Amber Zone',
    TradeCode.RedZone: 'Red Zone',
    TradeCode.ColdWorld: 'Cold World',
    TradeCode.FrozenWorld: 'Frozen World',
    TradeCode.HotWorld: 'Hot World',
    TradeCode.TropicWorld: 'Tropic World',
    TradeCode.TundraWorld: 'Tundra World',
    TradeCode.PreAgriculturalWorld: 'Pre-agricultural World',
    TradeCode.PreIndustrialWorld: 'Pre-Industrial World',
    TradeCode.PreRichWorld: 'Pre-rich World',
    TradeCode.HellWorld: 'Hell World',
    TradeCode.LockedWorld: 'Locked World',
    TradeCode.OceanWorld: 'Ocean World',
    TradeCode.TwilightZoneWorld: 'Twilight Zone World',
    TradeCode.SubsectorCapital: 'Subsector Capital',
    TradeCode.SectorCapital: 'Sector Capital',
    TradeCode.ImperialCapital: 'Imperial Capital',
    TradeCode.ColonyWorld: 'Colony World',
    TradeCode.DieBackWorld: 'Die Back World',
    TradeCode.PreHighPopulationWorld: 'Pre-high Population World',
    TradeCode.FarmingWorld: 'Farming World',
    TradeCode.MiningWorld: 'Mining World',
    TradeCode.MilitaryRule: 'Military Rule',
    TradeCode.PenalColony: 'Penal Colony',
    TradeCode.PrisonCamp: 'Prison Camp',
    TradeCode.Reserve: 'Reserve',
    TradeCode.DataRepositoryWorld: 'Data Repository World',
    TradeCode.AncientsSiteWorld: 'Ancients Site World',
    TradeCode.ConstructWorld: 'Construct World',
    TradeCode.DangerousWorld: 'Dangerous World',
    TradeCode.ForbiddenWorld: 'Forbidden World',
    TradeCode.PuzzleWorld: 'Puzzle World',
    TradeCode.ResearchStation: 'Research Station',
    TradeCode.SatelliteWorld: 'Satellite World',
    TradeCode.XBoatStation: 'X-Boat Station',
}

_TradeCodeDescriptionMap = {
    TradeCode.AgriculturalWorld: 'A reasonable atmosphere and available surface water, which may be ideal for agriculture with a moderate population (100s of thousands to 10s of millions).',
    TradeCode.AsteroidBelt: 'A ring of many small worldlets (planetoids), not capable of retaining an atmosphere or water.',
    TradeCode.BarrenWorld: 'A Barren world has no population, government, or law level.',
    TradeCode.DesertWorld: 'Desert worlds have no free-standing water.',
    TradeCode.FluidWorld: 'A fluid world has an ocean or oceans of a liquid other than water, (e.g., ammonia or methane).',
    TradeCode.GardenWorld: 'A world hospitable to most sophonts (...AKA a "paradise"), which does not require protective equipment.',
    TradeCode.HighPopulationWorld: 'A world with a billion or more in population.',
    TradeCode.HighTechWorld: 'A world with a higher than normal technology level.',
    TradeCode.IceCappedWorld: 'A world with little or no atmosphere with all of its water frozen.',
    TradeCode.IndustrialWorld: 'Industrial worlds have large production and manufacturing bases. It has an un-breathable atmosphere and high population (Billions or more) ',
    TradeCode.LowPopulationWorld: 'A world with less than 10 thousand in population.',
    TradeCode.LowTechWorld: 'A world with a lower than normal technology level.',
    TradeCode.NonAgriculturalWorld: 'Non-agricultural worlds are not able to produce quality foodstuffs and must import them.',
    TradeCode.NonIndustrialWorld: 'Non-Industrial worlds have a population of 10s of thousands to millions, lacking the population to be self supporting.',
    TradeCode.PoorWorld: 'Poor worlds have thin atmospheres and little or no surface water, making them poor places to live.',
    TradeCode.RichWorld: 'Rich worlds have high-grade living conditions. They have ideal breathable atmospheres and moderate populations (millions to 100s of millions).',
    TradeCode.VacuumWorld: 'Single worlds with no atmosphere.',
    TradeCode.WaterWorld: ' Water worlds have 90% or more of their surface covered in an ocean of water (H₂O).',
    TradeCode.AmberZone: 'A world that has been classified as requiring caution by the Travellers\' Aid Society',
    TradeCode.RedZone: 'A world that has been classified as dangerous by the Travellers\' Aid Society',
    TradeCode.ColdWorld: 'A world with a climate at the lower end of survivability for most sophonts.',
    TradeCode.FrozenWorld: 'A world with a climate beyond the lower end of survivability.',
    TradeCode.HotWorld: 'A world with a climate at the upper end of survivability for most sophonts.',
    TradeCode.TropicWorld: 'A world with a warmer than average climate but is also considered habitable.',
    TradeCode.TundraWorld: 'A world with a colder than average climate but is also considered habitable.',
    TradeCode.PreAgriculturalWorld: 'A world suited to being an agricultural world but lacking the population to exploit it (10s of Thousands). Or having too great a population to have suitable agricultural resources for export. (100s of millions)',
    TradeCode.PreIndustrialWorld: 'It is a world working toward being an industrial world but lacks the population to do so. (10s or 100s of millions).',
    TradeCode.PreRichWorld: 'A world suited to becoming a Rich world, but lacking the population to become Rich. (100s of thousands). Or having too many people to be rich (billions).',
    TradeCode.HellWorld: 'A world with a tainted atmosphere and little or no surface water.',
    TradeCode.LockedWorld: 'A tidally locked world does not rotate like most planets do. It has one face locked to the gravity source, usually a star, and the other locked away from the gravity source, making for extremely warm weather on one side and cold on the other.',
    TradeCode.OceanWorld: 'Ocean worlds are covered with very deep oceans with less than 1% of their land above sea level.',
    TradeCode.TwilightZoneWorld: 'The world is tide locked to the primary, giving a hot pole, a cold pole and a twilight zone between.',
    TradeCode.SubsectorCapital: 'The capital of the local region, usually a subsector in size.',
    TradeCode.SectorCapital: 'The capital of a group of hundreds of star systems, typically a sector in size.',
    TradeCode.ImperialCapital: 'The overall capital of an interstellar government.',
    TradeCode.ColonyWorld: 'The world is a colony of another, larger and more important world nearby.',
    TradeCode.DieBackWorld: 'The die back world was once settled and developed, but the inhabitants have either died off or left leaving behind the remnants of their civilization.',
    TradeCode.PreHighPopulationWorld: 'A world with over a hundred million people, but not yet at a billion.',
    TradeCode.FarmingWorld: 'A world devoted to agriculture.',
    TradeCode.MiningWorld: 'A world located in an Industrial system being exploited for mineral resources.',
    TradeCode.MilitaryRule: 'A world under overall control of the local military (...regardless of government type).',
    TradeCode.PenalColony: ' colony devoted to housing prisoners.',
    TradeCode.PrisonCamp: 'A prison for criminals or other exiles.',
    TradeCode.Reserve: 'A world with restricted access, either to protect the indigenous life forms, to protect available resources, or other reasons.',
    TradeCode.DataRepositoryWorld: 'The world has a centralized collection for information and data.',
    TradeCode.AncientsSiteWorld: 'A high-tech remnant of the now-vanished Ancients.',
    TradeCode.ConstructWorld: 'An unusually large and artificial construct, e.g. Rosettes, Ringworlds, etc.',
    TradeCode.DangerousWorld: 'A world with an environment, laws, customs, life forms, or other conditions make it dangerous to visitors.',
    TradeCode.ForbiddenWorld: 'This is a world considered "Forbidden", with an environment, laws, customs, life forms, or other conditions that make it extremely dangerous to visitors. Everyone is forbidden to travel here.',
    TradeCode.PuzzleWorld: 'A world with an environment, laws, customs, life forms, or other conditions that are not well understood and might be a danger to visitor.',
    TradeCode.ResearchStation: 'An experimental research facility.',
    TradeCode.SatelliteWorld: 'The main world is a satellite of either a gas giant or another world.',
    TradeCode.XBoatStation: 'An Imperial facility for rapid message transmission.',
}

def tradeCode(tradeCodeString: str) -> TradeCode:
    if tradeCodeString not in _StringToTradeCodeMap:
        return None
    return _StringToTradeCodeMap[tradeCodeString]

def tradeCodeString(tradeCode: TradeCode) -> str:
    assert(tradeCode in _TradeCodeStringMap)
    return _TradeCodeStringMap[tradeCode]

def tradeCodeName(tradeCode: TradeCode) -> str:
    assert(tradeCode in _TradeCodeNameMap)
    return _TradeCodeNameMap[tradeCode]

def tradeCodeNameMap() -> typing.Mapping[TradeCode, str]:
    return _TradeCodeNameMap

def tradeCodeDescription(tradeCode: TradeCode) -> str:
    assert(tradeCode in _TradeCodeDescriptionMap)
    return _TradeCodeDescriptionMap[tradeCode]

def tradeCodeDescriptionMap() -> typing.Mapping[TradeCode, str]:
    return _TradeCodeDescriptionMap

def calculateMongooseTradeCodes(
        uwp: str
        ) -> typing.Set[TradeCode]:
    _, size, atmosphere, hydrographics, population, government, \
        lawLevel, techLevel = survey.parseSystemUWPString(uwp)
    size = survey.ehexToInteger(size)
    atmosphere = survey.ehexToInteger(atmosphere)
    hydrographics = survey.ehexToInteger(hydrographics)
    population = survey.ehexToInteger(population)
    government = survey.ehexToInteger(government)
    lawLevel = survey.ehexToInteger(lawLevel)
    techLevel = survey.ehexToInteger(techLevel)
    tradeCodes = set()

    if (atmosphere >= 4 and atmosphere <= 9) and \
        (hydrographics >= 4 and hydrographics <= 8) and \
        (population >= 5 and population <= 7):
        tradeCodes.add(TradeCode.AgriculturalWorld)

    if (size == 0) and \
        (atmosphere == 0) and \
        (hydrographics == 0):
        tradeCodes.add(TradeCode.AsteroidBelt)

    if (population == 0) and \
        (government == 0) and \
        (lawLevel == 0):
        tradeCodes.add(TradeCode.BarrenWorld)

    # TODO: Mongoose 1e has this different
    # TODO: Mongoose 2e has this different
    if (atmosphere >= 2 and atmosphere <= 9) and \
        (hydrographics == 0):
        tradeCodes.add(TradeCode.DesertWorld)

    if (atmosphere >= 10) and \
        (hydrographics >= 1):
        tradeCodes.add(TradeCode.FluidWorld)

    # TODO: Mongoose 1e has this different
    if (size >= 6 and size <= 8) and \
        (atmosphere in [5,6,8]) and \
        (hydrographics >= 5 and hydrographics <= 7):
        tradeCodes.add(TradeCode.GardenWorld)

    if population >= 9:
        tradeCodes.add(TradeCode.HighPopulationWorld)

    if techLevel >= 12:
        tradeCodes.add(TradeCode.HighTechWorld)

    if (atmosphere in [0, 1]) and \
        (hydrographics >= 1):
        tradeCodes.add(TradeCode.IceCappedWorld)

    # TODO: Mongoose 1e has this different
    # TODO: Mongoose 2e has this different
    if (atmosphere in [0, 1, 2, 4, 7, 9, 10, 11, 12]) and \
        (population >= 9):
        tradeCodes.add(TradeCode.IndustrialWorld)

    # TODO: Mongoose 2e has this different
    if population >= 1 and population <= 3:
        tradeCodes.add(TradeCode.LowPopulationWorld)

    # TODO: Mongoose 1e has this different
    if (population >= 1) and \
        (techLevel >= 0 and techLevel <= 5):
        tradeCodes.add(TradeCode.LowTechWorld)

    if (atmosphere >= 0 and atmosphere <= 3) and \
        (hydrographics >= 0 and hydrographics <= 3) and \
        (population >= 6):
        tradeCodes.add(TradeCode.NonAgriculturalWorld)

    # TODO: Mongoose 2e has this different
    if population >= 4 and population <= 6:
        tradeCodes.add(TradeCode.NonIndustrialWorld)

    if (atmosphere >= 2 and atmosphere <= 5) and \
        (hydrographics >= 0 and hydrographics <= 3):
        tradeCodes.add(TradeCode.PoorWorld)

    # TODO: Mongoose 1e has this different
    if (atmosphere in [6, 8]) and \
        (population >= 6 and population <= 8) and \
        (government >= 4 and government <= 9):
        tradeCodes.add(TradeCode.RichWorld)

    if atmosphere == 0:
        tradeCodes.add(TradeCode.VacuumWorld)

    # TODO: Mongoose 1e has this different
    # TODO: Mongoose 2e has this different
    if ((atmosphere >= 3 and atmosphere <= 9) or (atmosphere >= 13)) and \
        (hydrographics >= 10):
        tradeCodes.add(TradeCode.WaterWorld)

    return tradeCodes

def calculateT5TradeCodes(uwp: str) -> typing.Set[TradeCode]:
    starport, size, atmosphere, hydrographics, population, government, \
        lawLevel, _ = survey.parseSystemUWPString(uwp)
    size = survey.ehexToInteger(size)
    atmosphere = survey.ehexToInteger(atmosphere)
    hydrographics = survey.ehexToInteger(hydrographics)
    population = survey.ehexToInteger(population)
    government = survey.ehexToInteger(government)
    lawLevel = survey.ehexToInteger(lawLevel)
    tradeCodes = set()

    if (size == 0) and \
        (atmosphere == 0) and \
        (hydrographics == 0):
        tradeCodes.add(TradeCode.AsteroidBelt)

    if (atmosphere >= 2 and atmosphere <= 9) and \
        (hydrographics == 0):
        tradeCodes.add(TradeCode.DesertWorld)

    if (atmosphere >= 10) and \
        (hydrographics >= 1):
        tradeCodes.add(TradeCode.FluidWorld)

    if (size >= 6 and size <= 8) and \
        (atmosphere in [5,6,8]) and \
        (hydrographics >= 5 and hydrographics <= 7):
        tradeCodes.add(TradeCode.GardenWorld)

    if (size >= 3 and size <= 12) and \
        (atmosphere in [2, 4, 7, 9, 10, 11, 12]) and \
        (hydrographics >= 0 and hydrographics <= 2):
        tradeCodes.add(TradeCode.HellWorld)

    if (atmosphere in [0, 1]) and \
        (hydrographics >= 1):
        tradeCodes.add(TradeCode.IceCappedWorld)

    if (size >= 10 and size <= 15) and \
        (atmosphere >= 3 and atmosphere <= 12) and \
        (hydrographics == 10):
        tradeCodes.add(TradeCode.OceanWorld)

    if atmosphere == 0:
        tradeCodes.add(TradeCode.VacuumWorld)

    # NOTE: This is different from the Mongoose definition
    if (size >= 3 and size <= 10) and \
        (size >= 3 and size <= 12) and \
        (hydrographics >= 10):
        tradeCodes.add(TradeCode.WaterWorld)

    # NOTE: This is different from the Mongoose definition
    if (population == 0) and \
        (government == 0) and \
        (lawLevel == 0) and \
        (starport in ['E', 'X']):
        tradeCodes.add(TradeCode.BarrenWorld)

    if (population >= 1 and population <= 3):
        tradeCodes.add(TradeCode.LowPopulationWorld)

    if population >= 4 and population <= 6:
        tradeCodes.add(TradeCode.NonIndustrialWorld)

    if population == 8:
        tradeCodes.add(TradeCode.PreHighPopulationWorld)

    if population >= 9:
        tradeCodes.add(TradeCode.HighPopulationWorld)

    if (atmosphere >= 4 and atmosphere <= 9) and \
        (hydrographics >= 4 and hydrographics <= 8) and \
        (population in [4, 8]):
        tradeCodes.add(TradeCode.PreAgriculturalWorld)

    if (atmosphere >= 4 and atmosphere <= 9) and \
        (hydrographics >= 4 and hydrographics <= 8) and \
        (population >= 5 and population <= 7):
        tradeCodes.add(TradeCode.AgriculturalWorld)

    if (atmosphere >= 0 and atmosphere <= 3) and \
        (hydrographics >= 0 and hydrographics <= 3) and \
        (population >= 6):
        tradeCodes.add(TradeCode.NonAgriculturalWorld)

    if (atmosphere in [0, 1, 2, 4, 7, 9]) and \
        (population in [7, 8]):
        tradeCodes.add(TradeCode.PreIndustrialWorld)

    if (atmosphere in [0, 1, 2, 4, 7, 9, 10, 11, 12]) and \
        (population >= 9):
        tradeCodes.add(TradeCode.IndustrialWorld)

    if (atmosphere >= 2 and atmosphere <= 5) and \
        (hydrographics >= 0 and hydrographics <= 3):
        tradeCodes.add(TradeCode.PoorWorld)

    if (atmosphere in [6, 8]) and \
        (population in [5, 9]):
        tradeCodes.add(TradeCode.PreRichWorld)

    # NOTE: This is different from the Mongoose definition
    if (atmosphere in [6, 8]) and \
        (population >= 6 and population <= 8):
        tradeCodes.add(TradeCode.RichWorld)

    return tradeCodes