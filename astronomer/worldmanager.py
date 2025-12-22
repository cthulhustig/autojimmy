import astronomer
import common
import re
import logging
import multiverse
import threading
import typing

# TODO: Rename astronomer namespace to astrogator (check spelling)

# This object is thread safe, however the world objects are only thread safe
# as they are currently read only (i.e. once loaded they never change).
class WorldManager(object):
    # To mimic the behaviour of Traveller Map, the world position data for
    # M1105 is used as placeholders if the specified milieu doesn't have
    # a sector at that location. The world details may not be valid for the
    # specified milieu but the position is
    _PlaceholderMilieu = astronomer.Milieu.M1105

    # Route and border style sheet regexes. Note that the names that follow
    # the . can contain spaces
    _BorderStylePattern = re.compile(r'border(?:\.(.+))?')
    _RouteStylePattern = re.compile(r'route(?:\.(.+))?')

    # Pattern used by Traveller Map to replace white space with '\n' to do
    # word wrapping
    # Use with `_WrapPattern.sub('\n', label)` to  replace
    _LineWrapPattern = re.compile(r'\s+(?![a-z])')

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

            dbUniverse = multiverse.MultiverseDb.instance().loadUniverse(
                universeId=multiverse.customUniverseId(),
                # TODO: I probably need to wrap the progress callback so the text that
                # gets put out makes sense
                progressCallback=progressCallback)
            dbSectors = dbUniverse.sectors()
            totalSectorCount = len(dbSectors)

            maxProgress = totalSectorCount
            currentProgress = 0
            sectors = []
            for dbSector in dbSectors:
                canonicalName = dbSector.primaryName()
                milieu = astronomer.Milieu[dbSector.milieu()] # TODO: This is ugly

                logging.debug(f'Processing sector {canonicalName} from {milieu.value}')

                if progressCallback:
                    stage = f'Processing: {milieu.value} - {canonicalName}'
                    currentProgress += 1
                    progressCallback(stage, currentProgress, maxProgress)

                try:
                    sector = self._processSector(dbSector=dbSector)
                except Exception as ex:
                    logging.error(f'Failed to process sector {canonicalName} from {milieu.value}', exc_info=ex)
                    continue

                worldCount = len(dbSector.systems()) if dbSector.systems() else 0
                logging.debug(f'Loaded {worldCount} worlds for sector {canonicalName} from {milieu.value}')
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
        sector = self._processSector(dbSector=dbSector)
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
    def _processSector(
            dbSector: multiverse.DbSector
            ) -> astronomer.Sector:
        sectorName = dbSector.primaryName()
        sectorX = dbSector.sectorX()
        sectorY = dbSector.sectorY()

        milieu = astronomer.Milieu[dbSector.milieu()] # TODO: This is ugly

        # TODO: I'm currently throwing away the language info for the
        # primary and alternate names
        dbAlternateNames = dbSector.alternateNames()
        alternateNames = None
        if dbAlternateNames:
            alternateNames = []
            for name, _ in dbAlternateNames:
                alternateNames.append(name)

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

        subsectorNames = dbSector.subsectorNames()
        if subsectorNames:
            for subsectorIndex, subsectorName in subsectorNames:
                # NOTE: Unlike most other places, it's intentional that this is upper case
                subsectorCode = chr(ord('A') + subsectorIndex)
                subsectorNameMap[subsectorCode] = (subsectorName, False)

        allegianceCodeMap: typing.Dict[str, astronomer.Allegiance] = {}
        if dbSector.allegiances():
            for dbAllegiance in dbSector.allegiances():
                allegianceCodeMap[dbAllegiance.code()] = astronomer.Allegiance(
                    code=dbAllegiance.code(),
                    name=dbAllegiance.name(),
                    legacyCode=dbAllegiance.legacy(),
                    baseCode=dbAllegiance.base())

        dbSophonts = dbSector.sophonts()
        sophontsNameMap: typing.Dict[str, str] = {}
        if dbSophonts:
            for dbSophont in dbSophonts:
                sophontsNameMap[dbSophont.code()] = dbSophont.name()

        dbSystems = dbSector.systems()
        if dbSystems:
            for dbSystem in dbSystems:
                try:
                    hex = f'{dbSystem.hexX():02d}{dbSystem.hexY():02d}' # TODO: I'm not a fan of having to create this
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
                        worldName = f'{sectorName} {hex}'
                        isNameGenerated = True

                    subsectorCode = WorldManager._calculateSubsectorCode(relativeWorldHex=hex)
                    subsectorName, _ = subsectorNameMap[subsectorCode]

                    dbAllegiance = dbSystem.allegiance()
                    allegiance = None
                    if dbAllegiance:
                        allegiance = allegianceCodeMap.get(dbAllegiance.code())
                        if not allegiance:
                            raise RuntimeError(f'World {worldName} is using an allegiance that is not defined by the system')

                    # TODO: All this checking for null and using an empty string instead
                    # is ugly as hell
                    zone = astronomer.parseZoneString(
                        dbSystem.zone() if dbSystem.zone() else '')
                    uwp = astronomer.UWP(
                        dbSystem.uwp() if dbSystem.uwp() else '')
                    economics = astronomer.Economics(
                        dbSystem.economics() if dbSystem.economics() else '')
                    culture = astronomer.Culture(
                        dbSystem.culture() if dbSystem.culture() else '')
                    nobilities = astronomer.Nobilities(dbSystem.nobilities())
                    remarks = astronomer.Remarks(
                        zone=zone,
                        dbTradeCodes=dbSystem.tradeCodes(),
                        dbSophontPopulations=dbSystem.sophontPopulations(),
                        dbRulingAllegiances=dbSystem.rulingAllegiances(),
                        dbOwningSystems=dbSystem.owningSystems(),
                        dbColonySystems=dbSystem.colonySystems(),
                        dbResearchStations=dbSystem.researchStations(),
                        dbCustomRemarks=dbSystem.customRemarks())
                    bases = astronomer.Bases(dbBases=dbSystem.bases())
                    stellar = astronomer.Stellar(dbStars=dbSystem.stars())
                    pbg = astronomer.PBG(
                        dbSystem.pbg() if dbSystem.pbg() else '')
                    systemWorlds = dbSystem.systemWorlds()

                    world = astronomer.World(
                        milieu=milieu,
                        hex=astronomer.HexPosition(
                            sectorX=sectorX,
                            sectorY=sectorY,
                            offsetX=dbSystem.hexX(),
                            offsetY=dbSystem.hexY()),
                        worldName=worldName,
                        isNameGenerated=isNameGenerated,
                        sectorName=sectorName,
                        subsectorName=subsectorName,
                        allegiance=allegiance,
                        uwp=uwp,
                        economics=economics,
                        culture=culture,
                        nobilities=nobilities,
                        remarks=remarks,
                        zone=zone,
                        stellar=stellar,
                        pbg=pbg,
                        systemWorlds=systemWorlds,
                        bases=bases)

                    subsectorWorlds = subsectorWorldsMap[subsectorCode]
                    subsectorWorlds.append(world)
                except Exception as ex:
                    logging.warning(
                        f'Failed to process system {dbSystem.id()} in data for sector {sectorName} from {milieu.value}',
                        exc_info=ex)
                    continue # Continue trying to process the rest of the worlds

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

        styleSheet = dbSector.styleSheet()
        borderStyleMap: typing.Dict[
            str, # Allegiance/Type
            typing.Tuple[
                typing.Optional[str], # Colour
                typing.Optional[astronomer.Border.Style] # Style
            ]] = {}
        routeStyleMap: typing.Dict[
            str, # Allegiance/Type
            typing.Tuple[
                typing.Optional[str], # Colour
                typing.Optional[astronomer.Route.Style], # Style
                typing.Optional[float] # Width
            ]] = {}
        if styleSheet:
            try:
                content = astronomer.readCssContent(styleSheet)
                for styleKey, properties in content.items():
                    try:
                        match = WorldManager._BorderStylePattern.match(styleKey)
                        if match:
                            tag = match.group(1)
                            colour = properties.get('color')
                            style = WorldManager._mapBorderStyle(properties.get('style'))
                            if colour or style:
                                borderStyleMap[tag] = (colour, style)

                        match = WorldManager._RouteStylePattern.match(styleKey)
                        if match:
                            tag = match.group(1)
                            colour = properties.get('color')
                            style = WorldManager._mapRouteStyle(properties.get('style'))
                            width = properties.get('width')
                            if width:
                                width = float(width)
                            if colour or style or width:
                                routeStyleMap[tag] = (colour, style, width)
                    except Exception as ex:
                        logging.warning(
                            f'Failed to process style sheet entry for {styleKey} in metadata for sector {sectorName} from {milieu.value}',
                            exc_info=ex)
            except Exception as ex:
                logging.warning(
                    f'Failed to parse style sheet for sector {sectorName} from {milieu.value}',
                    exc_info=ex)

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
                    style = WorldManager._mapRouteStyle(dbRoute.style())
                    width = dbRoute.width()

                    dbAllegiance = dbRoute.allegiance()
                    if not colour or not style or not width:
                        # This order of precedence matches the order in the Traveller Map
                        # DrawMicroRoutes code
                        # TODO: Should this be done at convert time?
                        precedence = []
                        if dbRoute.allegiance():
                            precedence.append(dbRoute.allegiance().code())
                        elif dbRoute.type():
                            precedence.append(dbRoute.type())
                        precedence.append(None) # Use default if there is one

                        for tag in precedence:
                            if tag in routeStyleMap:
                                defaultColour, defaultStyle, defaultWidth = routeStyleMap[tag]
                                if not colour:
                                    colour = defaultColour
                                if not style:
                                    style = defaultStyle
                                if not width:
                                    width = defaultWidth
                                break

                    if colour and not common.validateHtmlColour(htmlColour=colour):
                        logging.debug(f'Ignoring invalid colour for border {dbRoute.id()} in sector {sectorName} from {milieu.value}')
                        colour = None

                    routes.append(astronomer.Route(
                        startHex=startHex,
                        endHex=endHex,
                        allegiance=dbAllegiance.code() if dbAllegiance else None,
                        type=dbRoute.type(),
                        style=style,
                        colour=colour,
                        width=width))
                except Exception as ex:
                    logging.warning(
                        f'Failed to process route {dbRoute.id()} in metadata for sector {sectorName} from {milieu.value}',
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

                    labelHexX = dbBorder.labelHexX()
                    labelHexY = dbBorder.labelHexY()
                    if labelHexX is not None and labelHexY is not None:
                        labelHex = astronomer.HexPosition(
                            sectorX=sectorX,
                            sectorY=sectorY,
                            offsetX=labelHexX,
                            offsetY=labelHexY)
                    else:
                        labelHex = None

                    colour = dbBorder.colour()
                    style = WorldManager._mapBorderStyle(dbBorder.style())

                    dbAllegiance = dbBorder.allegiance()
                    if not colour or not style:
                        # This order of precedence matches the order in the Traveller Map
                        # DrawMicroBorders code
                        # TODO: Should this be done at convert time?
                        precedence = []
                        if dbBorder.allegiance():
                            precedence.append(dbBorder.allegiance().code())
                        precedence.append(None) # Use default if there is one

                        for tag in precedence:
                            if tag in borderStyleMap:
                                defaultColour, defaultStyle = borderStyleMap[tag]
                                if not colour:
                                    colour = defaultColour
                                if not style:
                                    style = defaultStyle
                                break

                    if colour and not common.validateHtmlColour(htmlColour=colour):
                        logging.debug(f'Ignoring invalid colour for border {dbBorder.id()} in sector {sectorName} from {milieu.value}')
                        colour = None

                    # Default label to allegiance and word wrap now so it doesn't need
                    # to be done every time the border is rendered
                    # TODO: This is probably bad, should be done in cartographer and border
                    # should store a label and allegiance if the source data has both
                    label = dbBorder.label()
                    if not label and dbAllegiance:
                        label = dbAllegiance.name()
                    if label and dbBorder.wrapLabel():
                        label = WorldManager._LineWrapPattern.sub('\n', label)

                    borders.append(astronomer.Border(
                        hexList=hexes,
                        allegiance=dbAllegiance.code() if dbAllegiance else None,
                        # Show label use the same defaults as the traveller map Border class
                        # TODO: I think I've broken something here as show label can't be null in the
                        # DB. I suspect I need to move this logic to the converter
                        showLabel=dbBorder.showLabel() if dbBorder.showLabel() is not None else True,
                        label=label,
                        labelHex=labelHex,
                        labelOffsetX=dbBorder.labelOffsetX(),
                        labelOffsetY=dbBorder.labelOffsetY(),
                        style=style,
                        colour=colour))
                except Exception as ex:
                    logging.warning(
                        f'Failed to process border {dbBorder.id()} in metadata for sector {sectorName} from {milieu.value}',
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

                    labelHexX = dbRegion.labelHexX()
                    labelHexY = dbRegion.labelHexY()
                    if labelHexX is not None and labelHexY is not None:
                        labelHex = astronomer.HexPosition(
                            sectorX=sectorX,
                            sectorY=sectorY,
                            offsetX=labelHexX,
                            offsetY=labelHexY)
                    else:
                        labelHex = None

                    # Line wrap now so it doesn't need to be done every time the border is rendered
                    label = dbRegion.label()
                    if label and dbRegion.wrapLabel():
                        label = WorldManager._LineWrapPattern.sub('\n', label)

                    colour = dbRegion.colour()
                    if colour and not common.validateHtmlColour(htmlColour=colour):
                        logging.debug(f'Ignoring invalid colour for region {dbRegion.id()} in sector {sectorName} from {milieu.value}')
                        colour = None

                    regions.append(astronomer.Region(
                        hexList=hexes,
                        # Show label use the same defaults as the Traveller Map Border class
                        # TODO: I think I've broken something here as show label can't be null in the
                        # DB. I suspect I need to move this logic to the converter
                        showLabel=dbRegion.showLabel() if dbRegion.showLabel() is not None else True,
                        label=label,
                        labelHex=labelHex,
                        labelOffsetX=dbRegion.labelOffsetX(),
                        labelOffsetY=dbRegion.labelOffsetY(),
                        colour=colour))
                except Exception as ex:
                    logging.warning(
                        f'Failed to process region {dbRegion.id()} in metadata for sector {sectorName} from {milieu.value}',
                        exc_info=ex)

        dbLabels = dbSector.labels()
        labels = []
        if dbLabels:
            for dbLabel in dbLabels:
                try:
                    hex = astronomer.HexPosition(
                        sectorX=sectorX,
                        sectorY=sectorY,
                        offsetX=dbLabel.hexX(),
                        offsetY=dbLabel.hexY())

                    # Line wrap now so it doesn't need to be done every time the border is rendered
                    text = dbLabel.text()
                    if dbLabel.wrap():
                        text = WorldManager._LineWrapPattern.sub('\n', text)

                    colour = dbLabel.colour()
                    if colour and not common.validateHtmlColour(htmlColour=colour):
                        logging.debug(f'Ignoring invalid colour for label {dbLabel.id()} in sector {sectorName} from {milieu.value}')
                        colour = None

                    labels.append(astronomer.Label(
                        text=text,
                        hex=hex,
                        colour=colour,
                        size=WorldManager._mapLabelSize(dbLabel.size()),
                        offsetX=dbLabel.offsetX(),
                        offsetY=dbLabel.offsetY()))
                except Exception as ex:
                    logging.warning(
                        f'Failed to process label {dbLabel.id()} in metadata for sector {sectorName} from {milieu.value}',
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
                primary = astronomer.SectorSource(
                    publication=dbPrimaryPublication,
                    author=dbPrimaryAuthor,
                    publisher=dbPrimaryPublisher,
                    reference=dbPrimaryReference)

            products = []
            if dbProducts:
                for dbProduct in dbProducts:
                    products.append(astronomer.SectorSource(
                        publication=dbProduct.publication(),
                        author=dbProduct.author(),
                        publisher=dbProduct.publisher(),
                        reference=dbProduct.reference()))

            sources = astronomer.SectorSources(
                credits=dbCredits,
                primary=primary,
                products=products)

        return astronomer.Sector(
            name=sectorName,
            milieu=milieu,
            index=astronomer.SectorIndex(sectorX=sectorX, sectorY=sectorY),
            # TODO: This is ugly and it also means I'm throwing away the language information
            alternateNames=alternateNames,
            abbreviation=dbSector.abbreviation(),
            sectorLabel=dbSector.sectorLabel(),
            subsectors=subsectors,
            allegiances=allegianceCodeMap.values(),
            routes=routes,
            borders=borders,
            regions=regions,
            labels=labels,
            selected=dbSector.selected() if dbSector.selected() else False,
            tags=astronomer.SectorTagging(dbSector.tags()),
            sources=sources,
            isCustom=dbSector.isCustom())

    _RouteStyleMap = {
        'solid': astronomer.Route.Style.Solid,
        'dashed': astronomer.Route.Style.Dashed,
        'dotted': astronomer.Route.Style.Dotted,
    }

    @staticmethod
    def _mapRouteStyle(
            style: typing.Optional[str]
            ) -> typing.Optional[astronomer.Route.Style]:
        if not style:
            return None
        lowerStyle = style.lower()
        mappedStyle = WorldManager._RouteStyleMap.get(lowerStyle)
        if not mappedStyle:
            raise ValueError(f'Invalid route style "{style}"')
        return mappedStyle

    _BorderStyleMap = {
        'solid': astronomer.Border.Style.Solid,
        'dashed': astronomer.Border.Style.Dashed,
        'dotted': astronomer.Border.Style.Dotted,
    }

    @staticmethod
    def _mapBorderStyle(
            style: typing.Optional[str]
            ) -> typing.Optional[astronomer.Border.Style]:
        if not style:
            return None
        lowerStyle = style.lower()
        mappedStyle = WorldManager._BorderStyleMap.get(lowerStyle)
        if not mappedStyle:
            raise ValueError(f'Invalid border style "{style}"')
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
            raise ValueError(f'Invalid label size "{size}"')
        return mappedSize

    @staticmethod
    def _calculateSubsectorCode(
            relativeWorldHex: str
            ) -> str:
        if len(relativeWorldHex) != 4:
            raise RuntimeError(f'Invalid relative world hex "{relativeWorldHex}"')

        worldX = int(relativeWorldHex[:2])
        worldY = int(relativeWorldHex[-2:])

        subsectorX = (worldX - 1) // astronomer.SubsectorWidth
        if subsectorX < 0 or subsectorX >= astronomer.HorzSubsectorsPerSector:
            raise RuntimeError(f'Subsector X position for world hex "{relativeWorldHex}" is out of range')

        subsectorY = (worldY - 1) // astronomer.SubsectorHeight
        if subsectorY < 0 or subsectorY >= astronomer.VertSubsectorPerSector:
            raise RuntimeError(f'Subsector Y position for world hex "{relativeWorldHex}" is out of range')

        index = (subsectorY * astronomer.HorzSubsectorsPerSector) + subsectorX

        return chr(ord('A') + index)
