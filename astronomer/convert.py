import astronomer
import common
import itertools
import logging
import math
import multiverse
import survey
import traveller
import typing

_ProgressChunkSize = 10000

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

_DbToAstronomerLabelLayerMap = {
    'mega': astronomer.LabelLayer.Mega,
    'minor': astronomer.LabelLayer.Minor,
    'world': astronomer.LabelLayer.World,
    'border': astronomer.LabelLayer.Border,
    'rift': astronomer.LabelLayer.Rift,
    'route': astronomer.LabelLayer.Route}
def _mapDbLabelLayerToAstronomerLabelLayer(
        layer: typing.Optional[str]
        ) -> typing.Optional[astronomer.LabelLayer]:
    if not layer:
        return None
    lower = layer.lower()
    mapped = _DbToAstronomerLabelLayerMap.get(lower)
    if not mapped:
        return None
    return mapped

_AstronomerToDbLabelLayerMap = {v: k for k, v in _DbToAstronomerLabelLayerMap.items()}
def _mapAstronomerLabelLayerToDbLabelLayer(
        layer: astronomer.LabelLayer
        ) -> typing.Optional[str]:
    return _AstronomerToDbLabelLayerMap.get(layer)

_DbToAstronomerVectorLayerMap = {
    'border': astronomer.VectorLayer.Border,
    'rift': astronomer.VectorLayer.Rift,
    'route': astronomer.VectorLayer.Route}
def _mapDbVectorLayerToAstronomerVectorLayer(
        layer: typing.Optional[str]
        ) -> typing.Optional[astronomer.LabelLayer]:
    if not layer:
        return None
    lower = layer.lower()
    mapped = _DbToAstronomerVectorLayerMap.get(lower)
    if not mapped:
        return None
    return mapped

_AstronomerToDbVectorLayerMap = {v: k for k, v in _DbToAstronomerVectorLayerMap.items()}
def _mapAstronomerVectorLayerToDbVectorLayer(
        layer: astronomer.LabelLayer
        ) -> typing.Optional[str]:
    return _AstronomerToDbVectorLayerMap.get(layer)

_DbToAstronomerLabelSizeMap = {
    'small': astronomer.LabelSize.Small,
    'large': astronomer.LabelSize.Large}
def _mapDbLabelSizeToAstronomerLabelSize(
        size: typing.Optional[str]
        ) -> typing.Optional[astronomer.LabelSize]:
    if not size:
        return None
    lowerSize = size.lower()
    mappedSize = _DbToAstronomerLabelSizeMap.get(lowerSize)
    if not mappedSize:
        return None
    return mappedSize

_AstronomerToDbLabelSizeMap = {v: k for k, v in _DbToAstronomerLabelSizeMap.items()}
def _mapAstronomerLabelSizeToDbLabelSize(
        size: astronomer.LabelSize
        ) -> typing.Optional[str]:
    return _AstronomerToDbLabelSizeMap.get(size)

_DbToAstronomerTextAlignmentMap = {
    'baseline': astronomer.TextAlignment.Baseline,
    'center': astronomer.TextAlignment.Center,
    'top_left': astronomer.TextAlignment.TopLeft,
    'top_center': astronomer.TextAlignment.TopCenter,
    'top_right': astronomer.TextAlignment.TopRight,
    'center_left': astronomer.TextAlignment.CenterLeft,
    'center_right': astronomer.TextAlignment.CenterRight,
    'bottom_left': astronomer.TextAlignment.BottomLeft,
    'bottom_center': astronomer.TextAlignment.BottomCenter,
    'bottom_right': astronomer.TextAlignment.BottomRight}
def _mapDbTextAlignmentToAstronomerTextAlignment(
        alignment: typing.Optional[str]
        ) -> typing.Optional[astronomer.TextAlignment]:
    if not alignment:
        return None
    lowerSize = alignment.lower()
    mappedSize = _DbToAstronomerTextAlignmentMap.get(lowerSize)
    if not mappedSize:
        return None
    return mappedSize

_AstronomerToDbTextAlignmentMap = {v: k for k, v in _DbToAstronomerTextAlignmentMap.items()}
def _mapAstronomerTextAlignmentToDbTextAlignment(
        alignment: typing.Optional[astronomer.TextAlignment]
        ) -> typing.Optional[str]:
    return _AstronomerToDbTextAlignmentMap.get(alignment)

def convertDbAllegiancesToAstronomerAllegiances(
        dbAllegiances: typing.Collection[multiverse.DbAllegiance],
        entityFactory: astronomer.EntityFactoryInterface,
        progress: typing.Optional[common.ProgressTracker] = None
        ) -> typing.List[astronomer.Allegiance]:
    if not dbAllegiances:
        if progress is not None:
            progress.complete()
        return []

    objectCount = len(dbAllegiances)
    chunkSize = objectCount
    localProgress = None
    if progress is not None:
        chunkSize = _ProgressChunkSize
        localProgress = progress.createChild(
            weight=1,
            steps=math.ceil(objectCount / chunkSize))

    astroAllegiances = []
    for chunkStart in range(0, objectCount, chunkSize):
        for dbAllegiance in itertools.islice(dbAllegiances, chunkStart, chunkStart + chunkSize):
            try:
                astroAllegiances.append(entityFactory.createAllegiance(
                    entityId=dbAllegiance.id(),
                    name=dbAllegiance.name(),
                    code=dbAllegiance.code(),
                    legacyCode=dbAllegiance.legacy(),
                    baseCode=dbAllegiance.base(),
                    routeColour=dbAllegiance.routeColour(),
                    routeStyle=_mapDbLineStyleToAstronomerLineStyle(dbAllegiance.routeStyle()),
                    routeWidth=dbAllegiance.routeWidth(),
                    borderColour=dbAllegiance.borderColour(),
                    borderStyle=_mapDbLineStyleToAstronomerLineStyle(dbAllegiance.borderStyle())))
            except Exception as ex:
                logging.warning('Failed to convert database allegiance {id!r} ({name!r}) to astro allegiance'.format(
                        id=dbAllegiance.id(),
                        name=dbAllegiance.name()),
                    exc_info=ex)

        if localProgress is not None:
            localProgress.advance()

    return astroAllegiances

def convertDbSophontsToAstronomerSophonts(
        dbSophonts: typing.Collection[multiverse.DbSophont],
        entityFactory: astronomer.EntityFactoryInterface,
        progress: typing.Optional[common.ProgressTracker] = None
        ) -> typing.List[astronomer.Allegiance]:
    if not dbSophonts:
        if progress is not None:
            progress.complete()
        return []

    objectCount = len(dbSophonts)
    chunkSize = objectCount
    localProgress = None
    if progress is not None:
        chunkSize = _ProgressChunkSize
        localProgress = progress.createChild(
            weight=1,
            steps=math.ceil(objectCount / chunkSize))

    astroSophonts = []
    for chunkStart in range(0, objectCount, chunkSize):
        for dbSophont in itertools.islice(dbSophonts, chunkStart, chunkStart + chunkSize):
            try:
                astroSophonts.append(entityFactory.createSophont(
                    entityId=dbSophont.id(),
                    name=dbSophont.name(),
                    code=dbSophont.code(),
                    isMajor=dbSophont.isMajor()))
            except Exception as ex:
                logging.warning('Failed to convert database sophont {id!r} ({name!r}) to astro sophont'.format(
                        id=dbSophont.id(),
                        name=dbSophont.name()),
                    exc_info=ex)

        if localProgress is not None:
            localProgress.advance()

    return astroSophonts

def _createAstronomerAlternateNames(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.List[str]]:
    dbAlternateNames = dbSector.alternateNames()
    if not dbAlternateNames:
        return None

    return [dbAlternateName.name() for dbAlternateName in dbAlternateNames]

def _createAstronomerNameLanguages(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.Dict[
            str, # Sector name
            str]]: # Language name is in
    astroNameLanguages = None

    language = dbSector.language()
    if language is not None:
        astroNameLanguages = {dbSector.name(): language}

    dbAlternateNames = dbSector.alternateNames()
    if dbAlternateNames:
        for dbAlternateName in dbAlternateNames:
            language = dbAlternateName.language()
            if language is None:
                continue

            if astroNameLanguages is None:
                astroNameLanguages = {}
            astroNameLanguages[dbAlternateName.name()] = language

    return astroNameLanguages

def _createAstronomerSubsectorNames(
        dbSector: multiverse.DbSector
        ) -> typing.Optional[typing.Dict[
            str, # Subsector code (A-P)
            str]]: # Subsector name
    dbSubsectorNames = dbSector.subsectorNames()
    if not dbSubsectorNames:
        return None

    return {dbSubsectorName.code(): dbSubsectorName.name() for dbSubsectorName in dbSubsectorNames}

def convertDbSystemsToAstronomerWorlds(
        dbSystems: typing.Collection[multiverse.DbSystem],
        entityFactory: astronomer.EntityFactoryInterface,
        astroAllegiances: typing.Optional[typing.Collection[astronomer.Allegiance]] = None,
        astroSophonts:typing.Optional[typing.Collection[astronomer.Sophont]] = None,
        progress: typing.Optional[common.ProgressTracker] = None
        ) -> typing.Optional[typing.List[astronomer.World]]:
    if not dbSystems:
        if progress is not None:
            progress.complete()
        return []

    objectCount = len(dbSystems)
    chunkSize = objectCount
    localProgress = None
    if progress is not None:
        chunkSize = _ProgressChunkSize
        localProgress = progress.createChild(
            weight=1,
            steps=math.ceil(objectCount / chunkSize))

    dbIdToAstroAllegianceMap = {a.entityId(): a for a in astroAllegiances} if astroAllegiances is not None else {}
    dbIdToAstroSophontMap = {s.entityId(): s for s in astroSophonts} if astroSophonts is not None else {}
    astroWorlds = []
    for chunkStart in range(0, objectCount, chunkSize):
        for dbSystem in itertools.islice(dbSystems, chunkStart, chunkStart + chunkSize):
            systemName = dbSystem.name()
            logMessageContext = 'when converting database system {id!r} ({name}) astro world'.format(
                id=dbSystem.id(),
                name=dbSystem.name() if dbSystem.name() else '<Unnamed System>')

            try:
                worldHex = astronomer.HexPosition(
                    absoluteX=dbSystem.hexX(),
                    absoluteY=dbSystem.hexY())

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
                    # TODO: This is EVEN WORSE now that it's just using the absolute hex rather than
                    # a sector hex string with the sector name
                    systemName = f'Hex {dbSystem.hexX():02d}, {dbSystem.hexY():02d}'
                    isNameGenerated = True

                allegianceId = dbSystem.allegianceId()
                systemAllegiance = None
                if allegianceId:
                    systemAllegiance = dbIdToAstroAllegianceMap.get(allegianceId) if dbIdToAstroAllegianceMap else None
                    if not systemAllegiance:
                        logging.warning('Ignoring unknown allegiance {allegianceId!r} {context}'.format(
                            allegianceId=allegianceId,
                            context=logMessageContext))

                dbZone = dbSystem.zone()
                zone = None
                if dbZone:
                    try:
                        zone = astronomer.codeToZoneType(dbZone)
                    except Exception as ex:
                        logging.warning('Failed to parse zone {zone!r} {context}'.format(
                                zone=dbZone,
                                context=logMessageContext),
                            exc_info=ex)

                dbBodies = dbSystem.bodies()
                dbMainWorld = None
                if dbBodies:
                    dbMainWorld = dbBodies[0]
                    if not isinstance(dbMainWorld, multiverse.DbWorld):
                        logging.warning('Ignoring {type!r} main world {context}'.format(
                                type=type(dbMainWorld),
                                context=logMessageContext))
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
                        logging.warning('Failed to create UWP {context}'.format(
                                context=logMessageContext),
                            exc_info=ex)

                    try:
                        economics = astronomer.Economics(
                            resources=dbMainWorld.resources(),
                            labour=dbMainWorld.labour(),
                            infrastructure=dbMainWorld.infrastructure(),
                            efficiency=dbMainWorld.efficiency())
                    except Exception as ex:
                        logging.warning('Failed to create economics {context}'.format(
                                context=logMessageContext),
                            exc_info=ex)

                    try:
                        culture = astronomer.Culture(
                            heterogeneity=dbMainWorld.heterogeneity(),
                            acceptance=dbMainWorld.acceptance(),
                            strangeness=dbMainWorld.strangeness(),
                            symbols=dbMainWorld.symbols())
                    except Exception as ex:
                        logging.warning('Failed to create culture {context}'.format(
                                context=logMessageContext),
                            exc_info=ex)

                    dbTradeCodes = dbMainWorld.tradeCodes()
                    tradeCodes: typing.Optional[typing.List[traveller.TradeCode]] = None
                    if dbTradeCodes:
                        tradeCodes = []
                        for dbTradeCode in dbTradeCodes:
                            tradeCode = traveller.tradeCode(tradeCodeString=dbTradeCode.code())
                            if not tradeCode:
                                logging.warning('Ignoring trade code {objectId!r} with unknown code {code!r} {context}'.format(
                                    objectId=dbTradeCode.id(),
                                    code=dbTradeCode.code(),
                                    context=logMessageContext))
                                continue
                            tradeCodes.append(tradeCode)

                    dbPopulations = dbMainWorld.sophontPopulations()
                    sophontPopulations: typing.Optional[typing.List[astronomer.SophontPopulation]] = None
                    if dbPopulations:
                        sophontPopulations = []
                        for dbPopulation in dbPopulations:
                            sophont = dbIdToAstroSophontMap.get(dbPopulation.sophontId()) if dbIdToAstroSophontMap else None
                            if not sophont:
                                logging.warning('Ignoring sophont population {objectId!r} with unknown sophont {sophontId!r} {context}'.format(
                                    objectId=dbPopulation.id(),
                                    sophontId=dbPopulation.sophontId(),
                                    context=logMessageContext))
                                continue

                            try:
                                sophontPopulations.append(astronomer.SophontPopulation(
                                    sophont=sophont,
                                    percentage=dbPopulation.percentage(),
                                    isHomeWorld=dbPopulation.isHomeWorld(),
                                    isDieBack=dbPopulation.isDieBack()))
                            except Exception as ex:
                                logging.warning('Failed to create sophont population {objectId!r} {context}'.format(
                                        objectId=dbPopulation.id(),
                                        context=logMessageContext),
                                    exc_info=ex)

                    dbRulingAllegiances = dbMainWorld.rulingAllegiances()
                    rulingAllegiances: typing.Optional[typing.List[astronomer.Allegiance]] = None
                    if dbRulingAllegiances:
                        rulingAllegiances = []
                        for dbAllegiance in dbRulingAllegiances:
                            rulingAllegiance = dbIdToAstroAllegianceMap.get(dbAllegiance.allegianceId()) if dbIdToAstroAllegianceMap else None
                            if not rulingAllegiance:
                                logging.warning('Ignoring ruling allegiance {objectId!r} with unknown allegiance {allegianceId!r} {context}'.format(
                                    objectId=dbAllegiance.id(),
                                    allegianceId=dbAllegiance.allegianceId(),
                                    context=logMessageContext))
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
                                logging.warning('Failed to create world reference for owning system {objectId!r} {context}'.format(
                                        objectId=dbOwningSystem.id(),
                                        context=logMessageContext),
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
                                logging.warning('Failed to create world reference for colony system {objectId} {context}'.format(
                                        objectId=dbColonySystem.id(),
                                        context=logMessageContext),
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
                                logging.warning('Ignoring nobility {objectId!r} with unknown code {code!r} {context}'.format(
                                    objectId=dbNobility.id(),
                                    code=dbNobility.code(),
                                    context=logMessageContext))
                                continue
                            nobilityTypes.append(nobilityType)

                    try:
                        nobilities = astronomer.Nobilities(nobilities=nobilityTypes)
                    except Exception as ex:
                        logging.warning('Failed to create nobilities {context}'.format(
                                context=logMessageContext),
                            exc_info=ex)

                    dbBases = dbMainWorld.bases()
                    baseTypes = None
                    if dbBases:
                        baseTypes = []
                        for dbBase in dbBases:
                            codeBaseTypes = astronomer.codeToBaseTypes(dbBase.code())
                            if codeBaseTypes is None:
                                logging.warning('Ignoring base {objectId!r} with unknown code {code!r} {context}'.format(
                                    objectId=dbBase.id(),
                                    code=dbBase.code(),
                                    context=logMessageContext))
                                continue
                            baseTypes.extend(codeBaseTypes)

                    try:
                        bases = astronomer.Bases(bases=baseTypes)
                    except Exception as ex:
                        logging.warning('Failed to create bases {context}'.format(
                                context=logMessageContext),
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
                    logging.warning('Failed to create PBG {context}'.format(
                            context=logMessageContext),
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
                            logging.warning('Failed to create star {objectId!r} {context}'.format(
                                    objectId=dbStar.id(),
                                    context=logMessageContext),
                                exc_info=ex)

                stellar = None
                try:
                    stellar = astronomer.Stellar(stars=stars)
                except Exception as ex:
                    logging.warning('Failed to create stellar {context}'.format(
                            context=logMessageContext),
                        exc_info=ex)

                astroWorlds.append(entityFactory.createWorld(
                    entityId=dbSystem.id(),
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
                    customRemarks=customRemarks))
            except Exception as ex:
                logging.warning('Failed to convert database system {systemId!r} ({name}) to astro world'.format(
                        systemId=dbSystem.id(),
                        name=dbSystem.name()),
                    exc_info=ex)

        if localProgress is not None:
            localProgress.advance()

    return astroWorlds

def _createAstronomerRegions(
        dbSector: multiverse.DbSector,
        entityFactory: astronomer.EntityFactoryInterface,
        sectorLogName: str
        ) -> typing.Optional[typing.List[astronomer.Region]]:
    dbRegions = dbSector.regions()
    if not dbRegions:
        return None

    astroRegions = []
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
            if colour is not None:
                try:
                    colour = common.canonicalHtmlColour(colour)
                except:
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
        ) -> typing.Optional[typing.List[astronomer.SectorLabel]]:
    dbLabels = dbSector.labels()
    if not dbLabels:
        return None

    astroLabels = []
    for dbLabel in dbLabels:
        try:
            colour = dbLabel.colour()
            if colour is not None:
                try:
                    colour = common.canonicalHtmlColour(colour)
                except:
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

            astroLabels.append(entityFactory.createSectorLabel(
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
    if not dbTags:
        return None

    astroTagging = None
    try:
        astroTagging = astronomer.SectorTagging(tags=[dbTag.tag() for dbTag in dbTags])
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
    astroSource = None

    dbPublication = dbSector.publication()
    dbAuthor = dbSector.author()
    dbPublisher = dbSector.publisher()
    dbReference = dbSector.reference()
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
    if not dbProducts:
        return None

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

def convertDbSectorsToAstronomerSectors(
        dbSectors: typing.Collection[multiverse.DbSector],
        entityFactory: astronomer.EntityFactoryInterface,
        progress: typing.Optional[common.ProgressTracker] = None
        ) -> typing.List[astronomer.Sector]:
    if not dbSectors:
        if progress is not None:
            progress.complete()
        return []

    objectCount = len(dbSectors)
    chunkSize = objectCount
    localProgress = None
    if progress is not None:
        chunkSize = _ProgressChunkSize
        localProgress = progress.createChild(
            weight=1,
            steps=math.ceil(objectCount / chunkSize))

    astroSectors = []
    for chunkStart in range(0, objectCount, chunkSize):
        for dbSector in itertools.islice(dbSectors, chunkStart, chunkStart + chunkSize):
            try:
                sectorName = dbSector.name()
                sectorX = dbSector.sectorX()
                sectorY = dbSector.sectorY()

                sectorLogName = '{sectorName} ({sectorX}, {sectorY})'.format(
                    sectorName=sectorName if sectorName else '<Unnamed Sector>',
                    sectorX=sectorX,
                    sectorY=sectorY)

                astroAlternateNames = _createAstronomerAlternateNames(dbSector=dbSector)

                astroNameLanguages = _createAstronomerNameLanguages(dbSector=dbSector)

                astroSubsectorNames = _createAstronomerSubsectorNames(dbSector=dbSector)

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

                astroSectors.append(entityFactory.createSector(
                    entityId=dbSector.id(),
                    name=sectorName,
                    position=astronomer.SectorPosition(sectorX=sectorX, sectorY=sectorY),
                    alternateNames=astroAlternateNames,
                    nameLanguages=astroNameLanguages,
                    abbreviation=dbSector.abbreviation(),
                    sectorLabel=dbSector.sectorLabel(),
                    subsectorNames=astroSubsectorNames,
                    regions=astroRegions,
                    labels=astroLabels,
                    selected=dbSector.selected(),
                    tagging=astroTagging,
                    credits=dbSector.credits(),
                    source=astroSource,
                    products=astroProducts))
            except Exception as ex:
                logging.warning('Failed to convert database sector {id!r} ({name!r}) to astro sector'.format(
                        id=dbSector.id(),
                        name=dbSector.name()),
                    exc_info=ex)

        if localProgress is not None:
            localProgress.advance()

    return astroSectors

def convertRawSectorToAstronomerSector(
        milieu: astronomer.Milieu,
        rawMetadata: survey.RawMetadata,
        rawSystems: typing.Collection[survey.RawWorld],
        rawStockAllegiances: typing.Optional[typing.Collection[survey.RawStockAllegiance]] = None,
        rawStockSophonts: typing.Optional[typing.Collection[survey.RawStockSophont]] = None,
        rawStockStyleSheet: typing.Optional[survey.RawStyleSheet] = None,
        entityFactory: typing.Optional[astronomer.EntityFactoryInterface] = None,
        sectorId: typing.Optional[str] = None
        ) -> astronomer.Sector:
    # TODO: Implement me
    assert(False)

def convertAstronomerSectorToRawSector(
        astroUniverse: astronomer.Universe,
        astroSectorPos: astronomer.SectorPosition
        ) -> typing.Tuple[
            survey.RawMetadata,
            typing.List[survey.RawWorld]]:
    # TODO: Reimplement me
    assert(False)

def convertDbRoutesToAstronomerRoutes(
        dbRoutes: typing.Collection[multiverse.DbRoute],
        entityFactory: astronomer.EntityFactoryInterface,
        astroAllegiances: typing.Optional[typing.Collection[astronomer.Allegiance]] = None,
        progress: typing.Optional[common.ProgressTracker] = None
        ) -> typing.List[astronomer.MapLabel]:
    if not dbRoutes:
        if progress is not None:
            progress.complete()
        return []

    objectCount = len(dbRoutes)
    chunkSize = objectCount
    localProgress = None
    if progress is not None:
        chunkSize = _ProgressChunkSize
        localProgress = progress.createChild(
            weight=1,
            steps=math.ceil(objectCount / chunkSize))

    dbIdToAstroAllegianceMap = {a.entityId(): a for a in astroAllegiances} if astroAllegiances is not None else {}
    astroRoutes = []
    for chunkStart in range(0, objectCount, chunkSize):
        for dbRoute in itertools.islice(dbRoutes, chunkStart, chunkStart + chunkSize):
            try:
                astroRoutes.append(entityFactory.createRoute(
                    entityId=dbRoute.id(),
                    startHex=astronomer.HexPosition(dbRoute.startHexX(), dbRoute.startHexY()),
                    endHex=astronomer.HexPosition(dbRoute.endHexX(), dbRoute.endHexY()),
                    allegiance=dbIdToAstroAllegianceMap.get(dbRoute.allegianceId()),
                    routeType=dbRoute.type(),
                    style=_mapDbLineStyleToAstronomerLineStyle(dbRoute.style()),
                    colour=dbRoute.colour(),
                    width=dbRoute.width()))
            except Exception as ex:
                logging.warning('Failed to convert database route {id!r} to astro route'.format(
                        id=dbRoute.id()),
                    exc_info=ex)

        if localProgress is not None:
            localProgress.advance()

    return astroRoutes

def _createAstronomerBorderLabels(
        dbBorder: multiverse.DbBorder,
        dbIdToAstroAllegianceMap: typing.Mapping[str, astronomer.Allegiance]
        ) -> typing.Optional[typing.List[astronomer.BorderLabel]]:
    dbLabels = dbBorder.labels()
    if dbLabels is None:
        return None

    astroLabels: typing.List[astronomer.Allegiance] = []
    for dbLabel in dbLabels:
        astroLabels.append(astronomer.BorderLabel(
            entityId=dbLabel.id(),
            worldX=dbLabel.worldX(),
            worldY=dbLabel.worldY(),
            allegiance=dbIdToAstroAllegianceMap.get(dbLabel.allegianceId()),
            text=dbLabel.text(),
            show=dbLabel.show(),
            wrap=dbLabel.wrap()))

    return astroLabels

def convertDbBordersToAstronomerBorders(
        dbBorders: typing.Collection[multiverse.DbBorder],
        entityFactory: astronomer.EntityFactoryInterface,
        astroAllegiances: typing.Optional[typing.Collection[astronomer.Allegiance]] = None,
        progress: typing.Optional[common.ProgressTracker] = None
        ) -> typing.List[astronomer.Border]:
    if not dbBorders:
        if progress is not None:
            progress.complete()
        return []

    objectCount = len(dbBorders)
    chunkSize = objectCount
    localProgress = None
    if progress is not None:
        chunkSize = _ProgressChunkSize
        localProgress = progress.createChild(
            weight=1,
            steps=math.ceil(objectCount / chunkSize))

    dbIdToAstroAllegianceMap = {a.entityId(): a for a in astroAllegiances} if astroAllegiances is not None else {}
    astroBorders = []
    for chunkStart in range(0, objectCount, chunkSize):
        for dbBorder in itertools.islice(dbBorders, chunkStart, chunkStart + chunkSize):
            try:
                astroBorders.append(entityFactory.createBorder(
                    entityId=dbBorder.id(),
                    hexes=[astronomer.HexPosition(absoluteX=x, absoluteY=y) for x, y in dbBorder.hexes()],
                    allegiance=dbIdToAstroAllegianceMap.get(dbBorder.allegianceId()),
                    style=_mapDbLineStyleToAstronomerLineStyle(dbBorder.style()),
                    colour=dbBorder.colour(),
                    labels=_createAstronomerBorderLabels(dbBorder=dbBorder, dbIdToAstroAllegianceMap=dbIdToAstroAllegianceMap)))
            except Exception as ex:
                logging.warning('Failed to convert database border {id!r} to astro border'.format(
                        id=dbBorder.id()),
                    exc_info=ex)

        if localProgress is not None:
            localProgress.advance()

    return astroBorders

def convertDbMapLabelsToAstronomerMapLabels(
        dbLabels: typing.Collection[multiverse.DbMapLabel],
        entityFactory: astronomer.EntityFactoryInterface,
        progress: typing.Optional[common.ProgressTracker] = None
        ) -> typing.List[astronomer.MapLabel]:
    if not dbLabels:
        if progress is not None:
            progress.complete()
        return []

    objectCount = len(dbLabels)
    chunkSize = objectCount
    localProgress = None
    if progress is not None:
        chunkSize = _ProgressChunkSize
        localProgress = progress.createChild(
            weight=1,
            steps=math.ceil(objectCount / chunkSize))

    astroLabels = []
    for chunkStart in range(0, objectCount, chunkSize):
        for dbLabel in itertools.islice(dbLabels, chunkStart, chunkStart + chunkSize):
            try:
                astroLabels.append(entityFactory.createMapLabel(
                    entityId=dbLabel.id(),
                    text=dbLabel.text(),
                    worldX=dbLabel.worldX(),
                    worldY=dbLabel.worldY(),
                    layer=_mapDbLabelLayerToAstronomerLabelLayer(dbLabel.layer()),
                    alignment=_mapDbTextAlignmentToAstronomerTextAlignment(dbLabel.alignment()),
                    colour=dbLabel.colour(),
                    size=_mapDbLabelSizeToAstronomerLabelSize(dbLabel.size()),
                    rotation=dbLabel.rotation()))
            except Exception as ex:
                logging.warning('Failed to convert database map label {id!r} to astro map label'.format(
                        id=dbLabel.id()),
                    exc_info=ex)

        if localProgress is not None:
            localProgress.advance()

    return astroLabels

def convertAstronomerMapLabelToDbMapLabel(
        astroLabel: astronomer.MapLabel
        ) -> multiverse.DbMapLabel:
    return multiverse.DbMapLabel(
        id=astroLabel.entityId(),
        text=astroLabel.text(),
        worldX=astroLabel.worldX(),
        worldY=astroLabel.worldY(),
        layer=_mapAstronomerLabelLayerToDbLabelLayer(astroLabel.layer()),
        alignment=_mapAstronomerTextAlignmentToDbTextAlignment(astroLabel.alignment()),
        colour=astroLabel.colour(),
        size=_mapAstronomerLabelSizeToDbLabelSize(astroLabel.size()),
        rotation=astroLabel.rotation())

def convertDbMapVectorsToAstronomerMapVectors(
        dbVectors: typing.Collection[multiverse.DbMapVector],
        entityFactory: astronomer.EntityFactoryInterface,
        progress: typing.Optional[common.ProgressTracker] = None
        ) -> typing.List[astronomer.MapVector]:
    if not dbVectors:
        if progress is not None:
            progress.complete()
        return []

    objectCount = len(dbVectors)
    chunkSize = objectCount
    localProgress = None
    if progress is not None:
        chunkSize = _ProgressChunkSize
        localProgress = progress.createChild(
            weight=1,
            steps=math.ceil(objectCount / chunkSize))

    astroVectors = []
    for chunkStart in range(0, objectCount, chunkSize):
        for dbVector in itertools.islice(dbVectors, chunkStart, chunkStart + chunkSize):
            try:
                astroVectors.append(entityFactory.createMapVector(
                    entityId=dbVector.id(),
                    points=dbVector.points(),
                    layer=_mapDbVectorLayerToAstronomerVectorLayer(dbVector.layer()),
                    closed=dbVector.isClosed()))
            except Exception as ex:
                logging.warning('Failed to convert database map vector {id!r} to astro map vector'.format(
                        id=dbVector.id()),
                    exc_info=ex)

        if localProgress is not None:
            localProgress.advance()

    return astroVectors

def convertAstronomerMapVectorToDbMapVector(
        astroVector: astronomer.MapVector
        ) -> multiverse.DbMapVector:
    return multiverse.DbMapVector(
        id=astroVector.entityId(),
        points=astroVector.points(),
        layer=_mapAstronomerVectorLayerToDbVectorLayer(astroVector.layer()),
        isClosed=astroVector.closed())