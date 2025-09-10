import common
import fnmatch
import re
import logging
import math
import threading
import multiverse
import typing

# This object is thread safe, however the world objects are only thread safe
# as they are currently read only (i.e. once loaded they never change).
class WorldManager(object):
    class _MilieuData(object):
        def __init__(self):
            self.sectorList: typing.List[multiverse.Sector] = []
            self.canonicalNameMap: typing.Dict[str, multiverse.Sector] = {}
            self.alternateNameMap: typing.Dict[str, typing.List[multiverse.Sector]] = {}
            self.sectorIndexMap: typing.Dict[typing.Tuple[int, int], multiverse.Sector] = {}
            self.subsectorNameMap: typing.Dict[str, typing.List[multiverse.Subsector]] = {}
            self.subsectorSectorMap: typing.Dict[multiverse.Subsector, multiverse.Sector] = {}
            self.worldPositionMap: typing.Dict[typing.Tuple[int, int], multiverse.World] = {}
            self.mainsList: typing.List[multiverse.Main] = []
            self.hexMainMap: typing.Dict[multiverse.HexPosition, multiverse.Main] = {}

    # To mimic the behaviour of Traveller Map, the world position data for
    # M1105 is used as placeholders if the specified milieu doesn't have
    # a sector at that location. The world details may not be valid for the
    # specified milieu but the position is
    _PlaceholderMilieu = multiverse.Milieu.M1105

    # The absolute and relative hex patterns match search strings formatted
    # as 2 or 4 comma separated signed integers respectively, optionally
    # surrounded by brackets. All integer values are extracted.
    _AbsoluteHexSearchPattern = re.compile(r'^\(?(-?\d+)[,\s]?\s*(-?\d+)\)?$')
    _RelativeHexSearchPattern = re.compile(r'^\(?(-?\d+)[,\s]?\s*(-?\d+)[,\s]?\s*(-?\d+)[,\s]?\s*(-?\d+)\)?$')
    # The sector hex search pattern matches a search string with the format
    # of a sector hex string optionally with the subsector in brackets
    # following it (i.e. the canonical name format used for a dead space
    # hex). The sector hex string is extracted but any subsector is discarded
    # as the sector hex uniquely identifies the world
    _SectorHexSearchPattern = re.compile(r'^(.+\s[0-9]{4})(?:\s+\(\s*.+\s*\))?$')
    # The world search pattern matches a search string with the format of
    # a world name followed by its subsector in brackets. Both the world name
    # and subsector name are extracted
    _WorldSearchPattern = re.compile(r'^(.+)\s+\(\s*(.+)\s*\)$')
    # Route and border style sheet regexes
    _BorderStylePattern = re.compile(r'border\.(\w+)')
    _RouteStylePattern = re.compile(r'route\.(\w+)')

    # Pattern used by Traveller Map to replace white space with '\n' to do
    # word wrapping
    # Use with `_WrapPattern.sub('\n', label)` to  replace
    _LineWrapPattern = re.compile(r'\s+(?![a-z])')

    # This is the value used by Traveller Map (tools\mains.js)
    _MinMainWorldCount = 5

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _milieuDataMap: typing.Dict[multiverse.Milieu, _MilieuData] = {}

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
        if self._milieuDataMap:
            return # Sector map already loaded

        # Acquire lock while loading sectors
        with self._lock:
            if self._milieuDataMap:
                # Another thread already loaded the sectors between the point we found they
                # weren't loaded and the point it acquired the mutex.
                return

            totalSectorCount = 0
            for milieu in multiverse.Milieu:
                totalSectorCount += multiverse.DataStore.instance().sectorCount(milieu=milieu)

            progress = 0
            for milieu in multiverse.Milieu:
                milieuData = WorldManager._MilieuData()

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

                    milieuData.sectorList.append(sector)
                    milieuData.sectorIndexMap[(sectorInfo.x(), sectorInfo.y())] = sector

                    # Add canonical name to the main name map. The name is added lower case as lookups are
                    # case insensitive
                    milieuData.canonicalNameMap[sectorInfo.canonicalName().lower()] = sector

                    # Add alternate names and abbreviations to the alternate name map
                    alternateNames = sector.alternateNames()
                    if alternateNames:
                        for alternateName in alternateNames:
                            alternateName = alternateName.lower()
                            sectorList = milieuData.alternateNameMap.get(alternateName)
                            if not sectorList:
                                sectorList = []
                                milieuData.alternateNameMap[alternateName] = sectorList
                            sectorList.append(sector)

                    abbreviation = sector.abbreviation()
                    if abbreviation:
                        abbreviation = abbreviation.lower()
                        sectorList = milieuData.alternateNameMap.get(abbreviation)
                        if not sectorList:
                            sectorList = []
                            milieuData.alternateNameMap[abbreviation] = sectorList
                        sectorList.append(sector)

                    for subsector in sector.subsectors():
                        subsectorName = subsector.name()
                        subsectorName = subsectorName.lower()
                        subsectorList = milieuData.subsectorNameMap.get(subsectorName)
                        if not subsectorList:
                            subsectorList = []
                            milieuData.subsectorNameMap[subsectorName] = subsectorList
                        subsectorList.append(subsector)

                        milieuData.subsectorSectorMap[subsector] = sector

                    for world in sector.worlds():
                        hex = world.hex()
                        milieuData.worldPositionMap[(hex.absoluteX(), hex.absoluteY())] = world

                self._milieuDataMap[milieu] = milieuData

    def sectorNames(
            self,
            milieu: multiverse.Milieu
            ) -> typing.Iterable[str]:
        milieuData = self._milieuDataMap[milieu]

        sectorNames = []
        for sector in milieuData.sectorList:
            sectorNames.append(sector.name())
        return sectorNames

    def sectorByName(
            self,
            milieu: multiverse.Milieu,
            name: str
            ) -> multiverse.Sector:
        milieuData = self._milieuDataMap[milieu]
        return milieuData.canonicalNameMap.get(name.lower())

    def sectors(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.Sector]:
        return list(self.yieldSectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def subsectors(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.Subsector]:
        return list(self.yieldSubsectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def worldBySectorHex(
            self,
            milieu: multiverse.Milieu,
            sectorHex: str,
            ) -> typing.Optional[multiverse.World]:
        try:
            hex = self.sectorHexToPosition(milieu=milieu, sectorHex=sectorHex)
        except Exception as ex:
            return None
        return self.worldByPosition(milieu=milieu, hex=hex)

    def worldByPosition(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[multiverse.World]:
        milieuData = self._milieuDataMap[milieu]
        world = milieuData.worldPositionMap.get(hex.absolute())
        if not world and includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            sectorPos = multiverse.absoluteSpaceToSectorPos(hex.absolute())
            if sectorPos not in milieuData.sectorIndexMap:
                world = self.worldByPosition(
                    milieu=WorldManager._PlaceholderMilieu,
                    hex=hex,
                    includePlaceholders=False)
        return world

    def sectorByPosition(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[multiverse.Sector]:
        milieuData = self._milieuDataMap[milieu]
        sector = milieuData.sectorIndexMap.get(hex.sectorIndex().components())
        if not sector and includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            sector = self.sectorByPosition(
                milieu=WorldManager._PlaceholderMilieu,
                hex=hex,
                includePlaceholders=False)
        return sector

    def sectorBySectorIndex(
            self,
            milieu: multiverse.Milieu,
            index: multiverse.SectorIndex,
            includePlaceholders: bool = False
            ) -> typing.Optional[multiverse.Sector]:
        milieuData = self._milieuDataMap[milieu]
        sector = milieuData.sectorIndexMap.get(index.components())
        if not sector and includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            sector = self.sectorBySectorIndex(
                milieu=WorldManager._PlaceholderMilieu,
                index=index,
                includePlaceholders=False)
        return sector

    def subsectorByPosition(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[multiverse.Subsector]:
        sector = self.sectorByPosition(
            milieu=milieu,
            hex=hex,
            includePlaceholders=includePlaceholders)
        if not sector:
            return None
        subsectors = sector.subsectors()
        assert(len(subsectors) == 16)

        _, _, offsetX, offsetY = hex.relative()
        subsectorX = (offsetX - 1) // multiverse.SubsectorWidth
        subsectorY = (offsetY - 1) // multiverse.SubsectorHeight
        index = (subsectorY * multiverse.HorzSubsectorsPerSector) + subsectorX
        if index < 0 or index >= 16:
            return None

        return subsectors[index]

    def sectorsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.Sector]:
        return list(self.yieldSectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def subsectorsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.Subsector]:
        return list(self.yieldSubsectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def worlds(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.World]:
        return list(self.yieldWorlds(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def worldsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.World]:
        return list(self.yieldWorldsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def worldsInRadius(
            self,
            milieu: multiverse.Milieu,
            center: multiverse.HexPosition,
            searchRadius: int,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.World]:
        return list(self.yieldWorldsInRadius(
            milieu=milieu,
            center=center,
            radius=searchRadius,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def worldsInFlood(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[multiverse.World]:
        return list(self.yieldWorldsInFlood(
            milieu=milieu,
            hex=hex,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def positionToSectorHex(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> str:
        milieuData = self._milieuDataMap[milieu]

        sectorX, sectorY, offsetX, offsetY = hex.relative()
        sectorPos = (sectorX, sectorY)
        sector = milieuData.sectorIndexMap.get(sectorPos)

        if not sector and includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            placeholderData = self._milieuDataMap[WorldManager._PlaceholderMilieu]
            sector = placeholderData.sectorIndexMap.get(sectorPos)

        return multiverse.formatSectorHex(
            sectorName=sector.name() if sector else f'{sectorX}:{sectorY}',
            offsetX=offsetX,
            offsetY=offsetY)

    def sectorHexToPosition(
            self,
            milieu: multiverse.Milieu,
            sectorHex: str
            ) -> multiverse.HexPosition:
        milieuData = self._milieuDataMap[milieu]

        sectorName, offsetX, offsetY = multiverse.splitSectorHex(
            sectorHex=sectorHex)

        # Sector name lookup is case insensitive. The sector name map stores
        # sector names in lower so search name should be converted to lower case
        # before searching
        sectorName = sectorName.lower()

        # Check to see if the sector name is a canonical sector name
        sector = milieuData.canonicalNameMap.get(sectorName)
        if not sector:
            # Make a best effort attempt to find the sector by looking at
            # abbreviations/alternate names and subsector names. This is
            # important as in some places the official data does ths for things
            # like owner/colony worlds sector hexes. These matches are not
            # always unique so just use the first if more than one is found
            sectors = milieuData.alternateNameMap.get(sectorName)
            if sectors:
                # Alternate sector name match
                sector = sectors[0]
            else:
                subsectors = milieuData.subsectorNameMap.get(sectorName)
                if subsectors:
                    # Subsector name match
                    sector = milieuData.subsectorSectorMap.get(subsectors[0])

        if sector:
            return multiverse.HexPosition(
                sectorIndex=sector.index(),
                offsetX=offsetX,
                offsetY=offsetY)

        # Check to see if the sector name is a sector x/y separated by a colon.
        # This is the format used by positionToSectorHex if there is no sector
        # at the specified hex
        tokens = sectorName.split(':')
        if len(tokens) == 2:
            try:
                sectorX = int(tokens[0])
                sectorY = int(tokens[1])
                return multiverse.HexPosition(
                    sectorX=sectorX,
                    sectorY=sectorY,
                    offsetX=offsetX,
                    offsetY=offsetY)
            except:
                pass

        if not sector:
            raise KeyError(f'Failed to resolve sector {sectorName} for sector hex {sectorHex}')

    def stringToPosition(
            self,
            milieu: multiverse.Milieu,
            string: str,
            ) -> multiverse.HexPosition:
        testString = string.strip()
        if not testString:
            raise ValueError(f'Invalid position string "{string}"')

        result = self._SectorHexSearchPattern.match(testString)
        if result:
            try:
                return self.sectorHexToPosition(milieu=milieu, sectorHex=testString)
            except:
                # Search string is not a valid sector hex. The search pattern
                # regex was matched so it should have the correct format, most
                # likely the sector name doesn't match a known sector
                pass

        result = self._AbsoluteHexSearchPattern.match(testString)
        if result:
            return multiverse.HexPosition(
                absoluteX=int(result.group(1)),
                absoluteY=int(result.group(2)))

        result = self._RelativeHexSearchPattern.match(testString)
        if result:
            sectorX = int(result.group(1))
            sectorY = int(result.group(2))
            offsetX = int(result.group(3))
            offsetY = int(result.group(4))
            if (offsetX >= 0  and offsetX < multiverse.SectorWidth) and \
                    (offsetY >= 0 and offsetY < multiverse.SectorHeight):
                return multiverse.HexPosition(
                    sectorX=sectorX,
                    sectorY=sectorY,
                    offsetX=offsetX,
                    offsetY=offsetY)

        raise ValueError(f'Invalid position string "{string}"')

    def canonicalHexName(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            ) -> str:
        world = self.worldByPosition(milieu=milieu, hex=hex)
        if world:
            return world.name(includeSubsector=True)
        try:
            name = self.positionToSectorHex(milieu=milieu, hex=hex)
            subsector = self.subsectorByPosition(milieu=milieu, hex=hex)
            if subsector:
                name += f' ({subsector.name()})'
            return name
        except KeyError:
            return str(hex)

    def mainByPosition(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition
            ) -> typing.Optional[multiverse.Main]:
        milieuData = self._milieuDataMap[milieu]
        main = milieuData.hexMainMap.get(hex)
        if main:
            return main

        worlds = self.worldsInFlood(
            hex=hex,
            milieu=milieu,
            includePlaceholders=True)
        if len(worlds) < WorldManager._MinMainWorldCount:
            return None

        main = multiverse.Main(worlds=worlds)
        for world in worlds:
            milieuData.hexMainMap[world.hex()] = main

        return main

    def yieldSectors(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.Sector, None, None]:
        milieuData = self._milieuDataMap[milieu]
        for sector in milieuData.sectorList:
            if not filterCallback or filterCallback(sector):
                yield sector

        if includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            placeholderData = self._milieuDataMap[WorldManager._PlaceholderMilieu]
            for sector in placeholderData.sectorList:
                sectorIndex = sector.index()
                sectorPos = sectorIndex.components()
                if sectorPos not in milieuData.sectorIndexMap:
                    if not filterCallback or filterCallback(sector):
                        yield sector

    def yieldSectorsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.Sector, None, None]:
        milieuData = self._milieuDataMap[milieu]

        placeholderData = None
        if includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            placeholderData = self._milieuDataMap[WorldManager._PlaceholderMilieu]

        startX, finishX = common.minmax(upperLeft.sectorX(), lowerRight.sectorX())
        startY, finishY = common.minmax(upperLeft.sectorY(), lowerRight.sectorY())

        x = startX
        while x <= finishX:
            y = startY
            while y <= finishY:
                key = (x, y)
                sector = milieuData.sectorIndexMap.get(key)
                if not sector and placeholderData:
                    sector = placeholderData.sectorIndexMap.get(key)

                if sector and (not filterCallback or filterCallback(sector)):
                    yield sector
                y += 1
            x += 1

    def yieldSubsectors(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.Subsector, None, None]:
        milieuData = self._milieuDataMap[milieu]
        for sector in milieuData.sectorList:
            for subsector in sector.yieldSubsectors():
                if not filterCallback or filterCallback(subsector):
                    yield subsector

        if includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            placeholderData = self._milieuDataMap[WorldManager._PlaceholderMilieu]
            for sector in placeholderData.sectorList:
                sectorIndex = sector.index()
                sectorPos = sectorIndex.components()
                if sectorPos not in milieuData.sectorIndexMap:
                    for subsector in sector.yieldSubsectors():
                        if not filterCallback or filterCallback(subsector):
                            yield subsector

    def yieldSubsectorsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.Subsector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.Subsector, None, None]:
        milieuData = self._milieuDataMap[milieu]

        placeholderData = None
        if includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            placeholderData = self._milieuDataMap[WorldManager._PlaceholderMilieu]

        startX, finishX = common.minmax(upperLeft.absoluteX(), lowerRight.absoluteX())
        startY, finishY = common.minmax(upperLeft.absoluteY(), lowerRight.absoluteY())

        for x in range(startX, finishX + multiverse.SubsectorWidth, multiverse.SubsectorWidth):
            for y in range(startY, finishY + multiverse.SubsectorHeight, multiverse.SubsectorHeight):
                sectorX, sectorY, offsetX, offsetY = \
                    multiverse.absoluteSpaceToRelativeSpace((x, y))

                key = (sectorX, sectorY)
                sector = milieuData.sectorIndexMap.get(key)
                if not sector and placeholderData:
                    sector = placeholderData.sectorIndexMap.get(key)

                if not sector:
                    continue
                subsector = sector.subsectorByIndex(
                    indexX=(offsetX - 1) // multiverse.SubsectorWidth,
                    indexY=(offsetY - 1) // multiverse.SubsectorHeight)
                if subsector and (not filterCallback or filterCallback(subsector)):
                    yield subsector

    def yieldWorlds(
            self,
            milieu: multiverse.Milieu,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.World, None, None]:
        milieuData = self._milieuDataMap[milieu]
        for world in milieuData.worldPositionMap.values():
            if not filterCallback or filterCallback(world):
                yield world

        if includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            placeholderData = self._milieuDataMap[WorldManager._PlaceholderMilieu]
            for sector in placeholderData.sectorList:
                sectorIndex = sector.index()
                sectorPos = sectorIndex.components()
                if sectorPos not in milieuData.sectorIndexMap:
                    for world in sector.yieldWorlds():
                        if not filterCallback or filterCallback(world):
                            yield world

    def yieldWorldsInArea(
            self,
            milieu: multiverse.Milieu,
            upperLeft: multiverse.HexPosition,
            lowerRight: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.World, None, None]:
        milieuData = self._milieuDataMap[milieu]

        placeholderData = None
        if includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            placeholderData = self._milieuDataMap[WorldManager._PlaceholderMilieu]

        startX, finishX = common.minmax(upperLeft.absoluteX(), lowerRight.absoluteX())
        startY, finishY = common.minmax(upperLeft.absoluteY(), lowerRight.absoluteY())

        x = startX
        while x <= finishX:
            y = startY
            while y <= finishY:
                key = (x, y)
                world = milieuData.worldPositionMap.get(key)
                if not world and placeholderData:
                    sectorPos = multiverse.absoluteSpaceToSectorPos(key)
                    if sectorPos not in milieuData.sectorIndexMap:
                        world = placeholderData.worldPositionMap.get(key)

                if world and ((not filterCallback) or filterCallback(world)):
                    yield world
                y += 1
            x += 1

    def yieldWorldsInRadius(
            self,
            milieu: multiverse.Milieu,
            center: multiverse.HexPosition,
            radius: int,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.World, None, None]:
        milieuData = self._milieuDataMap[milieu]

        placeholderData = None
        if includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            placeholderData = self._milieuDataMap[WorldManager._PlaceholderMilieu]

        minLength = radius + 1
        maxLength = (radius * 2) + 1
        deltaLength = int(math.floor((maxLength - minLength) / 2))

        centerX, centerY = center.absolute()
        startX = centerX - radius
        finishX = centerX + radius
        startY = (centerY - radius) + deltaLength
        finishY = (centerY + radius) - deltaLength
        if (startX & 0b1) != 0:
            startY += 1
            if (radius & 0b1) != 0:
                finishY -= 1
        else:
            if (radius & 0b1) != 0:
                startY += 1
            finishY -= 1
        for x in range(startX, finishX + 1):
            if (x & 0b1) != 0:
                if x <= centerX:
                    startY -= 1
                else:
                    finishY -= 1
            else:
                if x <= centerX:
                    finishY += 1
                else:
                    startY += 1

            for y in range(startY, finishY + 1):
                key = (x, y)
                world = milieuData.worldPositionMap.get(key)
                if not world and placeholderData:
                    sectorPos = multiverse.absoluteSpaceToSectorPos(key)
                    if sectorPos not in milieuData.sectorIndexMap:
                        world = placeholderData.worldPositionMap.get(key)

                if world and ((not filterCallback) or filterCallback(world)):
                    yield world

    def yieldWorldsInFlood(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            filterCallback: typing.Callable[[multiverse.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[multiverse.World, None, None]:
        milieuData = self._milieuDataMap[milieu]

        placeholderData = None
        if includePlaceholders and milieu is not WorldManager._PlaceholderMilieu:
            placeholderData = self._milieuDataMap[WorldManager._PlaceholderMilieu]

        key = hex.absolute()
        world = milieuData.worldPositionMap.get(key)
        if not world and placeholderData:
            sectorPos = multiverse.absoluteSpaceToSectorPos(key)
            if sectorPos not in milieuData.sectorIndexMap:
                world = placeholderData.worldPositionMap.get(key)
        if not world:
            return

        if not filterCallback or filterCallback(world):
            yield world

        todo = [world]
        seen = set(todo)
        while todo:
            world = todo.pop(0)
            hex = world.hex()
            for edge in multiverse.HexEdge:
                adjacentHex = hex.neighbourHex(edge=edge)

                key = adjacentHex.absolute()
                adjacentWorld = milieuData.worldPositionMap.get(key)
                if not adjacentWorld and placeholderData:
                    sectorPos = multiverse.absoluteSpaceToSectorPos(key)
                    if sectorPos not in milieuData.sectorIndexMap:
                        adjacentWorld = placeholderData.worldPositionMap.get(key)

                if adjacentWorld and (adjacentWorld not in seen):
                    todo.append(adjacentWorld)
                    seen.add(adjacentWorld)

                    if not filterCallback or filterCallback(adjacentWorld):
                        yield adjacentWorld

    def searchForWorlds(
            self,
            milieu: multiverse.Milieu,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[multiverse.World]:
        milieuData = self._milieuDataMap[milieu]

        searchString = searchString.strip()
        if not searchString:
            # No matches if search string is empty after white space stripped
            return []

        # Check if the world string specifies a hex, if it does and there is
        # a world at that location then that is our only result
        try:
            hex = self.stringToPosition(milieu=milieu, string=searchString)
            foundWorld = milieuData.worldPositionMap.get(hex.absolute())
            if foundWorld:
                return [foundWorld]
        except:
            pass

        searchWorldLists = None
        result = self._WorldSearchPattern.match(searchString)
        filterString = searchString
        if result:
            # We've matched the sector search hint pattern so check to see if the hint is actually
            # a known sector. If it is then perform the search with just the world portion of the
            # search string and filter the results afterwards. If it's not a known sector then just
            # perform the search with the full search string as normal
            worldString = result.group(1)
            hintString = result.group(2)

            searchWorldLists = self.searchForSectors(milieu=milieu, searchString=hintString)
            for subsector in self.searchForSubsectors(milieu=milieu, searchString=hintString):
                sector = milieuData.subsectorSectorMap.get(subsector)
                if sector not in searchWorldLists:
                    searchWorldLists.append(subsector)

            if searchWorldLists:
                filterString = worldString

        if not searchWorldLists:
            # Search the worlds in all sectors. This will happen if no sector/subsector is specified
            # _or_ if the specified sector/subsector is unknown
            searchWorldLists = milieuData.sectorList

        strictExpression = re.compile(
            fnmatch.translate(filterString),
            re.IGNORECASE)
        wildExpression = None
        if filterString[-1:] != '*':
            # Try to mimic the behaviour of Traveller Map where just typing the start of a world name
            # will match the world without needing to specify wild cards
            wildExpression = re.compile(
                fnmatch.translate(filterString + '*'),
                re.IGNORECASE)

        matches: typing.List[multiverse.World] = []
        for worldList in searchWorldLists:
            for world in worldList:
                if strictExpression.match(world.name()):
                    matches.append(world)
                elif wildExpression and wildExpression.match(world.name()):
                    matches.append(world)

        matches.sort(
            key=lambda world: f'{world.name()}/{world.subsectorName()}/{world.sectorName()}'.casefold())
        if maxResults and len(matches) >= maxResults:
            return matches[:maxResults]
        seen = set(matches)

        # If the search string matches any sub sectors add any worlds that
        # we've not already seen. Ordering of this relative to sectors
        # matches is important as sub sectors are more specific so matches
        # should be listed first in results
        subsectorMatches: typing.List[multiverse.World] = []
        for subsector in self.searchForSubsectors(milieu=milieu, searchString=searchString):
            for world in subsector:
                if world not in seen:
                    subsectorMatches.append(world)

        subsectorMatches.sort(
            key=lambda world: f'{world.name()}/{world.subsectorName()}/{world.sectorName()}'.casefold())
        for world in subsectorMatches:
            matches.append(world)
            if maxResults and len(matches) >= maxResults:
                return matches
            seen.add(world)

        # If the search string matches any sectors add any worlds that
        # we've not already seen
        sectorMatches: typing.List[multiverse.World] = []
        for sector in self.searchForSectors(milieu=milieu, searchString=searchString):
            for world in sector:
                if world not in seen:
                    sectorMatches.append(world)

        sectorMatches.sort(
            key=lambda world: f'{world.name()}/{world.subsectorName()}/{world.sectorName()}'.casefold())
        for world in sectorMatches:
            matches.append(world)
            if maxResults and len(matches) >= maxResults:
                return matches
            seen.add(world)

        return matches

    def searchForSubsectors(
            self,
            milieu: multiverse.Milieu,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[multiverse.Subsector]:
        milieuData = self._milieuDataMap[milieu]

        searchString = searchString.strip()
        if not searchString:
            # No matches if search string is empty after white space stripped
            return []

        strictExpression = re.compile(
            fnmatch.translate(searchString),
            re.IGNORECASE)
        wildExpression = None
        if searchString[-1:] != '*':
            # Try to mimic the behaviour of Traveller Map where just typing the start of a name
            # will match the without needing to specify wild cards.
            wildExpression = re.compile(
                fnmatch.translate(searchString + '*'),
                re.IGNORECASE)

        matches: typing.List[multiverse.Subsector] = []
        for sector in milieuData.sectorList:
            for subsector in sector.subsectors():
                if strictExpression.match(subsector.name()):
                    matches.append(subsector)
                elif wildExpression and wildExpression.match(subsector.name()):
                    matches.append(subsector)

        matches.sort(
            key=lambda subsector: f'{subsector.name()}/{subsector.sectorName()}'.casefold())
        if maxResults and len(matches) > maxResults:
            return matches[:maxResults]

        return matches

    def searchForSectors(
            self,
            milieu: multiverse.Milieu,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[multiverse.Sector]:
        milieuData = self._milieuDataMap[milieu]

        searchString = searchString.strip()
        if not searchString:
            # No matches if search string is empty after white space stripped
            return []

        strictExpression = re.compile(
            fnmatch.translate(searchString),
            re.IGNORECASE)
        wildExpression = None
        if searchString[-1:] != '*':
            # Try to mimic the behaviour of Traveller Map where just typing the start of a name
            # will match the without needing to specify wild cards.
            wildExpression = re.compile(
                fnmatch.translate(searchString + '*'),
                re.IGNORECASE)

        matches: typing.List[multiverse.Sector] = []
        for sector in milieuData.sectorList:
            if strictExpression.match(sector.name()):
                matches.append(sector)
                continue
            elif wildExpression and wildExpression.match(sector.name()):
                matches.append(sector)
                continue

            alternateNames = sector.alternateNames()
            if alternateNames:
                matched = False
                for alternateName in alternateNames:
                    if strictExpression.match(alternateName):
                        matched = True
                        break
                    elif wildExpression and wildExpression.match(sector.name()):
                        matched = True
                        break
                if matched:
                    matches.append(sector)
                    continue

        matches.sort(key=lambda sector: sector.name().casefold())
        if maxResults and len(matches) > maxResults:
            return matches[:maxResults]

        return matches

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
