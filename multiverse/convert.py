import common
import logging
import itertools
import math
import multiverse
import survey
import typing

# TODO: The conversion process needs to give better error/warning/info
# feedback to the user when converting custom sectors (converting the
# default universe should just log)
# TODO: A lot of places where I'm constructing DB objects, I should
# wrap them in a try/except and log and continue if they throw.
# - UPDATE: With recent changes I think it should maybe be the other way
# around. I've got validation that should ignore valid values so any
# exceptions when creating the DB objects should be coding errors rather
# than invalid data.
# TODO: It would probably be a good idea to store the zoomed out galaxy bitmap in the
# database as well. Remember there are two, one for light and one for dark maps. Again
# this will need an update to the rendering code but it should be trivial. I think it
# makes sense to leave the candy images as static files as they're more part of the
# rendering system than the universe

# Useful Test Locations:
# - Sector: Tsebntsiatldlants
#   - There is a route that runs the length of it (e.g. through Oiansh) that
#     should be dashed purple. The colour and style come from it using the
#     "Core Route" type which is the only type defined in the otu css file
#     that has a space in the name.
# - Sector: Glimmerdrift Reaches (Judges Guild)
#   - A lot of the borders in this sector use a dashed salmon pink colour. They get
#     this from the default border colour in the metadata style sheet info (i.e.
#     not the otu css file)
#   - Some of the routes are extra chunky because they use the Special type which
#     has a custom width defined in the metadata style sheet info (e.g ones
#     going into Rasma)
# - Sector: Far Frontiers
#   - The routes for the worlds around Bestus should be grey, not green. They can
#     get go wrong if the order the style sheet groups are looked up are messed up.
#     The reason it gets messed up is it relies on the colour not being taken from
#     the "Im" allegiance style because the route has a type specified (even though
#     that type doesn't have a style defined)
# -  Vanguard Reaches (Don McKinney 2015)
#   - There is a red route running vertically (e.g. through Cloister) that gets
#     its colour from the allegiance of Im on the route and the custom colour
#     specified for Im in the metadata style sheet info
#   - This is also a very colourful sector with lots of different borders and
#     regions
# - Sector: Far Home
#   - Routes in this sector have a custom default colour specified in the metadata
#     stylesheet info (such as those going through Iridina)
# - Sector: The Beyond
#   - When using Atlas style, the route between Djend and Morphy should be
#     solid rather than dashed. The special case for grayscale rendering in
#     my _drawMicroRoutes shouldn't kick in
# - System: Inast (Gateway)
#   - Has a ruling allegiance
# - System: Yeasea (Dark Nebula)
#   - Has an owner in another sector
# - System: Uyar (Datsatl)
#   - Has a colony
# - System: 551-458 (Storr)
#   - Has 6 stars of different types
# - System: Aestera (Storr)
#   - Has 3 bases
# - System: Ziruushda (Dagudashaag)
#   - Has 4 sophonts
# - System: Garden (Reft)
#   - Has a named die back sophont
# - System: Beta Station (Joyce's Void)
#   - Has research station
# - System: Canoga (Ilelish)
#   - Has 5 nobilities

_StockMajorSophonts = set([
    'Human',
    'Aslan',
    'Droyne',
    'Hiver',
    'K\'kree',
    'Vargr',
])

# This maps legacy single letter sophont codes to T5 sophont codes. There is no
# mapping for 'F' as I've no idea what T5 sophont it maps to
_LegacySophontMap = {
    'A': 'Asla',
    'C': 'Chir',
    'D': 'Droy',
    #'F': 'Non-Hiver Federation Member',
    'H': 'Hive',
    'I': 'Ithk',
    'M': 'Huma',
    'V': 'Varg',
    'X': 'Adda',
    'Z': 'Zhod'
}

_DieBackTradeCode = 'Di'
_MilitaryRuleTradeCode = 'Mr'
_ResearchStationTradeCode = 'Rs'

_ValidLineStyles = set(['solid', 'dashed', 'dotted'])
_ValidLabelSizes = set(['small', 'large'])

# This is based on the sector world bounds and hex world center code in
# astrometrics. It uses a coordinate space that has the same scale as
# world space coordinates but is relative to the upper left corner of
# the sector.
_ParsecScaleX = math.cos(math.pi / 6) # = cosine 30° = 0.8660254037844387
_HexWidthOffset = math.tan(math.pi / 6) / 4 / _ParsecScaleX # = 0.16666666666666666
def _hexToSectorWorldOffset(
        hexX: int,
        hexY: int,
        worldOffsetX: typing.Optional[float],
        worldOffsetY: typing.Optional[float]
        ) -> typing.Tuple[float, float]:
        worldX = (hexX - 0.5)
        worldX += _HexWidthOffset # Offset of sector origin
        if worldOffsetX is not None:
            worldX += worldOffsetX

        worldY = (hexY - (0.0 if ((hexX % 2) != 0) else -0.5))
        worldY -= 0.5 # Offset of sector origin
        if worldOffsetY is not None:
            worldY += worldOffsetY

        return (worldX, worldY)

def _sectorWorldOffsetToHex(
        worldX: float,
        worldY: float
        ) -> typing.Tuple[int, int, typing.Optional[float], typing.Optional[float]]:
    localX = worldX - _HexWidthOffset
    localY = worldY + 0.5

    hexX = int(localX + 0.5)
    worldOffsetX = localX - (hexX - 0.5)

    yBase = localY - (0.0 if ((hexX % 2) != 0) else -0.5)

    hexY = int(yBase)
    worldOffsetY = yBase - hexY

    return (hexX, hexY, worldOffsetX if worldOffsetX else None, worldOffsetY if worldOffsetY else None)

_ReferenceSectorX = 0
_ReferenceSectorY = 0
_ReferenceHexX = 1
_ReferenceHexY = 40
_SectorWidth = 32
_SectorHeight = 40
def _sectorHexToWorldSpace(
        sectorX: int,
        sectorY: int,
        hexX: int,
        hexY: int
        ) -> typing.Tuple[float, float]:
    absX = (sectorX - _ReferenceSectorX) * \
        _SectorWidth + \
        (hexX - _ReferenceHexX)
    absY = (sectorY - _ReferenceSectorY) * \
        _SectorHeight + \
        (hexY - _ReferenceHexY)
    return (
        absX - 0.5,
        absY - (0.0 if ((absX % 2) != 0) else 0.5))

def _createDbAlternateNames(
        rawMetadata: survey.RawMetadata
        ) -> typing.List[multiverse.DbAlternateName]:
    dbAlternateNames = []

    if rawMetadata.alternateNames():
        for name in rawMetadata.alternateNames():
            if not name:
                logging.warning(f'Converter ignoring alternate sector name with empty name in {rawMetadata.canonicalName()}')
                continue
            language = rawMetadata.nameLanguage(name)
            dbAlternateNames.append(multiverse.DbAlternateName(
                name=name,
                language=language if language else None))

    return dbAlternateNames

def _createDbSubsectorNames(
        rawMetadata: survey.RawMetadata
        ) -> typing.List[multiverse.DbSubsectorName]:
    dbSubsectorNames = []

    if rawMetadata.subsectorNames():
        for code, name in rawMetadata.subsectorNames().items():
            if not code:
                logging.warning(f'Converter ignoring subsector name with empty code in {rawMetadata.canonicalName()}')
                continue

            if not name:
                # This doesn't get logged as it happens quite a bit in the stock
                # data and just seems to be used when subsectors aren't named
                #logging.debug(f'Converter ignoring subsector name with empty name in {rawMetadata.canonicalName()}')
                continue

            # Silently fix instances where code is lower case
            code = code.upper()

            dbSubsectorNames.append(multiverse.DbSubsectorName(
                code=code,
                name=name))

    return dbSubsectorNames

# This code generates a code for a sophont name following the rules defined on
# the Traveller Wiki (at least as best as I can understand them)
# https://wiki.travellerrpg.com/Sophont_Code
def _generateSophontCode(
        name: str,
        existingCodes: typing.Collection[str]
        ) -> str:
    length = len(name)
    code = ''
    for i in range(4):
        char = name[i] if i < length else 'X'
        code += char if char.isalpha() else 'X'

    if code not in existingCodes:
        return code

    original = code
    for i in range(len(code) - 1, -1, -1):
        code = original
        prefix = code[:i]
        suffix = code[i + 1:]
        for j in range(25):
            old = ord(code[i])
            new = old + j + 1
            if old <= 90 and new > 90:
                new -= 26
            elif old <= 122 and new > 122:
                new -= 26

            code = prefix + chr(new) + suffix
            if code not in existingCodes:
                return code

    raise RuntimeError(f'Unable to generate unused code for sophont {name}')

def _generateSophontName(
        code: str,
        existingNames: typing.Collection[str]
        ) -> str:
    name = code
    while name in existingNames:
        name += 'X'
    return name

def _createDbSophonts(
        rawMetadata: survey.RawMetadata,
        rawSystems: typing.Collection[survey.RawWorld],
        rawStockSophonts: typing.Optional[typing.Collection[
            survey.RawStockSophont
            ]] = None,
        ) -> typing.Tuple[
            typing.Dict[str, multiverse.DbSophont], # Code to DbSophont map
            typing.Dict[str, multiverse.DbSophont]]: # Name to DbSophont map
    rawStockSophontCodeMap: typing.Dict[str, survey.RawStockSophont] = {}
    rawStockSophontNameMap: typing.Dict[str, survey.RawStockSophont] = {}
    if rawStockSophonts:
        for rawStockSophont in rawStockSophonts:
            if not rawStockSophont.code():
                logging.debug(f'Converter ignoring stock sophont with empty code when converting {rawMetadata.canonicalName()}')
                continue

            if not rawStockSophont.name():
                logging.debug(f'Converter ignoring stock sophont with empty name when converting {rawMetadata.canonicalName()}')
                continue

            if rawStockSophont.code() in rawStockSophontCodeMap:
                logging.warning(f'Converter ignoring duplicate stock sophont {rawStockSophont.code()} when converting {rawMetadata.canonicalName()}')
                continue

            if rawStockSophont.name() in rawStockSophontNameMap:
                logging.warning(f'Converter ignoring duplicate stock sophont {rawStockSophont.name()} when converting {rawMetadata.canonicalName()}')
                continue

            rawStockSophontCodeMap[rawStockSophont.code()] = rawStockSophont
            rawStockSophontNameMap[rawStockSophont.name()] = rawStockSophont

    rawUsedSophontCodes: typing.Set[str] = set()
    rawUsedSophontNames: typing.Set[str] = set()
    rawMajorSophontNames: typing.Set[str] = set(_StockMajorSophonts)
    if rawSystems:
        for rawWorld in rawSystems:
            rawRemarks = rawWorld.remarks()
            if not rawRemarks:
                continue

            if rawRemarks.sophontPopulations():
                for rawPopulation in rawRemarks.sophontPopulations():
                    rawUsedSophontCodes.add(rawPopulation.sophont())

            if rawRemarks.majorRaceHomeWorlds():
                for rawPopulation in rawRemarks.majorRaceHomeWorlds():
                    rawUsedSophontNames.add(rawPopulation.sophont())
                    rawMajorSophontNames.add(rawPopulation.sophont())

            if rawRemarks.minorRaceHomeWorlds():
                for rawPopulation in rawRemarks.minorRaceHomeWorlds():
                    rawUsedSophontNames.add(rawPopulation.sophont())

            if rawRemarks.dieBackSophonts():
                for rawSophont in rawRemarks.dieBackSophonts():
                    rawUsedSophontNames.add(rawSophont)

    dbSophontCodeMap: typing.Dict[str, multiverse.DbSophont] = {}
    dbSophontNameMap: typing.Dict[str, multiverse.DbSophont] = {}

    if rawUsedSophontNames or rawUsedSophontCodes:
        uniqueCodes = set(rawStockSophontCodeMap.keys())
        uniqueNames = set(rawStockSophontNameMap.keys())

        for rawSophontName in rawUsedSophontNames:
            if rawSophontName in dbSophontNameMap:
                continue

            rawStockSophont = rawStockSophontNameMap.get(rawSophontName)

            if rawStockSophont:
                dbSophont = multiverse.DbSophont(
                    code=rawStockSophont.code(),
                    name=rawStockSophont.name(),
                    isMajor=rawSophontName in rawMajorSophontNames)
            else:
                # There is no stock sophont and therefore no predefined code, so generate
                # one instead
                dbSophontCode = _generateSophontCode(
                    name=rawSophontName,
                    existingCodes=uniqueCodes)
                # NOTE: Only log this at debug as it happens a LOT in stock data
                logging.debug(f'Converter generating sophont code {dbSophontCode} for sophont {rawSophontName} in {rawMetadata.canonicalName()}')
                uniqueCodes.add(dbSophontCode)

                dbSophont = multiverse.DbSophont(
                    code=dbSophontCode,
                    name=rawSophontName,
                    isMajor=rawSophontName in rawMajorSophontNames)

            dbSophontNameMap[rawSophontName] = dbSophont

            # Add a mapping for the sophont code if it's used but there isn't
            # already a mapping
            if dbSophont.code() not in dbSophontCodeMap and \
                    dbSophont.code() in rawUsedSophontCodes:
                dbSophontCodeMap[dbSophont.code()] = dbSophont

        for rawSophontCode in rawUsedSophontCodes:
            if rawSophontCode in dbSophontCodeMap:
                continue

            overrideCode = _LegacySophontMap.get(rawSophontCode)
            rawStockSophont = rawStockSophontCodeMap.get(overrideCode if overrideCode else rawSophontCode)

            if rawStockSophont:
                # There is a stock sophont that matches the code. If there is no
                # DbSophont for that code then one needs to be created.
                dbSophont = dbSophontCodeMap.get(rawStockSophont.code())
                if not dbSophont:
                    dbSophont = multiverse.DbSophont(
                        code=rawStockSophont.code(),
                        name=rawStockSophont.name(),
                        isMajor=rawStockSophont.name() in rawMajorSophontNames)
            else:
                # There is no stock sophont that matches the code. Create a new
                # DbSophont using the information we do have.
                dbSophontName = _generateSophontName(
                    code=rawSophontCode,
                    existingNames=uniqueNames)
                uniqueNames.add(dbSophontName)

                dbSophont = multiverse.DbSophont(
                    code=rawSophontCode,
                    name=dbSophontName,
                    isMajor=False)

            # NOTE: It's important that the rawSophontCode is used as the key here as,
            # in the case that the code was overridden, we still need a mapping for
            # the raw code as that's what other raw data will be using
            dbSophontCodeMap[rawSophontCode] = dbSophont

            # If the sophont code was overridden, add an mapping for the real code if it's
            # used and there isn't a mapping for it already
            if rawSophontCode != dbSophont.code() and \
                    dbSophont.code() not in dbSophontCodeMap and \
                    dbSophont.code() in rawUsedSophontCodes:
                dbSophontCodeMap[dbSophont.code()] = dbSophont

            # Add a mapping for the sophont name if it's used but there isn't
            # already a mapping
            if dbSophont.name() not in dbSophontNameMap and \
                    dbSophont.name() in rawUsedSophontNames:
                dbSophontNameMap[dbSophont.name()] = dbSophont

    return (dbSophontCodeMap, dbSophontNameMap)

def _createDbStars(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld
        ) -> typing.Optional[typing.List[multiverse.DbStar]]:
    rawStars = rawWorld.stars()
    if not rawStars:
        return None

    dbStars = []
    for rawStar in rawStars:
        try:
            dbStars.append(multiverse.DbStar(
                luminosityClass=rawStar.luminosityClass(),
                spectralClass=rawStar.spectralClass(),
                spectralScale=rawStar.spectralScale()))
        except Exception as ex:
            logging.error('Converter failed to construct star for {world} in {sector}'.format(
                    world=rawWorld.name(),
                    sector=rawMetadata.canonicalName()),
                exc_info=ex)

    return dbStars

def _createDbBodies(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        allegianceMapper: multiverse.AllegianceMapper,
        dbSophontCodeMap: typing.Dict[str, multiverse.DbSophont],
        dbSophontNameMap: typing.Dict[str, multiverse.DbSophont]
        ) -> typing.Optional[typing.List[multiverse.DbBody]]:
    rawSystemName = rawWorld.name()
    dbSystemName = rawSystemName if rawSystemName else None

    rawUWP = rawWorld.uwp()
    dbStarport = dbWorldSize = dbAtmosphere = dbHydrographics = \
        dbPopulation = dbGovernment = dbLawLevel = dbTechLevel = None
    if rawUWP is not None:
        dbStarport = rawUWP.starport()
        dbWorldSize = rawUWP.worldSize()
        dbAtmosphere = rawUWP.atmosphere()
        dbHydrographics = rawUWP.hydrographics()
        dbPopulation = rawUWP.population()
        dbGovernment = rawUWP.government()
        dbLawLevel = rawUWP.lawLevel()
        dbTechLevel = rawUWP.techLevel()

    rawEconomics = rawWorld.economics()
    dbResources = dbLabour = dbInfrastructure = dbEfficiency = None
    if rawEconomics is not None:
        dbResources = rawEconomics.resources()
        dbLabour = rawEconomics.labour()
        dbInfrastructure = rawEconomics.infrastructure()
        dbEfficiency = rawEconomics.efficiency()

    rawCulture = rawWorld.culture()
    dbHeterogeneity = dbAcceptance = dbStrangeness = dbSymbols = None
    if rawCulture is not None:
        dbHeterogeneity = rawCulture.heterogeneity()
        dbAcceptance = rawCulture.acceptance()
        dbStrangeness = rawCulture.strangeness()
        dbSymbols = rawCulture.symbols()

    rawPBG = rawWorld.pbg()
    dbPopulationMultiplier = None
    if rawPBG is not None:
        dbPopulationMultiplier = rawPBG.populationMultiplier()

    dbNobilities = _createDbNobilities(
        rawMetadata=rawMetadata,
        rawWorld=rawWorld)

    dbBases = _createDbBases(
        rawMetadata=rawMetadata,
        rawWorld=rawWorld)

    dbSophontPopulations = _createDbSophontPopulations(
        rawMetadata=rawMetadata,
        rawWorld=rawWorld,
        dbSophontCodeMap=dbSophontCodeMap,
        dbSophontNameMap=dbSophontNameMap)

    dbOwningSystems = _createDbOwningSystems(
        rawMetadata=rawMetadata,
        rawWorld=rawWorld)

    dbColonySystems = _createDbColonySystems(
        rawMetadata=rawMetadata,
        rawWorld=rawWorld)

    dbRulingAllegiances = _createDbRulingAllegiances(
        rawMetadata=rawMetadata,
        rawWorld=rawWorld,
        allegianceMapper=allegianceMapper)

    dbResearchStations = _createDbResearchStations(
        rawMetadata=rawMetadata,
        rawWorld=rawWorld)

    dbTradeCodes = _createDbTradeCodes(
        rawMetadata=rawMetadata,
        rawWorld=rawWorld,
        dbSophontPopulations=dbSophontPopulations,
        dbRulingAllegiances=dbRulingAllegiances,
        dbResearchStations=dbResearchStations)

    dbCustomRemarks = _createDbCustomRemarks(
        rawMetadata=rawMetadata,
        rawWorld=rawWorld)

    # Only create the main world if there is some data or there is known
    # to be at least one system world
    hasData = dbStarport or dbWorldSize or dbAtmosphere or dbHydrographics or \
        dbPopulation or dbGovernment or dbLawLevel or dbTechLevel or \
        dbResources or dbLabour or dbInfrastructure or dbEfficiency or \
        dbHeterogeneity or dbAcceptance or dbStrangeness or dbSymbols or \
        dbPopulationMultiplier or dbTradeCodes or dbSophontPopulations or \
        dbRulingAllegiances or dbOwningSystems or dbColonySystems or \
        dbResearchStations or dbCustomRemarks
    numSystemWorlds = rawWorld.systemWorlds()
    if not hasData and not numSystemWorlds:
        return None

    return [multiverse.DbWorld(
        orbitIndex=1,
        isMainWorld=True,
        name=dbSystemName,
        starport=dbStarport,
        worldSize=dbWorldSize,
        atmosphere=dbAtmosphere,
        hydrographics=dbHydrographics,
        population=dbPopulation,
        government=dbGovernment,
        lawLevel=dbLawLevel,
        techLevel=dbTechLevel,
        resources=dbResources,
        labour=dbLabour,
        infrastructure=dbInfrastructure,
        efficiency=dbEfficiency,
        heterogeneity=dbHeterogeneity,
        acceptance=dbAcceptance,
        strangeness=dbStrangeness,
        symbols=dbSymbols,
        populationMultiplier=dbPopulationMultiplier,
        nobilities=dbNobilities,
        bases=dbBases,
        tradeCodes=dbTradeCodes,
        sophontPopulations=dbSophontPopulations,
        rulingAllegiances=dbRulingAllegiances,
        owningSystems=dbOwningSystems,
        colonySystems=dbColonySystems,
        researchStations=dbResearchStations,
        customRemarks=dbCustomRemarks)]

def _createDbNobilities(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld
        ) -> typing.Optional[typing.List[multiverse.DbNobility]]:
    rawNobilities = rawWorld.nobilities()
    if not rawNobilities:
        return None

    dbNobilities = []
    seenNobilities = set()
    for rawNobilityCode in rawNobilities:
        if rawNobilityCode in seenNobilities:
            logging.debug('Converter ignoring duplicate nobility {code} for {world} in {sector}'.format(
                code=rawNobilityCode,
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()))
            continue
        seenNobilities.add(rawNobilityCode)

        try:
            dbNobilities.append(multiverse.DbNobility(code=rawNobilityCode))
        except Exception as ex:
            logging.error('Converter failed to construct nobility {code} for {world} in {sector}'.format(
                    code=rawNobilityCode,
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()),
                exc_info=ex)

    return dbNobilities

def _createDbBases(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld
        ) -> typing.Optional[typing.List[multiverse.DbBase]]:
    rawBases = rawWorld.bases()
    if not rawBases:
        return None

    dbBases = []
    seenBases = set()
    for rawBaseCode in rawBases:
        if rawBaseCode in seenBases:
            logging.debug('Converter ignoring duplicate base {code} for {world} in {sector}'.format(
                code=rawBaseCode,
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()))
            continue
        seenBases.add(rawBaseCode)

        try:
            dbBases.append(multiverse.DbBase(code=rawBaseCode))
        except Exception as ex:
            logging.error('Converter failed to construct base {code} for {world} in {sector}'.format(
                    code=rawBaseCode,
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()),
                exc_info=ex)

    return dbBases

def _createDbSophontPopulations(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        dbSophontCodeMap: typing.Mapping[str, multiverse.DbSophont],
        dbSophontNameMap: typing.Mapping[str, multiverse.DbSophont]
        ) -> typing.Optional[typing.List[multiverse.DbSophontPopulation]]:
    remarks = rawWorld.remarks()
    if remarks is None:
        return None

    rawMajorHomeWorlds = remarks.majorRaceHomeWorlds()
    rawMinorHomeWorlds = remarks.minorRaceHomeWorlds()
    rawSophontPopulations = remarks.sophontPopulations()
    rawDieBackSophonts = remarks.dieBackSophonts()
    if not rawMajorHomeWorlds and not rawMinorHomeWorlds and not rawSophontPopulations and not rawDieBackSophonts:
        return None

    dbSophontPopulations: typing.List[multiverse.DbSophontPopulation] = []
    seenDbSophonts = set()

    if rawMajorHomeWorlds:
        for rawSophontPopulation in rawMajorHomeWorlds:
            dbSophont = dbSophontNameMap.get(rawSophontPopulation.sophont())
            if not dbSophont:
                # This should never happen, the remarks should already have been
                # processed to extract all the used sophont names & codes and
                # DbSophont instances should have been created for all of them
                logging.warning('Converter ignoring unknown major sophont {sophont} for {world} in {sector}'.format(
                    sophont=rawSophontPopulation.sophont(),
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()))
                continue
            if dbSophont in seenDbSophonts:
                # There is already a population entry for this sophont so
                # ignore this one
                logging.warning('Converter ignoring duplicate major sophont population for {sophont} for {world} in {sector}'.format(
                    sophont=dbSophont.name(),
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()))
                continue
            seenDbSophonts.add(dbSophont)

            try:
                dbSophontPopulations.append(multiverse.DbSophontPopulation(
                    sophontId=dbSophont.id(),
                    percentage=rawSophontPopulation.percentage(),
                    isHomeWorld=True,
                    isDieBack=False))
            except Exception as ex:
                logging.error('Converter failed to construct major sophont population for {sophont} for {world} in {sector}'.format(
                        sophont=dbSophont.name(),
                        world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                        sector=rawMetadata.canonicalName()),
                    exc_info=ex)

    if rawMinorHomeWorlds:
        for rawSophontPopulation in rawMinorHomeWorlds:
            dbSophont = dbSophontNameMap.get(rawSophontPopulation.sophont())
            if not dbSophont:
                # This should never happen, the remarks should already have been
                # processed to extract all the used sophont names & codes and
                # DbSophont instances should have been created for all of them
                logging.warning('Converter ignoring unknown minor sophont {sophont} for {world} in {sector}'.format(
                    sophont=rawSophontPopulation.sophont(),
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()))
                continue
            if dbSophont in seenDbSophonts:
                # There is already a population entry for this sophont so
                # ignore this one
                logging.warning('Converter ignoring duplicate minor sophont for {sophont} for {world} in {sector}'.format(
                    sophont=dbSophont.name(),
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()))
                continue
            seenDbSophonts.add(dbSophont)

            try:
                dbSophontPopulations.append(multiverse.DbSophontPopulation(
                    sophontId=dbSophont.id(),
                    percentage=rawSophontPopulation.percentage(),
                    isHomeWorld=True,
                    isDieBack=False))
            except Exception as ex:
                logging.error('Converter failed to construct minor sophont population for {sophont} for {world} in {sector}'.format(
                        sophont=dbSophont.name(),
                        world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                        sector=rawMetadata.canonicalName()),
                    exc_info=ex)

    if rawSophontPopulations:
        for rawSophontPopulation in rawSophontPopulations:
            dbSophont = dbSophontCodeMap.get(rawSophontPopulation.sophont())
            if not dbSophont:
                # This should never happen, the remarks should already have been
                # processed to extract all the used sophont names & codes and
                # DbSophont instances should have been created for all of them
                logging.warning('Converter ignoring unknown sophont {sophont} for {world} in {sector}'.format(
                    sophont=rawSophontPopulation.sophont(),
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()))
                continue
            if dbSophont in seenDbSophonts:
                # There is already a population entry for this sophont so
                # ignore this one
                logging.warning('Converter ignoring duplicate sophont {sophont} for {world} in {sector}'.format(
                    sophont=dbSophont.name(),
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()))
                continue
            seenDbSophonts.add(dbSophont)

            try:
                dbSophontPopulations.append(multiverse.DbSophontPopulation(
                    sophontId=dbSophont.id(),
                    percentage=rawSophontPopulation.percentage(),
                    isHomeWorld=False,
                    isDieBack=False))
            except Exception as ex:
                logging.error('Converter failed to construct sophont population for {sophont} for {world} in {sector}'.format(
                        sophont=dbSophont.name(),
                        world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                        sector=rawMetadata.canonicalName()),
                    exc_info=ex)

    if rawDieBackSophonts:
        for rawSophontName in rawDieBackSophonts:
            dbSophont = dbSophontNameMap.get(rawSophontName)
            if not dbSophont:
                # This should never happen, the remarks should already have been
                # processed to extract all the used sophont names & codes and
                # DbSophont instances should have been created for all of them
                logging.warning('Converter ignoring unknown die back sophont {sophont} for {world} in {sector}'.format(
                    sophont=rawSophontName,
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()))
                continue
            if dbSophont in seenDbSophonts:
                # There is already a population entry for this sophont so
                # ignore this one
                logging.warning('Converter ignoring duplicate die back sophont {sophont} for {world} in {sector}'.format(
                    sophont=dbSophont.name(),
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()))
                continue
            seenDbSophonts.add(dbSophont)

            try:
                dbSophontPopulations.append(multiverse.DbSophontPopulation(
                    sophontId=dbSophont.id(),
                    percentage=None,
                    isHomeWorld=False,
                    isDieBack=True))
            except Exception as ex:
                logging.error('Converter failed to construct die back sophont population for {sophont} for {world} in {sector}'.format(
                        sophont=dbSophont.name(),
                        world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                        sector=rawMetadata.canonicalName()),
                    exc_info=ex)

    return dbSophontPopulations

def _createDbOwningSystems(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld
        ) -> typing.Optional[typing.List[multiverse.DbOwningSystem]]:
    rawRemarks = rawWorld.remarks()
    if rawRemarks is None:
        return None

    rawOwningSystems = rawRemarks.owningSystems()
    if not rawOwningSystems:
        return None

    dbOwningSystems = []
    seenOwners = set()
    for rawHexRef in rawOwningSystems:
        rawHexX = rawHexRef.x()
        rawHexY = rawHexRef.y()
        rawSectorAbbreviation = rawHexRef.sector()
        if not rawSectorAbbreviation:
            rawSectorAbbreviation = None
        elif rawSectorAbbreviation == rawMetadata.abbreviation():
            # If the sector abbreviation is the same as the current sector
            # abbreviation then it can be omitted
            rawSectorAbbreviation = None

        key = (rawHexX, rawHexY, rawSectorAbbreviation)
        if key in seenOwners:
            logging.warning('Converter ignoring duplicate owner world for {world} in {sector}'.format(
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()))
            continue
        seenOwners.add(key)

        try:
            dbOwningSystems.append(multiverse.DbOwningSystem(
                hexX=rawHexX,
                hexY=rawHexY,
                sectorAbbreviation=rawSectorAbbreviation))
        except Exception as ex:
            logging.error('Converter failed to construct owner world for {world} in {sector}'.format(
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()),
                exc_info=ex)

    return dbOwningSystems

def _createDbColonySystems(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        ) -> typing.Optional[typing.List[multiverse.DbColonySystem]]:
    rawRemarks = rawWorld.remarks()
    if rawRemarks is None:
        return None

    rawColonySystems = rawRemarks.colonySystems()
    if not rawColonySystems:
        return None

    dbColonySystems = []
    seenColonies = set()
    for rawHexRef in rawColonySystems:
        rawHexX = rawHexRef.x()
        rawHexY = rawHexRef.y()
        rawSectorAbbreviation = rawHexRef.sector()
        if not rawSectorAbbreviation:
            rawSectorAbbreviation = None
        elif rawSectorAbbreviation == rawMetadata.abbreviation():
            # If the sector abbreviation is the same as the current sector
            # abbreviation then it can be omitted
            rawSectorAbbreviation = None

        key = (rawHexX, rawHexY, rawSectorAbbreviation)
        if key in seenColonies:
            logging.warning('Converter ignoring duplicate colony world for {world} in {sector}'.format(
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()))
            continue
        seenColonies.add(key)

        try:
            dbColonySystems.append(multiverse.DbColonySystem(
                hexX=rawHexX,
                hexY=rawHexY,
                sectorAbbreviation=rawSectorAbbreviation))
        except Exception as ex:
            logging.error('Converter failed to construct colony world for {world} in {sector}'.format(
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()),
                exc_info=ex)

    return dbColonySystems

def _createDbRulingAllegiances(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        allegianceMapper: multiverse.AllegianceMapper
        ) -> typing.Optional[typing.List[multiverse.DbRulingAllegiance]]:
    rawRemarks = rawWorld.remarks()
    if rawRemarks is None:
        return None

    rawRulingAllegiances = rawRemarks.rulingAllegiances()
    if not rawRulingAllegiances:
        return None

    dbRulingAllegiances = []
    seenRulingAllegiances = set()
    for rawAllegianceCode in rawRulingAllegiances:
        dbAllegiance = allegianceMapper.lookupAllegiance(
            rawMetadata=rawMetadata,
            code=rawAllegianceCode)
        if not dbAllegiance:
            # This should never happen. The remarks should already have been processed
            # to determine which allegiances were used and dbAllegiance created accordingly
            logging.warning('Converter ignoring unknown military rule allegiance {allegiance} for {world} in {sector}'.format(
                allegiance=rawAllegianceCode,
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()))
            continue

        if rawAllegianceCode in seenRulingAllegiances:
            logging.warning('Converter ignoring duplicate ruling allegiance {allegiance} for {world} in {sector}'.format(
                allegiance=rawAllegianceCode,
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()))
            continue
        seenRulingAllegiances.add(rawAllegianceCode)

        try:
            dbRulingAllegiances.append(multiverse.DbRulingAllegiance(allegianceId=dbAllegiance.id()))
        except Exception as ex:
            logging.error('Converter failed to construct ruling allegiance {allegiance} for {world} in {sector}'.format(
                    allegiance=rawAllegianceCode,
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()),
                exc_info=ex)

    return dbRulingAllegiances

def _createDbResearchStations(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld
        ) -> typing.Optional[typing.List[multiverse.DbResearchStation]]:
    rawRemarks = rawWorld.remarks()
    if rawRemarks is None:
        return None

    rawResearchStations = rawRemarks.researchStations()
    if not rawResearchStations:
        return None

    dbResearchStations = []
    seenResearchStations = set()
    for rawResearchStation in rawResearchStations:
        if rawResearchStation in seenResearchStations:
            logging.debug('Converter ignoring duplicate research station {station} for {world} in {sector}'.format(
                station=rawResearchStation,
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()))
            continue # Skip duplicates
        seenResearchStations.add(rawResearchStation)

        try:
            dbResearchStations.append(multiverse.DbResearchStation(code=rawResearchStation))
        except Exception as ex:
            logging.error('Converter failed to construct research station {station} for {world} in {sector}'.format(
                    station=rawResearchStation,
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()),
                exc_info=ex)

    return dbResearchStations

def _createDbTradeCodes(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld,
        dbSophontPopulations: typing.Optional[typing.Collection[multiverse.DbSophontPopulation]],
        dbRulingAllegiances: typing.Optional[typing.Collection[multiverse.DbRulingAllegiance]],
        dbResearchStations: typing.Optional[typing.Collection[multiverse.DbResearchStation]]
        ) -> typing.Optional[typing.List[multiverse.DbTradeCode]]:
    rawRemarks = rawWorld.remarks()
    if rawRemarks is None:
        return None

    rawTradeCodes = rawRemarks.tradeCodes()
    if not rawTradeCodes:
        return None

    dbTradeCodes = []
    seenTradeCodes = set()
    for rawTradeCode in rawTradeCodes:
        if rawTradeCode in seenTradeCodes:
            logging.debug('Converter ignoring duplicate trade code {code} for at {world} in {sector}'.format(
                code=rawTradeCode,
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()))
            continue
        seenTradeCodes.add(rawTradeCode)

        try:
            dbTradeCodes.append(multiverse.DbTradeCode(code=rawTradeCode))
        except Exception as ex:
            logging.error('Converter failed to construct trade code {code} for at {world} in {sector}'.format(
                code=rawTradeCode,
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()),
                exc_info=ex)

    if dbSophontPopulations:
        for population in dbSophontPopulations:
            if not population.isDieBack():
                continue

            if _DieBackTradeCode in seenTradeCodes:
                break
            seenTradeCodes.add(_DieBackTradeCode)

            try:
                dbTradeCodes.append(multiverse.DbTradeCode(code=_DieBackTradeCode))
            except Exception as ex:
                logging.error('Converter failed to construct die back trade code for at {world} in {sector}'.format(
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()),
                    exc_info=ex)
            break

    if dbRulingAllegiances and _MilitaryRuleTradeCode not in seenTradeCodes:
        seenTradeCodes.add(_MilitaryRuleTradeCode)
        try:
            dbTradeCodes.append(multiverse.DbTradeCode(code=_MilitaryRuleTradeCode))
        except Exception as ex:
            logging.error('Converter failed to construct military rule trade code for at {world} in {sector}'.format(
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()),
                exc_info=ex)

    if dbResearchStations and _ResearchStationTradeCode not in seenTradeCodes:
        seenTradeCodes.add(_ResearchStationTradeCode)
        try:
            dbTradeCodes.append(multiverse.DbTradeCode(code=_ResearchStationTradeCode))
        except Exception as ex:
            logging.error('Converter failed to construct research station trade code for at {world} in {sector}'.format(
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()),
                exc_info=ex)

    return dbTradeCodes

def _createDbCustomRemarks(
        rawMetadata: survey.RawMetadata,
        rawWorld: survey.RawWorld
        ) -> typing.Optional[typing.List[multiverse.DbCustomRemark]]:
    rawRemarks = rawWorld.remarks()
    if rawRemarks is None:
        return None

    rawCustomRemarks = rawRemarks.customRemarks()
    if not rawCustomRemarks:
        return None

    dbCustomRemarks = []
    for remark in rawCustomRemarks:
        if not remark:
            continue

        try:
            dbCustomRemarks.append(multiverse.DbCustomRemark(remark=remark))
        except Exception as ex:
            logging.error('Converter failed to construct custom remark {remark} for {world} in {sector}'.format(
                remark=remark,
                world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                sector=rawMetadata.canonicalName()),
                exc_info=ex)

    return dbCustomRemarks

def _createDbSystems(
        rawMetadata: survey.RawMetadata,
        rawSystems: typing.Collection[survey.RawWorld],
        allegianceMapper: multiverse.AllegianceMapper,
        dbSophontCodeMap: typing.Dict[str, multiverse.DbSophont],
        dbSophontNameMap: typing.Dict[str, multiverse.DbSophont],
        ) -> typing.List[multiverse.DbSystem]:
    dbSystems = []

    for systemIndex, rawWorld in enumerate(rawSystems):
        try:
            dbHexX = rawWorld.x()
            dbHexY = rawWorld.y()
            hexString = survey.formatHexString(x=dbHexX, y=dbHexY)

            rawSystemName = rawWorld.name()
            dbSystemName = rawSystemName if rawSystemName else None

            rawPBG = rawWorld.pbg()
            dbPlanetoidBeltCount = dbGasGiantCount = None
            if rawPBG:
                dbPlanetoidBeltCount = rawPBG.planetoidBeltCount()
                if dbPlanetoidBeltCount is not None:
                    dbPlanetoidBeltCount = survey.ehexToInteger(dbPlanetoidBeltCount, None)

                dbGasGiantCount = rawPBG.gasGiantCount()
                if dbGasGiantCount is not None:
                    dbGasGiantCount = survey.ehexToInteger(dbGasGiantCount, None)

            rawZone = rawWorld.zone()
            dbZone = None
            if rawZone:
                dbZone = survey.parseSystemZoneString(zone=rawZone.upper())
                if dbZone == 'G':
                    # In the database a green zone is represented by null
                    dbZone = None

            rawAllegianceCode = rawWorld.allegianceCode()
            dbAllegiance = None
            if rawAllegianceCode:
                dbAllegiance = allegianceMapper.lookupAllegiance(
                    rawMetadata=rawMetadata,
                    code=rawAllegianceCode)
            if rawAllegianceCode and not dbAllegiance:
                # This should never happen. The worlds should already have been processed
                # to determine which allegiances were used and dbAllegiance created accordingly
                logging.warning('Converter ignoring unknown allegiance {allegiance} for {world} in {sector}'.format(
                    allegiance=rawAllegianceCode,
                    world=rawWorld.name() if rawWorld.name() else survey.formatHexString(rawWorld.x(), rawWorld.y()),
                    sector=rawMetadata.canonicalName()))

            # From the Traveller Map Second Survey documentation the system world count is
            # Main World + Gas Giant Count + Planetoid Belt Count + Other Planetoid Count.
            # With the minimum being 1 for the Main World. Gas Giant satellites (I assume
            # this means moons or rings) aren't included in the Other Planetoid Count unless
            # they are the Main World. If the Main World is a gas giant satellite, the world
            # should have the "Sa" remark which I don't believe any of the current worlds
            # have (but user data could).
            # https://travellermap.com/doc/secondsurvey#worlds
            # The section covering the Planetoid Belt Count in the PBG also says that a
            # Main World of size 0 is not included in that count. I assume this is because
            # it should be included in the other world count.
            # https://travellermap.com/doc/secondsurvey#pbg
            rawSystemWorlds = rawWorld.systemWorlds()
            dbWorldCount = None
            if rawSystemWorlds is not None:
                numBelts = dbPlanetoidBeltCount if dbPlanetoidBeltCount else 0
                numGiants = dbGasGiantCount if dbGasGiantCount else 0
                numBeltsPlusGiants = numBelts + numGiants
                if rawSystemWorlds >= numBeltsPlusGiants:
                    dbWorldCount = rawSystemWorlds - numBeltsPlusGiants
                else:
                    logging.warning('Other world count for world at {hex} in {sector} is unknown as the world count {total} is lower than the number of known worlds (Main World + {belts} Planetoid Belts + {giants} Gas Giants)'.format(
                            total=rawSystemWorlds,
                            belts=numBelts,
                            giants=numGiants,
                            hex=hexString,
                            sector=rawMetadata.canonicalName()))

            dbBodies = _createDbBodies(
                rawMetadata=rawMetadata,
                rawWorld=rawWorld,
                allegianceMapper=allegianceMapper,
                dbSophontCodeMap=dbSophontCodeMap,
                dbSophontNameMap=dbSophontNameMap)

            if dbBodies is not None:
                numCreatedWorlds = 0
                for dbBody in dbBodies:
                    if isinstance(dbBody, multiverse.DbWorld):
                        numCreatedWorlds += 1
                if dbWorldCount is None or dbWorldCount < numCreatedWorlds:
                    dbWorldCount = numCreatedWorlds

            dbStars = _createDbStars(
                rawMetadata=rawMetadata,
                rawWorld=rawWorld)

            dbSystems.append(multiverse.DbSystem(
                hexX=dbHexX,
                hexY=dbHexY,
                name=dbSystemName,
                planetoidBeltCount=dbPlanetoidBeltCount,
                gasGiantCount=dbGasGiantCount,
                worldCount=dbWorldCount,
                zone=dbZone,
                allegianceId=dbAllegiance.id() if dbAllegiance else None,
                stars=dbStars,
                bodies=dbBodies))
        except Exception as ex:
            logging.warning(f'Failed to convert system {systemIndex} in {rawMetadata.canonicalName()}', exc_info=ex)

    return dbSystems

def _createDbRoutes(
        rawMetadata: survey.RawMetadata,
        allegianceMapper: multiverse.AllegianceMapper,
        styleMapper: multiverse.StyleMapper
        ) -> typing.List[multiverse.DbRoute]:
    dbRoutes = []

    if rawMetadata.routes():
        for rawRoute in rawMetadata.routes():
            rawAllegianceCode = rawRoute.allegianceCode()
            dbAllegiance = None
            if rawAllegianceCode:
                dbAllegiance = allegianceMapper.lookupAllegiance(
                    rawMetadata=rawMetadata,
                    code=rawAllegianceCode)
            if rawAllegianceCode and not dbAllegiance:
                # This should never happen. The routes should already have been processed
                # to determine which allegiances were used and dbAllegiance created accordingly
                logging.warning('Converter ignoring unknown route allegiance {allegiance} in {sector}'.format(
                    allegiance=rawAllegianceCode,
                    sector=rawMetadata.canonicalName()))

            rawType = rawRoute.type()
            dbType = rawType if rawType else None

            dbWidth = rawRoute.width()

            dbColour = rawRoute.colour()
            if dbColour is not None:
                try:
                    dbColour = common.canonicalHtmlColour(dbColour)
                except:
                    logging.warning(f'Converter ignoring invalid route colour {dbColour} in {rawMetadata.canonicalName()}')
                    dbColour = None

            dbStyle = rawRoute.style()
            if dbStyle is not None:
                if dbStyle.lower() in _ValidLineStyles:
                    dbStyle = dbStyle.lower()
                else:
                    logging.warning(f'Converter ignoring invalid route style {dbStyle} in {rawMetadata.canonicalName()}')
                    dbStyle = None

            # This is replicating code from Traveller Map DrawMicroBorders. The
            # logic is quite fragile in order to mimic the the behaviour from
            # that code while allowing routes to inherit their style from their
            # allegiance.
            # NOTE: When using this we use raw allegiance code as that is how the
            # sector refers to its allegiance
            # TODO: I'm really not sure about this logic, needs a lot of testing.
            # I __think__ the weird not hasBorderStyle might just be achieving the
            # same thing as dbAllegiance is None now
            if dbAllegiance is None or not styleMapper.hasRouteStyle(rawMetadata=rawMetadata, tag=rawAllegianceCode):
                precedence = []
                if dbType is not None:
                    precedence.append(dbType)
                else:
                    precedence.append('Im')
                precedence.append(None)

                for tag in precedence:
                    if not styleMapper.hasRouteStyle(rawMetadata=rawMetadata, tag=tag):
                        continue
                    defaultColour, defaultStyle, defaultWidth = styleMapper.lookupRouteStyle(
                        rawMetadata=rawMetadata,
                        tag=tag)
                    if dbColour is None:
                        dbColour = defaultColour
                    if dbStyle is None:
                        dbStyle = defaultStyle
                    if dbWidth is None:
                        dbWidth = defaultWidth
                    break

            if dbAllegiance is not None:
                dbAllegianceColour, dbAllegianceStyle, dbAllegianceWidth = styleMapper.lookupRouteStyle(
                    rawMetadata=rawMetadata,
                    # NOTE: Use raw allegiance code as that is how the sector refers
                    # to its allegiance
                    tag=rawAllegianceCode)

                # If the style for this route is not the default style for its allegiance,
                # we need to explicitly specify it as the route style
                if dbAllegianceColour == dbAllegiance.routeColour():
                    dbAllegianceColour = None
                if dbAllegianceStyle == dbAllegiance.routeStyle():
                    dbAllegianceStyle = None
                if dbAllegianceWidth == dbAllegiance.routeWidth():
                    dbAllegianceWidth = None

                if dbColour is None:
                    dbColour = dbAllegianceColour
                if dbStyle is None:
                    dbStyle = dbAllegianceStyle
                if dbWidth is None:
                    dbWidth = dbAllegianceWidth

            # TODO: Usually hex range from 1-32 in X and 1-40 in Y. For some reason the
            # metadata spec says route start ends can be in the range 0-33 and 0-41. This
            # is similar to the way border/region outlines work, but for routes there is
            # no need for that weirdness when the offset mechanism is specifically there
            # for this problem. Rather than pass on this horribleness to the DB, I think
            # it would make sense for the conversion process to convert the start/end
            # hex values so they are always in the range 1-32 & 1-40, and set the offset
            # if required. REMEMBER to account for the fact there may already be an offset
            # so it should be an addition/subtraction if there is
            # There are routes in the Rocket sector I have which have this behaviour
            dbRoutes.append(multiverse.DbRoute(
                startHexX=rawRoute.startHexX(),
                startHexY=rawRoute.startHexY(),
                endHexX=rawRoute.endHexX(),
                endHexY=rawRoute.endHexY(),
                startOffsetX=rawRoute.startOffsetX() if rawRoute.startOffsetX() is not None else 0,
                startOffsetY=rawRoute.startOffsetY() if rawRoute.startOffsetY() is not None else 0,
                endOffsetX=rawRoute.endOffsetX() if rawRoute.endOffsetX() is not None else 0,
                endOffsetY=rawRoute.endOffsetY() if rawRoute.endOffsetY() is not None else 0,
                type=dbType,
                style=dbStyle,
                colour=dbColour,
                width=dbWidth,
                allegianceId=dbAllegiance.id() if dbAllegiance else None))

    return dbRoutes

def _createDbBorders(
        rawMetadata: survey.RawMetadata,
        allegianceMapper: multiverse.AllegianceMapper,
        styleMapper: multiverse.StyleMapper
        ) -> typing.List[multiverse.DbBorder]:
    dbBorders = []

    if rawMetadata.borders():
        for rawBorder in rawMetadata.borders():
            dbHexes = rawBorder.hexes()
            if not dbHexes:
                logging.warning(f'Converter ignoring border with empty hex list in {rawMetadata.canonicalName()}')
                continue

            rawAllegianceCode = rawBorder.allegianceCode()
            dbAllegiance = None
            if rawAllegianceCode:
                dbAllegiance = allegianceMapper.lookupAllegiance(
                    rawMetadata=rawMetadata,
                    code=rawAllegianceCode)
            if rawAllegianceCode and not dbAllegiance:
                # This should never happen. The borders should already have been processed
                # to determine which allegiances were used and dbAllegiance created accordingly
                logging.warning('Converter ignoring unknown border allegiance {allegiance} in {sector}'.format(
                    allegiance=rawAllegianceCode,
                    sector=rawMetadata.canonicalName()))

            dbColour = rawBorder.colour()
            if dbColour is not None:
                try:
                    dbColour = common.canonicalHtmlColour(dbColour)
                except:
                    logging.warning(f'Converter ignoring invalid border colour {dbColour} in {rawMetadata.canonicalName()}')
                    dbColour = None

            dbStyle = rawBorder.style()
            if dbStyle is not None:
                if dbStyle.lower() in _ValidLineStyles:
                    dbStyle = dbStyle.lower()
                else:
                    logging.warning(f'Converter ignoring invalid border style {dbStyle} in {rawMetadata.canonicalName()}')
                    dbStyle = None

            # This is replicating code from Traveller Map DrawMicroBorders. The
            # logic is quite fragile in order to mimic the the behaviour from
            # that code while allowing borders to inherit their style from their
            # allegiance.
            # NOTE: When using this we use raw allegiance code as that is how the
            # sector refers to its allegiance
            # TODO: I'm really not sure about this logic, needs a lot of testing.
            # I __think__ the weird not hasBorderStyle might just be achieving the
            # same thing as dbAllegiance is None now
            if dbAllegiance is None or not styleMapper.hasBorderStyle(rawMetadata=rawMetadata, tag=rawAllegianceCode):
                defaultColour, defaultStyle = styleMapper.lookupBorderStyle(
                    rawMetadata=rawMetadata,
                    tag=None)
                if dbColour is None:
                    dbColour = defaultColour
                if dbStyle is None:
                    dbStyle = defaultStyle

            if dbAllegiance is not None:
                dbAllegianceColour, dbAllegianceStyle = styleMapper.lookupBorderStyle(
                    rawMetadata=rawMetadata,
                    tag=rawAllegianceCode)

                # If the style for this border is not the default style for its allegiance,
                # we need to explicitly specify it as the border style
                if dbAllegianceColour == dbAllegiance.borderColour():
                    dbAllegianceColour = None
                if dbAllegianceStyle == dbAllegiance.borderStyle():
                    dbAllegianceStyle = None

                if dbColour is None:
                    dbColour = dbAllegianceColour
                if dbStyle is None:
                    dbStyle = dbAllegianceStyle

            rawLabel = rawBorder.label()
            dbLabel = rawLabel if rawLabel else None

            rawLabelHexX = rawBorder.labelHexX()
            rawLabelHexY = rawBorder.labelHexY()
            dbLabelX = None
            dbLabelY = None
            if rawLabelHexX is not None and rawLabelHexY is not None:
                rawLabelOffsetX = rawBorder.labelOffsetX()
                rawLabelOffsetY = rawBorder.labelOffsetY()
                dbLabelX, dbLabelY = _hexToSectorWorldOffset(
                    hexX=rawLabelHexX,
                    hexY=rawLabelHexY,
                    # NOTE: The 0.7 multiplier is to mimic how Traveller Map
                    # scales the offset in DrawMicroLabels
                    worldOffsetX=(rawLabelOffsetX * 0.7) if rawLabelOffsetX is not None else None,
                    # NOTE: The coordinate space used for the offsets seems to
                    # have an inverted Y direction compared to world space
                    worldOffsetY=(-rawLabelOffsetY * 0.7) if rawLabelOffsetY is not None else None)

            # Show label use the same defaults as the traveller map Border class
            rawShowLabel = rawBorder.showLabel()
            dbShowLabel = rawShowLabel if rawShowLabel is not None else True

            rawWrapLabel = rawBorder.wrapLabel()
            dbWrapLabel = rawWrapLabel if rawWrapLabel is not None else False

            dbBorders.append(multiverse.DbBorder(
                hexes=dbHexes,
                allegianceId=dbAllegiance.id() if dbAllegiance else None,
                style=dbStyle,
                colour=dbColour,
                label=dbLabel,
                labelWorldX=dbLabelX,
                labelWorldY=dbLabelY,
                showLabel=dbShowLabel,
                wrapLabel=dbWrapLabel))

    return dbBorders

def _createDbRegions(
        rawMetadata: survey.RawMetadata,
        ) -> typing.List[multiverse.DbBorder]:
    dbRegions = []

    if rawMetadata.regions():
        for rawRegion in rawMetadata.regions():
            dbHexes = rawRegion.hexes()
            if not dbHexes:
                logging.warning(f'Converter ignoring region with empty hex list in {rawMetadata.canonicalName()}')
                continue

            rawLabel = rawRegion.label()
            dbLabel = rawLabel if rawLabel else None

            rawLabelHexX = rawRegion.labelHexX()
            rawLabelHexY = rawRegion.labelHexY()
            dbLabelX = None
            dbLabelY = None
            if rawLabelHexX is not None and rawLabelHexY is not None:
                rawLabelOffsetX = rawRegion.labelOffsetX()
                rawLabelOffsetY = rawRegion.labelOffsetY()
                dbLabelX, dbLabelY = _hexToSectorWorldOffset(
                    hexX=rawLabelHexX,
                    hexY=rawLabelHexY,
                    # NOTE: The 0.7 multiplier is to mimic how Traveller Map
                    # scales the offset in DrawMicroLabels
                    worldOffsetX=(rawLabelOffsetX * 0.7) if rawLabelOffsetX is not None else None,
                    # NOTE: The coordinate space used for the offsets seems to
                    # have an inverted Y direction compared to world space
                    worldOffsetY=(-rawLabelOffsetY * 0.7) if rawLabelOffsetY is not None else None)

            dbColour = rawRegion.colour()
            if dbColour is not None:
                try:
                    dbColour = common.canonicalHtmlColour(dbColour)
                except:
                    logging.warning(f'Converter ignoring invalid region colour {dbColour} in {rawMetadata.canonicalName()}')
                    dbColour = None

            # Show label use the same defaults as the Traveller Map Border class
            rawShowLabel = rawRegion.showLabel()
            dbShowLabel = rawShowLabel if rawShowLabel is not None else True

            rawWrapLabel = rawRegion.wrapLabel()
            dbWrapLabel = rawWrapLabel if rawWrapLabel is not None else False

            dbRegions.append(multiverse.DbRegion(
                hexes=dbHexes,
                colour=dbColour,
                label=dbLabel,
                labelWorldX=dbLabelX,
                labelWorldY=dbLabelY,
                showLabel=dbShowLabel,
                wrapLabel=dbWrapLabel))

    return dbRegions

def _createDbLabels(
        rawMetadata: survey.RawMetadata,
        ) -> typing.List[multiverse.DbSectorLabel]:
    dbLabels = []

    if rawMetadata.labels():
        for rawLabel in rawMetadata.labels():
            dbLabel = rawLabel.text()
            if not dbLabel:
                logging.warning(f'Converter ignoring empty label in {rawMetadata.canonicalName()}')
                continue

            rawHexX = rawLabel.hexX()
            rawHexY = rawLabel.hexY()
            rawOffsetX = rawLabel.offsetX()
            rawOffsetY = rawLabel.offsetY()
            dbX, dbY = _hexToSectorWorldOffset(
                hexX=rawHexX,
                hexY=rawHexY,
                # NOTE: The 0.7 multiplier is to mimic how Traveller Map
                # scales the offset in DrawMicroLabels
                worldOffsetX=(rawOffsetX * 0.7) if rawOffsetX is not None else None,
                # NOTE: The coordinate space used for the offsets seems to
                # have an inverted Y direction compared to world space
                worldOffsetY=(-rawOffsetY * 0.7) if rawOffsetY is not None else None)

            dbColour = rawLabel.colour()
            if dbColour is not None:
                try:
                    dbColour = common.canonicalHtmlColour(dbColour)
                except:
                    logging.warning(f'Converter ignoring invalid label colour {dbColour} in {rawMetadata.canonicalName()}')
                    dbColour = None

            dbSize = rawLabel.size()
            if dbSize is not None:
                if dbSize.lower() in _ValidLabelSizes:
                    dbSize = dbSize.lower()
                else:
                    logging.warning(f'Converter ignoring invalid label size {dbSize} in {rawMetadata.canonicalName()}')
                    dbSize = None

            rawWrap = rawLabel.wrap()
            dbWrap = rawWrap if rawWrap is not None else False

            dbLabels.append(multiverse.DbSectorLabel(
                text=dbLabel,
                worldX=dbX,
                worldY=dbY,
                colour=dbColour,
                size=dbSize,
                wrap=dbWrap))

    return dbLabels

def _createDbTags(
        rawMetadata: survey.RawMetadata
        ) -> typing.List[multiverse.DbTag]:
    dbTags = []

    rawTags = rawMetadata.tags()
    if rawTags:
        for rawTag in rawTags:
            dbTags.append(multiverse.DbTag(tag=rawTag))

    return dbTags

def _createDbProducts(
        rawMetadata: survey.RawMetadata
        ) -> typing.List[multiverse.DbProduct]:
    rawSources = rawMetadata.sources()
    dbProducts = []

    if rawSources and rawSources.products():
        for product in rawSources.products():
            rawPublication = product.publication()
            rawAuthor = product.author()
            rawPublisher =product.publisher()
            rawReference = product.reference()

            dbProducts.append(multiverse.DbProduct(
                publication=rawPublication if rawPublication else None,
                author=rawAuthor if rawAuthor else None,
                publisher=rawPublisher if rawPublisher else None,
                reference=rawReference if rawReference else None))

    return dbProducts

def _createRawAlternateNames(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[str]]:
    rawAlternateNames = None
    if dbSector.alternateNames():
        rawAlternateNames = []
        for dbName in dbSector.alternateNames():
            rawAlternateNames.append(dbName.name())
    return rawAlternateNames

def _createRawNameLanguages(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.Dict[str, str]]:
    rawNameLanguages = {} if dbSector.language() or dbSector.alternateNames() else None

    if dbSector.language():
        rawNameLanguages[dbSector.name()] = dbSector.language()

    if dbSector.alternateNames():
        for dbName in dbSector.alternateNames():
            if dbName.language():
                rawNameLanguages[dbName.name()] = dbName.language()

    return rawNameLanguages

def _createRawSubsectorNames(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.Dict[str, str]]:
    rawSubsectorNames = None
    if dbSector.subsectorNames():
        rawSubsectorNames = {}
        for dbName in dbSector.subsectorNames():
            rawSubsectorNames[dbName.code()] = dbName.name()
    return rawSubsectorNames

def _createRawTags(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[str]]:
    rawTags = None
    if dbSector.tags():
        rawTags = [dbTag.tag() for dbTag in dbSector.tags()]
    return rawTags

def _createRawAllegiances(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[survey.RawAllegiance]]:
    rawAllegiances = None
    if dbSector.allegiances():
        rawAllegiances = []
        for dbAllegiance in dbSector.allegiances():
            rawAllegiances.append(survey.RawAllegiance(
                code=dbAllegiance.code(),
                name=dbAllegiance.name(),
                base=dbAllegiance.base()))
    return rawAllegiances

def _createRawRoutes(
        dbSector: multiverse.DbSector,
        dbIdToAllegianceMap: typing.Mapping[str, multiverse.DbAllegiance]
        ) -> typing.Optional[typing.List[survey.RawRoute]]:
    rawRoutes = None
    if dbSector.routes():
        rawRoutes = []
        for dbRoute in dbSector.routes():
            dbAllegiance = None
            if dbRoute.allegianceId():
                dbAllegiance = dbIdToAllegianceMap.get(dbRoute.allegianceId())
                if not dbAllegiance:
                    # This should never happen, the sector should always have an entry for every
                    # allegiance used
                    logging.warning('Converter ignoring unknown allegiance {allegiance} for route {route} in {sector}'.format(
                        allegiance=dbRoute.allegianceId(),
                        route=dbRoute.id(),
                        sector=dbSector.name()))

            rawRoutes.append(survey.RawRoute(
                startHexX=dbRoute.startHexX(),
                startHexY=dbRoute.startHexY(),
                endHexX=dbRoute.endHexX(),
                endHexY=dbRoute.endHexY(),
                startOffsetX=dbRoute.startOffsetX() if dbRoute.startOffsetX() else None,
                startOffsetY=dbRoute.startOffsetY() if dbRoute.startOffsetY() else None,
                endOffsetX=dbRoute.endOffsetX() if dbRoute.endOffsetX() else None,
                endOffsetY=dbRoute.endOffsetY() if dbRoute.endOffsetY() else None,
                allegianceCode=dbAllegiance.code() if dbAllegiance else None,
                type=dbRoute.type(),
                style=dbRoute.style(),
                colour=dbRoute.colour(),
                width=dbRoute.width()))

    return rawRoutes

def _createRawBorders(
        dbSector: multiverse.DbSector,
        dbIdToAllegianceMap: typing.Mapping[str, multiverse.DbAllegiance]
        ) -> typing.Optional[typing.List[survey.RawBorder]]:
    rawBorders = None
    if dbSector.borders():
        rawBorders = []
        for dbBorder in dbSector.borders():
            dbAllegiance = None
            if dbBorder.allegianceId():
                dbAllegiance = dbIdToAllegianceMap.get(dbBorder.allegianceId())
                if not dbAllegiance:
                    # This should never happen, the sector should always have an entry for every
                    # allegiance used
                    logging.warning('Converter ignoring unknown allegiance {allegiance} for border {border} in {sector}'.format(
                        allegiance=dbBorder.allegianceId(),
                        border=dbBorder.id(),
                        sector=dbSector.name()))

            labelHexX = labelHexY = labelOffsetX = labelOffsetY = None
            if dbBorder.labelWorldX() is not None and dbBorder.labelWorldY() is not None:
                labelHexX, labelHexY, labelOffsetX, labelOffsetY = _sectorWorldOffsetToHex(
                    worldX=dbBorder.labelWorldX(),
                    worldY=dbBorder.labelWorldY())

                # NOTE: The 0.7 divisor is to mimic how Traveller Map scales the offset
                # in DrawMicroLabels
                if labelOffsetX is not None:
                    labelOffsetX = labelOffsetX / 0.7
                if labelOffsetY is not None:
                    labelOffsetY = -labelOffsetY / 0.7

            rawBorders.append(survey.RawBorder(
                hexes=dbBorder.hexes(),
                allegianceCode=dbAllegiance.code() if dbAllegiance else None,
                showLabel=dbBorder.showLabel(),
                wrapLabel=dbBorder.wrapLabel(),
                labelHexX=labelHexX,
                labelHexY=labelHexY,
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=dbBorder.label(),
                style=dbBorder.style(),
                colour=dbBorder.colour()))

    return rawBorders

def _createRawRegions(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[survey.RawRegion]]:
    rawRegions = None
    if dbSector.regions():
        rawRegions = []
        for dbRegion in dbSector.regions():
            labelHexX = labelHexY = labelOffsetX = labelOffsetY = None
            if dbRegion.labelWorldX() is not None and dbRegion.labelWorldY() is not None:
                labelHexX, labelHexY, labelOffsetX, labelOffsetY = _sectorWorldOffsetToHex(
                    worldX=dbRegion.labelWorldX(),
                    worldY=dbRegion.labelWorldY())

                # NOTE: The 0.7 divisor is to mimic how Traveller Map scales the offset
                # in DrawMicroLabels
                if labelOffsetX is not None:
                    labelOffsetX = labelOffsetX / 0.7
                if labelOffsetY is not None:
                    labelOffsetY = -labelOffsetY / 0.7

            rawRegions.append(survey.RawRegion(
                hexes=dbRegion.hexes(),
                showLabel=dbRegion.showLabel(),
                wrapLabel=dbRegion.wrapLabel(),
                labelHexX=labelHexX,
                labelHexY=labelHexY,
                labelOffsetX=labelOffsetX,
                labelOffsetY=labelOffsetY,
                label=dbRegion.label(),
                colour=dbRegion.colour()))

    return rawRegions

def _createRawLabels(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[survey.RawSectorLabel]]:
    rawLabels = None
    if dbSector.labels():
        rawLabels = []
        for dbLabel in dbSector.labels():
            labelHexX = labelHexY = labelOffsetX = labelOffsetY = None
            if dbLabel.worldX() is not None and dbLabel.worldY() is not None:
                labelHexX, labelHexY, labelOffsetX, labelOffsetY = _sectorWorldOffsetToHex(
                    worldX=dbLabel.worldX(),
                    worldY=dbLabel.worldY())

                # NOTE: The 0.7 divisor is to mimic how Traveller Map scales the offset
                # in DrawMicroLabels
                if labelOffsetX is not None:
                    labelOffsetX = labelOffsetX / 0.7
                if labelOffsetY is not None:
                    labelOffsetY = -labelOffsetY / 0.7

            rawLabels.append(survey.RawSectorLabel(
                text=dbLabel.text(),
                hexX=labelHexX,
                hexY=labelHexY,
                offsetX=labelOffsetX,
                offsetY=labelOffsetY,
                colour=dbLabel.colour(),
                size=dbLabel.size(),
                wrap=dbLabel.wrap()))

    return rawLabels

def _createRawSources(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[survey.RawSources]:
    rawPrimarySource = None
    if dbSector.publication() or dbSector.author() or dbSector.publisher() or dbSector.reference():
        rawPrimarySource = survey.RawSource(
            publication=dbSector.publication(),
            author=dbSector.author(),
            publisher=dbSector.publisher(),
            reference=dbSector.reference())

    rawProducts = None
    if dbSector.products():
        rawProducts = []
        for dbProduct in dbSector.products():
            rawProducts.append(survey.RawSource(
                publication=dbProduct.publication(),
                author=dbProduct.author(),
                publisher=dbProduct.publisher(),
                reference=dbProduct.reference()))

    rawSources = None
    if dbSector.credits() or rawPrimarySource or rawProducts:
        rawSources = survey.RawSources(
            credits=dbSector.credits(),
            primary=rawPrimarySource,
            products=rawProducts)

    return rawSources

def _createRawMetadata(
        dbSector: multiverse.DbSector
        ) -> survey.RawMetadata:
    if dbSector.allegiances():
        dbIdToAllegianceMap = {dbAllegiance.id(): dbAllegiance for dbAllegiance in dbSector.allegiances()}
    else:
        dbIdToAllegianceMap = {}

    return survey.RawMetadata(
        x=dbSector.sectorX(),
        y=dbSector.sectorY(),
        canonicalName=dbSector.name(),
        alternateNames=_createRawAlternateNames(dbSector=dbSector),
        nameLanguages=_createRawNameLanguages(dbSector=dbSector),
        abbreviation=dbSector.abbreviation(),
        sectorLabel=dbSector.sectorLabel(),
        subsectorNames=_createRawSubsectorNames(dbSector=dbSector),
        selected=dbSector.selected(),
        tags=_createRawTags(dbSector=dbSector),
        allegiances=_createRawAllegiances(dbSector=dbSector),
        routes=_createRawRoutes(dbSector=dbSector, dbIdToAllegianceMap=dbIdToAllegianceMap),
        borders=_createRawBorders(dbSector=dbSector, dbIdToAllegianceMap=dbIdToAllegianceMap),
        regions=_createRawRegions(dbSector=dbSector),
        labels=_createRawLabels(dbSector=dbSector),
        sources=_createRawSources(dbSector=dbSector),
        styleSheet=None)

def _createRawWorlds(
        dbSector: multiverse.DbSector
        ) -> typing.List[survey.RawWorld]:
    if dbSector.allegiances():
        dbIdToAllegianceMap = {dbAllegiance.id(): dbAllegiance for dbAllegiance in dbSector.allegiances()}
    else:
        dbIdToAllegianceMap = {}

    if dbSector.sophonts():
        dbIdToSophontMap = {dbSophont.id(): dbSophont for dbSophont in dbSector.sophonts()}
    else:
        dbIdToSophontMap = {}

    rawWorlds = []
    if dbSector.systems():
        for dbSystem in dbSector.systems():
            dbMainWorld = None
            for dbBody in dbSystem.bodies():
                if isinstance(dbBody, multiverse.DbWorld) and dbBody.isMainWorld():
                    dbMainWorld = dbBody
                    break

            dbSystemAllegiance = None
            if dbSystem.allegianceId():
                dbSystemAllegiance = dbIdToAllegianceMap.get(dbSystem.allegianceId())
                if not dbSystemAllegiance:
                    # This should never happen, the sector should always have an entry for every
                    # allegiance used
                    logging.warning('Converter ignoring unknown system allegiance {allegiance} in {sector}'.format(
                        allegiance=dbSystem.allegianceId(),
                        sector=dbSector.name()))

            rawUWP = survey.RawUWP(
                starport=dbMainWorld.starport() if dbMainWorld else None,
                worldSize=dbMainWorld.worldSize() if dbMainWorld else None,
                atmosphere=dbMainWorld.atmosphere() if dbMainWorld else None,
                hydrographics=dbMainWorld.hydrographics() if dbMainWorld else None,
                population=dbMainWorld.population() if dbMainWorld else None,
                government=dbMainWorld.government() if dbMainWorld else None,
                lawLevel=dbMainWorld.lawLevel() if dbMainWorld else None,
                techLevel=dbMainWorld.techLevel() if dbMainWorld else None)

            rawEconomics = survey.RawEconomics(
                resources=dbMainWorld.resources() if dbMainWorld else None,
                labour=dbMainWorld.labour() if dbMainWorld else None,
                infrastructure=dbMainWorld.infrastructure() if dbMainWorld else None,
                # TODO: Check that generated tab & column files are valid
                # when the efficiency is unknown. I think the fact it's
                # 2 character string (with +/-) but it's only putting
                # in a single ? might break things
                efficiency=dbMainWorld.efficiency() if dbMainWorld else None)

            rawCulture = survey.RawCulture(
                heterogeneity=dbMainWorld.heterogeneity() if dbMainWorld else None,
                acceptance=dbMainWorld.acceptance() if dbMainWorld else None,
                strangeness=dbMainWorld.strangeness() if dbMainWorld else None,
                symbols=dbMainWorld.symbols() if dbMainWorld else None)

            rawPBG = survey.RawPBG(
                populationMultiplier=dbMainWorld.populationMultiplier() if dbMainWorld else None,
                planetoidBeltCount=survey.ehexFromInteger(value=dbSystem.planetoidBeltCount(), default=None),
                gasGiantCount=survey.ehexFromInteger(value=dbSystem.gasGiantCount(), default=None))

            numPlanetoidBelt = dbSystem.planetoidBeltCount()
            numGasGiants = dbSystem.gasGiantCount()
            numWorlds = dbSystem.worldCount()
            rawSystemWorldCount = None
            if numPlanetoidBelt is not None or numGasGiants is not None or numWorlds is not None:
                rawSystemWorldCount = 0
                if numPlanetoidBelt:
                    rawSystemWorldCount += numPlanetoidBelt
                if numGasGiants:
                    rawSystemWorldCount += numGasGiants
                if numWorlds:
                    rawSystemWorldCount += numWorlds

            rawNobilities = None
            rawBases = None
            rawTradeCodes = None
            rawRemarks = None
            if dbMainWorld:
                if dbMainWorld.nobilities():
                    rawNobilities = [dbNobility.code() for dbNobility in dbMainWorld.nobilities()]

                if dbMainWorld.bases():
                    rawBases = [dbBase.code() for dbBase in dbMainWorld.bases()]

                if dbMainWorld.tradeCodes():
                    rawTradeCodes = [dbTradeCode.code() for dbTradeCode in dbMainWorld.tradeCodes()]

                rawMajorRaceHomeWorlds: typing.Optional[typing.List[survey.RawSophontPopulation]] = None
                rawMinorRaceHomeWorlds: typing.Optional[typing.List[survey.RawSophontPopulation]] = None
                rawSophontPopulations: typing.Optional[typing.List[survey.RawSophontPopulation]] = None
                rawDiebackSophonts: typing.Optional[typing.List[str]] = None
                if dbMainWorld.sophontPopulations():
                    for dbSophontPopulation in dbMainWorld.sophontPopulations():
                        dbSophont = dbIdToSophontMap.get(dbSophontPopulation.sophontId())
                        if not dbSophont:
                            # This should never happen, the sector should always have an entry for every
                            # sophont used
                            logging.warning('Converter ignoring sophont population {population} using unknown sophont {sophont} in {sector}'.format(
                                population=dbSophontPopulation.id(),
                                sophont=dbSophontPopulation.sophontId(),
                                sector=dbSector.name()))
                            continue

                        if dbSophontPopulation.isHomeWorld():
                            if dbSophont.isMajor():
                                if rawMajorRaceHomeWorlds is None:
                                    rawMajorRaceHomeWorlds = []
                                rawMajorRaceHomeWorlds.append(survey.RawSophontPopulation(
                                    sophont=dbSophont.name(),
                                    percentage=dbSophontPopulation.percentage()))
                            else:
                                if rawMinorRaceHomeWorlds is None:
                                    rawMinorRaceHomeWorlds = []
                                rawMinorRaceHomeWorlds.append(survey.RawSophontPopulation(
                                    sophont=dbSophont.name(),
                                    percentage=dbSophontPopulation.percentage()))

                        if dbSophontPopulation.isDieBack():
                            if rawDiebackSophonts is None:
                                rawDiebackSophonts = []
                            rawDiebackSophonts.append(dbSophont.name())
                        elif not dbSophontPopulation.isHomeWorld():
                            if rawSophontPopulations is None:
                                rawSophontPopulations = []
                            rawSophontPopulations.append(survey.RawSophontPopulation(
                                sophont=dbSophont.code(),
                                percentage=dbSophontPopulation.percentage()))

                rawOwningSystems: typing.Optional[typing.List[survey.RawHexRef]] = None
                if dbMainWorld.owningSystems():
                    rawOwningSystems = []
                    for dbOwner in dbMainWorld.owningSystems():
                        rawOwningSystems.append(survey.RawHexRef(
                            x=dbOwner.hexX(),
                            y=dbOwner.hexY(),
                            sector=dbOwner.sectorAbbreviation()))

                rawColonySystems: typing.Optional[typing.List[survey.RawHexRef]] = None
                if dbMainWorld.colonySystems():
                    rawColonySystems = []
                    for dbColony in dbMainWorld.colonySystems():
                        rawColonySystems.append(survey.RawHexRef(
                            x=dbColony.hexX(),
                            y=dbColony.hexY(),
                            sector=dbColony.sectorAbbreviation()))

                rawRulingAllegiances: typing.Optional[typing.List[str]] = None
                if dbMainWorld.rulingAllegiances():
                    rawRulingAllegiances = []
                    for dbRuler in dbMainWorld.rulingAllegiances():
                        dbRulingAllegiance = dbIdToAllegianceMap.get(dbRuler.allegianceId())
                        if dbRulingAllegiance is None:
                            # This should never happen, the sector should always have an entry for every
                            # allegiance used
                            logging.warning('Converter ignoring ruler {ruler} with unknown allegiance {allegiance} in {sector}'.format(
                                ruler=dbRuler.id(),
                                allegiance=dbRuler.allegianceId(),
                                sector=dbSector.name()))
                            continue
                        rawRulingAllegiances.append(dbRulingAllegiance.code())

                rawResearchStations: typing.Optional[typing.List[str]] = None
                if dbMainWorld.researchStations():
                    rawResearchStations = [dbStation.code() for dbStation in dbMainWorld.researchStations()]

                rawCustomRemarks: typing.Optional[typing.List[str]] = None
                if dbMainWorld.customRemarks():
                    rawCustomRemarks = [dbRemark.remark() for dbRemark in dbMainWorld.customRemarks()]

                hasRemarks = rawTradeCodes or rawMajorRaceHomeWorlds or rawMinorRaceHomeWorlds or \
                    rawSophontPopulations or rawDiebackSophonts or rawOwningSystems or rawColonySystems or \
                    rawRulingAllegiances or rawResearchStations or rawCustomRemarks
                if hasRemarks:
                    rawRemarks = survey.RawRemarks(
                        tradeCodes=rawTradeCodes,
                        majorRaceHomeWorlds=rawMajorRaceHomeWorlds,
                        minorRaceHomeWorlds=rawMinorRaceHomeWorlds,
                        sophontPopulations=rawSophontPopulations,
                        dieBackSophonts=rawDiebackSophonts,
                        owningSystems=rawOwningSystems,
                        colonySystems=rawColonySystems,
                        rulingAllegiances=rawRulingAllegiances,
                        researchStations=rawResearchStations,
                        customRemarks=rawCustomRemarks)

            rawStars = None
            if dbSystem.stars():
                rawStars = []
                for dbStar in dbSystem.stars():
                    rawStars.append(survey.RawStar(
                        luminosityClass=dbStar.luminosityClass(),
                        spectralClass=dbStar.spectralClass(),
                        spectralScale=dbStar.spectralScale()))

            rawWorlds.append(survey.RawWorld(
                x=dbSystem.hexX(),
                y=dbSystem.hexY(),
                name=dbSystem.name(),
                allegianceCode=dbSystemAllegiance.code() if dbSystemAllegiance else None,
                zone=dbSystem.zone(),
                uwp=rawUWP,
                economics=rawEconomics,
                culture=rawCulture,
                nobilities=rawNobilities,
                bases=rawBases,
                remarks=rawRemarks,
                pbg=rawPBG,
                systemWorlds=rawSystemWorldCount,
                stars=rawStars,
                # TODO: I'm not sure if I need to bother supporting these
                importance=None))

    return rawWorlds

def convertDbSectorToRawSector(
        dbSector: multiverse.DbSector
        ) -> typing.Tuple[
            survey.RawMetadata,
            typing.List[survey.RawWorld]]:
    rawMetadata = _createRawMetadata(
        dbSector=dbSector)

    rawWorlds = _createRawWorlds(
        dbSector=dbSector)

    return (rawMetadata, rawWorlds)

def convertRawLabelsToDbMapLabels(
        rawMegaLabels: typing.Collection[survey.RawUniverseLabel],
        rawMinorLabels: typing.Collection[survey.RawUniverseLabel],
        rawWorldLabels: typing.Collection[survey.RawWorldLabel],
        rawUniverseInfo: typing.Collection[survey.RawSectorInfo]
        ) -> typing.List[multiverse.DbMapLabel]:
    dbLabels: typing.List[multiverse.DbMapLabel] = []

    for rawLabel in rawMegaLabels:
        dbLabels.append(multiverse.DbMapLabel(
            text=rawLabel.text(),
            worldX=rawLabel.worldX(),
            worldY=rawLabel.worldY(),
            layer='mega',
            size='small' if rawLabel.minor() else 'large'))

    for rawLabel in rawMinorLabels:
        dbLabels.append(multiverse.DbMapLabel(
            text=rawLabel.text(),
            worldX=rawLabel.worldX(),
            worldY=rawLabel.worldY(),
            layer='minor',
            size='small' if rawLabel.minor() else 'large'))

    if rawWorldLabels:
        sectorNameMap: typing.Dict[str, survey.RawSectorInfo] = {}
        for sectorInfo in rawUniverseInfo:
            nameInfos = sectorInfo.nameInfos()
            if not nameInfos:
                continue
            sectorNameMap[nameInfos[0].name()] = sectorInfo

        for rawLabel in rawWorldLabels:
            sectorInfo = sectorNameMap.get(rawLabel.sector())
            if sectorInfo is None:
                # TODO: Log this or write to reporter
                continue

            worldX, worldY = _sectorHexToWorldSpace(
                sectorX=sectorInfo.x(),
                sectorY=sectorInfo.y(),
                hexX=rawLabel.hexX(),
                hexY=rawLabel.hexY())

            biasX = rawLabel.biasX()
            if biasX is None:
                biasX = 1 # Default comes from traveller map default
            biasY = rawLabel.biasY()
            if biasY is None:
                biasY = 1 # Default comes from traveller map default

            if biasX > 0:
                if biasY < 0:
                    alignment = 'bottom_left'
                elif biasY > 0:
                    alignment = 'top_left'
                else:
                    alignment = 'center_left'
            elif biasX < 0:
                if biasY < 0:
                    alignment = 'bottom_right'
                elif biasY > 0:
                    alignment = 'top_right'
                else:
                    alignment = 'center_right'
            else:
                if biasY < 0:
                    alignment = 'bottom_center'
                elif biasY > 0:
                    alignment = 'top_center'
                else:
                    alignment = 'center'

            dbLabels.append(multiverse.DbMapLabel(
                text=rawLabel.name(),
                worldX=worldX,
                worldY=worldY,
                layer='world',
                alignment=alignment))

    return dbLabels

_RawVectorPointTypeStart = 0x00
_RawVectorPointTypeLine = 0x01
_RawVectorPointTypeMask = 0x07
_RawVectorPointTypeCloseSubpath = 0x80
def _convertRawVectorToDbMapVectors(
        rawVector: survey.RawVector,
        layer: str
        ) -> typing.List[multiverse.DbMapVector]:
    mapOptions = rawVector.mapOptions()
    if mapOptions is None or ('BordersMajor' not in mapOptions and 'BordersMinor' not in mapOptions):
        return []

    originX = rawVector.originX() if rawVector.originX() is not None else 0
    originY = rawVector.originY() if rawVector.originY() is not None else 0
    scaleX = rawVector.scaleX() if rawVector.scaleX() is not None else 1
    scaleY = rawVector.scaleY() if rawVector.scaleY() is not None else 1

    vectorPoints = rawVector.pathDataPoints()
    pointTypes = rawVector.pathDataTypes()
    dbVectors: typing.List[multiverse.DbMapVector] = []
    if pointTypes is None:
        sectionPoints = []
        for point in vectorPoints:
            sectionPoints.append((
                (point[0] - originX) * scaleX,
                (point[1] - originY) * scaleY))
        dbVectors.append(multiverse.DbMapVector(
            points=sectionPoints,
            layer=layer,
            closed=False))
    else:
        finishIndex = len(vectorPoints) - 1
        sectionPoints = []

        for currentIndex, (point, type) in enumerate(zip(vectorPoints, pointTypes)):
            isStartPoint = (type & _RawVectorPointTypeMask) == _RawVectorPointTypeStart
            isLastPoint = currentIndex == finishIndex
            isClosed = (type & _RawVectorPointTypeCloseSubpath) == _RawVectorPointTypeCloseSubpath

            if isClosed or isLastPoint:
                sectionPoints.append((
                    (point[0] - originX) * scaleX,
                    (point[1] - originY) * scaleY))

            if (isStartPoint and sectionPoints) or isClosed or isLastPoint:
                dbVectors.append(multiverse.DbMapVector(
                    points=sectionPoints,
                    layer=layer,
                    closed=isClosed))
                sectionPoints.clear()

            sectionPoints.append((
                (point[0] - originX) * scaleX,
                (point[1] - originY) * scaleY))

    return dbVectors

def convertRawVectorsToDbMapVectors(
        rawBorderVectors: typing.Collection[survey.RawVector],
        rawRiftVectors: typing.Collection[survey.RawVector],
        rawRouteVectors: typing.Collection[survey.RawVector]
        ) -> typing.List[multiverse.DbMapVector]:
    dbVectors: typing.List[multiverse.DbMapVector] = []

    for rawVector in rawBorderVectors:
        dbVectors.extend(_convertRawVectorToDbMapVectors(
            rawVector=rawVector,
            layer='border'))

    # Rift vectors are never drawn so no point converting them (but
    # the names are drawn)
    """
    for rawVector in rawRiftVectors:
        dbVectors.extend(_convertRawVectorToDbMapVectors(
            rawVector=rawVector,
            layer='rift'))
    """

    for rawVector in rawRouteVectors:
        dbVectors.extend(_convertRawVectorToDbMapVectors(
            rawVector=rawVector,
            layer='route'))

    return dbVectors

def _convertRawVectorToDbMapLabel(
        rawVector: survey.RawVector,
        layer: str
        ) -> typing.Optional[multiverse.DbMapLabel]:
        text = rawVector.name()
        if text is None:
            return None

        mapOptions = rawVector.mapOptions()
        if mapOptions is None:
            return None

        if 'NamesMajor' in mapOptions:
            isMajor = True
        elif 'NamesMinor' in mapOptions:
            isMajor = False
        else:
            return None

        originX = rawVector.originX() if rawVector.originX() is not None else 0
        originY = rawVector.originY() if rawVector.originY() is not None else 0
        scaleX = rawVector.scaleX() if rawVector.scaleX() is not None else 1
        scaleY = rawVector.scaleY() if rawVector.scaleY() is not None else 1
        nameX = rawVector.nameX() if rawVector.nameX() is not None else 0
        nameY = rawVector.nameY() if rawVector.nameY() is not None else 0

        bounds = rawVector.bounds()
        if bounds is not None:
            boundsMinX = (bounds.x() - originX) * scaleX
            boundsMinY = (bounds.y() - originY) * scaleY
            boundsMaxX = boundsMinX + (bounds.width() * scaleX)
            boundsMaxY = boundsMinY + (bounds.height() * scaleY)
            boundsMinX, boundsMaxX = common.minmax(boundsMinX, boundsMaxX)
            boundsMinY, boundsMaxY = common.minmax(boundsMinY, boundsMaxY)

            textX = (boundsMaxX + boundsMinX) / 2
            textX += (boundsMaxX - boundsMinX) * (nameX / bounds.width())
            textY = (boundsMaxY + boundsMinY) / 2
            textY += (boundsMaxY - boundsMinY) * (nameY / bounds.height())
        else:
            # TODO: Check this works
            boundsMinX = boundsMinY = boundsMaxX = boundsMaxY = None
            for x, y in rawVector.pathDataPoints():
                x = (x - originX) * scaleX
                y = (y - originY) * scaleY
                if boundsMinX is None or x < boundsMinX:
                    boundsMinX = x
                if boundsMinY is None or y < boundsMinY:
                    boundsMinY = y
                if boundsMaxX is None or x > boundsMaxX:
                    boundsMaxX = x
                if boundsMaxY is None or y > boundsMaxY:
                    boundsMaxY = y
            if boundsMinX is None or boundsMinY is None or boundsMaxX is None or boundsMaxY is None:
                return None

            textX = (boundsMaxX + boundsMinX) / 2
            textY = (boundsMaxY + boundsMinY) / 2

        return multiverse.DbMapLabel(
            text=text.upper() if isMajor else text,
            worldX=textX,
            worldY=textY,
            layer=layer,
            size='large' if isMajor else 'small',
            rotation=35 if layer == 'rift' else None)

def convertRawVectorsToDbMapLabels(
        rawBorderVectors: typing.Collection[survey.RawVector],
        rawRiftVectors: typing.Collection[survey.RawVector],
        rawRouteVectors: typing.Collection[survey.RawVector]
        ) -> typing.List[multiverse.DbMapLabel]:
    dbLabels: typing.List[multiverse.DbMapLabel] = []

    for rawVector in rawBorderVectors:
        dbLabel = _convertRawVectorToDbMapLabel(
            rawVector=rawVector,
            layer='border')
        if dbLabel is not None:
            dbLabels.append(dbLabel)

    for rawVector in rawRiftVectors:
        dbLabel = _convertRawVectorToDbMapLabel(
            rawVector=rawVector,
            layer='rift')
        if dbLabel is not None:
            dbLabels.append(dbLabel)

    for rawVector in rawRouteVectors:
        dbLabel = _convertRawVectorToDbMapLabel(
            rawVector=rawVector,
            layer='route')
        if dbLabel is not None:
            dbLabels.append(dbLabel)

    return dbLabels

def _convertRawSectorToDbSector(
        rawMetadata: survey.RawMetadata,
        rawWorlds: typing.Collection[survey.RawWorld],
        rawStockSophonts: typing.Collection[survey.RawStockSophont],
        allegianceMapper: multiverse.AllegianceMapper,
        styleMapper: multiverse.StyleMapper
        ) -> multiverse.DbSector:
    dbSectorX = rawMetadata.x()
    dbSectorY = rawMetadata.y()
    dbSectorName = rawMetadata.canonicalName()

    rawSectorLanguage = rawMetadata.nameLanguage(rawMetadata.canonicalName())
    dbSectorLanguage = rawSectorLanguage if rawSectorLanguage else None

    rawAbbreviation = rawMetadata.abbreviation()
    dbAbbreviation = rawAbbreviation if rawAbbreviation else None

    rawSectorLabel = rawMetadata.sectorLabel()
    dbSectorLabel = rawSectorLabel if rawSectorLabel else None

    rawSelected = rawMetadata.selected()
    dbSelected = rawSelected if rawSelected is not None else False

    dbAlternateNames = _createDbAlternateNames(
        rawMetadata=rawMetadata)

    dbSubsectorNames = _createDbSubsectorNames(
        rawMetadata=rawMetadata)

    dbSophontCodeMap, dbSophontNameMap = _createDbSophonts(
        rawMetadata=rawMetadata,
        rawSystems=rawWorlds,
        rawStockSophonts=rawStockSophonts)
    dbSophonts = set(itertools.chain(dbSophontCodeMap.values(), dbSophontNameMap.values())) # Use unique sophonts

    dbSystems = _createDbSystems(
        rawMetadata=rawMetadata,
        rawSystems=rawWorlds,
        allegianceMapper=allegianceMapper,
        dbSophontCodeMap=dbSophontCodeMap,
        dbSophontNameMap=dbSophontNameMap)

    dbRoutes = _createDbRoutes(
        rawMetadata=rawMetadata,
        allegianceMapper=allegianceMapper,
        styleMapper=styleMapper)

    dbBorders = _createDbBorders(
        rawMetadata=rawMetadata,
        allegianceMapper=allegianceMapper,
        styleMapper=styleMapper)

    dbRegions = _createDbRegions(
        rawMetadata=rawMetadata)

    dbLabels = _createDbLabels(
        rawMetadata=rawMetadata)

    dbTags = _createDbTags(rawMetadata=rawMetadata)

    dbProducts = _createDbProducts(rawMetadata=rawMetadata)

    rawSources = rawMetadata.sources()
    rawPrimarySource = rawSources.primary() if rawSources else None

    rawCredits = rawSources.credits() if rawSources else None
    dbCredits = rawCredits if rawCredits else None

    rawPublication = rawPrimarySource.publication() if rawPrimarySource else None
    dbPublication = rawPublication if rawPublication else None

    rawAuthor = rawPrimarySource.author() if rawPrimarySource else None
    dbAuthor = rawAuthor if rawAuthor else None

    rawPublisher = rawPrimarySource.publisher() if rawPrimarySource else None
    dbPublisher = rawPublisher if rawPublisher else None

    rawReference = rawPrimarySource.reference() if rawPrimarySource else None
    dbReference = rawReference if rawReference else None

    return multiverse.DbSector(
        sectorX=dbSectorX,
        sectorY=dbSectorY,
        name=dbSectorName,
        language=dbSectorLanguage,
        abbreviation=dbAbbreviation,
        sectorLabel=dbSectorLabel,
        selected=dbSelected,
        alternateNames=dbAlternateNames,
        subsectorNames=dbSubsectorNames,
        sophonts=dbSophonts,
        systems=dbSystems,
        routes=dbRoutes,
        borders=dbBorders,
        regions=dbRegions,
        labels=dbLabels,
        tags=dbTags,
        credits=dbCredits,
        publication=dbPublication,
        author=dbAuthor,
        publisher=dbPublisher,
        reference=dbReference,
        products=dbProducts)

def convertRawSectorsToDbSectors(
        rawSectors: typing.List[typing.Tuple[survey.RawMetadata, typing.Collection[survey.RawWorld]]],
        rawStockSophonts: typing.Collection[survey.RawStockSophont],
        allegianceMapper: multiverse.AllegianceMapper,
        styleMapper: multiverse.StyleMapper
        ) -> typing.List[multiverse.DbSector]:
    dbSectors: typing.List[multiverse.DbSector] = []
    for rawMetadata, rawWorlds in rawSectors:
        dbSector = _convertRawSectorToDbSector(
            rawMetadata=rawMetadata,
            rawWorlds=rawWorlds,
            rawStockSophonts=rawStockSophonts,
            allegianceMapper=allegianceMapper,
            styleMapper=styleMapper)
        dbSectors.append(dbSector)

    return dbSectors