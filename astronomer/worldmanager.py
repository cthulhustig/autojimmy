import astronomer
import common
import logging
import multiverse
import threading
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

    def loadSectors(
            self,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        # Check if the sectors are already loaded. For speed we don't lock the mutex, this
        # works on the basis that checking the size of a dict is thread safe. This approach
        # means, if the sectors are found to not be loaded, we need to check again after we've
        # acquired the lock as another thread could sneak in and load the sectors between this
        # point and the point where we acquire the lock
        if self._universe:
            return # Sector map already loaded

        # Acquire lock while loading sectors
        with self._lock:
            if self._universe:
                # Another thread already loaded the sectors between the point we found they
                # weren't loaded and the point it acquired the mutex.
                return

            with multiverse.MultiverseDb.instance().createTransaction() as transaction:
                if progressCallback:
                    stage = f'Enumerating Sectors'
                    try:
                        progressCallback(stage, 0, 0)
                    except Exception as ex:
                        logging.warning(f'Sector loading progress callback threw an exception', exc_info=ex)

                dbSectorInfos = multiverse.MultiverseDb.instance().listSectorInfo(
                    universeId=multiverse.customUniverseId(),
                    transaction=transaction)

                totalSectorCount = len(dbSectorInfos)
                maxProgress = totalSectorCount
                currentProgress = 0
                sectors = []
                for dbSectorInfo in dbSectorInfos:
                    sectorX = dbSectorInfo.sectorX()
                    sectorY = dbSectorInfo.sectorY()
                    canonicalName = dbSectorInfo.name()
                    milieu = WorldManager._mapMilieu(dbSectorInfo.milieu())

                    if not milieu:
                        logging.warning(
                            f'Ignoring sector with unknown milieu "{dbSectorInfo.milieu()}" at ({sectorX}, {sectorY})')
                        continue

                    logging.debug(f'Loading sector {canonicalName} at ({sectorX}, {sectorY}) from {milieu.value}')

                    if progressCallback:
                        stage = f'Loading: {milieu.value} - {canonicalName}'
                        currentProgress += 1
                        try:
                            progressCallback(stage, currentProgress, maxProgress)
                        except Exception as ex:
                            logging.warning(f'Sector loading progress callback threw an exception', exc_info=ex)

                    try:
                        dbSector = multiverse.MultiverseDb.instance().loadSector(
                            sectorId=dbSectorInfo.id(),
                            transaction=transaction)
                        sector = self._convertDbSector(dbSector=dbSector)
                    except Exception as ex:
                        logging.error(f'Failed to load sector {canonicalName} at ({sectorX}, {sectorY}) from {milieu.value}', exc_info=ex)
                        continue

                    worldCount = sector.worldCount()
                    logging.debug(f'Loaded {worldCount} worlds for sector {canonicalName} at ({sectorX}, {sectorY}) from {milieu.value}')
                    sectors.append(sector)

                self._universe = astronomer.Universe(
                    sectors=sectors,
                    placeholderMilieu=WorldManager._PlaceholderMilieu)

    # TODO: This function probably shouldn't be dealing with dbSectorIds
    # _or_ the higher level astronomer Sector needs to use the same id
    def createSectorUniverse(
            self,
            dbSectorId: str
            ) -> typing.Tuple[astronomer.Universe, astronomer.Sector]:
        dbSector = multiverse.MultiverseDb.instance().loadSector(
            sectorId=dbSectorId)
        sector = self._convertDbSector(dbSector=dbSector)
        return (astronomer.Universe(sectors=[sector]), sector)

    def universe(self) -> astronomer.Universe:
        return self._universe

    def sectorNames(
            self,
            milieu: astronomer.Milieu
            ) -> typing.Iterable[str]:
        return self._universe.sectorNames(milieu=milieu)

    def sectorByName(
            self,
            milieu: astronomer.Milieu,
            name: str
            ) -> astronomer.Sector:
        return self._universe.sectorByName(milieu=milieu, name=name)

    def sectorByAbbreviation(
            self,
            milieu: astronomer.Milieu,
            abbreviation: str,
            ) -> typing.List[astronomer.Sector]:
        return self._universe.sectorsByAbbreviation(milieu=milieu, abbreviation=abbreviation)

    def sectors(
            self,
            milieu: astronomer.Milieu,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.Sector]:
        return self._universe.sectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def subsectors(
            self,
            milieu: astronomer.Milieu,
            filterCallback: typing.Callable[[astronomer.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.Subsector]:
        return self._universe.subsectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def worldBySectorHex(
            self,
            milieu: astronomer.Milieu,
            sectorHex: str,
            ) -> typing.Optional[astronomer.World]:
        return self._universe.worldBySectorHex(
            milieu=milieu,
            sectorHex=sectorHex)

    def worldByPosition(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[astronomer.World]:
        return self._universe.worldByPosition(
            milieu=milieu,
            hex=hex,
            includePlaceholders=includePlaceholders)

    def sectorByPosition(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[astronomer.Sector]:
        return self._universe.sectorByPosition(
            milieu=milieu,
            hex=hex,
            includePlaceholders=includePlaceholders)

    def sectorBySectorIndex(
            self,
            milieu: astronomer.Milieu,
            index: astronomer.SectorIndex,
            includePlaceholders: bool = False
            ) -> typing.Optional[astronomer.Sector]:
        return self._universe.sectorBySectorIndex(
            milieu=milieu,
            index=index,
            includePlaceholders=includePlaceholders)

    def subsectorByPosition(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[astronomer.Subsector]:
        return self._universe.subsectorByPosition(
            milieu=milieu,
            hex=hex,
            includePlaceholders=includePlaceholders)

    def sectorsInArea(
            self,
            milieu: astronomer.Milieu,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.Sector]:
        return self._universe.sectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def subsectorsInArea(
            self,
            milieu: astronomer.Milieu,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.Subsector]:
        return self._universe.subsectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def worlds(
            self,
            milieu: astronomer.Milieu,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.World]:
        return self._universe.worlds(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def worldsInArea(
            self,
            milieu: astronomer.Milieu,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.World]:
        return self._universe.worldsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def worldsInRadius(
            self,
            milieu: astronomer.Milieu,
            center: astronomer.HexPosition,
            searchRadius: int,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.World]:
        return self._universe.worldsInRadius(
            milieu=milieu,
            center=center,
            searchRadius=searchRadius,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def worldsInFlood(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.World]:
        return self._universe.worldsInFlood(
            milieu=milieu,
            hex=hex,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def positionToSectorHex(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            includePlaceholders: bool = False
            ) -> str:
        return self._universe.positionToSectorHex(
            milieu=milieu,
            hex=hex,
            includePlaceholders=includePlaceholders)

    def sectorHexToPosition(
            self,
            milieu: astronomer.Milieu,
            sectorHex: str
            ) -> typing.Optional[astronomer.HexPosition]:
        return self._universe.sectorHexToPosition(
            milieu=milieu,
            sectorHex=sectorHex)

    def stringToPosition(
            self,
            milieu: astronomer.Milieu,
            string: str,
            ) -> astronomer.HexPosition:
        return self._universe.stringToPosition(
            milieu=milieu,
            string=string)

    def canonicalHexName(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            ) -> str:
        return self._universe.canonicalHexName(
            milieu=milieu,
            hex=hex)

    def mainByPosition(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition
            ) -> typing.Optional[astronomer.Main]:
        return self._universe.mainByPosition(
            milieu=milieu,
            hex=hex)

    def yieldSectors(
            self,
            milieu: astronomer.Milieu,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.Sector, None, None]:
        return self._universe.yieldSectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldSectorsInArea(
            self,
            milieu: astronomer.Milieu,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.Sector, None, None]:
        return self._universe.yieldSectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldSubsectors(
            self,
            milieu: astronomer.Milieu,
            filterCallback: typing.Callable[[astronomer.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.Subsector, None, None]:
        return self._universe.yieldSubsectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldSubsectorsInArea(
            self,
            milieu: astronomer.Milieu,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.Subsector, None, None]:
        return self._universe.yieldSubsectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldWorlds(
            self,
            milieu: astronomer.Milieu,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.World, None, None]:
        return self._universe.yieldWorlds(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldWorldsInArea(
            self,
            milieu: astronomer.Milieu,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.World, None, None]:
        return self._universe.yieldWorldsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldWorldsInRadius(
            self,
            milieu: astronomer.Milieu,
            center: astronomer.HexPosition,
            radius: int,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.World, None, None]:
        return self._universe.yieldWorldsInRadius(
            milieu=milieu,
            center=center,
            radius=radius,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldWorldsInFlood(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.World, None, None]:
        return self._universe.yieldWorldsInFlood(
            milieu=milieu,
            hex=hex,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def searchForWorlds(
            self,
            milieu: astronomer.Milieu,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[astronomer.World]:
        return self._universe.searchForWorlds(
            milieu=milieu,
            searchString=searchString,
            maxResults=maxResults)

    def searchForSubsectors(
            self,
            milieu: astronomer.Milieu,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[astronomer.Subsector]:
        return self._universe.searchForSubsectors(
            milieu=milieu,
            searchString=searchString,
            maxResults=maxResults)

    def searchForSectors(
            self,
            milieu: astronomer.Milieu,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[astronomer.Sector]:
        return self._universe.searchForSectors(
            milieu=milieu,
            searchString=searchString,
            maxResults=maxResults)

    @staticmethod
    def _convertDbSector(
            dbSector: multiverse.DbSector
            ) -> astronomer.Sector:
        sectorName = dbSector.primaryName()
        sectorX = dbSector.sectorX()
        sectorY = dbSector.sectorY()

        milieu = WorldManager._mapMilieu(dbSector.milieu())
        if not milieu:
            raise ValueError(f'Sector has unknown milieu "{dbSector.milieu()}"')

        dbAlternateNames = dbSector.alternateNames()
        alternateNames = None
        if dbAlternateNames:
            alternateNames = []
            for dbAlternateName in dbAlternateNames:
                alternateNames.append(dbAlternateName.name())

        subsectorNameMap: typing.Dict[
            str, # Subsector code (A-P)
            typing.Tuple[
                str, # Subsector name
                bool # True if the name was generated
                ]] = {}
        subsectorWorldsMap: typing.Dict[
            str, # Subsector code (A-P)
            typing.List[astronomer.World]
            ] = {}

        # Setup default subsector names. Some sectors just use the code A-P but we need
        # something unique
        subsectorCodes = list(map(chr, range(ord('A'), ord('P') + 1)))
        for subsectorCode in subsectorCodes:
            subsectorNameMap[subsectorCode] = (f'{sectorName} Subsector {subsectorCode}', True)
            subsectorWorldsMap[subsectorCode] = []

        if dbSector.subsectorNames():
            for dbSubsectorName in dbSector.subsectorNames():
                # NOTE: Unlike most other places, it's intentional that this is upper case
                subsectorNameMap[dbSubsectorName.code()] = (dbSubsectorName.name(), False)

        allegianceCodeMap: typing.Dict[str, astronomer.Allegiance] = {}
        if dbSector.allegiances():
            for dbAllegiance in dbSector.allegiances():
                try:
                    routeStyle = dbAllegiance.routeStyle()
                    if routeStyle:
                        routeStyle = WorldManager._mapLineStyle(routeStyle)
                        if not routeStyle:
                            logging.warning(
                                f'Ignoring invalid route style "{dbAllegiance.routeStyle()}" for allegiance {dbAllegiance.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')

                    borderStyle = dbAllegiance.borderStyle()
                    if borderStyle:
                        borderStyle = WorldManager._mapLineStyle(borderStyle)
                        if not borderStyle:
                            logging.warning(
                                f'Ignoring invalid border style "{dbAllegiance.borderStyle()}" for allegiance {dbAllegiance.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')

                    allegianceCodeMap[dbAllegiance.code()] = astronomer.Allegiance(
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
                    logging.warning(
                        f'Failed to load allegiance {dbAllegiance.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                        exc_info=ex)

        dbSophonts = dbSector.sophonts()
        sophontCodeMap: typing.Dict[str, astronomer.Sophont] = {}
        if dbSophonts:
            for dbSophont in dbSophonts:
                try:
                    sophontCodeMap[dbSophont.code()] = astronomer.Sophont(
                        code=dbSophont.code(),
                        name=dbSophont.name(),
                        isMajor=dbSophont.isMajor())
                except Exception as ex:
                    logging.warning(
                        f'Failed to load sophont {dbSophont.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                        exc_info=ex)

        dbSystems = dbSector.systems()
        if dbSystems:
            for dbSystem in dbSystems:
                try:
                    worldHex = astronomer.HexPosition(
                        sectorX=sectorX,
                        sectorY=sectorY,
                        offsetX=dbSystem.hexX(),
                        offsetY=dbSystem.hexY())

                    worldName = dbSystem.name()
                    isNameGenerated = False
                    if not worldName:
                        # If the world doesn't have a name the sector combined with the hex. This format
                        # is important as it's the same format as Traveller Map meaning searches will
                        # work
                        # TODO: I don't like the fact I do this. It's done so all "worlds" (aka systems)
                        # have a name. I think the only reason to really do this is so, when they're
                        # displayed in tables and other places there is always something to show to
                        # the user (in tables name is generally the first column in the table).
                        # - Need to look to see what Traveller Map displays on map and in the info
                        # dialog for worlds that have no name (but have a non ? UWP).
                        worldName = f'{sectorName} {dbSystem.hexX():02d}{dbSystem.hexY():02d}'
                        isNameGenerated = True

                    subsectorIndex = worldHex.subsectorIndex()
                    subsectorCode = subsectorIndex.code()
                    subsectorName, _ = subsectorNameMap[subsectorCode]

                    allegianceCode = dbSystem.allegianceCode()
                    allegiance = None
                    if allegianceCode:
                        allegiance = allegianceCodeMap.get(allegianceCode)
                        if not allegiance:
                            logging.warning(f'Ignoring unknown allegiance "{allegianceCode}" for world {worldName} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')

                    zone = astronomer.parseZoneString(
                        dbSystem.zone() if dbSystem.zone() else '')
                    uwp = astronomer.UWP(
                        starport=dbSystem.starport(),
                        worldSize=dbSystem.worldSize(),
                        atmosphere=dbSystem.atmosphere(),
                        hydrographics=dbSystem.hydrographics(),
                        population=dbSystem.population(),
                        government=dbSystem.government(),
                        lawLevel=dbSystem.lawLevel(),
                        techLevel=dbSystem.techLevel())
                    economics = astronomer.Economics(
                        resources=dbSystem.resources(),
                        labour=dbSystem.labour(),
                        infrastructure=dbSystem.infrastructure(),
                        efficiency=dbSystem.efficiency())
                    culture = astronomer.Culture(
                        heterogeneity=dbSystem.heterogeneity(),
                        acceptance=dbSystem.acceptance(),
                        strangeness=dbSystem.strangeness(),
                        symbols=dbSystem.symbols())
                    nobilities = astronomer.Nobilities(dbSystem.nobilities())
                    remarks = astronomer.Remarks(
                        zone=zone,
                        uwp=uwp,
                        dbTradeCodes=dbSystem.tradeCodes(),
                        dbSophontPopulations=dbSystem.sophontPopulations(),
                        dbRulingAllegiances=dbSystem.rulingAllegiances(),
                        dbOwningSystems=dbSystem.owningSystems(),
                        dbColonySystems=dbSystem.colonySystems(),
                        dbResearchStations=dbSystem.researchStations(),
                        dbCustomRemarks=dbSystem.customRemarks(),
                        allegianceCodeMap=allegianceCodeMap,
                        sophontCodeMap=sophontCodeMap)
                    bases = astronomer.Bases(dbBases=dbSystem.bases())
                    stellar = astronomer.Stellar(dbStars=dbSystem.stars())
                    pbg = astronomer.PBG(
                        populationMultiplier=dbSystem.populationMultiplier(),
                        planetoidBelts=dbSystem.planetoidBelts(),
                        gasGiants=dbSystem.gasGiants())
                    systemWorlds = dbSystem.systemWorlds()

                    world = astronomer.World(
                        milieu=milieu,
                        hex=worldHex,
                        worldName=worldName,
                        isNameGenerated=isNameGenerated,
                        sectorName=sectorName,
                        subsectorName=subsectorName,
                        allegiance=allegiance,
                        zone=zone,
                        uwp=uwp,
                        economics=economics,
                        culture=culture,
                        nobilities=nobilities,
                        bases=bases,
                        remarks=remarks,
                        systemWorlds=systemWorlds,
                        pbg=pbg,
                        stellar=stellar)

                    subsectorWorlds = subsectorWorldsMap[subsectorCode]
                    subsectorWorlds.append(world)
                except Exception as ex:
                    logging.warning(
                        f'Failed to load system {dbSystem.id()} in data for sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                        exc_info=ex)

        subsectors = []
        for subsectorCode in subsectorCodes:
            subsectorName, isNameGenerated = subsectorNameMap[subsectorCode]
            subsectorWorlds = subsectorWorldsMap[subsectorCode]
            subsectors.append(astronomer.Subsector(
                milieu=milieu,
                index=astronomer.SubsectorIndex(
                    sectorX=sectorX,
                    sectorY=sectorY,
                    code=subsectorCode),
                subsectorName=subsectorName,
                isNameGenerated=isNameGenerated,
                sectorName=sectorName,
                worlds=subsectorWorlds))

        dbRoutes = dbSector.routes()
        routes = []
        if dbRoutes:
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
                        logging.warning(
                            f'Ignoring invalid colour "{colour}" for route {dbRoute.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')
                        colour = None

                    allegianceCode = dbRoute.allegianceCode()
                    allegiance = None
                    if allegianceCode:
                        allegiance = allegianceCodeMap.get(allegianceCode)
                        if not allegiance:
                            logging.warning(
                                f'Ignoring unknown allegiance "{allegianceCode}" for route {dbRoute.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')

                    style = dbRoute.style()
                    if style:
                        style = WorldManager._mapLineStyle(style)
                        if not style:
                            logging.warning(
                                f'Ignoring invalid style "{dbRoute.style()}" for route {dbRoute.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')

                    routes.append(astronomer.Route(
                        startHex=startHex,
                        endHex=endHex,
                        allegiance=allegiance,
                        type=dbRoute.type(),
                        style=style,
                        colour=colour,
                        width=dbRoute.width()))
                except Exception as ex:
                    logging.warning(
                        f'Failed to load route {dbRoute.id()} for sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                        exc_info=ex)

        dbBorders = dbSector.borders()
        borders = []
        if dbBorders:
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
                        logging.warning(
                            f'Ignoring invalid colour "{colour}" for border {dbBorder.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')
                        colour = None

                    allegianceCode = dbBorder.allegianceCode()
                    allegiance = None
                    if allegianceCode:
                        allegiance = allegianceCodeMap.get(allegianceCode)
                        if not allegiance:
                            logging.warning(
                                f'Ignoring unknown allegiance "{allegianceCode}" for border {dbBorder.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')

                    style = dbBorder.style()
                    if style:
                        style = WorldManager._mapLineStyle(style)
                        if not style:
                            logging.warning(
                                f'Ignoring invalid style "{dbBorder.style()}" for border {dbBorder.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')

                    borders.append(astronomer.Border(
                        hexList=hexes,
                        allegiance=allegiance,
                        style=style,
                        colour=colour,
                        label=dbBorder.label(),
                        labelWorldX=dbBorder.labelWorldX(),
                        labelWorldY=dbBorder.labelWorldY(),
                        showLabel=dbBorder.showLabel(),
                        wrapLabel=dbBorder.wrapLabel()))
                except Exception as ex:
                    logging.warning(
                        f'Failed to load border {dbBorder.id()} for sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                        exc_info=ex)

        dbRegions = dbSector.regions()
        regions = []
        if dbRegions:
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
                        logging.warning(f'Ignoring invalid colour "{colour}" for region {dbRegion.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')
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
                    logging.warning(
                        f'Failed to load region {dbRegion.id()} for sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                        exc_info=ex)

        dbLabels = dbSector.labels()
        labels = []
        if dbLabels:
            for dbLabel in dbLabels:
                try:
                    colour = dbLabel.colour()
                    if colour and not common.isValidHtmlColour(htmlColour=colour):
                        logging.warning(
                            f'Ignoring invalid colour "{colour}" for label {dbLabel.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')
                        colour = None

                    size = dbLabel.size()
                    if size:
                        size = WorldManager._mapLabelSize(size)
                        if not size:
                            logging.warning(
                                f'Ignoring invalid size "{dbLabel.size()}" for label {dbLabel.id()} in sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}')

                    labels.append(astronomer.Label(
                        text=dbLabel.text(),
                        worldX=dbLabel.worldX(),
                        worldY=dbLabel.worldY(),
                        colour=colour,
                        size=size,
                        wrap=dbLabel.wrap()))
                except Exception as ex:
                    logging.warning(
                        f'Failed to load label {dbLabel.id()} for sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                        exc_info=ex)

        try:
            tags = astronomer.SectorTagging(dbTags=dbSector.tags())
        except Exception as ex:
            logging.warning(
                f'Failed to load sector tagging for sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                exc_info=ex)

        dbPrimaryPublication = dbSector.publication()
        dbPrimaryAuthor = dbSector.author()
        dbPrimaryPublisher = dbSector.publisher()
        dbPrimaryReference = dbSector.reference()
        dbCredits = dbSector.credits()
        dbProducts = dbSector.products()
        sources = None
        if dbPrimaryPublication or dbPrimaryAuthor or dbPrimaryPublisher or dbPrimaryReference or dbCredits or dbProducts:
            primary = None
            if dbPrimaryPublication or dbPrimaryAuthor or dbPrimaryPublisher or dbPrimaryReference:
                try:
                    primary = astronomer.SectorSource(
                        publication=dbPrimaryPublication,
                        author=dbPrimaryAuthor,
                        publisher=dbPrimaryPublisher,
                        reference=dbPrimaryReference)
                except Exception as ex:
                    logging.warning(
                        f'Failed to load primary source for sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                        exc_info=ex)

            products = []
            if dbProducts:
                for dbProduct in dbProducts:
                    try:
                        products.append(astronomer.SectorSource(
                            publication=dbProduct.publication(),
                            author=dbProduct.author(),
                            publisher=dbProduct.publisher(),
                            reference=dbProduct.reference()))
                    except Exception as ex:
                        logging.warning(
                            f'Failed to load source {dbProduct.id()} for sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                            exc_info=ex)

            try:
                sources = astronomer.SectorSources(
                    credits=dbCredits,
                    primary=primary,
                    products=products)
            except Exception as ex:
                logging.warning(
                    f'Failed to load sources for sector {sectorName} at ({sectorX}, {sectorY}) from {milieu.value}',
                    exc_info=ex)

        return astronomer.Sector(
            name=sectorName,
            milieu=milieu,
            index=astronomer.SectorIndex(sectorX=sectorX, sectorY=sectorY),
            alternateNames=alternateNames,
            abbreviation=dbSector.abbreviation(),
            sectorLabel=dbSector.sectorLabel(),
            subsectors=subsectors,
            allegiances=allegianceCodeMap.values(),
            sophonts=sophontCodeMap.values(),
            routes=routes,
            borders=borders,
            regions=regions,
            labels=labels,
            selected=dbSector.selected(),
            tags=tags,
            sources=sources,
            isCustom=dbSector.isCustom())

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
