import astronomer
import common
import logging
import multiverse
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
                    logging.warning('Failed to create allegiance {objectId} when loading sector {sectorId} ({name})'.format(
                            objectId=dbAllegiance.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName),
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
                    logging.warning('Failed to create sophont {objectId} when loading sector {sectorId} ({name})'.format(
                            objectId=dbSophont.id(),
                            sectorId=dbSector.id(),
                            name=sectorLoggingName),
                        exc_info=ex)

        dbSystems = dbSector.systems()
        if dbSystems:
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


                    subsectorIndex = worldHex.subsectorIndex()
                    subsectorCode = subsectorIndex.code()
                    subsectorName, _ = subsectorNameMap[subsectorCode]

                    allegianceCode = dbSystem.allegianceCode()
                    allegiance = None
                    if allegianceCode:
                        allegiance = allegianceCodeMap.get(allegianceCode)
                        if not allegiance:
                            logging.warning('Ignoring unknown allegiance "{code}" when loading system {systemId} in sector {sectorId} ({name})'.format(
                                code=allegianceCode,
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

                    try:
                        uwp = astronomer.UWP(
                            starport=dbSystem.starport(),
                            worldSize=dbSystem.worldSize(),
                            atmosphere=dbSystem.atmosphere(),
                            hydrographics=dbSystem.hydrographics(),
                            population=dbSystem.population(),
                            government=dbSystem.government(),
                            lawLevel=dbSystem.lawLevel(),
                            techLevel=dbSystem.techLevel())
                    except Exception as ex:
                        logging.warning('Failed to create UWP when loading system {systemId} in sector {sectorId} ({name})'.format(
                                systemId=dbSystem.id(),
                                sectorId=dbSector.id(),
                                name=systemLoggingName),
                            exc_info=ex)
                        uwp = astronomer.UWP()

                    try:
                        economics = astronomer.Economics(
                            resources=dbSystem.resources(),
                            labour=dbSystem.labour(),
                            infrastructure=dbSystem.infrastructure(),
                            efficiency=dbSystem.efficiency())
                    except Exception as ex:
                        logging.warning('Failed to create economics when loading system {systemId} in sector {sectorId} ({name})'.format(
                                systemId=dbSystem.id(),
                                sectorId=dbSector.id(),
                                name=systemLoggingName),
                            exc_info=ex)
                        economics = astronomer.Economics()

                    try:
                        culture = astronomer.Culture(
                            heterogeneity=dbSystem.heterogeneity(),
                            acceptance=dbSystem.acceptance(),
                            strangeness=dbSystem.strangeness(),
                            symbols=dbSystem.symbols())
                    except Exception as ex:
                        logging.warning('Failed to create culture when loading system {systemId} in sector {sectorId} ({name})'.format(
                                systemId=dbSystem.id(),
                                sectorId=dbSector.id(),
                                name=systemLoggingName),
                            exc_info=ex)
                        culture = astronomer.Culture()

                    try:
                        pbg = astronomer.PBG(
                            populationMultiplier=dbSystem.populationMultiplier(),
                            planetoidBelts=dbSystem.planetoidBelts(),
                            gasGiants=dbSystem.gasGiants())
                    except Exception as ex:
                        logging.warning('Failed to create PBG when loading system {systemId} in sector {sectorId} ({name})'.format(
                                systemId=dbSystem.id(),
                                sectorId=dbSector.id(),
                                name=systemLoggingName),
                            exc_info=ex)
                        pbg = astronomer.PBG()

                    systemWorlds = dbSystem.systemWorlds()

                    dbTradeCodes = dbSystem.tradeCodes()
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

                    dbPopulations = dbSystem.sophontPopulations()
                    sophontPopulations: typing.Optional[typing.List[astronomer.SophontPopulation]] = None
                    if dbPopulations:
                        sophontPopulations = []
                        for dbPopulation in dbPopulations:
                            sophont = sophontCodeMap.get(dbPopulation.sophontCode())
                            if not sophont:
                                logging.warning('Ignoring sophont population {objectId} with unknown sophont "{code}" when loading system {systemId} in sector {sectorId} ({name})'.format(
                                    objectId=dbPopulation.id(),
                                    code=dbPopulation.sophontCode(),
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

                    dbRulingAllegiances = dbSystem.rulingAllegiances()
                    rulingAllegiances: typing.Optional[typing.List[str]] = None
                    if dbRulingAllegiances:
                        rulingAllegiances = []
                        for dbAllegiance in dbRulingAllegiances:
                            allegiance = allegianceCodeMap.get(dbAllegiance.allegianceCode())
                            if not allegiance:
                                logging.warning('Ignoring ruling allegiance {objectId} with unknown allegiance "{code}" when loading system {systemId} in sector {sectorId} ({name})'.format(
                                    objectId=dbAllegiance.id(),
                                    code=dbAllegiance.allegianceCode(),
                                    systemId=dbSystem.id(),
                                    sectorId=dbSector.id(),
                                    name=systemLoggingName))
                                continue
                            rulingAllegiances.append(allegiance)

                    dbOwningSystems = dbSystem.owningSystems()
                    owningWorlds: typing.Optional[typing.List[astronomer.WorldReference]] = None
                    if dbOwningSystems:
                        owningWorlds = []
                        for dbOwningSystem in dbOwningSystems:
                            try:
                                owningWorlds.append(astronomer.WorldReference(
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

                    dbColonySystems = dbSystem.colonySystems()
                    colonyWorlds: typing.Optional[typing.List[astronomer.WorldReference]] = None
                    if dbColonySystems:
                        colonyWorlds = []
                        for dbColonySystem in dbColonySystems:
                            try:
                                colonyWorlds.append(astronomer.WorldReference(
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

                    dbResearchStations = dbSystem.researchStations()
                    researchStations: typing.Optional[typing.List[str]] = None
                    if dbResearchStations:
                        researchStations = [s.code() for s in dbResearchStations]

                    dbCustomRemarks = dbSystem.customRemarks()
                    customRemarks: typing.Optional[typing.List[str]] = None
                    if dbCustomRemarks:
                        customRemarks = [r.remark() for r in dbCustomRemarks]

                    remarks = None
                    try:
                        remarks = astronomer.Remarks(
                            uwp=uwp,
                            tradeCodes=tradeCodes,
                            sophontPopulations=sophontPopulations,
                            rulingAllegiances=rulingAllegiances,
                            owningSystems=owningWorlds,
                            colonySystems=colonyWorlds,
                            researchStations=researchStations,
                            customRemarks=customRemarks)
                    except Exception as ex:
                        logging.warning('Failed to create remarks when loading system {systemId} in sector {sectorId} ({name})'.format(
                                systemId=dbSystem.id(),
                                sectorId=dbSector.id(),
                                name=systemLoggingName),
                            exc_info=ex)

                    dbNobilities = dbSystem.nobilities()
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

                    nobilities = None
                    try:
                        nobilities = astronomer.Nobilities(nobilities=nobilityTypes)
                    except Exception as ex:
                        logging.warning('Failed to create nobilities when loading system {systemId} in sector {sectorId} ({name})'.format(
                                systemId=dbSystem.id(),
                                sectorId=dbSector.id(),
                                name=systemLoggingName),
                            exc_info=ex)

                    dbBases = dbSystem.bases()
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

                    bases = None
                    try:
                        bases = astronomer.Bases(bases=baseTypes)
                    except Exception as ex:
                        logging.warning('Failed to create bases when loading system {systemId} in sector {sectorId} ({name})'.format(
                                systemId=dbSystem.id(),
                                sectorId=dbSector.id(),
                                name=systemLoggingName),
                            exc_info=ex)

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
                        worldName=systemName,
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
                    logging.warning('Failed to load system {systemId} in sector {sectorId} ({name})'.format(
                            systemId=dbSystem.id(),
                            sectorId=dbSector.id(),
                            name=systemLoggingName),
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

                    allegianceCode = dbRoute.allegianceCode()
                    allegiance = None
                    if allegianceCode:
                        allegiance = allegianceCodeMap.get(allegianceCode)
                        if not allegiance:
                            logging.warning('Ignoring unknown allegiance code "{code}" for route {objectId} when loading sector {sectorId} ({name})'.format(
                                code=allegianceCode,
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
                        allegiance=allegiance,
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

                    allegianceCode = dbBorder.allegianceCode()
                    allegiance = None
                    if allegianceCode:
                        allegiance = allegianceCodeMap.get(allegianceCode)
                        if not allegiance:
                            logging.warning('Ignoring unknown allegiance code "{code}" for border {objectId} when loading sector {sectorId} ({name})'.format(
                                code=allegianceCode,
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
                        allegiance=allegiance,
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
                    logging.warning('Failed to create primary source when loading sector {sectorId} ({name})'.format(
                            sectorId=dbSector.id(),
                            name=sectorLoggingName),
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
                        logging.warning('Failed to create source {objectId} when loading sector {sectorId} ({name})'.format(
                                objectId=dbProduct.id(),
                                sectorId=dbSector.id(),
                                name=sectorLoggingName),
                            exc_info=ex)

            try:
                sources = astronomer.SectorSources(
                    credits=dbCredits,
                    primary=primary,
                    products=products)
            except Exception as ex:
                logging.warning('Failed to create sources when loading sector {sectorId} ({name})'.format(
                        sectorId=dbSector.id(),
                        name=sectorLoggingName),
                    exc_info=ex)

        return astronomer.Sector(
            isCustom=dbSector.isCustom(),
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
            tagging=tagging,
            sources=sources)

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
