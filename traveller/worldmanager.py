import fnmatch
import re
import logging
import math
import threading
import traveller
import travellermap
import typing

# This object is thread safe, however the world objects are only thread safe
# as they are currently read only (i.e. once loaded they never change).
class WorldManager(object):
    _SectorSearchHintPattern = re.compile(r'^(\(?.+?\)?)\s*\(\s*(.*)\s*\)\s*$')
    _AbsoluteHexPattern = re.compile(r'^\(?(-?\d+),\s*(-?\d+)\)?$')
    _RelativeHexPattern = re.compile(r'^\(?(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\)?$')

    _SubsectorHexWidth = 8
    _SubsectorHexHeight = 10
    _SubsectorPerSectorX = 4
    _SubsectorPerSectorY = 4
    _SubsectorCodeMap = {
        0:  'A', 1:  'B', 2:  'C', 3:  'D',
        4:  'E', 5:  'F', 6:  'G', 7:  'H',
        8:  'I', 9:  'J', 10: 'K', 11: 'L',
        12: 'M', 13: 'N', 14: 'O', 15: 'P'
    }

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _milieu = travellermap.Milieu.M1105 # Same default as Traveller Map
    _sectorList: typing.List[traveller.Sector] = []
    _canonicalNameMap: typing.Dict[str, traveller.Sector] = {}
    _alternateNameMap: typing.Dict[str, typing.List[traveller.Sector]] = {}
    _sectorPositionMap: typing.Dict[typing.Tuple[int, int], traveller.Sector] = {}
    _subsectorNameMap: typing.Dict[str, typing.List[traveller.Subsector]] = {}
    _subsectorSectorMap: typing.Dict[traveller.Subsector, traveller.Sector] = {}
    _absoluteWorldMap: typing.Dict[typing.Tuple[int, int], traveller.World] = {}

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

    @staticmethod
    def setMilieu(milieu: travellermap.Milieu) -> None:
        if WorldManager._instance:
            raise RuntimeError('You can\'t set the milieu after the singleton has been initialised')
        WorldManager._milieu = milieu

        # Configure the allegiance manager to use the same milieu
        traveller.AllegianceManager.setMilieu(milieu=milieu)

    def loadSectors(
            self,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> None:
        # Check if the sectors are already loaded. For speed we don't lock the mutex, this
        # works on the basis that checking the size of a dict is thread safe. This approach
        # means, if the sectors are found to not be loaded, we need to check again after we've
        # acquired the lock as another thread could sneak in and load the sectors between this
        # point and the point where we acquire the lock
        if self._canonicalNameMap:
            return # Sector map already loaded

        # Acquire lock while loading sectors
        with self._lock:
            if self._canonicalNameMap:
                # Another thread already loaded the sectors between the point we found they
                # weren't loaded and the point it acquired the mutex.
                return

            sectorCount = travellermap.DataStore.instance().sectorCount(milieu=self._milieu)
            for index, sectorInfo in enumerate(travellermap.DataStore.instance().sectors(milieu=self._milieu)):
                canonicalName = sectorInfo.canonicalName()
                logging.debug(f'Loading worlds for sector {canonicalName}')

                if progressCallback:
                    progressCallback(canonicalName, index + 1, sectorCount)

                sectorContent = travellermap.DataStore.instance().sectorFileData(
                    sectorName=canonicalName,
                    milieu=self._milieu)

                metadataContent = travellermap.DataStore.instance().sectorMetaData(
                    sectorName=canonicalName,
                    milieu=self._milieu)

                sector = self._loadSector(
                    sectorInfo=sectorInfo,
                    sectorContent=sectorContent,
                    metadataContent=metadataContent)

                logging.debug(f'Loaded {sector.worldCount()} worlds for sector {canonicalName}')

                self._sectorList.append(sector)
                self._sectorPositionMap[(sectorInfo.x(), sectorInfo.y())] = sector

                # Add canonical name to the main name map. The name is added lower case as lookups are
                # case insensitive
                self._canonicalNameMap[sectorInfo.canonicalName().lower()] = sector

                # Add alternate names and abbreviations to the alternate name map
                alternateNames = sector.alternateNames()
                if alternateNames:
                    for alternateName in alternateNames:
                        alternateName = alternateName.lower()
                        sectorList = self._alternateNameMap.get(alternateName)
                        if not sectorList:
                            sectorList = []
                            self._alternateNameMap[alternateName] = sectorList
                        sectorList.append(sector)

                abbreviation = sector.abbreviation()
                if abbreviation:
                    abbreviation = abbreviation.lower()
                    sectorList = self._alternateNameMap.get(abbreviation)
                    if not sectorList:
                        sectorList = []
                        self._alternateNameMap[abbreviation] = sectorList
                    sectorList.append(sector)

                for subsector in sector.subsectors():
                    subsectorName = subsector.name()
                    subsectorName = subsectorName.lower()
                    subsectorList = self._subsectorNameMap.get(subsectorName)
                    if not subsectorList:
                        subsectorList = []
                        self._subsectorNameMap[subsectorName] = subsectorList
                    subsectorList.append(subsector)

                    self._subsectorSectorMap[subsector] = sector

                for world in sector.worlds():
                    hexPos = world.hexPosition()
                    self._absoluteWorldMap[(hexPos.absoluteX(), hexPos.absoluteY())] = world

    def sectorName(
            self,
            sectorX: int,
            sectorY: int
            ) -> str:
        sector: traveller.Sector = self._sectorPositionMap.get((sectorX, sectorY))
        if not sector:
            return None
        return sector.name()

    def sectorNames(self) -> typing.Iterable[str]:
        sectorNames = []
        for sector in self._sectorList:
            sectorNames.append(sector.name())
        return sectorNames

    def sector(
            self,
            name: str
            ) -> traveller.Sector:
        return self._canonicalNameMap.get(name.lower())

    def sectors(self) -> typing.Iterable[traveller.Sector]:
        return self._sectorList

    # TODO: Should probably rename this to worldBySectorHex
    def world(
            self,
            sectorHex: str,
            ) -> typing.Optional[traveller.World]:
        try:
            pos = self.sectorHexToPosition(sectorHex=sectorHex)
        except Exception as ex:
            return None
        return self.worldByPosition(pos=pos)

    def worldByPosition(
            self,
            pos: travellermap.HexPosition
            ) -> typing.Optional[traveller.World]:
        return self._absoluteWorldMap.get(pos.absolute())

    def sectorByPosition(
            self,
            pos: travellermap.HexPosition
            ) -> typing.Optional[traveller.Sector]:
        return self._sectorPositionMap.get((pos.sectorX(), pos.sectorY()))

    def worldsInArea(
            self,
            center: travellermap.HexPosition,
            searchRadius: int,
            worldFilterCallback: typing.Callable[[traveller.World], bool] = None
            ) -> typing.List[traveller.World]:
        return list(self.yieldWorldsInArea(
            center=center,
            searchRadius=searchRadius,
            worldFilterCallback=worldFilterCallback))

    def positionToSectorHex(
            self,
            pos: travellermap.HexPosition
            ) -> str:
        sectorX, sectorY, offsetX, offsetY = pos.relative()
        sector = self._sectorPositionMap.get((sectorX, sectorY))
        if not sector:
            raise RuntimeError('No sector located at {sectorX}, {sectorY}')
        return traveller.formatSectorHex(
            sectorName=sector.name(),
            worldX=offsetX,
            worldY=offsetY)

    def sectorHexToPosition(
            self,
            sectorHex: str,
            ) -> travellermap.HexPosition:
        sectorName, offsetX, offsetY = traveller.splitSectorHex(
            sectorHex=sectorHex)

        # Sector name lookup is case insensitive. The sector name map stores
        # sector names in lower so search name should be converted to lower case
        # before searching
        sectorName = sectorName.lower()

        # Check to see if the sector name is a canonical sector name
        sector = self._canonicalNameMap.get(sectorName)
        if not sector:
            # Make a best effort attempt to find the sector by looking at
            # abbreviations/alternate names and subsector names. This is
            # important as in some places the official data does ths for things
            # like owner/colony worlds sector hexes. These matches are not
            # always unique so just use the first if more than one is found
            sectors = self._alternateNameMap.get(sectorName)
            if sectors:
               # Alternate sector name match
               sector = sectors[0]
            else:
                subsectors = self._subsectorNameMap.get(sectorName)
                if subsectors:
                    # Subsector name match
                    sector = self._subsectorSectorMap.get(subsectors[0])

        if not sector:
            raise RuntimeError(f'Failed to resolve sector {sectorName} for sector hex {sectorHex}')

        return travellermap.HexPosition(
            sectorX=sector.x(),
            sectorY=sector.y(),
            offsetX=offsetX,
            offsetY=offsetY)

    def canonicalHexName(
            self,
            pos: travellermap.HexPosition
            ) -> str:
        world = self.worldByPosition(pos=pos)
        if world:
            return world.name(includeSubsector=True)
        try:
            return self.positionToSectorHex(pos=pos)
        except ValueError:
            return str(pos)

    def yieldWorldsInArea(
            self,
            center: travellermap.HexPosition,
            searchRadius: int,
            worldFilterCallback: typing.Callable[[traveller.World], bool] = None
            ) -> typing.Generator[traveller.World, None, None]:
        minLength = searchRadius + 1
        maxLength = (searchRadius * 2) + 1
        deltaLength = int(math.floor((maxLength - minLength) / 2))

        centerX, centerY = center.absolute()
        startX = centerX - searchRadius
        finishX = centerX + searchRadius
        startY = (centerY - searchRadius) + deltaLength
        finishY = (centerY + searchRadius) - deltaLength
        if (startX & 0b1) != 0:
            startY += 1
            if (searchRadius & 0b1) != 0:
                finishY -= 1
        else:
            if (searchRadius & 0b1) != 0:
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
                world = self._absoluteWorldMap.get((x, y))
                if world and ((not worldFilterCallback) or worldFilterCallback(world)):
                    yield world

    def searchForWorlds(
            self,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[traveller.World]:
        searchString = searchString.strip()

        # If the search string matches the sector hex format or either the
        # absolute or relative coordinate formats then try to a world at the
        # specified location. If a world is found then it's our only result
        try:
            foundWorld = self.world(sectorHex=searchString)
            if foundWorld:
                return [foundWorld]
        except:
            pass # Search string is not a sector hex

        result = self._AbsoluteHexPattern.match(searchString)
        if result:
            pos = travellermap.HexPosition(
                absoluteX=int(result.group(1)),
                absoluteY=int(result.group(2)))
            foundWorld = self.worldByPosition(pos=pos)
            if foundWorld:
                return [foundWorld]

        result = self._RelativeHexPattern.match(searchString)
        if result:
            sectorX = int(result.group(1))
            sectorY = int(result.group(2))
            offsetX = int(result.group(3))
            offsetY = int(result.group(4))
            if (offsetX >= 0  and offsetX < travellermap.SectorWidth) and \
                (offsetY >= 0 and offsetY < travellermap.SectorHeight):
                pos = travellermap.HexPosition(
                    sectorX=sectorX,
                    sectorY=sectorY,
                    offsetX=offsetX,
                    offsetY=offsetY)
                foundWorld = self.worldByPosition(pos=pos)
                if foundWorld:
                    return [foundWorld]

        searchWorldLists = None
        result = self._SectorSearchHintPattern.match(searchString)
        filterString = searchString
        if result:
            # We've matched the sector search hint pattern so check to see if the hint is actually
            # a known sector. If it is then perform the search with just the world portion of the
            # search string and filter the results afterwards. If it's not a known sector then just
            # perform the search with the full search string as normal
            worldString = result.group(1)
            hintString = result.group(2)

            searchWorldLists = self.searchForSectors(searchString=hintString)
            for subsector in self.searchForSubsectors(searchString=hintString):
                sector = self._subsectorSectorMap.get(subsector)
                if sector not in searchWorldLists:
                    searchWorldLists.append(subsector)

            if searchWorldLists:
                filterString = worldString

        if not searchWorldLists:
            # Search the worlds in all sectors. This will happen if no sector/subsector is specified
            # _or_ if the specified sector/subsector is unknown
            searchWorldLists = self._sectorList

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

        matches: typing.List[traveller.World] = []
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
        subsectorMatches: typing.List[traveller.World] = []
        for subsector in self.searchForSubsectors(searchString=searchString):
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
        sectorMatches: typing.List[traveller.World] = []
        for sector in self.searchForSectors(searchString=searchString):
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
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[traveller.Subsector]:
        searchString = searchString.strip()
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

        matches: typing.List[traveller.Subsector] = []
        for sector in self._sectorList:
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
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[traveller.Sector]:
        searchString = searchString.strip()
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

        matches: typing.List[traveller.Sector] = []
        for sector in self._sectorList:
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
            sectorInfo: travellermap.SectorInfo,
            sectorContent: str,
            metadataContent: str
            ) -> traveller.Sector:
        sectorName = sectorInfo.canonicalName()
        sectorX = sectorInfo.x()
        sectorY = sectorInfo.y()

        subsectorMap = {}
        allegianceMap = {}

        # Setup default subsector names. Some sectors just use the code A-P but we need
        # something unique
        for code in list(map(chr, range(ord('A'), ord('P') + 1))):
            subsectorMap[code] = f'{sectorName} Subsector {code}'

        rawMetadata = travellermap.readMetadata(
            content=metadataContent,
            format=sectorInfo.metadataFormat(),
            identifier=sectorName)

        rawWorlds = travellermap.readSector(
            content=sectorContent,
            format=sectorInfo.sectorFormat(),
            identifier=sectorName)

        subsectorNames = rawMetadata.subsectorNames()
        if subsectorNames:
            for code, name in subsectorNames.items():
                if not code or not name:
                    continue

                # NOTE: Unlike most other places, it's intentional that this is upper
                code = code.upper()
                assert(code in subsectorMap)
                subsectorMap[code] = name

        allegiances = rawMetadata.allegiances()
        if allegiances:
            for allegiance in allegiances:
                if not allegiance.code() or not allegiance.name():
                    continue

                # NOTE: The code here is intentionally left with the case as it appears int metadata as
                # there are some sectors where allegiances vary only by case (see AllegianceManager)
                allegianceMap[allegiance.code()] = allegiance.name()

        worlds = []
        for rawWorld in rawWorlds:
            try:
                hex = rawWorld.attribute(travellermap.WorldAttribute.Hex)
                worldName = rawWorld.attribute(travellermap.WorldAttribute.Name)
                if not worldName:
                    # If the world doesn't have a name the sector combined with the hex. This format
                    # is important as it's the same format as Traveller Map meaning searches will
                    # work
                    worldName = f'{sectorName} {hex}'

                subsectorCode = WorldManager._calculateSubsectorCode(relativeWorldHex=hex)
                subsectorName = subsectorMap[subsectorCode]

                world = traveller.World(
                    name=worldName,
                    sectorName=sectorName,
                    subsectorName=subsectorName,
                    hex=hex,
                    allegiance=rawWorld.attribute(travellermap.WorldAttribute.Allegiance),
                    uwp=rawWorld.attribute(travellermap.WorldAttribute.UWP),
                    economics=rawWorld.attribute(travellermap.WorldAttribute.Economics),
                    culture=rawWorld.attribute(travellermap.WorldAttribute.Culture),
                    nobilities=rawWorld.attribute(travellermap.WorldAttribute.Nobility),
                    remarks=rawWorld.attribute(travellermap.WorldAttribute.Remarks),
                    zone=rawWorld.attribute(travellermap.WorldAttribute.Zone),
                    stellar=rawWorld.attribute(travellermap.WorldAttribute.Stellar),
                    pbg=rawWorld.attribute(travellermap.WorldAttribute.PBG),
                    systemWorlds=rawWorld.attribute(travellermap.WorldAttribute.SystemWorlds),
                    bases=rawWorld.attribute(travellermap.WorldAttribute.Bases),
                    sectorX=sectorX,
                    sectorY=sectorY)
                worlds.append(world)
            except Exception as ex:
                logging.warning(
                    f'Failed to process world entry on line {rawWorld.lineNumber()} in data for sector {sectorName}',
                    exc_info=ex)
                continue # Continue trying to process the rest of the worlds

        # Add the allegiances for this sector to the allegiance manager
        traveller.AllegianceManager.instance().addSectorAllegiances(
            sectorName=sectorName,
            allegiances=allegianceMap)

        return traveller.Sector(
            name=sectorName,
            alternateNames=rawMetadata.alternateNames(),
            abbreviation=rawMetadata.abbreviation(),
            x=sectorX,
            y=sectorY,
            worlds=worlds,
            subsectorNames=subsectorMap.values())

    @staticmethod
    def _calculateSubsectorCode(
            relativeWorldHex: str
            ) -> typing.Optional[str]:
        if len(relativeWorldHex) != 4:
            raise RuntimeError(f'Invalid relative world hex "{relativeWorldHex}"')

        worldX = int(relativeWorldHex[:2])
        worldY = int(relativeWorldHex[-2:])

        subsectorX = (worldX - 1) // WorldManager._SubsectorHexWidth
        if subsectorX < 0 or subsectorX >= WorldManager._SubsectorPerSectorX:
            raise RuntimeError(f'Subsector X position for world hex "{relativeWorldHex}" is out of range')

        subsectorY = (worldY - 1) // WorldManager._SubsectorHexHeight
        if subsectorY < 0 or subsectorY >= WorldManager._SubsectorPerSectorY:
            raise RuntimeError(f'Subsector Y position for world hex "{relativeWorldHex}" is out of range')

        index = (subsectorY * WorldManager._SubsectorPerSectorX) + subsectorX

        code = WorldManager._SubsectorCodeMap.get(index)
        return code
