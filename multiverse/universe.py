import common
import fnmatch
import re
import math
import multiverse
import typing

class Universe(object):
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

    # This is the value used by Traveller Map (tools\mains.js)
    _MinMainWorldCount = 5

    def __init__(
            self,
            sectors: typing.Collection[multiverse.Sector], # Sectors for all milieu
            placeholderMilieu: typing.Optional[multiverse.Milieu] = None
            ) -> None:
        self._milieuDataMap: typing.Dict[multiverse.Milieu, Universe._MilieuData] = {}
        self._placeholderMilieu = placeholderMilieu

        for sector in sectors:
            milieu = sector.milieu()

            milieuData = self._milieuDataMap.get(milieu)
            if not milieuData:
                milieuData = Universe._MilieuData()
                self._milieuDataMap[milieu] = milieuData

            index = sector.index()
            milieuData.sectorList.append(sector)
            milieuData.sectorIndexMap[index.elements()] = sector

            # Add canonical name to the main name map. The name is added lower case as lookups are
            # case insensitive
            milieuData.canonicalNameMap[sector.name().lower()] = sector

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
        if not world and includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            sectorPos = multiverse.absoluteSpaceToSectorPos(hex.absolute())
            if sectorPos not in milieuData.sectorIndexMap:
                world = self.worldByPosition(
                    milieu=self._placeholderMilieu,
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
        sector = milieuData.sectorIndexMap.get(hex.sectorIndex().elements())
        if not sector and includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            sector = self.sectorByPosition(
                milieu=self._placeholderMilieu,
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
        sector = milieuData.sectorIndexMap.get(index.elements())
        if not sector and includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            sector = self.sectorBySectorIndex(
                milieu=self._placeholderMilieu,
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

        if not sector and includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap[self._placeholderMilieu]
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
        if len(worlds) < Universe._MinMainWorldCount:
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

        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap[self._placeholderMilieu]
            for sector in placeholderData.sectorList:
                sectorIndex = sector.index()
                sectorPos = sectorIndex.elements()
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
        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap[self._placeholderMilieu]

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

        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap[self._placeholderMilieu]
            for sector in placeholderData.sectorList:
                sectorIndex = sector.index()
                sectorPos = sectorIndex.elements()
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
        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap[self._placeholderMilieu]

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

        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap[self._placeholderMilieu]
            for sector in placeholderData.sectorList:
                sectorIndex = sector.index()
                sectorPos = sectorIndex.elements()
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
        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap[self._placeholderMilieu]

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
        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap[self._placeholderMilieu]

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
        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap[self._placeholderMilieu]

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
