import astronomer
import common
import math
import re
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
            allegiances: typing.Collection[astronomer.Allegiance],
            sophonts: typing.Collection[astronomer.Sophont],
            sectors: typing.Collection[astronomer.Sector],
            worlds: typing.Collection[astronomer.World],
            routes: typing.Collection[astronomer.Route],
            labels: typing.Collection[astronomer.MapLabel],
            vectors: typing.Collection[astronomer.MapVector]
            ) -> None:
        common.validateStr(name='universeId', value=universeId, allowEmpty=False)
        common.validateObject(name='milieu', value=milieu, objectType=astronomer.Milieu)
        common.validateCollection(name='allegiances', value=allegiances, elementType=astronomer.Allegiance)
        common.validateCollection(name='sophonts', value=sophonts, elementType=astronomer.Sophont)
        common.validateCollection(name='sectors', value=sectors, elementType=astronomer.Sector)
        common.validateCollection(name='worlds', value=worlds, elementType=astronomer.World)
        common.validateCollection(name='routes', value=routes, elementType=astronomer.Route)
        common.validateCollection(name='labels', value=labels, elementType=astronomer.MapLabel)
        common.validateCollection(name='vectors', value=vectors, elementType=astronomer.MapVector)

        self._universeId = universeId
        self._milieu = milieu

        self._idToEntityMap: typing.Dict[str, astronomer.Entity] = {}

        self._allegiances: typing.List[astronomer.Allegiance] = []
        for allegiance in allegiances:
            self._addAllegiance(allegiance=allegiance)

        self._sophonts: typing.List[astronomer.Sophont] = []
        for sophont in sophonts:
            self._addSophont(sophont=sophont)

        self._nameToSectorMap: typing.Dict[str, typing.Set[astronomer.Sector]] = {}
        self._abbreviationToSectorMap: typing.Dict[str, typing.Set[astronomer.Sector]] = {}
        self._subsectorNameToSectorMap: typing.Dict[str, typing.Set[astronomer.Sector]] = {}
        self._sectorPositionToSectorMap: typing.Dict[typing.Tuple[int, int], astronomer.Sector] = {}
        for sector in sectors:
            self._addSector(sector=sector)

        self._sectorPositionToWorldsMap: typing.Dict[typing.Tuple[int, int], typing.Set[astronomer.World]] = {}
        self._subsectorPositionToWorldsMap: typing.Dict[typing.Tuple[int, int, str], typing.Set[astronomer.World]] = {}
        self._hexPositionToWorldMap: typing.Dict[typing.Tuple[int, int], astronomer.World] = {}
        self._hexPositionToMainMap: typing.Dict[typing.Tuple[int, int], astronomer.Main] = {}
        for world in worlds:
            self._addWorld(world=world)

        self._routes: typing.Set[astronomer.Route] = set()
        self._hexPositionToRoutesMap: typing.Dict[typing.Tuple[int, int], typing.Set[astronomer.Route]] = {}
        for route in routes:
            self._addRoute(route=route)

        self._labels: typing.List[astronomer.MapLabel] = []
        for label in labels:
            self._addLabel(label=label)

        self._vectors: typing.List[astronomer.MapVector] = []
        for vector in vectors:
            self._addVector(vector=vector)

    def id(self) -> str:
        return self._universeId

    def milieu(self) -> astronomer.Milieu:
        return self._milieu

    def allegiances(self) -> typing.Collection[astronomer.Allegiance]:
        return common.ConstCollectionRef(self._allegiances)

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
        if filterCallback is None:
            return list(self._sectorPositionToSectorMap.values())
        else:
            sectors = []
            for sector in self._sectorPositionToSectorMap.values():
                if filterCallback(sector):
                    sectors.append(sector)
            return sector

    def worlds(
            self,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.List[astronomer.World]:
        if filterCallback is None:
            return list(self._hexPositionToWorldMap.values())
        else:
            worlds = []
            for world in self._hexPositionToWorldMap.values():
                if filterCallback(world):
                    worlds.append(world)
            return worlds

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
        return self._hexPositionToWorldMap.get(hex.absolute())

    def sectorByPosition(
            self,
            position: typing.Union[astronomer.SectorPosition, astronomer.HexPosition]
            ) -> typing.Optional[astronomer.Sector]:
        if isinstance(position, astronomer.HexPosition):
            position = position.sectorPosition()

        return self._sectorPositionToSectorMap.get(position.elements())

    def sectorsInArea(
            self,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.Sector], bool] = None
            ) -> typing.List[astronomer.Sector]:
        startX, finishX = common.minmax(upperLeft.sectorX(), lowerRight.sectorX())
        startY, finishY = common.minmax(upperLeft.sectorY(), lowerRight.sectorY())
        sectors = []

        if filterCallback is None:
            x = startX
            while x <= finishX:
                y = startY
                while y <= finishY:
                    sector = self._sectorPositionToSectorMap.get((x, y))
                    if sector:
                        sectors.append(sector)
                    y += 1
                x += 1
        else:
            x = startX
            while x <= finishX:
                y = startY
                while y <= finishY:
                    sector = self._sectorPositionToSectorMap.get((x, y))
                    if sector and filterCallback(sector):
                        sectors.append(sector)
                    y += 1
                x += 1

        return sectors

    def worldsInArea(
            self,
            upperLeft: astronomer.HexPosition,
            lowerRight: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.List[astronomer.World]:
        startX, finishX = common.minmax(upperLeft.absoluteX(), lowerRight.absoluteX())
        startY, finishY = common.minmax(upperLeft.absoluteY(), lowerRight.absoluteY())

        worlds = []
        if filterCallback is None:
            x = startX
            while x <= finishX:
                y = startY
                while y <= finishY:
                    key = (x, y)
                    world = self._hexPositionToWorldMap.get(key)
                    if world:
                        worlds.append(world)
                    y += 1
                x += 1
        else:
            x = startX
            while x <= finishX:
                y = startY
                while y <= finishY:
                    key = (x, y)
                    world = self._hexPositionToWorldMap.get(key)
                    if world and filterCallback(world):
                        worlds.append(world)
                    y += 1
                x += 1

        return worlds

    def worldsInSector(
            self,
            position: astronomer.SectorPosition,
            subsectorCode: typing.Optional[str] = None,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.List[astronomer.World]:
        if subsectorCode is None:
            worlds = self._sectorPositionToWorldsMap.get(position.elements())
        else:
            worlds = self._subsectorPositionToWorldsMap.get((*position.elements(), subsectorCode))
        if worlds is None:
            return []

        if filterCallback is None:
            return list(worlds)
        else:
            return [world for world in worlds if filterCallback(world)]

    def worldsInRadius(
            self,
            center: astronomer.HexPosition,
            radius: int,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.List[astronomer.World]:
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

        worlds = []
        if filterCallback is None:
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
                    world = self._hexPositionToWorldMap.get((x, y))
                    if world:
                        worlds.append(world)
        else:
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
                    world = self._hexPositionToWorldMap.get((x, y))
                    if world and filterCallback(world):
                        worlds.append(world)

        return worlds

    def worldsInFlood(
            self,
            hex: astronomer.HexPosition,
            filterCallback: typing.Callable[[astronomer.World], bool] = None
            ) -> typing.List[astronomer.World]:
        world = self._hexPositionToWorldMap.get(hex.absolute())
        if not world:
            return []

        worlds = []
        if not filterCallback or filterCallback(world):
            worlds.append(world)

        todo = [world]
        seen = set(todo)
        while todo:
            world = todo.pop(0)
            hex = world.hex()
            for edge in astronomer.HexEdge:
                adjacentHex = hex.neighbour(edge=edge)
                adjacentWorld = self._hexPositionToWorldMap.get(adjacentHex.absolute())
                if adjacentWorld and (adjacentWorld not in seen):
                    todo.append(adjacentWorld)
                    seen.add(adjacentWorld)

                    if not filterCallback or filterCallback(adjacentWorld):
                        worlds.append(adjacentWorld)
        return worlds

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
        sector = self._sectorPositionToSectorMap.get(sectorPos)

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
        main = self._hexPositionToMainMap.get(hex.absolute())
        if main:
            return main

        worlds = self.worldsInFlood(hex=hex)
        if len(worlds) < Universe._MinMainWorldCount:
            return None

        main = astronomer.Main(hexes=(world.hex() for world in worlds))
        for world in worlds:
            self._hexPositionToMainMap[world.hex().absolute()] = main

        return main

    def routes(self) -> typing.Collection[astronomer.Route]:
        return common.ConstCollectionRef(self._routes)

    def hasRoutes(
            self,
            hex: astronomer.HexPosition
            ) -> bool:
        routes = self._hexPositionToRoutesMap.get(hex.absolute())
        return routes and len(routes) > 0

    def routesByPosition(
            self,
            hex: astronomer.HexPosition
            ) -> typing.List[astronomer.Route]:
        routes = self._hexPositionToRoutesMap.get(hex.absolute())
        if not routes:
            return []
        return list(routes)

    def connectedWorlds(
            self,
            hex: astronomer.HexPosition
            ) -> typing.List[astronomer.World]:
        routes = self._hexPositionToRoutesMap.get(hex.absolute())
        if not routes:
            return []

        worlds = []
        for route in routes:
            connectedHex = None
            if hex != route.startHex():
                connectedHex = route.startHex()
            elif hex != route.endHex():
                connectedHex = route.endHex()

            if connectedHex:
                connectedWorld = self._hexPositionToWorldMap.get(connectedHex.absolute())
                if connectedWorld:
                    worlds.append(connectedWorld)
        return worlds

    def labels(self) -> typing.Collection[astronomer.MapLabel]:
        return common.ConstCollectionRef(self._labels)

    def vectors(self) -> typing.Collection[astronomer.MapVector]:
        return common.ConstCollectionRef(self._vectors)

    def _addAllegiance(self, allegiance: astronomer.Allegiance) -> None:
        self._idToEntityMap[allegiance.entityId()] = allegiance
        self._allegiances.append(allegiance)

    def _addSophont(self, sophont: astronomer.Sophont) -> None:
        self._idToEntityMap[sophont.entityId()] = sophont
        self._sophonts.append(sophont)

    def _addSector(self, sector: astronomer.Sector) -> None:
        self._idToEntityMap[sector.entityId()] = sector
        # TODO: I don't thing I'll need the concept of subentities when
        # I've finished moving worlds, routes etc from sectors to the
        # universe
        for entity in sector.entities():
            self._idToEntityMap[entity.entityId()] = entity

        sectorPos = sector.position()
        self._sectorPositionToSectorMap[sectorPos.elements()] = sector

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

    def _removeSector(self, sector: astronomer.Sector) -> None:
        self._idToEntityMap.pop(sector.entityId(), None)
        for entity in sector.entities():
            self._idToEntityMap.pop(entity.entityId(), None)

        sectorPos = sector.position()
        self._sectorPositionToSectorMap.pop(sectorPos.elements(), None)

        canonicalName = sector.name().lower()
        sectors = self._nameToSectorMap.get(canonicalName)
        if sectors:
            sectors.discard(sector)
            if not sectors:
                del self._nameToSectorMap[canonicalName]

        for alternateName in sector.alternateNames():
            alternateName = alternateName.lower()
            sectors = self._nameToSectorMap.get(alternateName)
            if sectors:
                sectors.discard(sector)
                if not sectors:
                    del self._nameToSectorMap[alternateName]

        abbreviation = sector.abbreviation()
        if abbreviation:
            # NOTE: Unlike most string -> sector lookups, the abbreviation
            # map is case sensitive
            sectors = self._abbreviationToSectorMap.get(abbreviation)
            if sectors:
                sectors.discard(sector)
                if not sectors:
                    del self._abbreviationToSectorMap[abbreviation]

        for subsectorName in sector.subsectorNames():
            subsectorName = subsectorName.lower()
            sectors = self._subsectorNameToSectorMap.get(subsectorName)
            if sectors:
                sectors.discard(sector)
                if not sectors:
                    del self._subsectorNameToSectorMap[subsectorName]

    def _addWorld(self, world: astronomer.World) -> None:
        self._idToEntityMap[world.entityId()] = world

        hexPos = world.hex()
        self._hexPositionToWorldMap[hexPos.absolute()] = world

        sectorPos = hexPos.sectorPosition()
        sectorWorlds = self._sectorPositionToWorldsMap.get(sectorPos.elements())
        if sectorWorlds is None:
            sectorWorlds = set()
            self._sectorPositionToWorldsMap[sectorPos.elements()] = sectorWorlds
        sectorWorlds.add(world)

        subsectorPos = (*sectorPos.elements(), hexPos.subsectorCode())
        subsectorWorlds = self._subsectorPositionToWorldsMap.get(subsectorPos)
        if subsectorWorlds is None:
            subsectorWorlds = set()
            self._subsectorPositionToWorldsMap[subsectorPos] = subsectorWorlds
        subsectorWorlds.add(world)

        # Clear mains so they will be regenerated from the updated data
        self._hexPositionToMainMap.clear()

    def _removeWorld(self, world: astronomer.World) -> None:
        self._idToEntityMap.pop(world.entityId(), None)

        hexPos = world.hex()
        self._hexPositionToWorldMap.pop(hexPos.absolute(), None)

        sectorPos = hexPos.sectorPosition()
        sectorWorlds = self._sectorPositionToWorldsMap.get(sectorPos.elements())
        if sectorWorlds:
            sectorWorlds.discard(world)
            if not sectorWorlds:
                del self._sectorPositionToWorldsMap[sectorPos.elements()]

        subsectorPos = (*sectorPos.elements(), hexPos.subsectorCode())
        subsectorWorlds = self._subsectorPositionToWorldsMap.get(subsectorPos)
        if subsectorWorlds:
            subsectorWorlds.discard(world)
            if not subsectorWorlds:
                del self._subsectorPositionToWorldsMap[subsectorPos]

        # Clear mains so they will be regenerated from the updated data
        self._hexPositionToMainMap.clear()

    def _addRoute(self, route: astronomer.Route) -> None:
        self._routes.add(route)
        self._idToEntityMap[route.entityId()] = route

        for hex in (route.startHex(), route.endHex()):
            endpoints = self._hexPositionToRoutesMap.get(hex.absolute())
            if not endpoints:
                endpoints = set()
                self._hexPositionToRoutesMap[hex.absolute()] = endpoints
            endpoints.add(route)

    def _removeRoute(self, route: astronomer.Route) -> None:
        self._routes.discard(route)
        self._idToEntityMap.pop(route.entityId(), None)

        for hex in [route.startHex(), route.endHex()]:
            endpoints = self._hexPositionToRoutesMap.get(hex.absolute())
            if endpoints:
                endpoints.discard(route)
                if not endpoints:
                    del self._hexPositionToRoutesMap[hex.absolute()]

    def _addLabel(self, label: astronomer.MapLabel) -> None:
        self._idToEntityMap[label.entityId()] = label
        self._labels.append(label)

    def _addVector(self, vector: astronomer.MapVector) -> None:
        self._idToEntityMap[vector.entityId()] = vector
        self._vectors.append(vector)