import astronomer
import common
import re
import math
import typing

class Universe(object):
    class _MilieuData(object):
        def __init__(self):
            self.sectorList: typing.List[astronomer.Sector] = []
            self.canonicalNameToSectorMap: typing.Dict[str, astronomer.Sector] = {}
            self.alternateNameToSectorMap: typing.Dict[str, typing.List[astronomer.Sector]] = {}
            self.abbreviationToSectorMap: typing.Dict[str, typing.List[astronomer.Sector]] = {}
            self.positionToSectorMap: typing.Dict[typing.Tuple[int, int], astronomer.Sector] = {}
            self.subsectorNameToSectorMap: typing.Dict[str, typing.List[astronomer.Sector]] = {}
            self.positionToWorldMap: typing.Dict[typing.Tuple[int, int], astronomer.World] = {}
            self.mainsList: typing.List[astronomer.Main] = []
            self.positionToMainMap: typing.Dict[typing.Tuple[int, int], astronomer.Main] = {}
            self.positionToRoutesMap: typing.Dict[typing.Tuple[int, int], typing.List[astronomer.Route]] = {}

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

    # This is the value used by Traveller Map (tools\mains.js)
    _MinMainWorldCount = 5

    def __init__(
            self,
            id: str,
            sectors: typing.Collection[astronomer.Sector], # Sectors for all milieu
            placeholderMilieu: typing.Optional[astronomer.Milieu] = None
            ) -> None:
        self._id = id
        self._milieuDataMap: typing.Dict[astronomer.Milieu, Universe._MilieuData] = {}
        self._placeholderMilieu = placeholderMilieu

        for sector in sectors:
            milieu = sector.milieu()

            milieuData = self._milieuDataMap.get(milieu)
            if not milieuData:
                milieuData = Universe._MilieuData()
                self._milieuDataMap[milieu] = milieuData

            sectorPos = sector.position()
            milieuData.sectorList.append(sector)
            milieuData.positionToSectorMap[sectorPos.elements()] = sector

            # Add canonical name to the main name map. The name is added lower case as lookups are
            # case insensitive
            milieuData.canonicalNameToSectorMap[sector.name().lower()] = sector

            alternateNames = sector.alternateNames()
            if alternateNames:
                for alternateName in alternateNames:
                    alternateName = alternateName.lower()
                    sectorList = milieuData.alternateNameToSectorMap.get(alternateName)
                    if not sectorList:
                        sectorList = []
                        milieuData.alternateNameToSectorMap[alternateName] = sectorList
                    sectorList.append(sector)

            abbreviation = sector.abbreviation()
            if abbreviation:
                # NOTE: Unlike most string -> sector lookups, the abbreviation
                # map is case sensitive
                sectorList = milieuData.abbreviationToSectorMap.get(abbreviation)
                if not sectorList:
                    sectorList = []
                    milieuData.abbreviationToSectorMap[abbreviation] = sectorList
                sectorList.append(sector)

            for subsectorName in sector.subsectorNames():
                subsectorName = subsectorName.lower()
                sectorList = milieuData.subsectorNameToSectorMap.get(subsectorName)
                if not sectorList:
                    sectorList = []
                    milieuData.subsectorNameToSectorMap[subsectorName] = sectorList
                sectorList.append(sector)

            for world in sector.worlds():
                hex = world.hex()
                milieuData.positionToWorldMap[hex.absolute()] = world

            for route in sector.routes():
                for hex in [route.startHex(), route.endHex()]:
                    endpoints = milieuData.positionToRoutesMap.get(hex.absolute())
                    if not endpoints:
                        endpoints = []
                        milieuData.positionToRoutesMap[hex.absolute()] = endpoints
                    endpoints.append(route)

    def id(self) -> str:
        return self._id

    def sectorNames(
            self,
            milieu: astronomer.Milieu
            ) -> typing.Iterable[str]:
        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return []

        sectorNames = []
        for sector in milieuData.sectorList:
            sectorNames.append(sector.name())
        return sectorNames

    def sectorByName(
            self,
            milieu: astronomer.Milieu,
            name: str
            ) -> typing.Optional[astronomer.Sector]:
        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return None
        return milieuData.canonicalNameToSectorMap.get(name.lower())

    def sectorsByAbbreviation(
            self,
            milieu: astronomer.Milieu,
            abbreviation: str
            ) -> typing.List[astronomer.Sector]:
        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return []
        sectors = milieuData.abbreviationToSectorMap.get(abbreviation)
        if not sectors:
            return []
        return list(sectors)

    def sectors(
            self,
            milieu: astronomer.Milieu,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.Sector]:
        return list(self.yieldSectors(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def worlds(
            self,
            milieu: astronomer.Milieu,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.World]:
        return list(self.yieldWorlds(
            milieu=milieu,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def worldBySectorHex(
            self,
            milieu: astronomer.Milieu,
            sectorHex: str,
            ) -> typing.Optional[astronomer.World]:
        hex = self.sectorHexToPosition(milieu=milieu, sectorHex=sectorHex)
        return self.worldByPosition(milieu=milieu, hex=hex) if hex else None

    def worldByPosition(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[astronomer.World]:
        milieuData = self._milieuDataMap.get(milieu)
        world = milieuData.positionToWorldMap.get(hex.absolute()) if milieuData else None

        if not world and includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            sectorPos = hex.sectorPosition()
            if not milieuData or sectorPos.elements() not in milieuData.positionToSectorMap:
                world = self.worldByPosition(
                    milieu=self._placeholderMilieu,
                    hex=hex,
                    includePlaceholders=False)

        return world

    def sectorByPosition(
            self,
            milieu: astronomer.Milieu,
            position: typing.Union[astronomer.SectorPosition, astronomer.HexPosition],
            includePlaceholders: bool = False
            ) -> typing.Optional[astronomer.Sector]:
        if isinstance(position, astronomer.HexPosition):
            position = position.sectorPosition()

        milieuData = self._milieuDataMap.get(milieu)
        sector = milieuData.positionToSectorMap.get(position.elements()) if milieuData else None

        if not sector and includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            sector = self.sectorByPosition(
                milieu=self._placeholderMilieu,
                position=position,
                includePlaceholders=False)

        return sector

    def sectorsInArea(
            self,
            milieu: astronomer.Milieu,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.Sector]:
        return list(self.yieldSectorsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def worldsInArea(
            self,
            milieu: astronomer.Milieu,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.World]:
        return list(self.yieldWorldsInArea(
            milieu=milieu,
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def worldsInRadius(
            self,
            milieu: astronomer.Milieu,
            center: astronomer.HexPosition,
            searchRadius: int,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.World]:
        return list(self.yieldWorldsInRadius(
            milieu=milieu,
            center=center,
            radius=searchRadius,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def worldsInFlood(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.List[astronomer.World]:
        return list(self.yieldWorldsInFlood(
            milieu=milieu,
            hex=hex,
            filterCallback=filterCallback,
            includePlaceholders=includePlaceholders))

    def formatSectorHex(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            includePlaceholders: bool = False
            ) -> str:
        milieuData = self._milieuDataMap.get(milieu)

        sectorX, sectorY, offsetX, offsetY = hex.relative()
        sectorPos = (sectorX, sectorY)
        sector = milieuData.positionToSectorMap.get(sectorPos) if milieuData else None

        if not sector and includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap.get(self._placeholderMilieu)
            if placeholderData:
                sector = placeholderData.positionToSectorMap.get(sectorPos)

        return astronomer.formatSectorHex(
            sectorName=sector.name() if sector else f'{sectorX}:{sectorY}',
            offsetX=offsetX,
            offsetY=offsetY)

    def sectorHexToPosition(
            self,
            milieu: astronomer.Milieu,
            sectorHex: str
            ) -> typing.Optional[astronomer.HexPosition]:
        originalSectorName, offsetX, offsetY = astronomer.splitSectorHex(
            sectorHex=sectorHex)

        # Sector name lookup is case insensitive. The sector name map stores
        # sector names in lower so search name should be converted to lower case
        # before searching
        lowerCaseSectorName = originalSectorName.lower()

        # Check to see if the sector name is a canonical sector name
        milieuData = self._milieuDataMap.get(milieu)
        sector = None
        if milieuData:
            sector = milieuData.canonicalNameToSectorMap.get(lowerCaseSectorName)
            if not sector:
                # Make a best effort attempt to find the sector by looking at
                # abbreviations, alternate names and subsector names. These
                # matches are not always unique so just use the first if more
                # than one is found
                sectors = milieuData.alternateNameToSectorMap.get(lowerCaseSectorName)
                if sectors:
                    # Alternate sector name match
                    sector = sectors[0]
                else:
                    # NOTE: Use original case for abbreviation lookup as in theory two
                    # sectors abbreviations could vary by case
                    sectors = milieuData.abbreviationToSectorMap.get(originalSectorName)
                    if sectors:
                        sector = sectors[0]
                    else:
                        sectors = milieuData.subsectorNameToSectorMap.get(lowerCaseSectorName)
                        if sectors:
                            # Subsector name match
                            sector = sectors[0]

        if sector:
            return astronomer.HexPosition(
                sectorPos=sector.position(),
                offsetX=offsetX,
                offsetY=offsetY)

        # Check to see if the sector name is a sector x/y separated by a colon.
        # This is the format used by positionToSectorHex if there is no sector
        # at the specified hex
        tokens = lowerCaseSectorName.split(':')
        if len(tokens) == 2:
            try:
                sectorX = int(tokens[0])
                sectorY = int(tokens[1])
                return astronomer.HexPosition(
                    sectorX=sectorX,
                    sectorY=sectorY,
                    offsetX=offsetX,
                    offsetY=offsetY)
            except:
                pass

        return None

    def stringToPosition(
            self,
            milieu: astronomer.Milieu,
            string: str,
            ) -> astronomer.HexPosition:
        testString = string.strip()
        if not testString:
            raise ValueError(f'Invalid position string "{string}"')

        result = self._SectorHexSearchPattern.match(testString)
        if result:
            hex = self.sectorHexToPosition(milieu=milieu, sectorHex=testString)
            if hex:
                return hex

            # Search string is not a valid sector hex. The search pattern
            # regex was matched so it should have the correct format, most
            # likely the sector name doesn't match a known sector. Continue
            # in case it matches one of the other patterns (but it's unlikely)

        result = self._AbsoluteHexSearchPattern.match(testString)
        if result:
            return astronomer.HexPosition(
                absoluteX=int(result.group(1)),
                absoluteY=int(result.group(2)))

        result = self._RelativeHexSearchPattern.match(testString)
        if result:
            sectorX = int(result.group(1))
            sectorY = int(result.group(2))
            offsetX = int(result.group(3))
            offsetY = int(result.group(4))
            if (offsetX >= 0  and offsetX < astronomer.SectorWidth) and \
                    (offsetY >= 0 and offsetY < astronomer.SectorHeight):
                return astronomer.HexPosition(
                    sectorX=sectorX,
                    sectorY=sectorY,
                    offsetX=offsetX,
                    offsetY=offsetY)

        raise ValueError(f'Invalid position string "{string}"')

    def canonicalHexName(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            ) -> str:
        world = self.worldByPosition(milieu=milieu, hex=hex)
        name = world.name() if world else self.formatSectorHex(milieu=milieu, hex=hex)

        sector = self.sectorByPosition(milieu=milieu, position=hex)
        if sector:
            subsectorName = sector.subsectorName(code=hex.subsectorCode())
            if subsectorName:
                name += f' ({subsectorName})'
        return name

    def mainByPosition(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition
            ) -> typing.Optional[astronomer.Main]:
        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return None

        main = milieuData.positionToMainMap.get(hex.absolute())
        if main:
            return main

        worlds = self.worldsInFlood(
            hex=hex,
            milieu=milieu,
            includePlaceholders=True)
        if len(worlds) < Universe._MinMainWorldCount:
            return None

        main = astronomer.Main(worlds=worlds)
        for world in worlds:
            milieuData.positionToMainMap[world.hex().absolute()] = main

        return main

    def yieldSectors(
            self,
            milieu: astronomer.Milieu,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.Sector, None, None]:
        milieuData = self._milieuDataMap.get(milieu)
        if milieuData:
            for sector in milieuData.sectorList:
                if not filterCallback or filterCallback(sector):
                    yield sector

        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap.get(self._placeholderMilieu)
            if placeholderData:
                for sector in placeholderData.sectorList:
                    sectorPos = sector.position()
                    if not milieuData or sectorPos.elements() not in milieuData.positionToSectorMap:
                        if not filterCallback or filterCallback(sector):
                            yield sector

    def yieldSectorsInArea(
            self,
            milieu: astronomer.Milieu,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.Sector, None, None]:
        milieuData = self._milieuDataMap.get(milieu)
        placeholderData = None
        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap.get(self._placeholderMilieu)

        startX, finishX = common.minmax(upperLeft.sectorX(), lowerRight.sectorX())
        startY, finishY = common.minmax(upperLeft.sectorY(), lowerRight.sectorY())

        x = startX
        while x <= finishX:
            y = startY
            while y <= finishY:
                key = (x, y)
                sector = milieuData.positionToSectorMap.get(key) if milieuData else None
                if not sector and placeholderData:
                    sector = placeholderData.positionToSectorMap.get(key)

                if sector and (not filterCallback or filterCallback(sector)):
                    yield sector
                y += 1
            x += 1

    def yieldWorlds(
            self,
            milieu: astronomer.Milieu,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.World, None, None]:
        milieuData = self._milieuDataMap.get(milieu)
        if milieuData:
            for world in milieuData.positionToWorldMap.values():
                if not filterCallback or filterCallback(world):
                    yield world

        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap.get(self._placeholderMilieu)
            if placeholderData:
                for sector in placeholderData.sectorList:
                    sectorPos = sector.position()
                    if not milieuData or sectorPos.elements() not in milieuData.positionToSectorMap:
                        for world in sector.yieldWorlds():
                            if not filterCallback or filterCallback(world):
                                yield world

    def yieldWorldsInArea(
            self,
            milieu: astronomer.Milieu,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.World, None, None]:
        milieuData = self._milieuDataMap.get(milieu)
        placeholderData = None
        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap.get(self._placeholderMilieu)

        startX, finishX = common.minmax(upperLeft.absoluteX(), lowerRight.absoluteX())
        startY, finishY = common.minmax(upperLeft.absoluteY(), lowerRight.absoluteY())

        x = startX
        while x <= finishX:
            y = startY
            while y <= finishY:
                key = (x, y)
                world = milieuData.positionToWorldMap.get(key) if milieuData else None
                if not world and placeholderData:
                    sectorPos = astronomer.absoluteSpaceToSectorPos(key)
                    if not milieuData or sectorPos not in milieuData.positionToSectorMap:
                        world = placeholderData.positionToWorldMap.get(key)

                if world and ((not filterCallback) or filterCallback(world)):
                    yield world
                y += 1
            x += 1

    def yieldWorldsInRadius(
            self,
            milieu: astronomer.Milieu,
            center: astronomer.HexPosition,
            radius: int,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.World, None, None]:
        milieuData = self._milieuDataMap.get(milieu)
        placeholderData = None
        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap.get(self._placeholderMilieu)

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
                world = milieuData.positionToWorldMap.get(key) if milieuData else None
                if not world and placeholderData:
                    sectorPos = astronomer.absoluteSpaceToSectorPos(key)
                    if not milieuData or sectorPos not in milieuData.positionToSectorMap:
                        world = placeholderData.positionToWorldMap.get(key)

                if world and ((not filterCallback) or filterCallback(world)):
                    yield world

    def yieldWorldsInFlood(
            self,
            milieu: astronomer.Milieu,
            hex: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None,
            includePlaceholders: bool = False
            ) -> typing.Generator[astronomer.World, None, None]:
        milieuData = self._milieuDataMap.get(milieu)
        placeholderData = None
        if includePlaceholders and self._placeholderMilieu and milieu is not self._placeholderMilieu:
            placeholderData = self._milieuDataMap.get(self._placeholderMilieu)

        key = hex.absolute()
        world = milieuData.positionToWorldMap.get(key) if milieuData else None
        if not world and placeholderData:
            sectorPos = astronomer.absoluteSpaceToSectorPos(key)
            if not milieuData or sectorPos not in milieuData.positionToSectorMap:
                world = placeholderData.positionToWorldMap.get(key)
        if not world:
            return

        if not filterCallback or filterCallback(world):
            yield world

        todo = [world]
        seen = set(todo)
        while todo:
            world = todo.pop(0)
            hex = world.hex()
            for edge in astronomer.HexEdge:
                adjacentHex = hex.neighbour(edge=edge)

                key = adjacentHex.absolute()
                adjacentWorld = milieuData.positionToWorldMap.get(key) if milieuData else None
                if not adjacentWorld and placeholderData:
                    sectorPos = astronomer.absoluteSpaceToSectorPos(key)
                    if not milieuData or sectorPos not in milieuData.positionToSectorMap:
                        adjacentWorld = placeholderData.positionToWorldMap.get(key)

                if adjacentWorld and (adjacentWorld not in seen):
                    todo.append(adjacentWorld)
                    seen.add(adjacentWorld)

                    if not filterCallback or filterCallback(adjacentWorld):
                        yield adjacentWorld

    def hasRoutes(
            self,
            hex: astronomer.HexPosition,
            milieu: astronomer.Milieu
            ) -> bool:
        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return
        routes = milieuData.positionToRoutesMap.get(hex.absolute())
        return routes and len(routes) > 0

    def routesByPosition(
            self,
            hex: astronomer.HexPosition,
            milieu: astronomer.Milieu
            ) -> typing.List[astronomer.Route]:
        return list(self.yieldRouteByPosition(hex=hex, milieu=milieu))

    def yieldRouteByPosition(
            self,
            hex: astronomer.HexPosition,
            milieu: astronomer.Milieu
            ) -> typing.Generator[astronomer.Route, None, None]:
        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return
        routes = milieuData.positionToRoutesMap.get(hex.absolute())
        if routes:
            for route in routes:
                yield route

    def connectedWorlds(
            self,
            hex: astronomer.HexPosition,
            milieu: astronomer.Milieu
            ) -> typing.List[astronomer.World]:
        return list(self.yieldConnectedWorlds(hex=hex, milieu=milieu))

    def yieldConnectedWorlds(
            self,
            hex: astronomer.HexPosition,
            milieu: astronomer.Milieu
            ) -> typing.Generator[astronomer.World, None, None]:
        milieuData = self._milieuDataMap.get(milieu)
        if not milieuData:
            return
        routes = milieuData.positionToRoutesMap.get(hex.absolute())
        if not routes:
            return

        for route in routes:
            connectedHex = None
            if hex != route.startHex():
                connectedHex = route.startHex()
            elif hex != route.endHex():
                connectedHex = route.endHex()

            if connectedHex:
                connectedWorld = milieuData.positionToWorldMap.get(connectedHex.absolute())
                if connectedWorld:
                    yield connectedWorld
