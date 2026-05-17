import astronomer
import common
import logging
import multiverse
import survey
import traveller
import typing

def _mapDbMilieuToAstronomerMilieu(milieu: str) -> typing.Optional[astronomer.Milieu]:
    if milieu not in astronomer.Milieu:
        return None
    return astronomer.Milieu[milieu]

def _mapAstronomerMilieuToDbMilieu(milieu: astronomer.Milieu) -> str:
    return milieu.value

_DbToAstronomerLineStyleMap = {
    'solid': astronomer.LineStyle.Solid,
    'dashed': astronomer.LineStyle.Dashed,
    'dotted': astronomer.LineStyle.Dotted}
def _mapDbLineStyleToAstronomerLineStyle(
        style: typing.Optional[str]
        ) -> typing.Optional[astronomer.LineStyle]:
    if not style:
        return None
    lowerStyle = style.lower()
    mappedStyle = _DbToAstronomerLineStyleMap.get(lowerStyle)
    if not mappedStyle:
        return None
    return mappedStyle

_AstronomerToDbLineStyleMap = {v: k for k, v in _DbToAstronomerLineStyleMap.items()}
def _mapAstronomerLineStyleToDbLineStyle(
        style: typing.Optional[astronomer.LineStyle]
        ) -> typing.Optional[str]:
    return _AstronomerToDbLineStyleMap.get(style)

_DbToAstronomerLabelSizeMap = {
    'small': astronomer.Label.Size.Small,
    'large': astronomer.Label.Size.Large}
def _mapDbLabelSizeToAstronomerLabelSize(
        size: typing.Optional[str]
        ) -> typing.Optional[astronomer.Label.Size]:
    if not size:
        return None
    lowerSize = size.lower()
    mappedSize = _DbToAstronomerLabelSizeMap.get(lowerSize)
    if not mappedSize:
        None
    return mappedSize

_AstronomerToDbLabelSizeMap = {v: k for k, v in _DbToAstronomerLabelSizeMap.items()}
def _mapAstronomerLabelSizeToDbLabelSize(
        size: astronomer.Label.Size
        ) -> typing.Optional[str]:
    return _AstronomerToDbLabelSizeMap.get(size)

def _createAstronomerAlternateNames(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[str]]:
    dbAlternateNames = dbSector.alternateNames()
    astroAlternateNames: typing.Optional[typing.List[str]] = []
    if dbAlternateNames:
        for dbAlternateName in dbAlternateNames:
            astroAlternateNames.append(dbAlternateName.name())
    return astroAlternateNames

def _createAstronomerSubsectorNames(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.Dict[
            str, # Subsector code (A-P)
            str]]:
    dbSubsectorNames = dbSector.subsectorNames()
    astronomerSubsectorNames: typing.Optional[typing.Dict[
        str, # Subsector code (A-P)
        str]] = {}

    if dbSubsectorNames:
        for dbSubsectorName in dbSubsectorNames:
            # NOTE: Unlike most other places, it's intentional that this is upper case
            astronomerSubsectorNames[dbSubsectorName.code()] = dbSubsectorName.name()
    return astronomerSubsectorNames

def _createAstronomerAllegiances(
        dbSector: multiverse.DbSector,
        sectorLogName: str
        ) -> typing.Dict[
            str, # Allegiance Id
            astronomer.Allegiance]:
    dbAllegiances = dbSector.allegiances()
    dbIdToAstroAllegianceMap: typing.Dict[str, astronomer.Allegiance] = {}
    if dbAllegiances:
        for dbAllegiance in dbAllegiances:
            try:
                routeStyle = dbAllegiance.routeStyle()
                if routeStyle:
                    routeStyle = _mapDbLineStyleToAstronomerLineStyle(routeStyle)
                    if not routeStyle:
                        logging.warning('Ignoring invalid route style "{style}" for allegiance {objectId} when loading sector {sectorId} ({name})'.format(
                            style=dbAllegiance.routeStyle(),
                            objectId=dbAllegiance.id(),
                            sectorId=dbSector.id(),
                            name=sectorLogName))

                borderStyle = dbAllegiance.borderStyle()
                if borderStyle:
                    borderStyle = _mapDbLineStyleToAstronomerLineStyle(borderStyle)
                    if not borderStyle:
                        logging.warning('Ignoring invalid border style "{style}" for allegiance {objectId} when loading sector {sectorId} ({name})'.format(
                            style=dbAllegiance.borderStyle(),
                            objectId=dbAllegiance.id(),
                            sectorId=dbSector.id(),
                            name=sectorLogName))

                dbIdToAstroAllegianceMap[dbAllegiance.id()] = astronomer.Allegiance(
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
                        name=sectorLogName),
                    exc_info=ex)

    return dbIdToAstroAllegianceMap

def _createAstronomerSophonts(
        dbSector: multiverse.DbSector,
        sectorLogName: str
        ) -> typing.Dict[
            str, # Sophont Id
            astronomer.Sophont]:
    dbSophonts = dbSector.sophonts()
    dbIdToAstroSophontMap: typing.Dict[str, astronomer.Sophont] = {}
    if dbSophonts:
        for dbSophont in dbSophonts:
            try:
                dbIdToAstroSophontMap[dbSophont.id()] = astronomer.Sophont(
                    code=dbSophont.code(),
                    name=dbSophont.name(),
                    isMajor=dbSophont.isMajor())
            except Exception as ex:
                logging.warning('Failed to create sophont {objectId} when loading sector {sectorId} ({name})'.format(
                        objectId=dbSophont.id(),
                        sectorId=dbSector.id(),
                        name=sectorLogName),
                    exc_info=ex)

    return dbIdToAstroSophontMap

def _createAstronomerWorlds(
        dbSector: multiverse.DbSector,
        milieu: astronomer.Milieu,
        dbIdToAstroAllegianceMap: typing.Mapping[str, astronomer.Allegiance],
        dbIdToAstroSophontMap: typing.Mapping[str, astronomer.Sophont],
        entityFactory: astronomer.EntityFactoryInterface,
        sectorLogName: str
        ) -> typing.List[astronomer.World]:
    dbSystems = dbSector.systems()
    astroWorlds: typing.List[astronomer.World] = []
    if dbSystems:
        for dbSystem in dbSystems:
            systemName = dbSystem.name()
            systemLoggingName = '{systemName} ({hexX}, {hexY}) in {sectorString}'.format(
                systemName=systemName if systemName else '<Unnamed System>',
                hexX=dbSystem.hexX(),
                hexY=dbSystem.hexY(),
                sectorString=sectorLogName)

            try:
                worldHex = astronomer.HexPosition(
                    sectorX=dbSector.sectorX(),
                    sectorY=dbSector.sectorY(),
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
                    systemName = f'{dbSector.name()} {dbSystem.hexX():02d}{dbSystem.hexY():02d}'
                    isNameGenerated = True

                allegianceId = dbSystem.allegianceId()
                systemAllegiance = None
                if allegianceId:
                    systemAllegiance = dbIdToAstroAllegianceMap.get(allegianceId)
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
                            sophont = dbIdToAstroSophontMap.get(dbPopulation.sophontId())
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
                            rulingAllegiance = dbIdToAstroAllegianceMap.get(dbAllegiance.allegianceId())
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
                dbWorldCount = dbSystem.worldCount()
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
                if dbWorldCount is not None:
                    systemWorlds = \
                        (dbPlanetoidBeltCount if dbPlanetoidBeltCount else 0) + \
                        (dbGasGiantCount if dbGasGiantCount else 0) + \
                        (dbWorldCount if dbWorldCount else 0)

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

                world = entityFactory.createWorld(
                    entityId=dbSystem.id(),
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

                astroWorlds.append(world)
            except Exception as ex:
                logging.warning('Failed to load system {systemId} in sector {sectorId} ({name})'.format(
                        systemId=dbSystem.id(),
                        sectorId=dbSector.id(),
                        name=systemLoggingName),
                    exc_info=ex)

    return astroWorlds

def _createAstronomerRoutes(
        dbSector: multiverse.DbSector,
        dbIdToAstroAllegianceMap: typing.Mapping[str, astronomer.Allegiance],
        entityFactory: astronomer.EntityFactoryInterface,
        sectorLogName: str
        ) -> typing.List[astronomer.Route]:
    dbRoutes = dbSector.routes()
    astroRoutes: typing.List[astronomer.Route] = []
    if dbRoutes:
        for dbRoute in dbRoutes:
            try:
                startHex = astronomer.HexPosition(
                    sectorX=dbSector.sectorX() + dbRoute.startOffsetX(),
                    sectorY=dbSector.sectorY() + dbRoute.startOffsetY(),
                    offsetX=dbRoute.startHexX(),
                    offsetY=dbRoute.startHexY())

                endHex = astronomer.HexPosition(
                    sectorX=dbSector.sectorX() + dbRoute.endOffsetX(),
                    sectorY=dbSector.sectorY() + dbRoute.endOffsetY(),
                    offsetX=dbRoute.endHexX(),
                    offsetY=dbRoute.endHexY())

                colour = dbRoute.colour()
                if colour and not common.isValidHtmlColour(htmlColour=colour):
                    logging.warning('Ignoring invalid colour "{colour}" for route {objectId} when loading sector {sectorId} ({name})'.format(
                        colour=colour,
                        objectId=dbRoute.id(),
                        sectorId=dbSector.id(),
                        name=sectorLogName))
                    colour = None

                allegianceId = dbRoute.allegianceId()
                routeAllegiance = None
                if allegianceId:
                    routeAllegiance = dbIdToAstroAllegianceMap.get(allegianceId)
                    if not routeAllegiance:
                        logging.warning('Ignoring unknown allegiance {allegianceId} for route {objectId} when loading sector {sectorId} ({name})'.format(
                            allegianceId=allegianceId,
                            objectId=dbRoute.id(),
                            sectorId=dbSector.id(),
                            name=sectorLogName))

                style = dbRoute.style()
                if style:
                    style = _mapDbLineStyleToAstronomerLineStyle(style)
                    if not style:
                        logging.warning('Ignoring invalid style "{style}" for route {objectId} when loading sector {sectorId} ({name})'.format(
                            style=dbRoute.style(),
                            objectId=dbRoute.id(),
                            sectorId=dbSector.id(),
                            name=sectorLogName))

                astroRoutes.append(entityFactory.createRoute(
                    entityId=dbRoute.id(),
                    startHex=startHex,
                    endHex=endHex,
                    allegiance=routeAllegiance,
                    routeType=dbRoute.type(),
                    style=style,
                    colour=colour,
                    width=dbRoute.width()))
            except Exception as ex:
                logging.warning('Failed to create route {objectId} when loading sector {sectorId} ({name})'.format(
                        objectId=dbRoute.id(),
                        sectorId=dbSector.id(),
                        name=sectorLogName),
                    exc_info=ex)

    return astroRoutes

def _createAstronomerBorders(
        dbSector: multiverse.DbSector,
        dbIdToAstroAllegianceMap: typing.Mapping[str, astronomer.Allegiance],
        entityFactory: astronomer.EntityFactoryInterface,
        sectorLogName: str
        ) -> typing.List[astronomer.Border]:
    dbBorders = dbSector.borders()
    astroBorders: typing.List[astronomer.Border] = []
    if dbBorders:
        for dbBorder in dbBorders:
            try:
                hexes = []
                for hexX, hexY in dbBorder.hexes():
                    hexes.append(astronomer.HexPosition(
                        sectorX=dbSector.sectorX(),
                        sectorY=dbSector.sectorY(),
                        offsetX=hexX,
                        offsetY=hexY))

                colour = dbBorder.colour()
                if colour and not common.isValidHtmlColour(htmlColour=colour):
                    logging.warning('Ignoring invalid colour "{colour}" for border {objectId} when loading sector {sectorId} ({name})'.format(
                        colour=colour,
                        objectId=dbBorder.id(),
                        sectorId=dbSector.id(),
                        name=sectorLogName))
                    colour = None

                allegianceId = dbBorder.allegianceId()
                borderAllegiance = None
                if allegianceId:
                    borderAllegiance = dbIdToAstroAllegianceMap.get(allegianceId)
                    if not borderAllegiance:
                        logging.warning('Ignoring unknown allegiance code {allegianceId} for border {objectId} when loading sector {sectorId} ({name})'.format(
                            allegianceId=allegianceId,
                            objectId=dbBorder.id(),
                            sectorId=dbSector.id(),
                            name=sectorLogName))

                style = dbBorder.style()
                if style:
                    style = _mapDbLineStyleToAstronomerLineStyle(style)
                    if not style:
                        logging.warning('Ignoring invalid style "{style}" for border {objectId} when loading sector {sectorId} ({name})'.format(
                            style=dbBorder.style(),
                            objectId=dbBorder.id(),
                            sectorId=dbSector.id(),
                            name=sectorLogName))

                astroBorders.append(entityFactory.createBorder(
                    entityId=dbBorder.id(),
                    hexes=hexes,
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
                        name=sectorLogName),
                    exc_info=ex)

    return astroBorders

def _createAstronomerRegions(
        dbSector: multiverse.DbSector,
        entityFactory: astronomer.EntityFactoryInterface,
        sectorLogName: str
        ) -> typing.List[astronomer.Region]:
    dbRegions = dbSector.regions()
    astroRegions: typing.List[astronomer.Region] = []
    if dbRegions:
        for dbRegion in dbRegions:
            try:
                hexes = []
                for hexX, hexY in dbRegion.hexes():
                    hexes.append(astronomer.HexPosition(
                        sectorX=dbSector.sectorX(),
                        sectorY=dbSector.sectorY(),
                        offsetX=hexX,
                        offsetY=hexY))

                colour = dbRegion.colour()
                if colour and not common.isValidHtmlColour(htmlColour=colour):
                    logging.warning('Ignoring invalid colour "{colour}" for region {objectId} when loading sector {sectorId} ({name})'.format(
                        colour=colour,
                        objectId=dbRegion.id(),
                        sectorId=dbSector.id(),
                        name=sectorLogName))
                    colour = None

                astroRegions.append(entityFactory.createRegion(
                    entityId=dbRegion.id(),
                    hexes=hexes,
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
                        name=sectorLogName),
                    exc_info=ex)

    return astroRegions

def _createAstronomerLabels(
        dbSector: multiverse.DbSector,
        entityFactory: astronomer.EntityFactoryInterface,
        sectorLogName: str
        ) -> typing.List[astronomer.Label]:
    dbLabels = dbSector.labels()
    astroLabels: typing.List[astronomer.Label] = []
    if dbLabels:
        for dbLabel in dbLabels:
            try:
                colour = dbLabel.colour()
                if colour and not common.isValidHtmlColour(htmlColour=colour):
                    logging.warning('Ignoring invalid colour "{colour}" for label {objectId} when loading sector {sectorId} ({name})'.format(
                        colour=colour,
                        objectId=dbLabel.id(),
                        sectorId=dbSector.id(),
                        name=sectorLogName))
                    colour = None

                size = dbLabel.size()
                if size:
                    size = _mapDbLabelSizeToAstronomerLabelSize(size)
                    if not size:
                        logging.warning('Ignoring invalid size "{size}" for label {objectId} when loading sector {sectorId} ({name})'.format(
                            size=dbLabel.size(),
                            objectId=dbLabel.id(),
                            sectorId=dbSector.id(),
                            name=sectorLogName))

                astroLabels.append(entityFactory.createLabel(
                    entityId=dbLabel.id(),
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
                        name=sectorLogName),
                    exc_info=ex)

    return astroLabels

def _createAstronomerTagging(
        dbSector: multiverse.DbSector,
        sectorLogName: str
        ) -> typing.Optional[astronomer.SectorTagging]:
    dbTags = dbSector.tags()
    astroTagging = None
    if dbTags:
        astroTags = []
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
            astroTags.append(tag)

        try:
            astroTagging = astronomer.SectorTagging(tags=astroTags)
        except Exception as ex:
            logging.warning('Failed to create sector tagging when loading sector {sectorId} ({name})'.format(
                    sectorId=dbSector.id(),
                    name=sectorLogName),
                exc_info=ex)

    return astroTagging

def _createAstronomerSource(
        dbSector: multiverse.DbSector,
        sectorLogName: str
        ) -> typing.Optional[astronomer.SectorSource]:
    dbPublication = dbSector.publication()
    dbAuthor = dbSector.author()
    dbPublisher = dbSector.publisher()
    dbReference = dbSector.reference()
    astroSource = None
    if dbPublication or dbAuthor or dbPublisher or dbReference:
        try:
            astroSource = astronomer.SectorSource(
                publication=dbPublication,
                author=dbAuthor,
                publisher=dbPublisher,
                reference=dbReference)
        except Exception as ex:
            logging.warning('Failed to create primary source when loading sector {sectorId} ({name})'.format(
                    sectorId=dbSector.id(),
                    name=sectorLogName),
                exc_info=ex)

    return astroSource

def _createAstronomerProducts(
        dbSector: multiverse.DbSector,
        sectorLogName: str
        ) -> typing.Optional[typing.List[astronomer.SectorSource]]:
    dbProducts = dbSector.products()
    astroProducts = None
    if dbProducts:
        astroProducts = []
        for dbProduct in dbProducts:
            try:
                astroProducts.append(astronomer.SectorSource(
                    publication=dbProduct.publication(),
                    author=dbProduct.author(),
                    publisher=dbProduct.publisher(),
                    reference=dbProduct.reference()))
            except Exception as ex:
                logging.warning('Failed to create source {objectId} when loading sector {sectorId} ({name})'.format(
                        objectId=dbProduct.id(),
                        sectorId=dbSector.id(),
                        name=sectorLogName),
                    exc_info=ex)

    return astroProducts

def convertDbSectorToAstronomerSector(
        dbSector: multiverse.DbSector,
        isCustom: bool,
        entityFactory: typing.Optional[astronomer.EntityFactoryInterface] = None
        ) -> astronomer.Sector:
    if entityFactory is None:
        entityFactory = astronomer.DefaultEntityFactory()

    sectorName = dbSector.name()
    sectorX = dbSector.sectorX()
    sectorY = dbSector.sectorY()

    milieu = _mapDbMilieuToAstronomerMilieu(dbSector.milieu())
    if not milieu:
        raise ValueError(f'Unknown milieu "{dbSector.milieu()}"')

    sectorLogName = '{sectorName} ({sectorX}, {sectorY}) from {milieu}'.format(
        sectorName=sectorName if sectorName else '<Unnamed Sector>',
        sectorX=sectorX,
        sectorY=sectorY,
        milieu=milieu.value)

    astroAlternateNames = _createAstronomerAlternateNames(dbSector=dbSector)

    astroSubsectorNames = _createAstronomerSubsectorNames(dbSector=dbSector)

    dbIdToAstroAllegianceMap = _createAstronomerAllegiances(
        dbSector=dbSector,
        sectorLogName=sectorLogName)

    dbIdToAstroSophontMap = _createAstronomerSophonts(
        dbSector=dbSector,
        sectorLogName=sectorLogName)

    astroWorlds = _createAstronomerWorlds(
        dbSector=dbSector,
        milieu=milieu,
        dbIdToAstroAllegianceMap=dbIdToAstroAllegianceMap,
        dbIdToAstroSophontMap=dbIdToAstroSophontMap,
        entityFactory=entityFactory,
        sectorLogName=sectorLogName)

    astroRoutes = _createAstronomerRoutes(
        dbSector=dbSector,
        dbIdToAstroAllegianceMap=dbIdToAstroAllegianceMap,
        entityFactory=entityFactory,
        sectorLogName=sectorLogName)

    astroBorders = _createAstronomerBorders(
        dbSector=dbSector,
        dbIdToAstroAllegianceMap=dbIdToAstroAllegianceMap,
        entityFactory=entityFactory,
        sectorLogName=sectorLogName)

    astroRegions = _createAstronomerRegions(
        dbSector=dbSector,
        entityFactory=entityFactory,
        sectorLogName=sectorLogName)

    astroLabels = _createAstronomerLabels(
        dbSector=dbSector,
        entityFactory=entityFactory,
        sectorLogName=sectorLogName)

    astroTagging = _createAstronomerTagging(
        dbSector=dbSector,
        sectorLogName=sectorLogName)

    astroSource = _createAstronomerSource(
        dbSector=dbSector,
        sectorLogName=sectorLogName)

    astroProducts = _createAstronomerProducts(
        dbSector=dbSector,
        sectorLogName=sectorLogName)

    return entityFactory.createSector(
        entityId=dbSector.id(),
        isCustom=isCustom,
        name=sectorName,
        milieu=milieu,
        position=astronomer.SectorPosition(sectorX=sectorX, sectorY=sectorY),
        alternateNames=astroAlternateNames,
        abbreviation=dbSector.abbreviation(),
        sectorLabel=dbSector.sectorLabel(),
        subsectorNames=astroSubsectorNames,
        worlds=astroWorlds,
        allegiances=dbIdToAstroAllegianceMap.values(),
        sophonts=dbIdToAstroSophontMap.values(),
        routes=astroRoutes,
        borders=astroBorders,
        regions=astroRegions,
        labels=astroLabels,
        selected=dbSector.selected(),
        tagging=astroTagging,
        credits=dbSector.credits(),
        source=astroSource,
        products=astroProducts)

def convertRawSectorToAstronomerSector(
        milieu: astronomer.Milieu,
        rawMetadata: survey.RawMetadata,
        rawSystems: typing.Collection[survey.RawWorld],
        isCustom: bool,
        rawStockAllegiances: typing.Optional[typing.Collection[survey.RawStockAllegiance]] = None,
        rawStockSophonts: typing.Optional[typing.Collection[survey.RawStockSophont]] = None,
        rawStockStyleSheet: typing.Optional[survey.RawStyleSheet] = None,
        entityFactory: typing.Optional[astronomer.EntityFactoryInterface] = None,
        sectorId: typing.Optional[str] = None
        ) -> astronomer.Sector:
    dbSector = multiverse.convertRawSectorToDbSector(
        milieu=milieu.name,
        rawMetadata=rawMetadata,
        rawSystems=rawSystems,
        rawStockAllegiances=rawStockAllegiances,
        rawStockSophonts=rawStockSophonts,
        rawStockStyleSheet=rawStockStyleSheet,
        sectorId=sectorId)
    return convertDbSectorToAstronomerSector(
        dbSector=dbSector,
        isCustom=isCustom,
        entityFactory=entityFactory)

def _createDbAlternateNames(
        astroSector: astronomer.Sector,
        sectorLogName: str
        ) -> typing.List[multiverse.DbAlternateName]:
    dbAlternateNames: typing.List[multiverse.DbAlternateName] = []
    for name in astroSector.alternateNames():
        try:
            dbAlternateNames.append(multiverse.DbAlternateName(
                name=name,
                # TODO: I'm loosing the language because it's not stored in the
                # astronomer model
                language=None))
        except Exception as ex:
            pass # TODO: Log something
    return dbAlternateNames

def _createDbSubsectorNames(
        astroSector: astronomer.Sector,
        sectorLogName: str
        ) -> typing.List[multiverse.DbSubsectorName]:
    dbSubsectorNames: typing.List[multiverse.DbSubsectorName] = []
    for code in map(chr, range(ord('A'), ord('P') + 1)):
        try:
            name = astroSector.subsectorName(code)
            if name is None:
                continue
            dbSubsectorNames.append(multiverse.DbSubsectorName(
                code=code,
                name=name))
        except Exception as ex:
            pass # TODO: Log something
    return dbSubsectorNames

def _createDbAllegiances(
        astroSector: astronomer.Sector,
        sectorLogName: str
        ) -> typing.Dict[astronomer.Allegiance, multiverse.DbAllegiance]:
    astroAllegianceToDbAllegianceMap: typing.Dict[astronomer.Allegiance, multiverse.DbAllegiance] = {}
    for astroAllegiance in astroSector.allegiances():
        try:
            dbRouteStyle = None
            if astroAllegiance.routeStyle():
                dbRouteStyle = _mapAstronomerLineStyleToDbLineStyle(astroAllegiance.routeStyle())
                if dbRouteStyle is None:
                    pass # TODO: Log something

            dbBorderStyle = None
            if astroAllegiance.borderStyle():
                dbBorderStyle = _mapAstronomerLineStyleToDbLineStyle(astroAllegiance.borderStyle())
                if dbBorderStyle is None:
                    pass # TODO: Log something

            astroAllegianceToDbAllegianceMap[astroAllegiance] = multiverse.DbAllegiance(
                code=astroAllegiance.code(),
                name=astroAllegiance.name(),
                legacy=astroAllegiance.legacyCode(),
                base=astroAllegiance.baseCode(),
                routeColour=astroAllegiance.routeColour(),
                routeStyle=dbRouteStyle,
                routeWidth=astroAllegiance.routeWidth(),
                borderColour=astroAllegiance.borderColour(),
                borderStyle=dbBorderStyle)
        except Exception as ex:
            pass # TODO: Log something

    return astroAllegianceToDbAllegianceMap

def _createDbSophonts(
        astroSector: astronomer.Sector,
        sectorLogName: str
        ) -> typing.Dict[astronomer.Sophont, multiverse.DbSophont]:
    astroSophontToDbSophontMap: typing.Dict[astronomer.Sophont, multiverse.DbSophont] = {}
    for astroSophont in astroSector.sophonts():
        try:
            astroSophontToDbSophontMap[astroSophont] = multiverse.DbSophont(
                code=astroSophont.code(),
                name=astroSophont.name(),
                isMajor=astroSophont.isMajor())
        except Exception as ex:
            pass # TODO: Log something

    return astroSophontToDbSophontMap

def _createDbSystems(
        astroSector: astronomer.Sector,
        astroAllegianceToDbAllegianceMap: typing.Mapping[astronomer.Allegiance, multiverse.DbAllegiance],
        astroSophontToDbSophontMap: typing.Mapping[astronomer.Sophont, multiverse.DbSophont],
        sectorLogName: str
        ) -> typing.List[multiverse.DbSystem]:
    dbSystems: typing.List[multiverse.DbSystem] = []
    for world in astroSector.worlds():
        try:
            hexPos = world.hex()

            dbSystemAllegiance = astroAllegianceToDbAllegianceMap.get(world.allegiance())
            if dbSystemAllegiance is None:
                pass # TODO: Log something

            stellar = world.stellar()
            dbStars: typing.List[multiverse.DbStar] = []
            for star in stellar.stars():
                try:
                    dbStars.append(multiverse.DbStar(
                        luminosityClass=star.code(astronomer.Star.Element.LuminosityClass),
                        spectralClass=star.code(astronomer.Star.Element.SpectralClass),
                        spectralScale=star.code(astronomer.Star.Element.SpectralScale)))
                except Exception as ex:
                    print(ex)
                    pass # TODO: Log something

            nobilities = world.nobilities()
            dbNobilities: typing.List[multiverse.DbNobility] = []
            for nobilityType in astronomer.NobilityType:
                try:
                    if not nobilities.hasNobility(nobilityType):
                        continue
                    dbNobilities.append(multiverse.DbNobility(
                        code=nobilities.code(nobilityType)))
                except Exception as ex:
                    print(ex)
                    pass # TODO: Log something

            bases = world.bases()
            dbBases: typing.List[multiverse.DbBase] = []
            for baseType in astronomer.BaseType:
                try:
                    if not bases.hasBase(baseType):
                        continue
                    dbBases.append(multiverse.DbBase(
                        code=bases.code(baseType)))
                except Exception as ex:
                    print(ex)
                    pass # TODO: Log something

            dbTradeCodes: typing.List[multiverse.DbTradeCode] = []
            for tradeCode in world.tradeCodes():
                try:
                    dbTradeCodes.append(multiverse.DbTradeCode(
                        code=traveller.tradeCodeString(tradeCode)))
                except Exception as ex:
                    print(ex)
                    pass # TODO: Log something

            dbSophontPopulations: typing.List[multiverse.DbSophontPopulation] = []
            for population in world.sophonts():
                try:
                    dbSophont = astroSophontToDbSophontMap.get(population.sophont())
                    if dbSophont is None:
                        # TODO: Log something
                        continue

                    dbSophontPopulations.append(multiverse.DbSophontPopulation(
                        sophontId=dbSophont.id(),
                        percentage=population.percentage(),
                        isHomeWorld=population.isHomeWorld(),
                        isDieBack=population.isDieBack()))
                except Exception as ex:
                    print(ex)
                    pass # TODO: Log something

            dbRulingAllegiances: typing.List[multiverse.DbRulingAllegiance] = []
            for allegiance in world.rulingAllegiances():
                try:
                    dbRulingAllegiance = astroAllegianceToDbAllegianceMap.get(allegiance)
                    if dbRulingAllegiance is None:
                        # TODO: Log something
                        continue

                    dbRulingAllegiances.append(multiverse.DbRulingAllegiance(
                        allegianceId=dbRulingAllegiance.id()))
                except Exception as ex:
                    print(ex)
                    pass # TODO: Log something

            dbOwningSystems: typing.List[multiverse.DbOwningSystem] = []
            for worldRef in world.ownerWorldReferences():
                try:
                    dbOwningSystems.append(multiverse.DbOwningSystem(
                        hexX=worldRef.hexX(),
                        hexY=worldRef.hexY(),
                        sectorAbbreviation=worldRef.sectorAbbreviation()))
                except Exception as ex:
                    print(ex)
                    pass # TODO: Log something

            dbColonySystems: typing.List[multiverse.DbColonySystem] = []
            for worldRef in world.colonyWorldReferences():
                try:
                    dbColonySystems.append(multiverse.DbColonySystem(
                        hexX=worldRef.hexX(),
                        hexY=worldRef.hexY(),
                        sectorAbbreviation=worldRef.sectorAbbreviation()))
                except Exception as ex:
                    print(ex)
                    pass # TODO: Log something

            dbResearchStations: typing.List[multiverse.DbResearchStation] = []
            for code in world.researchStations():
                dbResearchStations.append(multiverse.DbResearchStation(code=code))

            dbCustomRemarks: typing.List[multiverse.DbCustomRemark] = []
            for remark in world.customRemarks():
                dbCustomRemarks.append(multiverse.DbCustomRemark(remark=remark))

            uwp = world.uwp()
            economics = world.economics()
            culture = world.culture()
            pbg = world.pbg()
            dbBodies: typing.List[multiverse.DbBody] = []
            dbBodies.append(multiverse.DbWorld(
                # NOTE: Astronomer worlds currently use the system id rather than
                # the world id. This will change when I add support for editing
                # worlds
                id=None,
                orbitIndex=1, # TODO: Not sure about this
                name=world.name() if not world.isNameGenerated() else None,
                isMainWorld=True,
                starport=uwp.code(astronomer.UWP.Element.StarPort, default=None),
                worldSize=uwp.code(astronomer.UWP.Element.WorldSize, default=None),
                atmosphere=uwp.code(astronomer.UWP.Element.Atmosphere, default=None),
                hydrographics=uwp.code(astronomer.UWP.Element.Hydrographics, default=None),
                population=uwp.code(astronomer.UWP.Element.Population, default=None),
                government=uwp.code(astronomer.UWP.Element.Government, default=None),
                lawLevel=uwp.code(astronomer.UWP.Element.LawLevel, default=None),
                techLevel=uwp.code(astronomer.UWP.Element.TechLevel, default=None),
                resources=economics.code(astronomer.Economics.Element.Resources, default=None),
                labour=economics.code(astronomer.Economics.Element.Labour, default=None),
                infrastructure=economics.code(astronomer.Economics.Element.Infrastructure, default=None),
                efficiency=economics.code(astronomer.Economics.Element.Efficiency, default=None),
                heterogeneity=culture.code(astronomer.Culture.Element.Heterogeneity, default=None),
                acceptance=culture.code(astronomer.Culture.Element.Acceptance, default=None),
                strangeness=culture.code(astronomer.Culture.Element.Strangeness, default=None),
                symbols=culture.code(astronomer.Culture.Element.Symbols, default=None),
                populationMultiplier=pbg.code(astronomer.PBG.Element.PopulationMultiplier, default=None),
                nobilities=dbNobilities,
                bases=dbBases,
                tradeCodes=dbTradeCodes,
                sophontPopulations=dbSophontPopulations,
                rulingAllegiances=dbRulingAllegiances,
                owningSystems=dbOwningSystems,
                colonySystems=dbColonySystems,
                researchStations=dbResearchStations,
                customRemarks=dbCustomRemarks))

            numSystemWorlds = world.numberOfSystemWorlds()
            numPlanetoidBelts = world.numberOfPlanetoidBelts()
            numGasGiants = world.numberOfGasGiants()
            numOtherWorlds = None
            if numSystemWorlds is not None:
                numOtherWorlds = numSystemWorlds
                if numPlanetoidBelts is not None:
                    numOtherWorlds -= numPlanetoidBelts
                if numGasGiants is not None:
                    numOtherWorlds -= numGasGiants
                if numOtherWorlds < 0:
                    numOtherWorlds = None

            dbSystems.append(multiverse.DbSystem(
                id=world.entityId(),
                hexX=hexPos.offsetX(),
                hexY=hexPos.offsetY(),
                name=world.name() if not world.isNameGenerated() else None,
                planetoidBeltCount=numPlanetoidBelts,
                gasGiantCount=numGasGiants,
                worldCount=numOtherWorlds,
                zone=astronomer.zoneTypeCode(world.zone()) if world.zone() else None,
                allegianceId=dbSystemAllegiance.id() if dbSystemAllegiance else None,
                stars=dbStars,
                bodies=dbBodies,
                # TODO: Support notes
                notes=None))
        except Exception as ex:
            print(ex)
            pass # TODO: Log something

    return dbSystems

def _createDbRoutes(
        astroSector: astronomer.Sector,
        astroAllegianceToDbAllegianceMap: typing.Mapping[astronomer.Allegiance, multiverse.DbAllegiance],
        sectorLogName: str
        ) -> typing.List[multiverse.DbRoute]:
    sectorPos = astroSector.position()
    dbRoutes: typing.List[multiverse.DbRoute] = []
    for route in astroSector.routes():
        try:
            startHex = route.startHex()
            endHex = route.endHex()

            dbLineStyle = None
            if route.style():
                dbLineStyle = _mapAstronomerLabelSizeToDbLabelSize(route.style())
                if dbLineStyle is None:
                    pass # TODO: Log something

            dbAllegiance = None
            if route.allegiance():
                dbAllegiance = astroAllegianceToDbAllegianceMap.get(route.allegiance())
                if dbAllegiance is None:
                    pass # TODO: Log something

            # TODO: Need to check the start/end offsets are being calculated correctly
            dbRoutes.append(multiverse.DbRoute(
                id=route.entityId(),
                startHexX=startHex.offsetX(),
                startHexY=startHex.offsetY(),
                startOffsetX=startHex.sectorX() - sectorPos.sectorX(),
                startOffsetY=startHex.sectorY() - sectorPos.sectorY(),
                endHexX=endHex.offsetX(),
                endHexY=endHex.offsetY(),
                endOffsetX=endHex.sectorX() - sectorPos.sectorX(),
                endOffsetY=endHex.sectorY() - sectorPos.sectorY(),
                type=route.routeType(),
                style=dbLineStyle,
                colour=route.colour(),
                width=route.width(),
                allegianceId=dbAllegiance.id() if dbAllegiance else None))
        except Exception as ex:
            pass # TODO: Log something

    return dbRoutes

def _createDbBorders(
        astroSector: astronomer.Sector,
        astroAllegianceToDbAllegianceMap: typing.Mapping[astronomer.Allegiance, multiverse.DbAllegiance],
        sectorLogName: str
        ) -> typing.List[multiverse.DbBorder]:
    dbBorders: typing.List[multiverse.DbBorder] = []
    for astroBorder in astroSector.borders():
        try:
            dbHexes: typing.List[typing.Tuple[int, int]] = []
            for hex in astroBorder.hexes():
                dbHexes.append(hex.offset())

            dbAllegiance = astroAllegianceToDbAllegianceMap.get(astroBorder.allegiance())
            if dbAllegiance is None:
                pass # TODO: Log something

            dbStyle = None
            if astroBorder.style():
                dbStyle = _mapAstronomerLineStyleToDbLineStyle(astroBorder.style())
                if dbStyle is None:
                    pass # TODO: Log something

            dbBorders.append(multiverse.DbBorder(
                id=astroBorder.entityId(),
                hexes=dbHexes,
                allegianceId=dbAllegiance.id() if dbAllegiance else None,
                style=dbStyle,
                colour=astroBorder.colour(),
                label=astroBorder.label(),
                labelWorldX=astroBorder.labelWorldX(),
                labelWorldY=astroBorder.labelWorldY(),
                showLabel=astroBorder.showLabel(),
                wrapLabel=astroBorder.wrapLabel()))
        except Exception as ex:
            pass # TODO: Log something

    return dbBorders

def _createDbRegions(
        astroSector: astronomer.Sector,
        sectorLogName: str
        ) -> typing.List[multiverse.DbRegion]:
    dbRegions: typing.List[multiverse.DbRegion] = []
    for astroRegion in astroSector.regions():
        try:
            dbHexes: typing.List[typing.Tuple[int, int]] = []
            for hex in astroRegion.hexes():
                dbHexes.append(hex.offset())

            dbRegions.append(multiverse.DbRegion(
                id=astroRegion.entityId(),
                hexes=dbHexes,
                colour=astroRegion.colour(),
                label=astroRegion.label(),
                labelWorldX=astroRegion.labelWorldX(),
                labelWorldY=astroRegion.labelWorldY(),
                showLabel=astroRegion.showLabel(),
                wrapLabel=astroRegion.wrapLabel()))
        except Exception as ex:
            pass # TODO: Log something

    return dbRegions

def _createDbLabels(
        astroSector: astronomer.Sector,
        sectorLogName: str
        ) -> typing.List[multiverse.DbLabel]:
    dbLabels: typing.List[multiverse.DbLabel] = []
    for astroLabel in astroSector.labels():
        try:
            dbSize = None
            if astroLabel.size():
                dbSize = _mapAstronomerLabelSizeToDbLabelSize(astroLabel.size())
                if dbSize is None:
                    pass # TODO: Log something

            dbLabels.append(multiverse.DbLabel(
                id=astroLabel.entityId(),
                text=astroLabel.text(),
                worldX=astroLabel.worldX(),
                worldY=astroLabel.worldY(),
                colour=astroLabel.colour(),
                size=dbSize,
                wrap=astroLabel.wrap()))
        except Exception as ex:
            pass # TODO: Log something

    return dbLabels

def _createDbTags(
        astroSector: astronomer.Sector,
        sectorLogName: str
        ) -> typing.List[multiverse.DbTag]:
    astroTagging = astroSector.tagging()
    dbTags: typing.List[multiverse.DbTag] = []
    if astroTagging:
        for astroTag in astroTagging.tags():
            try:
                dbTags.append(multiverse.DbTag(tag=astroTag.value))
            except Exception as ex:
                pass # TODO: Log something

    return dbTags

def _createDbProducts(
        astroSector: astronomer.Sector,
        sectorLogName: str
        ) -> typing.List[multiverse.DbProduct]:
    dbProducts: typing.List[multiverse.DbProduct] = []
    for astroProduct in astroSector.products():
        try:
            dbProducts.append(multiverse.DbProduct(
                publication=astroProduct.publication(),
                author=astroProduct.author(),
                publisher=astroProduct.publisher(),
                reference=astroProduct.reference()))
        except Exception as ex:
            pass # TODO: Log something

    return dbProducts

def convertAstronomerSectorToDbSector(astroSector: astronomer.Sector) -> multiverse.DbSector:
    sectorName = astroSector.name()
    sectorPos = astroSector.position()
    milieu = astroSector.milieu()

    sectorLogName = '{sectorName} ({sectorX}, {sectorY}) from {milieu}'.format(
        sectorName=sectorName if sectorName else '<Unnamed Sector>',
        sectorX=sectorPos.sectorX(),
        sectorY=sectorPos.sectorY(),
        milieu=milieu.value)

    dbAlternateNames = _createDbAlternateNames(
        astroSector=astroSector,
        sectorLogName=sectorLogName)

    dbSubsectorNames = _createDbSubsectorNames(
        astroSector=astroSector,
        sectorLogName=sectorLogName)

    astroAllegianceToDbAllegianceMap = _createDbAllegiances(
        astroSector=astroSector,
        sectorLogName=sectorLogName)

    astroSophontToDbSophontMap = _createDbSophonts(
        astroSector=astroSector,
        sectorLogName=sectorLogName)

    dbSystems = _createDbSystems(
        astroSector=astroSector,
        astroAllegianceToDbAllegianceMap=astroAllegianceToDbAllegianceMap,
        astroSophontToDbSophontMap=astroSophontToDbSophontMap,
        sectorLogName=sectorLogName)

    dbRoutes = _createDbRoutes(
        astroSector=astroSector,
        astroAllegianceToDbAllegianceMap=astroAllegianceToDbAllegianceMap,
        sectorLogName=sectorLogName)

    dbBorders = _createDbBorders(
        astroSector=astroSector,
        astroAllegianceToDbAllegianceMap=astroAllegianceToDbAllegianceMap,
        sectorLogName=sectorLogName)

    dbRegions = _createDbRegions(
        astroSector=astroSector,
        sectorLogName=sectorLogName)

    dbLabels = _createDbLabels(
        astroSector=astroSector,
        sectorLogName=sectorLogName)

    dbTags = _createDbTags(
        astroSector=astroSector,
        sectorLogName=sectorLogName)

    dbProducts = _createDbProducts(
        astroSector=astroSector,
        sectorLogName=sectorLogName)

    astroSource = astroSector.source()

    return multiverse.DbSector(
        id=astroSector.entityId(),
        milieu=milieu.value,
        sectorX=sectorPos.sectorX(),
        sectorY=sectorPos.sectorY(),
        name=sectorName,
        language=None,
        abbreviation=astroSector.abbreviation(),
        sectorLabel=astroSector.sectorLabel(),
        selected=astroSector.selected(),
        alternateNames=dbAlternateNames,
        subsectorNames=dbSubsectorNames,
        allegiances=astroAllegianceToDbAllegianceMap.values(),
        sophonts=astroSophontToDbSophontMap.values(),
        systems=dbSystems,
        routes=dbRoutes,
        borders=dbBorders,
        regions=dbRegions,
        labels=dbLabels,
        tags=dbTags,
        credits=astroSector.credits(),
        publication=astroSource.publication() if astroSource else None,
        author=astroSource.author() if astroSource else None,
        publisher=astroSource.publisher() if astroSource else None,
        reference=astroSource.reference() if astroSource else None,
        products=dbProducts,
        # TODO: Support notes
        notes=None)

def convertAstronomerSectorToRawSector(
        astroSector: astronomer.Sector
        ) -> typing.Tuple[
            survey.RawMetadata,
            typing.List[survey.RawWorld]]:
    dbSector = convertAstronomerSectorToDbSector(astroSector=astroSector)
    return multiverse.convertDbSectorToRawSector(dbSector=dbSector)