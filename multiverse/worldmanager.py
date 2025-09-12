import common
import re
import logging
import threading
import multiverse
import typing

# This object is thread safe, however the world objects are only thread safe
# as they are currently read only (i.e. once loaded they never change).
class WorldManager(object):
    # To mimic the behaviour of Traveller Map, the world position data for
    # M1105 is used as placeholders if the specified milieu doesn't have
    # a sector at that location. The world details may not be valid for the
    # specified milieu but the position is
    _PlaceholderMilieu = multiverse.Milieu.M1105

    # Route and border style sheet regexes
    _BorderStylePattern = re.compile(r'border\.(\w+)')
    _RouteStylePattern = re.compile(r'route\.(\w+)')

    # Pattern used by Traveller Map to replace white space with '\n' to do
    # word wrapping
    # Use with `_WrapPattern.sub('\n', label)` to  replace
    _LineWrapPattern = re.compile(r'\s+(?![a-z])')

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _universe: multiverse.Universe = None

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

            totalSectorCount = 0
            for milieu in multiverse.Milieu:
                totalSectorCount += multiverse.DataStore.instance().sectorCount(milieu=milieu)

            sectors = []
            progress = 0
            for milieu in multiverse.Milieu:
                for sectorInfo in multiverse.DataStore.instance().sectors(milieu=milieu):
                    canonicalName = sectorInfo.canonicalName()
                    logging.debug(f'Loading worlds for sector {canonicalName}')

                    if progressCallback:
                        stage = f'{milieu.value} - {canonicalName}'
                        progress += 1
                        progressCallback(stage, progress, totalSectorCount)

                    sectorContent = multiverse.DataStore.instance().sectorFileData(
                        sectorName=canonicalName,
                        milieu=milieu)

                    metadataContent = multiverse.DataStore.instance().sectorMetaData(
                        sectorName=canonicalName,
                        milieu=milieu)

                    try:
                        sector = self._loadSector(
                            milieu=milieu,
                            sectorInfo=sectorInfo,
                            sectorContent=sectorContent,
                            metadataContent=metadataContent)
                    except Exception as ex:
                        logging.error(f'Failed to load sector {canonicalName} in {milieu.value}', exc_info=ex)
                        continue

                    logging.debug(f'Loaded {sector.worldCount()} worlds for sector {canonicalName} in {milieu.value}')
                    sectors.append(sector)

            self._universe = multiverse.Universe(
                sectors=sectors,
                placeholderMilieu=WorldManager._PlaceholderMilieu)

    def sectorNames(
            self,
            milieu: multiverse.Milieu
            ) -> typing.Iterable[str]:
        return self._universe.sectorNames(milieu=milieu)

    def sectorByName(
            self,
            milieu: multiverse.Milieu,
            name: str
            ) -> multiverse.Sector:
        return self._universe.sectorByName(milieu=milieu, name=name)

    def sectors(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.Sector]:
        return self._universe.sectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def subsectors(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.Subsector]:
        return self._universe.subsectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def worldBySectorHex(
            self,
            milieu: multiverse.Milieu,
            sectorHex: str,
            ) -> typing.Optional[multiverse.World]:
        return self._universe.worldBySectorHex(
            milieu=milieu,
            sectorHex=sectorHex)

    def worldByPosition(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[multiverse.World]:
        return self._universe.worldByPosition(
            milieu=milieu,
            hex=hex,
            includePlaceholders=includePlaceholders)

    def sectorByPosition(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[multiverse.Sector]:
        return self._universe.sectorByPosition(
            milieu=milieu,
            hex=hex,
            includePlaceholders=includePlaceholders)

    def sectorBySectorIndex(
            self,
            milieu: multiverse.Milieu,
            index: multiverse.SectorIndex,
            includePlaceholders: bool = False
            ) -> typing.Optional[multiverse.Sector]:
        return self._universe.sectorBySectorIndex(
            milieu=milieu,
            index=index,
            includePlaceholders=includePlaceholders)

    def subsectorByPosition(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[multiverse.Subsector]:
        return self._universe.subsectorByPosition(
            milieu=milieu,
            hex=hex,
            includePlaceholders=includePlaceholders)

    def sectorsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.Sector]:
        return self._universe.sectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def subsectorsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.Subsector]:
        return self._universe.subsectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def worlds(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.World]:
        return self._universe.worlds(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def worldsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.World]:
        return self._universe.worldsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def worldsInRadius(
            self,
            milieu: multiverse.Milieu,
            center: multiverse.HexPosition,
            searchRadius: int,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.World]:
        return self._universe.worldsInRadius(
            milieu=milieu,
            center=center,
            searchRadius=searchRadius,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def worldsInFlood(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.World]:
        return self._universe.worldsInFlood(
            milieu=milieu,
            hex=hex,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def positionToSectorHex(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> str:
        return self._universe.positionToSectorHex(
            milieu=milieu,
            hex=hex,
            includePlaceholders=includePlaceholders)

    def sectorHexToPosition(
            self,
            milieu: multiverse.Milieu,
            sectorHex: str
            ) -> multiverse.HexPosition:
        return self._universe.sectorHexToPosition(
            milieu=milieu,
            sectorHex=sectorHex)

    def stringToPosition(
            self,
            milieu: multiverse.Milieu,
            string: str,
            ) -> multiverse.HexPosition:
        return self._universe.stringToPosition(
            milieu=milieu,
            string=string)

    def canonicalHexName(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            ) -> str:
        return self._universe.canonicalHexName(
            milieu=milieu,
            hex=hex)

    def mainByPosition(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition
            ) -> typing.Optional[multiverse.Main]:
        return self._universe.mainByPosition(
            milieu=milieu,
            hex=hex)

    def yieldSectors(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.Sector, None, None]:
        return self._universe.yieldSectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldSectorsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.Sector, None, None]:
        return self._universe.yieldSectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldSubsectors(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.Subsector, None, None]:
        return self._universe.yieldSubsectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldSubsectorsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.Subsector, None, None]:
        return self._universe.yieldSubsectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldWorlds(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.World, None, None]:
        return self._universe.yieldWorlds(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldWorldsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.World, None, None]:
        return self._universe.yieldWorldsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldWorldsInRadius(
            self,
            milieu: multiverse.Milieu,
            center: multiverse.HexPosition,
            radius: int,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.World, None, None]:
        return self._universe.yieldWorldsInRadius(
            milieu=milieu,
            center=center,
            radius=radius,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def yieldWorldsInFlood(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.World, None, None]:
        return self._universe.yieldWorldsInFlood(
            milieu=milieu,
            hex=hex,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders)

    def searchForWorlds(
            self,
            milieu: multiverse.Milieu,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[multiverse.World]:
        return self._universe.searchForWorlds(
            milieu=milieu,
            searchString=searchString,
            maxResults=maxResults)

    def searchForSubsectors(
            self,
            milieu: multiverse.Milieu,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[multiverse.Subsector]:
        return self._universe.searchForSubsectors(
            milieu=milieu,
            searchString=searchString,
            maxResults=maxResults)

    def searchForSectors(
            self,
            milieu: multiverse.Milieu,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[multiverse.Sector]:
        return self._universe.searchForSectors(
            milieu=milieu,
            searchString=searchString,
            maxResults=maxResults)

    @staticmethod
    def _loadSector(
            milieu: multiverse.Milieu,
            sectorInfo: multiverse.SectorInfo,
            sectorContent: str,
            metadataContent: str
            ) -> multiverse.Sector:
        sectorName = sectorInfo.canonicalName()
        sectorX = sectorInfo.x()
        sectorY = sectorInfo.y()

        subsectorNameMap: typing.Dict[
            str, # Subsector code (A-P)
            typing.Tuple[
                str, # Subsector name
                bool # True if the name was generated
                ]] = {}
        subsectorWorldsMap: typing.Dict[
            str, # Subsector code (A-P)
            typing.List[multiverse.World]
        ] = {}
        allegianceNameMap: typing.Dict[
            str, # Allegiance code
            str # Allegiance name
        ] = {}

        # Setup default subsector names. Some sectors just use the code A-P but we need
        # something unique
        subsectorCodes = list(map(chr, range(ord('A'), ord('P') + 1)))
        for subsectorCode in subsectorCodes:
            subsectorNameMap[subsectorCode] = (f'{sectorName} Subsector {subsectorCode}', True)
            subsectorWorldsMap[subsectorCode] = []

        rawMetadata = multiverse.readMetadata(
            content=metadataContent,
            format=sectorInfo.metadataFormat(),
            identifier=sectorName)

        subsectorNames = rawMetadata.subsectorNames()
        if subsectorNames:
            for subsectorCode, subsectorName in subsectorNames.items():
                if not subsectorCode or not subsectorName:
                    continue

                # NOTE: Unlike most other places, it's intentional that this is upper
                subsectorCode = subsectorCode.upper()
                subsectorNameMap[subsectorCode] = (subsectorName, False)

        allegiances = rawMetadata.allegiances()
        if allegiances:
            for allegiance in allegiances:
                if not allegiance.code() or not allegiance.name():
                    continue

                # NOTE: The code here is intentionally left with the case as it appears int metadata as
                # there are some sectors where allegiances vary only by case (see AllegianceManager)
                allegianceNameMap[allegiance.code()] = allegiance.name()

        rawWorlds = multiverse.readSector(
            content=sectorContent,
            format=sectorInfo.sectorFormat(),
            identifier=sectorName)

        for rawWorld in rawWorlds:
            try:
                hex = rawWorld.attribute(multiverse.WorldAttribute.Hex)
                worldName = rawWorld.attribute(multiverse.WorldAttribute.Name)
                isNameGenerated = False
                if not worldName:
                    # If the world doesn't have a name the sector combined with the hex. This format
                    # is important as it's the same format as Traveller Map meaning searches will
                    # work
                    worldName = f'{sectorName} {hex}'
                    isNameGenerated = True

                subsectorCode = WorldManager._calculateSubsectorCode(relativeWorldHex=hex)
                subsectorName, _ = subsectorNameMap[subsectorCode]

                world = multiverse.World(
                    milieu=milieu,
                    hex=multiverse.HexPosition(
                        sectorX=sectorX,
                        sectorY=sectorY,
                        offsetX=int(hex[:2]),
                        offsetY=int(hex[-2:])),
                    worldName=worldName,
                    isNameGenerated=isNameGenerated,
                    sectorName=sectorName,
                    subsectorName=subsectorName,
                    allegiance=rawWorld.attribute(multiverse.WorldAttribute.Allegiance),
                    uwp=rawWorld.attribute(multiverse.WorldAttribute.UWP),
                    economics=rawWorld.attribute(multiverse.WorldAttribute.Economics),
                    culture=rawWorld.attribute(multiverse.WorldAttribute.Culture),
                    nobilities=rawWorld.attribute(multiverse.WorldAttribute.Nobility),
                    remarks=rawWorld.attribute(multiverse.WorldAttribute.Remarks),
                    zone=rawWorld.attribute(multiverse.WorldAttribute.Zone),
                    stellar=rawWorld.attribute(multiverse.WorldAttribute.Stellar),
                    pbg=rawWorld.attribute(multiverse.WorldAttribute.PBG),
                    systemWorlds=rawWorld.attribute(multiverse.WorldAttribute.SystemWorlds),
                    bases=rawWorld.attribute(multiverse.WorldAttribute.Bases))

                subsectorWorlds = subsectorWorldsMap[subsectorCode]
                subsectorWorlds.append(world)
            except Exception as ex:
                logging.warning(
                    f'Failed to process world entry on line {rawWorld.lineNumber()} in data for sector {sectorName}',
                    exc_info=ex)
                continue # Continue trying to process the rest of the worlds

        subsectors = []
        for subsectorCode in subsectorCodes:
            subsectorName, isNameGenerated = subsectorNameMap[subsectorCode]
            subsectorWorlds = subsectorWorldsMap[subsectorCode]
            subsectors.append(multiverse.Subsector(
                milieu=milieu,
                index=multiverse.SubsectorIndex(
                    sectorX=sectorX,
                    sectorY=sectorY,
                    code=subsectorCode),
                subsectorName=subsectorName,
                isNameGenerated=isNameGenerated,
                sectorName=sectorName,
                worlds=subsectorWorlds))

        # Add the allegiances for this sector to the allegiance manager
        multiverse.AllegianceManager.instance().addSectorAllegiances(
            milieu=milieu,
            sectorName=sectorName,
            allegiances=allegianceNameMap)

        styleSheet = rawMetadata.styleSheet()
        borderStyleMap: typing.Dict[
            str, # Allegiance/Type
            typing.Tuple[
                typing.Optional[str], # Colour
                typing.Optional[multiverse.Border.Style] # Style
            ]] = {}
        routeStyleMap: typing.Dict[
            str, # Allegiance/Type
            typing.Tuple[
                typing.Optional[str], # Colour
                typing.Optional[multiverse.Route.Style], # Style
                typing.Optional[float] # Width
            ]] = {}
        if styleSheet:
            try:
                content = multiverse.readCssContent(styleSheet)
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
                            f'Failed to process style sheet entry for {styleKey} in metadata for sector {sectorName}',
                            exc_info=ex)
            except Exception as ex:
                logging.warning(
                    f'Failed to parse style sheet for sector {sectorName}',
                    exc_info=ex)

        rawRoutes = rawMetadata.routes()
        routes = []
        if rawRoutes:
            for rawRoute in rawRoutes:
                try:
                    startHex = rawRoute.startHex()
                    startHex = multiverse.HexPosition(
                        sectorX=sectorX + (rawRoute.startOffsetX() if rawRoute.startOffsetX() else 0),
                        sectorY=sectorY + (rawRoute.startOffsetY() if rawRoute.startOffsetY() else 0),
                        offsetX=int(startHex[:2]),
                        offsetY=int(startHex[-2:]))

                    endHex = rawRoute.endHex()
                    endHex = multiverse.HexPosition(
                        sectorX=sectorX + (rawRoute.endOffsetX() if rawRoute.endOffsetX() else 0),
                        sectorY=sectorY + (rawRoute.endOffsetY() if rawRoute.endOffsetY() else 0),
                        offsetX=int(endHex[:2]),
                        offsetY=int(endHex[-2:]))

                    colour = rawRoute.colour()
                    style = WorldManager._mapRouteStyle(rawRoute.style())
                    width = rawRoute.width()

                    if not colour or not style or not width:
                        # This order of precedence matches the order in the Traveller Map
                        # DrawMicroRoutes code
                        stylePrecedence = [
                            rawRoute.allegiance(),
                            rawRoute.type(),
                            'Im']
                        for tag in stylePrecedence:
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
                        logging.debug(f'Ignoring invalid colour for border {rawRoute.fileIndex()} in sector {sectorName}')
                        colour = None

                    routes.append(multiverse.Route(
                        startHex=startHex,
                        endHex=endHex,
                        allegiance=rawRoute.allegiance(),
                        type=rawRoute.type(),
                        style=style,
                        colour=colour,
                        width=width))
                except Exception as ex:
                    logging.warning(
                        f'Failed to process route {rawRoute.fileIndex()} in metadata for sector {sectorName}',
                        exc_info=ex)

        rawBorders = rawMetadata.borders()
        borders = []
        if rawBorders:
            for rawBorder in rawBorders:
                try:
                    hexes = []
                    for rawHex in rawBorder.hexList():
                        hexes.append(multiverse.HexPosition(
                            sectorX=sectorX,
                            sectorY=sectorY,
                            offsetX=int(rawHex[:2]),
                            offsetY=int(rawHex[-2:])))

                    labelHex = rawBorder.labelHex()
                    if labelHex:
                        labelHex = multiverse.HexPosition(
                            sectorX=sectorX,
                            sectorY=sectorY,
                            offsetX=int(labelHex[:2]),
                            offsetY=int(labelHex[-2:]))
                    else:
                        labelHex = None

                    colour = rawBorder.colour()
                    style = WorldManager._mapBorderStyle(rawBorder.style())

                    if not colour or not style:
                        # This order of precedence matches the order in the Traveller Map
                        # DrawMicroBorders code
                        stylePrecedence = [
                            rawBorder.allegiance(),
                            'Im']
                        for tag in stylePrecedence:
                            if tag in borderStyleMap:
                                defaultColour, defaultStyle = borderStyleMap[tag]
                                if not colour:
                                    colour = defaultColour
                                if not style:
                                    style = defaultStyle
                                break

                    if colour and not common.validateHtmlColour(htmlColour=colour):
                        logging.debug(f'Ignoring invalid colour for border {rawBorder.fileIndex()} in sector {sectorName}')
                        colour = None

                    # Default label to allegiance and word wrap now so it doesn't need
                    # to be done every time the border is rendered
                    label = rawBorder.label()
                    if not label and rawBorder.allegiance():
                        label = multiverse.AllegianceManager.instance().allegianceName(
                            milieu=milieu,
                            code=rawBorder.allegiance(),
                            sectorName=sectorName)
                    if label and rawBorder.wrapLabel():
                        label = WorldManager._LineWrapPattern.sub('\n', label)

                    borders.append(multiverse.Border(
                        hexList=hexes,
                        allegiance=rawBorder.allegiance(),
                        # Show label use the same defaults as the traveller map Border class
                        showLabel=rawBorder.showLabel() if rawBorder.showLabel() != None else True,
                        label=label,
                        labelHex=labelHex,
                        labelOffsetX=rawBorder.labelOffsetX(),
                        labelOffsetY=rawBorder.labelOffsetY(),
                        style=style,
                        colour=colour))
                except Exception as ex:
                    logging.warning(
                        f'Failed to process border {rawBorder.fileIndex()} in metadata for sector {sectorName}',
                        exc_info=ex)

        rawRegions = rawMetadata.regions()
        regions = []
        if rawRegions:
            for rawRegion in rawRegions:
                try:
                    hexes = []
                    for rawHex in rawRegion.hexList():
                        hexes.append(multiverse.HexPosition(
                            sectorX=sectorX,
                            sectorY=sectorY,
                            offsetX=int(rawHex[:2]),
                            offsetY=int(rawHex[-2:])))

                    labelHex = rawRegion.labelHex()
                    if labelHex:
                        labelHex = multiverse.HexPosition(
                            sectorX=sectorX,
                            sectorY=sectorY,
                            offsetX=int(labelHex[:2]),
                            offsetY=int(labelHex[-2:]))
                    else:
                        labelHex = None

                    # Line wrap now so it doesn't need to be done every time the border is rendered
                    label = rawRegion.label()
                    if label and rawRegion.wrapLabel():
                        label = WorldManager._LineWrapPattern.sub('\n', label)

                    colour = rawRegion.colour()
                    if colour and not common.validateHtmlColour(htmlColour=colour):
                        logging.debug(f'Ignoring invalid colour for region {rawRegion.fileIndex()} in sector {sectorName}')
                        colour = None

                    regions.append(multiverse.Region(
                        hexList=hexes,
                        # Show label use the same defaults as the Traveller Map Border class
                        showLabel=rawRegion.showLabel() if rawRegion.showLabel() != None else True,
                        label=label,
                        labelHex=labelHex,
                        labelOffsetX=rawRegion.labelOffsetX(),
                        labelOffsetY=rawRegion.labelOffsetY(),
                        colour=colour))
                except Exception as ex:
                    logging.warning(
                        f'Failed to process region {rawRegion.fileIndex()} in metadata for sector {sectorName}',
                        exc_info=ex)

        rawLabels = rawMetadata.labels()
        labels = []
        if rawLabels:
            for rawLabel in rawLabels:
                try:
                    hex = rawLabel.hex()
                    hex = multiverse.HexPosition(
                        sectorX=sectorX,
                        sectorY=sectorY,
                        offsetX=int(hex[:2]),
                        offsetY=int(hex[-2:]))

                    # Line wrap now so it doesn't need to be done every time the border is rendered
                    text = rawLabel.text()
                    if rawLabel.wrap():
                        text = WorldManager._LineWrapPattern.sub('\n', text)

                    colour = rawLabel.colour()
                    if colour and not common.validateHtmlColour(htmlColour=colour):
                        logging.debug(f'Ignoring invalid colour for label {rawLabel.fileIndex()} in sector {sectorName}')
                        colour = None

                    labels.append(multiverse.Label(
                        text=text,
                        hex=hex,
                        colour=colour,
                        size=WorldManager._mapLabelSize(rawLabel.size()),
                        offsetX=rawLabel.offsetX(),
                        offsetY=rawLabel.offsetY()))
                except Exception as ex:
                    logging.warning(
                        f'Failed to process label {rawLabel.fileIndex()} in metadata for sector {sectorName}',
                        exc_info=ex)

        return multiverse.Sector(
            name=sectorName,
            milieu=milieu,
            index=multiverse.SectorIndex(
                sectorX=sectorX,
                sectorY=sectorY),
            alternateNames=rawMetadata.alternateNames(),
            abbreviation=rawMetadata.abbreviation(),
            sectorLabel=rawMetadata.sectorLabel(),
            subsectors=subsectors,
            routes=routes,
            borders=borders,
            regions=regions,
            labels=labels,
            selected=rawMetadata.selected() if rawMetadata.selected() else False,
            tags=rawMetadata.tags())

    _RouteStyleMap = {
        'solid': multiverse.Route.Style.Solid,
        'dashed': multiverse.Route.Style.Dashed,
        'dotted': multiverse.Route.Style.Dotted,
    }

    @staticmethod
    def _mapRouteStyle(
            style: typing.Optional[str]
            ) -> typing.Optional[multiverse.Route.Style]:
        if not style:
            return None
        lowerStyle = style.lower()
        mappedStyle = WorldManager._RouteStyleMap.get(lowerStyle)
        if not mappedStyle:
            raise ValueError(f'Invalid route style "{style}"')
        return mappedStyle

    _BorderStyleMap = {
        'solid': multiverse.Border.Style.Solid,
        'dashed': multiverse.Border.Style.Dashed,
        'dotted': multiverse.Border.Style.Dotted,
    }

    @staticmethod
    def _mapBorderStyle(
            style: typing.Optional[str]
            ) -> typing.Optional[multiverse.Border.Style]:
        if not style:
            return None
        lowerStyle = style.lower()
        mappedStyle = WorldManager._BorderStyleMap.get(lowerStyle)
        if not mappedStyle:
            raise ValueError(f'Invalid border style "{style}"')
        return mappedStyle

    _LabelSizeMap = {
        'small': multiverse.Label.Size.Small,
        'large': multiverse.Label.Size.Large,
    }

    def _mapLabelSize(
            size: typing.Optional[str]
            ) -> typing.Optional[multiverse.Label.Size]:
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

        subsectorX = (worldX - 1) // multiverse.SubsectorWidth
        if subsectorX < 0 or subsectorX >= multiverse.HorzSubsectorsPerSector:
            raise RuntimeError(f'Subsector X position for world hex "{relativeWorldHex}" is out of range')

        subsectorY = (worldY - 1) // multiverse.SubsectorHeight
        if subsectorY < 0 or subsectorY >= multiverse.VertSubsectorPerSector:
            raise RuntimeError(f'Subsector Y position for world hex "{relativeWorldHex}" is out of range')

        index = (subsectorY * multiverse.HorzSubsectorsPerSector) + subsectorX

        return chr(ord('A') + index)
