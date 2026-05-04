import astronomer
import common
import logging
import multiverse
import survey
import threading
import traveller
import typing

# This object is thread safe, however the world objects are only thread safe
# as they are currently read only (i.e. once loaded they never change).
class WorldManager(object):
    # To mimic the behaviour of Traveller Map, the world position data for
    # M1105 is used as placeholders if the specified milieu doesn't have
    # a sector at that location. The world details may not be valid for the
    # specified milieu but the position is
    _PlaceholderMilieu = astronomer.Milieu.M1105

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _universe: astronomer.Universe = None

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
        return cls._instance

    def setCurrentUniverse(
            self,
            universeId: str,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        # Acquire lock while loading universe
        with self._lock:
            universeInfo = multiverse.UniverseManager.instance().universeInfo(
                universeId=universeId)
            if not universeInfo:
                raise ValueError(f'Unknown universe "{universeId}"')

            logging.info(f'Loaded universe {universeId} ({universeInfo.name()})')

            customSectors = set()
            if not universeInfo.isStock():
                sectorInfos = multiverse.UniverseManager.instance().sectorInfos(
                    universeId=universeId)
                for sectorInfo in sectorInfos:
                    fromStockData = sectorInfo.stockDataHash() is not None
                    isModified = sectorInfo.modifiedTimestamp() is not None
                    if fromStockData and isModified:
                        customSectors.add(sectorInfo.id())

            sectorGenerator = multiverse.UniverseManager.instance().yieldSectors(
                universeId=universeId,
                progressCallback=progressCallback)
            sectors = []
            for dbSector in sectorGenerator:
                try:
                    sector = self._convertDbSector(
                        dbSector=dbSector,
                        isCustom=dbSector.id() in customSectors)
                    sectors.append(sector)

                    logging.debug(
                        'Loaded {worlds} worlds for sector {name} at ({x}, {y}) from {milieu}'.format(
                            worlds=sector.worldCount(),
                            name=sector.name(),
                            x=sector.position().sectorX(),
                            y=sector.position().sectorY(),
                            milieu=sector.milieu().value))
                except Exception as ex:
                    logging.error(
                        'Failed to load sector {name} at ({x}, {y}) from {milieu.value}'.format(
                            name=sector.name(),
                            x=sector.position().sectorX(),
                            y=sector.position().sectorY(),
                            milieu=sector.milieu().value),
                        exc_info=ex)
                    continue

            self._universe = astronomer.Universe(
                id=universeId,
                sectors=sectors,
                placeholderMilieu=WorldManager._PlaceholderMilieu)

    def universe(self) -> astronomer.Universe:
        return self._universe

    @staticmethod
    def _convertDbSector(
            dbSector: multiverse.DbSector,
            isCustom: bool
            ) -> astronomer.Sector:
        sectorName = dbSector.name()
        sectorX = dbSector.sectorX()
        sectorY = dbSector.sectorY()

        milieu = WorldManager._mapMilieu(dbSector.milieu())
        if not milieu:
            raise ValueError(f'Unknown milieu "{dbSector.milieu()}"')

        sectorLoggingName = '{sectorName} ({sectorX}, {sectorY}) from {milieu}'.format(
            sectorName=sectorName if sectorName else '<Unnamed Sector>',
            sectorX=sectorX,
            sectorY=sectorY,
            milieu=milieu.value)

        dbAlternateNames = dbSector.alternateNames()
        alternateNames = None
        if dbAlternateNames:
            alternateNames = []
            for dbAlternateName in dbAlternateNames:
                alternateNames.append(dbAlternateName.name())

        subsectorNameMap: typing.Dict[
            str, # Subsector code (A-P)
            str] = {}

        if dbSector.subsectorNames():
            for dbSubsectorName in dbSector.subsectorNames():
                # NOTE: Unlike most other places, it's intentional that this is upper case
                subsectorNameMap[dbSubsectorName.code()] = dbSubsectorName.name()

        allegianceIdMap: typing.Dict[str, astronomer.Allegiance] = {}
        if dbSector.allegiances():
            for dbAllegiance in dbSector.allegiances():
                try:
                    routeStyle = dbAllegiance.routeStyle()
                    if routeStyle:
                        routeStyle = WorldManager._mapLineStyle(routeStyle)
                        if not routeStyle:
                            logging.warning('Ignoring invalid route style "{style}" for allegiance {objectId} when loading sector {sectorId} ({name})'.format(
                                style=dbAllegiance.routeStyle(),
                                objectId=dbAllegiance.id(),
                                sectorId=dbSector.id(),
                                name=sectorLoggingName))

                    borderStyle = dbAllegiance.borderStyle()
                    if borderStyle:
                        borderStyle = WorldManager._mapLineStyle(borderStyle)
                        if not borderStyle:
                            logging.warning('Ignoring invalid border style "{style}" for allegiance {objectId} when loading sector {sectorId} ({name})'.format(
                                style=dbAllegiance.borderStyle(),
                                objectId=dbAllegiance.id(),
                                sectorId=dbSector.id(),
                                name=sectorLoggingName))

                    allegianceIdMap[dbAllegiance.id()] = astronomer.Allegiance(
                        code=dbAllegiance.code(),
                        name=dbAllegiance.name(),
                        legacyCode=dbAllegiance.legacy(),
                        baseCode=dbAllegiance.base(),
                        routeColour=dbAllegiance.routeColour(),
                        routeStyle=routeStyle,
                        routeWidth=dbAllegiance.routeWidth(),
                        borderColour=dbAllegiance.borderColour(),
                        borderStyle=borderStyle)
                except Exception as ex:
                    logging.warning('Failed to create allegiance {objectId} when loading sector {sectorId} ({name})'.format(
                            objectId=dbAllegiance.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName),
                        exc_info=ex)

        dbSophonts = dbSector.sophonts()
        sophontIdMap: typing.Dict[str, astronomer.Sophont] = {}
        if dbSophonts:
            for dbSophont in dbSophonts:
                try:
                    sophontIdMap[dbSophont.id()] = astronomer.Sophont(
                        code=dbSophont.code(),
                        name=dbSophont.name(),
                        isMajor=dbSophont.isMajor())
                except Exception as ex:
                    logging.warning('Failed to create sophont {objectId} when loading sector {sectorId} ({name})'.format(
                            objectId=dbSophont.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName),
                        exc_info=ex)

        dbSystems = dbSector.systems()
        worlds: typing.Optional[typing.List[astronomer.World]] = None
        if dbSystems:
            worlds = []
            for dbSystem in dbSystems:
                systemName = dbSystem.name()
                systemLoggingName = '{systemName} ({hexX}, {hexY}) in {sectorString}'.format(
                    systemName=systemName if systemName else '<Unnamed System>',
                    hexX=dbSystem.hexX(),
                    hexY=dbSystem.hexY(),
                    sectorString=sectorLoggingName)

                try:
                    worldHex = astronomer.HexPosition(
                        sectorX=sectorX,
                        sectorY=sectorY,
                        offsetX=dbSystem.hexX(),
                        offsetY=dbSystem.hexY())

                    isNameGenerated = False
                    if not systemName:
                        # If the world doesn't have a name the sector combined with the hex. This format
                        # is important as it's the same format as Traveller Map meaning searches will
                        # work
                        # TODO: I don't like the fact I do this. It's done so all "worlds" (aka systems)
                        # have a name. I think the only reason to really do this is so, when they're
                        # displayed in tables and other places there is always something to show to
                        # the user (in tables name is generally the first column in the table).
                        # - Need to look to see what Traveller Map displays on map and in the info
                        # dialog for worlds that have no name (but have a non ? UWP).
                        systemName = f'{sectorName} {dbSystem.hexX():02d}{dbSystem.hexY():02d}'
                        isNameGenerated = True

                    allegianceId = dbSystem.allegianceId()
                    systemAllegiance = None
                    if allegianceId:
                        systemAllegiance = allegianceIdMap.get(allegianceId)
                        if not systemAllegiance:
                            logging.warning('Ignoring unknown allegiance {allegianceId} when loading system {systemId} in sector {sectorId} ({name})'.format(
                                allegianceId=allegianceId,
                                systemId=dbSystem.id(),
                                sectorId=dbSector.id(),
                                name=systemLoggingName))

                    dbZone = dbSystem.zone()
                    zone = None
                    if dbZone:
                        try:
                            zone = astronomer.parseZoneString(dbZone)
                        except Exception as ex:
                            logging.warning('Failed to parse zone "{zone}" when loading system {systemId} in sector {sectorId} ({name})'.format(
                                    zone=dbZone,
                                    systemId=dbSystem.id(),
                                    sectorId=dbSector.id(),
                                    name=systemLoggingName),
                                exc_info=ex)

                    dbBodies = dbSystem.bodies()
                    dbMainWorld = None
                    if dbBodies:
                        dbMainWorld = dbBodies[0]
                        if not isinstance(dbMainWorld, multiverse.DbWorld):
                            logging.warning('Ignoring {type} main world when loading system {systemId} in sector {sectorId} ({name})'.format(
                                    type=type(dbMainWorld),
                                    systemId=dbSystem.id(),
                                    sectorId=dbSector.id(),
                                    name=systemLoggingName))
                            dbMainWorld = None

                    uwp = None
                    economics = None
                    culture = None
                    nobilities = None
                    bases = None
                    tradeCodes = None
                    sophontPopulations = None
                    rulingAllegiances = None
                    owningWorldRefs = None
                    colonyWorldRefs = None
                    researchStations = None
                    customRemarks = None
                    if dbMainWorld:
                        try:
                            uwp = astronomer.UWP(
                                starport=dbMainWorld.starport(),
                                worldSize=dbMainWorld.worldSize(),
                                atmosphere=dbMainWorld.atmosphere(),
                                hydrographics=dbMainWorld.hydrographics(),
                                population=dbMainWorld.population(),
                                government=dbMainWorld.government(),
                                lawLevel=dbMainWorld.lawLevel(),
                                techLevel=dbMainWorld.techLevel())
                        except Exception as ex:
                            logging.warning('Failed to create UWP when loading system {systemId} in sector {sectorId} ({name})'.format(
                                    systemId=dbSystem.id(),
                                    sectorId=dbSector.id(),
                                    name=systemLoggingName),
                                exc_info=ex)

                        try:
                            economics = astronomer.Economics(
                                resources=dbMainWorld.resources(),
                                labour=dbMainWorld.labour(),
                                infrastructure=dbMainWorld.infrastructure(),
                                efficiency=dbMainWorld.efficiency())
                        except Exception as ex:
                            logging.warning('Failed to create economics when loading system {systemId} in sector {sectorId} ({name})'.format(
                                    systemId=dbSystem.id(),
                                    sectorId=dbSector.id(),
                                    name=systemLoggingName),
                                exc_info=ex)

                        try:
                            culture = astronomer.Culture(
                                heterogeneity=dbMainWorld.heterogeneity(),
                                acceptance=dbMainWorld.acceptance(),
                                strangeness=dbMainWorld.strangeness(),
                                symbols=dbMainWorld.symbols())
                        except Exception as ex:
                            logging.warning('Failed to create culture when loading system {systemId} in sector {sectorId} ({name})'.format(
                                    systemId=dbSystem.id(),
                                    sectorId=dbSector.id(),
                                    name=systemLoggingName),
                                exc_info=ex)

                        dbTradeCodes = dbMainWorld.tradeCodes()
                        tradeCodes: typing.Optional[typing.List[traveller.TradeCode]] = None
                        if dbTradeCodes:
                            tradeCodes = []
                            for dbTradeCode in dbTradeCodes:
                                tradeCode = traveller.tradeCode(tradeCodeString=dbTradeCode.code())
                                if not tradeCode:
                                    logging.warning('Ignoring trade code {objectId} with unknown code "{code}" when loading system {systemId} in sector {sectorId} ({name})'.format(
                                        objectId=dbTradeCode.id(),
                                        code=dbTradeCode.code(),
                                        systemId=dbSystem.id(),
                                        sectorId=dbSector.id(),
                                        name=systemLoggingName))
                                    continue
                                tradeCodes.append(tradeCode)

                        dbPopulations = dbMainWorld.sophontPopulations()
                        sophontPopulations: typing.Optional[typing.List[astronomer.SophontPopulation]] = None
                        if dbPopulations:
                            sophontPopulations = []
                            for dbPopulation in dbPopulations:
                                sophont = sophontIdMap.get(dbPopulation.sophontId())
                                if not sophont:
                                    logging.warning('Ignoring sophont population {objectId} with unknown sophont {sophontId} when loading system {systemId} in sector {sectorId} ({name})'.format(
                                        objectId=dbPopulation.id(),
                                        sophontId=dbPopulation.sophontId(),
                                        systemId=dbSystem.id(),
                                        sectorId=dbSector.id(),
                                        name=systemLoggingName))
                                    continue

                                try:
                                    sophontPopulations.append(astronomer.SophontPopulation(
                                        sophont=sophont,
                                        percentage=dbPopulation.percentage(),
                                        isHomeWorld=dbPopulation.isHomeWorld(),
                                        isDieBack=dbPopulation.isDieBack()))
                                except Exception as ex:
                                    logging.warning('Failed to create sophont population {objectId} when loading system {systemId} in sector {sectorId} ({name})'.format(
                                            objectId=dbPopulation.id(),
                                            systemId=dbSystem.id(),
                                            sectorId=dbSector.id(),
                                            name=systemLoggingName),
                                        exc_info=ex)

                        dbRulingAllegiances = dbMainWorld.rulingAllegiances()
                        rulingAllegiances: typing.Optional[typing.List[astronomer.Allegiance]] = None
                        if dbRulingAllegiances:
                            rulingAllegiances = []
                            for dbAllegiance in dbRulingAllegiances:
                                rulingAllegiance = allegianceIdMap.get(dbAllegiance.allegianceId())
                                if not rulingAllegiance:
                                    logging.warning('Ignoring ruling allegiance {objectId} with unknown allegiance {allegianceId} when loading system {systemId} in sector {sectorId} ({name})'.format(
                                        objectId=dbAllegiance.id(),
                                        allegianceId=dbAllegiance.allegianceId(),
                                        systemId=dbSystem.id(),
                                        sectorId=dbSector.id(),
                                        name=systemLoggingName))
                                    continue
                                rulingAllegiances.append(rulingAllegiance)

                        dbOwningSystems = dbMainWorld.owningSystems()
                        owningWorldRefs: typing.Optional[typing.List[astronomer.WorldReference]] = None
                        if dbOwningSystems:
                            owningWorldRefs = []
                            for dbOwningSystem in dbOwningSystems:
                                try:
                                    owningWorldRefs.append(astronomer.WorldReference(
                                        hexX=dbOwningSystem.hexX(),
                                        hexY=dbOwningSystem.hexY(),
                                        sectorAbbreviation=dbOwningSystem.sectorAbbreviation()))
                                except Exception as ex:
                                    logging.warning('Failed to create world reference for owning system {objectId} when loading system {systemId} in sector {sectorId} ({name})'.format(
                                            objectId=dbOwningSystem.id(),
                                            systemId=dbSystem.id(),
                                            sectorId=dbSector.id(),
                                            name=systemLoggingName),
                                        exc_info=ex)

                        dbColonySystems = dbMainWorld.colonySystems()
                        colonyWorldRefs: typing.Optional[typing.List[astronomer.WorldReference]] = None
                        if dbColonySystems:
                            colonyWorldRefs = []
                            for dbColonySystem in dbColonySystems:
                                try:
                                    colonyWorldRefs.append(astronomer.WorldReference(
                                        hexX=dbColonySystem.hexX(),
                                        hexY=dbColonySystem.hexY(),
                                        sectorAbbreviation=dbColonySystem.sectorAbbreviation()))
                                except Exception as ex:
                                    logging.warning('Failed to create world reference for colony system {objectId} when loading system {systemId} in sector {sectorId} ({name})'.format(
                                            objectId=dbColonySystem.id(),
                                            systemId=dbSystem.id(),
                                            sectorId=dbSector.id(),
                                            name=systemLoggingName),
                                        exc_info=ex)

                        dbResearchStations = dbMainWorld.researchStations()
                        researchStations: typing.Optional[typing.List[str]] = None
                        if dbResearchStations:
                            researchStations = [s.code() for s in dbResearchStations]

                        dbCustomRemarks = dbMainWorld.customRemarks()
                        customRemarks: typing.Optional[typing.List[str]] = None
                        if dbCustomRemarks:
                            customRemarks = [r.remark() for r in dbCustomRemarks]

                        dbNobilities = dbMainWorld.nobilities()
                        nobilityTypes = None
                        if dbNobilities:
                            nobilityTypes = []
                            for dbNobility in dbNobilities:
                                nobilityType = astronomer.codeToNobilityType(dbNobility.code())
                                if nobilityType is None:
                                    logging.warning('Ignoring nobility {objectId} with unknown code "{code}" when loading system {systemId} in sector {sectorId} ({name})'.format(
                                        objectId=dbNobility.id(),
                                        code=dbNobility.code(),
                                        systemId=dbSystem.id(),
                                        sectorId=dbSector.id(),
                                        name=systemLoggingName))
                                    continue
                                nobilityTypes.append(nobilityType)

                        try:
                            nobilities = astronomer.Nobilities(nobilities=nobilityTypes)
                        except Exception as ex:
                            logging.warning('Failed to create nobilities when loading system {systemId} in sector {sectorId} ({name})'.format(
                                    systemId=dbSystem.id(),
                                    sectorId=dbSector.id(),
                                    name=systemLoggingName),
                                exc_info=ex)

                        dbBases = dbMainWorld.bases()
                        baseTypes = None
                        if dbBases:
                            baseTypes = []
                            for dbBase in dbBases:
                                codeBaseTypes = astronomer.codeToBaseTypes(dbBase.code())
                                if codeBaseTypes is None:
                                    logging.warning('Ignoring base {objectId} with unknown code "{code}" when loading system {systemId} in sector {sectorId} ({name})'.format(
                                        objectId=dbBase.id(),
                                        code=dbBase.code(),
                                        systemId=dbSystem.id(),
                                        sectorId=dbSector.id(),
                                        name=systemLoggingName))
                                    continue
                                baseTypes.extend(codeBaseTypes)

                        try:
                            bases = astronomer.Bases(bases=baseTypes)
                        except Exception as ex:
                            logging.warning('Failed to create bases when loading system {systemId} in sector {sectorId} ({name})'.format(
                                    systemId=dbSystem.id(),
                                    sectorId=dbSector.id(),
                                    name=systemLoggingName),
                                exc_info=ex)

                    dbPopulationMultiplier = dbMainWorld.populationMultiplier() if dbMainWorld else None
                    dbPlanetoidBeltCount = dbSystem.planetoidBeltCount()
                    dbGasGiantCount = dbSystem.gasGiantCount()
                    dbOtherWorldCount = dbSystem.otherWorldCount()
                    pbg = None
                    try:
                        pbg = astronomer.PBG(
                            # Multiplier is stored as ehex code
                            populationMultiplier=dbPopulationMultiplier,
                            # Belt and giant counts need converted to an ehex code
                            planetoidBelts=survey.ehexFromInteger(dbPlanetoidBeltCount),
                            gasGiants=survey.ehexFromInteger(dbGasGiantCount))
                    except Exception as ex:
                        logging.warning('Failed to create PBG when loading system {systemId} in sector {sectorId} ({name})'.format(
                                systemId=dbSystem.id(),
                                sectorId=dbSector.id(),
                                name=systemLoggingName),
                            exc_info=ex)

                    # This code regenerates the system world count from the the original
                    # second survey data. The other world count that it uses was derived
                    # from the system world count at convert time. The aim is to keep the
                    # old logic where the number of gas giants and/or belts in a system
                    # can be known but the total number of worlds in the system can be
                    # unknown rather than known to be 0. An example of this would be
                    # Khoengu in Mugheen't. It works on the logic that the only way the
                    # other worlds count could have been calculated is the total system
                    # world count was specified in the source data. This isn't completely
                    # accurate as it ignores the fact the other world count could be null
                    # because the source data did specify a count but it was invalid (e.g.
                    # the count was lower than the gas giant and belt count specified in
                    # the PBG), however I think it would be good enough if things stay the
                    # way they are.
                    systemWorlds = None
                    if dbOtherWorldCount is not None:
                        systemWorlds = \
                            (dbPlanetoidBeltCount if dbPlanetoidBeltCount else 0) + \
                            (dbGasGiantCount if dbGasGiantCount else 0) + \
                            (dbOtherWorldCount if dbOtherWorldCount else 0) + \
                            (1 if dbMainWorld else 0) # For the main world

                    dbStars = dbSystem.stars()
                    stars = None
                    if dbStars:
                        stars = []
                        for dbStar in dbStars:
                            try:
                                stars.append(astronomer.Star(
                                    luminosityClass=dbStar.luminosityClass(),
                                    spectralClass=dbStar.spectralClass(),
                                    spectralScale=dbStar.spectralScale()))
                            except Exception as ex:
                                logging.warning('Failed to create star {objectId} when loading system {systemId} in sector {sectorId} ({name})'.format(
                                        objectId=dbStar.id(),
                                        systemId=dbSystem.id(),
                                        sectorId=dbSector.id(),
                                        name=systemLoggingName),
                                    exc_info=ex)

                    stellar = None
                    try:
                        stellar = astronomer.Stellar(stars=stars)
                    except Exception as ex:
                        logging.warning('Failed to create stellar when loading system {systemId} in sector {sectorId} ({name})'.format(
                                systemId=dbSystem.id(),
                                sectorId=dbSector.id(),
                                name=systemLoggingName),
                            exc_info=ex)

                    world = astronomer.World(
                        milieu=milieu,
                        hex=worldHex,
                        name=systemName,
                        isNameGenerated=isNameGenerated,
                        allegiance=systemAllegiance,
                        zone=zone,
                        uwp=uwp,
                        economics=economics,
                        culture=culture,
                        nobilities=nobilities,
                        bases=bases,
                        systemWorlds=systemWorlds,
                        pbg=pbg,
                        stellar=stellar,
                        tradeCodes=tradeCodes,
                        sophontPopulations=sophontPopulations,
                        rulingAllegiances=rulingAllegiances,
                        owningWorldRefs=owningWorldRefs,
                        colonyWorldRefs=colonyWorldRefs,
                        researchStations=researchStations,
                        customRemarks=customRemarks)

                    worlds.append(world)
                except Exception as ex:
                    logging.warning('Failed to load system {systemId} in sector {sectorId} ({name})'.format(
                            systemId=dbSystem.id(),
                            sectorId=dbSector.id(),
                            name=systemLoggingName),
                        exc_info=ex)

        dbRoutes = dbSector.routes()
        routes = None
        if dbRoutes:
            routes = []
            for dbRoute in dbRoutes:
                try:
                    startHex = astronomer.HexPosition(
                        sectorX=sectorX + dbRoute.startOffsetX(),
                        sectorY=sectorY + dbRoute.startOffsetY(),
                        offsetX=dbRoute.startHexX(),
                        offsetY=dbRoute.startHexY())

                    endHex = astronomer.HexPosition(
                        sectorX=sectorX + dbRoute.endOffsetX(),
                        sectorY=sectorY + dbRoute.endOffsetY(),
                        offsetX=dbRoute.endHexX(),
                        offsetY=dbRoute.endHexY())

                    colour = dbRoute.colour()
                    if colour and not common.isValidHtmlColour(htmlColour=colour):
                        logging.warning('Ignoring invalid colour "{colour}" for route {objectId} when loading sector {sectorId} ({name})'.format(
                            colour=colour,
                            objectId=dbRoute.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName))
                        colour = None

                    allegianceId = dbRoute.allegianceId()
                    routeAllegiance = None
                    if allegianceId:
                        routeAllegiance = allegianceIdMap.get(allegianceId)
                        if not routeAllegiance:
                            logging.warning('Ignoring unknown allegiance {allegianceId} for route {objectId} when loading sector {sectorId} ({name})'.format(
                                allegianceId=allegianceId,
                                objectId=dbRoute.id(),
                                sectorId=dbSector.id(),
                                name=sectorLoggingName))

                    style = dbRoute.style()
                    if style:
                        style = WorldManager._mapLineStyle(style)
                        if not style:
                            logging.warning('Ignoring invalid style "{style}" for route {objectId} when loading sector {sectorId} ({name})'.format(
                                style=dbRoute.style(),
                                objectId=dbRoute.id(),
                                sectorId=dbSector.id(),
                                name=sectorLoggingName))

                    routes.append(astronomer.Route(
                        startHex=startHex,
                        endHex=endHex,
                        allegiance=routeAllegiance,
                        type=dbRoute.type(),
                        style=style,
                        colour=colour,
                        width=dbRoute.width()))
                except Exception as ex:
                    logging.warning('Failed to create route {objectId} when loading sector {sectorId} ({name})'.format(
                            objectId=dbRoute.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName),
                        exc_info=ex)

        dbBorders = dbSector.borders()
        borders = None
        if dbBorders:
            borders = []
            for dbBorder in dbBorders:
                try:
                    hexes = []
                    for hexX, hexY in dbBorder.hexes():
                        hexes.append(astronomer.HexPosition(
                            sectorX=sectorX,
                            sectorY=sectorY,
                            offsetX=hexX,
                            offsetY=hexY))

                    colour = dbBorder.colour()
                    if colour and not common.isValidHtmlColour(htmlColour=colour):
                        logging.warning('Ignoring invalid colour "{colour}" for border {objectId} when loading sector {sectorId} ({name})'.format(
                            colour=colour,
                            objectId=dbBorder.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName))
                        colour = None

                    allegianceId = dbBorder.allegianceId()
                    borderAllegiance = None
                    if allegianceId:
                        borderAllegiance = allegianceIdMap.get(allegianceId)
                        if not borderAllegiance:
                            logging.warning('Ignoring unknown allegiance code {allegianceId} for border {objectId} when loading sector {sectorId} ({name})'.format(
                                allegianceId=allegianceId,
                                objectId=dbBorder.id(),
                                sectorId=dbSector.id(),
                                name=sectorLoggingName))

                    style = dbBorder.style()
                    if style:
                        style = WorldManager._mapLineStyle(style)
                        if not style:
                            logging.warning('Ignoring invalid style "{style}" for border {objectId} when loading sector {sectorId} ({name})'.format(
                                style=dbBorder.style(),
                                objectId=dbBorder.id(),
                                sectorId=dbSector.id(),
                                name=sectorLoggingName))

                    borders.append(astronomer.Border(
                        hexList=hexes,
                        allegiance=borderAllegiance,
                        style=style,
                        colour=colour,
                        label=dbBorder.label(),
                        labelWorldX=dbBorder.labelWorldX(),
                        labelWorldY=dbBorder.labelWorldY(),
                        showLabel=dbBorder.showLabel(),
                        wrapLabel=dbBorder.wrapLabel()))
                except Exception as ex:
                    logging.warning('Failed to create border {objectId} when loading sector {sectorId} ({name})'.format(
                            objectId=dbBorder.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName),
                        exc_info=ex)

        dbRegions = dbSector.regions()
        regions = None
        if dbRegions:
            regions = []
            for dbRegion in dbRegions:
                try:
                    hexes = []
                    for hexX, hexY in dbRegion.hexes():
                        hexes.append(astronomer.HexPosition(
                            sectorX=sectorX,
                            sectorY=sectorY,
                            offsetX=hexX,
                            offsetY=hexY))

                    colour = dbRegion.colour()
                    if colour and not common.isValidHtmlColour(htmlColour=colour):
                        logging.warning('Ignoring invalid colour "{colour}" for region {objectId} when loading sector {sectorId} ({name})'.format(
                            colour=colour,
                            objectId=dbRegion.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName))
                        colour = None

                    regions.append(astronomer.Region(
                        hexList=hexes,
                        colour=colour,
                        label=dbRegion.label(),
                        labelWorldX=dbRegion.labelWorldX(),
                        labelWorldY=dbRegion.labelWorldY(),
                        showLabel=dbRegion.showLabel(),
                        wrapLabel=dbRegion.wrapLabel()))
                except Exception as ex:
                    logging.warning('Failed to create region {objectId} when loading sector {sectorId} ({name})'.format(
                            objectId=dbRegion.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName),
                        exc_info=ex)

        dbLabels = dbSector.labels()
        labels = None
        if dbLabels:
            labels = []
            for dbLabel in dbLabels:
                try:
                    colour = dbLabel.colour()
                    if colour and not common.isValidHtmlColour(htmlColour=colour):
                        logging.warning('Ignoring invalid colour "{colour}" for label {objectId} when loading sector {sectorId} ({name})'.format(
                            colour=colour,
                            objectId=dbLabel.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName))
                        colour = None

                    size = dbLabel.size()
                    if size:
                        size = WorldManager._mapLabelSize(size)
                        if not size:
                            logging.warning('Ignoring invalid size "{size}" for label {objectId} when loading sector {sectorId} ({name})'.format(
                                size=dbLabel.size(),
                                objectId=dbLabel.id(),
                                sectorId=dbSector.id(),
                                name=sectorLoggingName))

                    labels.append(astronomer.Label(
                        text=dbLabel.text(),
                        worldX=dbLabel.worldX(),
                        worldY=dbLabel.worldY(),
                        colour=colour,
                        size=size,
                        wrap=dbLabel.wrap()))
                except Exception as ex:
                    logging.warning('Failed to create label {objectId} when loading sector {sectorId} ({name})'.format(
                            objectId=dbLabel.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName),
                        exc_info=ex)

        dbTags = dbSector.tags()
        tagging = None
        if dbTags:
            tags = []
            for dbTag in dbTags:
                tag = astronomer.stringToSectorTag(dbTag.tag())
                if not tag:
                    # NOTE: This is disabled as it's very spammy
                    #logging.warning('Ignoring sector tag {objectId} with unknown value "{value}" when loading sector {sectorId} ({name})'.format(
                    #    objectId=dbTag.id(),
                    #    value=dbTag.tag(),
                    #    sectorId=dbSector.id(),
                    #    name=sectorLoggingName))
                    continue
                tags.append(tag)

            try:
                tagging = astronomer.SectorTagging(tags=tags)
            except Exception as ex:
                logging.warning('Failed to create sector tagging when loading sector {sectorId} ({name})'.format(
                        sectorId=dbSector.id(),
                        name=sectorLoggingName),
                    exc_info=ex)

        dbPublication = dbSector.publication()
        dbAuthor = dbSector.author()
        dbPublisher = dbSector.publisher()
        dbReference = dbSector.reference()
        source = None
        if dbPublication or dbAuthor or dbPublisher or dbReference:
            try:
                source = astronomer.SectorSource(
                    publication=dbPublication,
                    author=dbAuthor,
                    publisher=dbPublisher,
                    reference=dbReference)
            except Exception as ex:
                logging.warning('Failed to create primary source when loading sector {sectorId} ({name})'.format(
                        sectorId=dbSector.id(),
                        name=sectorLoggingName),
                    exc_info=ex)

        dbProducts = dbSector.products()
        products = None
        if dbProducts:
            products = []
            for dbProduct in dbProducts:
                try:
                    products.append(astronomer.SectorSource(
                        publication=dbProduct.publication(),
                        author=dbProduct.author(),
                        publisher=dbProduct.publisher(),
                        reference=dbProduct.reference()))
                except Exception as ex:
                    logging.warning('Failed to create source {objectId} when loading sector {sectorId} ({name})'.format(
                            objectId=dbProduct.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName),
                        exc_info=ex)

        return astronomer.Sector(
            isCustom=isCustom,
            name=sectorName,
            milieu=milieu,
            position=astronomer.SectorPosition(sectorX=sectorX, sectorY=sectorY),
            alternateNames=alternateNames,
            abbreviation=dbSector.abbreviation(),
            sectorLabel=dbSector.sectorLabel(),
            subsectorNames=subsectorNameMap,
            worlds=worlds,
            allegiances=allegianceIdMap.values(),
            sophonts=sophontIdMap.values(),
            routes=routes,
            borders=borders,
            regions=regions,
            labels=labels,
            selected=dbSector.selected(),
            tagging=tagging,
            credits=dbSector.credits(),
            source=source,
            products=products)

    @staticmethod
    def _mapMilieu(milieu: str) -> typing.Optional[astronomer.Milieu]:
        if milieu not in astronomer.Milieu:
            return None
        return astronomer.Milieu[milieu]

    _LineStyleMap = {
        'solid': astronomer.LineStyle.Solid,
        'dashed': astronomer.LineStyle.Dashed,
        'dotted': astronomer.LineStyle.Dotted,
    }

    @staticmethod
    def _mapLineStyle(
            style: typing.Optional[str]
            ) -> typing.Optional[astronomer.LineStyle]:
        if not style:
            return None
        lowerStyle = style.lower()
        mappedStyle = WorldManager._LineStyleMap.get(lowerStyle)
        if not mappedStyle:
            return None
        return mappedStyle

    _LabelSizeMap = {
        'small': astronomer.Label.Size.Small,
        'large': astronomer.Label.Size.Large,
    }

    @staticmethod
    def _mapLabelSize(
            size: typing.Optional[str]
            ) -> typing.Optional[astronomer.Label.Size]:
        if not size:
            return None
        lowerSize = size.lower()
        mappedSize = WorldManager._LabelSizeMap.get(lowerSize)
        if not mappedSize:
            None
        return mappedSize
