import astronomer
import common
import re
import math
import typing

class Universe(object):
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
            universeId: str,
            milieu: astronomer.Milieu,
            sectors: typing.Collection[astronomer.Sector],
            labels: typing.Collection[astronomer.MapLabel]
            ) -> None:
        common.validateStr(name='universeId', value=universeId, allowEmpty=False)
        common.validateObject(name='milieu', value=milieu, objectType=astronomer.Milieu)
        common.validateCollection(name='sectors', value=sectors, elementType=astronomer.Sector)
        common.validateCollection(name='labels', value=labels, elementType=astronomer.MapLabel)

        self._universeId = universeId
        self._milieu = milieu

        self._idToEntityMap: typing.Dict[str, astronomer.Entity] = {}

        self._nameToSectorMap: typing.Dict[str, typing.Set[astronomer.Sector]] = {}
        self._abbreviationToSectorMap: typing.Dict[str, typing.Set[astronomer.Sector]] = {}
        self._subsectorNameToSectorMap: typing.Dict[str, typing.Set[astronomer.Sector]] = {}
        self._positionToSectorMap: typing.Dict[typing.Tuple[int, int], astronomer.Sector] = {}
        self._positionToWorldMap: typing.Dict[typing.Tuple[int, int], astronomer.World] = {}
        self._positionToMainMap: typing.Dict[typing.Tuple[int, int], astronomer.Main] = {}
        self._positionToRoutesMap: typing.Dict[typing.Tuple[int, int], typing.Set[astronomer.Route]] = {}
        for sector in sectors:
            self._addSector(sector=sector)

        self._labels: typing.List[astronomer.MapLabel] = []
        for label in labels:
            self._addLabel(label=label)

    def universeId(self) -> str:
        return self._universeId

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def sectorsByAbbreviation(
            self,
            abbreviation: str
            ) -> typing.Collection[astronomer.Sector]:
        sectors = self._abbreviationToSectorMap.get(abbreviation)
        if not sectors:
            return []
        return common.ConstCollectionRef(sectors)

    def sectors(
            self,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None
            ) -> typing.List[astronomer.Sector]:
        return list(self.yieldSectors(filterCallback=filterCallback))

    def worlds(
            self,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.List[astronomer.World]:
        return list(self.yieldWorlds(filterCallback=filterCallback))

    def worldsByWorldRef(
            self,
            worldRef: astronomer.WorldReference,
            sourceSectorPos: astronomer.SectorPosition
            ) -> typing.List[astronomer.World]:
        sectors: typing.List[astronomer.Sector] = []
        if worldRef.sectorAbbreviation():
            sectors.extend(self.sectorsByAbbreviation(
                abbreviation=worldRef.sectorAbbreviation()))
        else:
            sector = self.sectorByPosition(position=sourceSectorPos)
            if sector:
                sectors.append(sector)

        worlds: typing.List[astronomer.World] = []
        for sector in sectors:
            hex = astronomer.HexPosition(
                sectorPos=sector.position(),
                offsetX=worldRef.hexX(),
                offsetY=worldRef.hexY())
            world = self.worldByPosition(hex=hex)
            if world:
                worlds.append(world)

        return worlds

    def worldByPosition(
            self,
            hex: astronomer.HexPosition
            ) -> typing.Optional[astronomer.World]:
        return self._positionToWorldMap.get(hex.absolute())

    def sectorByPosition(
            self,
            position: typing.Union[astronomer.SectorPosition, astronomer.HexPosition]
            ) -> typing.Optional[astronomer.Sector]:
        if isinstance(position, astronomer.HexPosition):
            position = position.sectorPosition()

        return self._positionToSectorMap.get(position.elements())

    def sectorsInArea(
            self,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None
            ) -> typing.List[astronomer.Sector]:
        return list(self.yieldSectorsInArea(
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback))

    def worldsInArea(
            self,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.List[astronomer.World]:
        return list(self.yieldWorldsInArea(
            upperLeft=upperLeft,
            lowerRight=lowerRight,
            filterCallback=filterCallback))

    def worldsInRadius(
            self,
            center: astronomer.HexPosition,
            searchRadius: int,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.List[astronomer.World]:
        return list(self.yieldWorldsInRadius(
            center=center,
            radius=searchRadius,
            filterCallback=filterCallback))

    def worldsInFlood(
            self,
            hex: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.List[astronomer.World]:
        return list(self.yieldWorldsInFlood(
            hex=hex,
            filterCallback=filterCallback))

    def entityById(
            self,
            entityId: str
            ) -> typing.Optional[astronomer.Entity]:
        return self._idToEntityMap.get(entityId)

    def formatSectorHex(
            self,
            hex: astronomer.HexPosition
            ) -> str:
        sectorX, sectorY, offsetX, offsetY = hex.relative()
        sectorPos = (sectorX, sectorY)
        sector = self._positionToSectorMap.get(sectorPos)

        return astronomer.formatSectorHex(
            sectorName=sector.name() if sector else f'{sectorX}:{sectorY}',
            offsetX=offsetX,
            offsetY=offsetY)

    # NOTE: This returns a list of positions as sector names are not guaranteed
    # to be unique in the universe
    def sectorHexToPositions(
            self,
            sectorHex: str,
            closetTo: typing.Optional[astronomer.HexPosition] = None
            ) -> typing.List[astronomer.HexPosition]:
        originalSectorName, offsetX, offsetY = astronomer.splitSectorHex(
            sectorHex=sectorHex)

        # Sector name lookup is case insensitive. The sector name map stores
        # sector names in lower so search name should be converted to lower case
        # before searching
        lowerCaseSectorName = originalSectorName.lower()

        # Check to see if we sector name is recognised
        sectors = self._nameToSectorMap.get(lowerCaseSectorName)
        if not sectors:
            # No name match so check abbreviations and subsector names
            # NOTE: Use original case for abbreviation lookup as in theory two
            # sectors abbreviations could vary by case
            sectors = self._abbreviationToSectorMap.get(originalSectorName)
            if not sectors:
                sectors = self._subsectorNameToSectorMap.get(lowerCaseSectorName)

        if sectors:
            if closetTo is None:
                return [astronomer.HexPosition(sector.position(), offsetX, offsetY) for sector in sectors]

            closestDistance = None
            closestHex = None
            for sector in sectors:
                hex = astronomer.HexPosition(sector.position(), offsetX, offsetY)
                distance = hex.parsecsTo(closetTo)
                if closestDistance is None or distance < closestDistance:
                    closestHex = hex
                    closestDistance = distance

            return [closestHex] if closestHex is not None else []

        # Check to see if the sector name is a sector x/y separated by a colon.
        # This is the format used by positionToSectorHex if there is no sector
        # at the specified hex
        tokens = lowerCaseSectorName.split(':')
        if len(tokens) == 2:
            try:
                sectorX = int(tokens[0])
                sectorY = int(tokens[1])
                return [astronomer.HexPosition(
                    sectorX=sectorX,
                    sectorY=sectorY,
                    offsetX=offsetX,
                    offsetY=offsetY)]
            except:
                pass

        return []

    # NOTE: This returns a list of positions as sector names are not guaranteed
    # to be unique in the universe
    def stringToPositions(
            self,
            string: str,
            closetTo: typing.Optional[astronomer.HexPosition] = None
            ) -> typing.List[astronomer.HexPosition]:
        testString = string.strip()
        if not testString:
            return []

        result = self._SectorHexSearchPattern.match(testString)
        if result:
            # NOTE: Perform the search on the first group in the result.
            # This is the sector hex string that was matched in the
            # supplied string. The second group, if there is one, is
            # expected to be the subsector
            hexes = self.sectorHexToPositions(
                sectorHex=result.group(1),
                closetTo=closetTo)
            if hexes:
                return hexes

            # Search string is not a valid sector hex. The search pattern
            # regex was matched so it should have the correct format, most
            # likely the sector name doesn't match a known sector. Continue
            # in case it matches one of the other patterns (but it's unlikely)

        result = self._AbsoluteHexSearchPattern.match(testString)
        if result:
            return [astronomer.HexPosition(
                absoluteX=int(result.group(1)),
                absoluteY=int(result.group(2)))]

        result = self._RelativeHexSearchPattern.match(testString)
        if result:
            sectorX = int(result.group(1))
            sectorY = int(result.group(2))
            offsetX = int(result.group(3))
            offsetY = int(result.group(4))
            if (offsetX >= 0  and offsetX < astronomer.SectorWidth) and \
                    (offsetY >= 0 and offsetY < astronomer.SectorHeight):
                return [astronomer.HexPosition(
                    sectorX=sectorX,
                    sectorY=sectorY,
                    offsetX=offsetX,
                    offsetY=offsetY)]

        return []

    def canonicalHexName(
            self,
            hex: astronomer.HexPosition,
            ) -> str:
        world = self.worldByPosition(hex=hex)
        name = world.name() if world else self.formatSectorHex(hex=hex)

        sector = self.sectorByPosition(position=hex)
        if sector:
            subsectorName = sector.subsectorName(code=hex.subsectorCode())
            if subsectorName:
                name += f' ({subsectorName})'
        return name

    def mainByPosition(
            self,
            hex: astronomer.HexPosition
            ) -> typing.Optional[astronomer.Main]:
        main = self._positionToMainMap.get(hex.absolute())
        if main:
            return main

        worlds = self.worldsInFlood(hex=hex)
        if len(worlds) < Universe._MinMainWorldCount:
            return None

        main = astronomer.Main(hexes=(world.hex() for world in worlds))
        for world in worlds:
            self._positionToMainMap[world.hex().absolute()] = main

        return main

    def yieldSectors(
            self,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None
            ) -> typing.Generator[astronomer.Sector, None, None]:
        for sector in self._positionToSectorMap.values():
            if not filterCallback or filterCallback(sector):
                yield sector

    def yieldSectorsInArea(
            self,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None
            ) -> typing.Generator[astronomer.Sector, None, None]:
        startX, finishX = common.minmax(upperLeft.sectorX(), lowerRight.sectorX())
        startY, finishY = common.minmax(upperLeft.sectorY(), lowerRight.sectorY())

        x = startX
        while x <= finishX:
            y = startY
            while y <= finishY:
                key = (x, y)
                sector = self._positionToSectorMap.get(key)
                if sector and (not filterCallback or filterCallback(sector)):
                    yield sector
                y += 1
            x += 1

    def yieldWorlds(
            self,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.Generator[astronomer.World, None, None]:
        for world in self._positionToWorldMap.values():
            if not filterCallback or filterCallback(world):
                yield world

    def yieldWorldsInArea(
            self,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.Generator[astronomer.World, None, None]:
        startX, finishX = common.minmax(upperLeft.absoluteX(), lowerRight.absoluteX())
        startY, finishY = common.minmax(upperLeft.absoluteY(), lowerRight.absoluteY())

        x = startX
        while x <= finishX:
            y = startY
            while y <= finishY:
                key = (x, y)
                world = self._positionToWorldMap.get(key)
                if world and ((not filterCallback) or filterCallback(world)):
                    yield world
                y += 1
            x += 1

    def yieldWorldsInRadius(
            self,
            center: astronomer.HexPosition,
            radius: int,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.Generator[astronomer.World, None, None]:
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
                world = self._positionToWorldMap.get(key)
                if world and ((not filterCallback) or filterCallback(world)):
                    yield world

    def yieldWorldsInFlood(
            self,
            hex: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.Generator[astronomer.World, None, None]:
        key = hex.absolute()
        world = self._positionToWorldMap.get(key)
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
                adjacentWorld = self._positionToWorldMap.get(key)
                if adjacentWorld and (adjacentWorld not in seen):
                    todo.append(adjacentWorld)
                    seen.add(adjacentWorld)

                    if not filterCallback or filterCallback(adjacentWorld):
                        yield adjacentWorld

    def hasRoutes(
            self,
            hex: astronomer.HexPosition
            ) -> bool:
        routes = self._positionToRoutesMap.get(hex.absolute())
        return routes and len(routes) > 0

    def routesByPosition(
            self,
            hex: astronomer.HexPosition
            ) -> typing.List[astronomer.Route]:
        return list(self.yieldRouteByPosition(hex=hex))

    def yieldRouteByPosition(
            self,
            hex: astronomer.HexPosition
            ) -> typing.Generator[astronomer.Route, None, None]:
        routes = self._positionToRoutesMap.get(hex.absolute())
        if routes:
            for route in routes:
                yield route

    def connectedWorlds(
            self,
            hex: astronomer.HexPosition
            ) -> typing.List[astronomer.World]:
        return list(self.yieldConnectedWorlds(hex=hex))

    def yieldConnectedWorlds(
            self,
            hex: astronomer.HexPosition
            ) -> typing.Generator[astronomer.World, None, None]:
        routes = self._positionToRoutesMap.get(hex.absolute())
        if not routes:
            return

        for route in routes:
            connectedHex = None
            if hex != route.startHex():
                connectedHex = route.startHex()
            elif hex != route.endHex():
                connectedHex = route.endHex()

            if connectedHex:
                connectedWorld = self._positionToWorldMap.get(connectedHex.absolute())
                if connectedWorld:
                    yield connectedWorld

    def labels(self) -> typing.Collection[astronomer.MapLabel]:
        return common.ConstCollectionRef(self._labels)

    def _addSector(self, sector: astronomer.Sector) -> None:
        self._idToEntityMap[sector.entityId()] = sector
        for entity in sector.entities():
            self._idToEntityMap[entity.entityId()] = entity

        sectorPos = sector.position()
        self._positionToSectorMap[sectorPos.elements()] = sector

        # Add canonical name to the main name map. The name is added lower case as lookups are
        # case insensitive
        canonicalName = sector.name().lower()
        sectors = self._nameToSectorMap.get(canonicalName)
        if not sectors:
            sectors = set()
            self._nameToSectorMap[canonicalName] = sectors
        sectors.add(sector)

        for alternateName in sector.alternateNames():
            alternateName = alternateName.lower()
            sectors = self._nameToSectorMap.get(alternateName)
            if not sectors:
                sectors = set()
                self._nameToSectorMap[alternateName] = sectors
            sectors.add(sector)

        abbreviation = sector.abbreviation()
        if abbreviation:
            # NOTE: Unlike most string -> sector lookups, the abbreviation
            # map is case sensitive
            sectors = self._abbreviationToSectorMap.get(abbreviation)
            if not sectors:
                sectors = set()
                self._abbreviationToSectorMap[abbreviation] = sectors
            sectors.add(sector)

        for subsectorName in sector.subsectorNames():
            subsectorName = subsectorName.lower()
            sectors = self._subsectorNameToSectorMap.get(subsectorName)
            if not sectors:
                sectors = set()
                self._subsectorNameToSectorMap[subsectorName] = sectors
            sectors.add(sector)

        for world in sector.worlds():
            hex = world.hex()
            self._positionToWorldMap[hex.absolute()] = world

        for route in sector.routes():
            for hex in [route.startHex(), route.endHex()]:
                endpoints = self._positionToRoutesMap.get(hex.absolute())
                if not endpoints:
                    endpoints = set()
                    self._positionToRoutesMap[hex.absolute()] = endpoints
                endpoints.add(route)

        # Clear mains so they will be regenerated from the updated data
        self._positionToMainMap.clear()

    def _removeSector(self, sector: astronomer.Sector) -> None:
        self._idToEntityMap.pop(sector.entityId(), None)
        for entity in sector.entities():
            self._idToEntityMap.pop(entity.entityId(), None)

        sectorPos = sector.position()
        self._positionToSectorMap.pop(sectorPos.elements(), None)

        canonicalName = sector.name().lower()
        sectors = self._nameToSectorMap.get(canonicalName)
        if sectors:
            sectors.discard(sector)

        for alternateName in sector.alternateNames():
            alternateName = alternateName.lower()
            sectors = self._nameToSectorMap.get(alternateName)
            if sectors:
                sectors.discard(sector)

        abbreviation = sector.abbreviation()
        if abbreviation:
            # NOTE: Unlike most string -> sector lookups, the abbreviation
            # map is case sensitive
            sectors = self._abbreviationToSectorMap.get(abbreviation)
            if sectors:
                sectors.discard(sector)

        for subsectorName in sector.subsectorNames():
            subsectorName = subsectorName.lower()
            sectors = self._subsectorNameToSectorMap.get(subsectorName)
            if sectors:
                sectors.discard(sector)

        for world in sector.worlds():
            hex = world.hex()
            self._positionToWorldMap.pop(hex.absolute(), None)

        for route in sector.routes():
            for hex in [route.startHex(), route.endHex()]:
                endpoints = self._positionToRoutesMap.get(hex.absolute())
                if endpoints:
                    endpoints.discard(route)

        # Clear mains so they will be regenerated from the updated data
        self._positionToMainMap.clear()

    def _addLabel(self, label: astronomer.MapLabel) -> None:
        self._idToEntityMap[label.entityId()] = label
        self._labels.append(label)