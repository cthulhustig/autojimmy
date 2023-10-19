import fnmatch
import re
import logging
import threading
import traveller
import travellermap
import typing

# This object is thread safe, however the world objects are only thread safe
# as they are currently read only (i.e. once loaded they never change).
class WorldManager(object):
    _SectorSearchHintPattern = re.compile('^(\(?.+?\)?)\s*\(\s*(.*)\s*\)\s*$')
    _HeaderPattern = re.compile('(?:([\w{}()\[\]]+)\s*)')
    _SeparatorPattern = re.compile('(?:([-]+)\s?)')
    _SubsectorPattern = re.compile('#\s*Subsector ([a-pA-P]{1}): (.+)')
    _AllegiancePattern = re.compile('#\s*Alleg: (\S+): ["?](.+)["?]')

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

    _HexColumn = 'Hex'
    _NameColumn = 'Name'
    _UWPColumn = 'UWP'
    _RemarksColumn = 'Remarks'
    _ImportanceColumn = '{Ix}'
    _EconomicsColumn = '(Ex)'
    _CultureColumn = '[Cx]'
    _NobilityColumn = 'N'
    _BasesColumn = 'B'
    _ZoneColumn = 'Z'
    _PBGColumn = 'PBG'
    _SystemWorldsColumn = 'W'
    _AllegianceColumn = 'A'
    _StellarColumn = 'Stellar'

    _instance = None # Singleton instance
    _lock = threading.Lock()
    _milieu = travellermap.Milieu.M1105 # Same default as Traveller Map
    _sectorList: typing.List[traveller.Sector] = []
    _sectorNameMap: typing.Dict[str, traveller.Sector] = {}
    _sectorPositionMap: typing.Dict[typing.Tuple[int, int], traveller.Sector] = {}
    _subsectorNameMap: typing.Dict[str, typing.List[traveller.Subsector]] = {}

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
        if self._sectorNameMap:
            return # Sector map already loaded

        # Acquire lock while loading sectors
        with self._lock:
            if self._sectorNameMap:
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

                # Sectors can have multiple names. We have a single  sector object that uses the
                # first name but multiple entries in the sector name map (but only a single entry
                # in the position map). The name is converted to lower case before storing in the
                # map to allow for case insensitive searching
                self._sectorNameMap[sectorInfo.canonicalName().lower()] = sector

                alternateNames = sector.alternateNames()
                if alternateNames:
                    for sectorName in alternateNames:
                        sectorName = sectorName.lower()
                        self._sectorNameMap[sectorName] = sector

                # If the sector has an abbreviation add it to the name map
                abbreviation = sector.abbreviation()
                if abbreviation:
                    abbreviation = abbreviation.lower()
                    assert((abbreviation not in self._sectorNameMap) or (self._sectorNameMap[abbreviation] == sector))
                    self._sectorNameMap[abbreviation] = sector

                for subsector in sector.subsectors():
                    subsectorName = subsector.name()
                    subsectorName = subsectorName.lower()
                    subsectorList = self._subsectorNameMap.get(subsectorName)
                    if not subsectorList:
                        subsectorList = []
                        self._subsectorNameMap[subsectorName] = subsectorList
                    subsectorList.append(subsector)

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
        return self._sectorNameMap.get(name.lower())

    def sectors(self) -> typing.Iterable[traveller.Sector]:
        return self._sectorList

    def world(
            self,
            sectorHex: str,
            ) -> typing.Optional[traveller.World]:
        sectorName, worldX, worldY = traveller.splitSectorHex(sectorHex=sectorHex)

        # Sector name lookup is case insensitive. The sector name map stores sector names in lower
        # so search name should be converted to lower case before searching
        sectorName = sectorName.lower()
        sector: traveller.Sector = self._sectorNameMap.get(sectorName)
        if not sector:
            # Return None rather than throwing an exception, some of the Second Survey data has
            # invalid sector names (example: The owner of Seddon has a sector hex of Zaru-2340 but
            # Zaru isn't a sector (it's a sub sector))
            return None

        return sector.worldByPosition(x=worldX, y=worldY)

    # Reimplementation of code from Traveller Map source code.
    # Sectors in Selector.cs
    def worldsInArea(
            self,
            sectorName: str,
            worldX: int,
            worldY: int,
            searchRadius: int,
            worldFilterCallback: typing.Callable[[traveller.World], bool] = None
            ) -> typing.List[traveller.World]:
        # Sector name lookup is case insensitive. The sector name map stores sector names in lower
        # so search name should be converted to lower case before searching
        sectorName = sectorName.lower()
        sector = self._sectorNameMap.get(sectorName)
        if not sector:
            raise RuntimeError(f'Unknown sector "{sectorName}"')

        sectorX = sector.x()
        sectorY = sector.y()

        centerX, centerY = travellermap.relativeHexToAbsoluteHex(sectorX, sectorY, worldX, worldY)
        minX = centerX - (searchRadius + 1)
        maxX = centerX + (searchRadius + 1)
        minY = centerY - (searchRadius + 1)
        maxY = centerY + (searchRadius + 1)

        worlds = []
        for y in range(minY, maxY + 1):
            for x in range(minX, maxX + 1):
                if travellermap.hexDistance(centerX, centerY, x, y) > searchRadius:
                    continue

                sectorX, sectorY, worldX, worldY = travellermap.absoluteHexToRelativeHex(x, y)
                sector: traveller.Sector = self._sectorPositionMap.get((sectorX, sectorY))
                if not sector:
                    # No sector with this position (we've hit the edge of the map)
                    continue

                world = sector.worldByPosition(worldX, worldY)
                if world:
                    if worldFilterCallback and not worldFilterCallback(world):
                        # Skip the world if it doesn't match the filter
                        continue

                    worlds.append(world)

        return worlds

    def searchForWorlds(
            self,
            searchString: str,
            maxResults: int = 0 # 0 means unlimited
            ) -> typing.List[traveller.World]:
        searchLists = None
        result = self._SectorSearchHintPattern.match(searchString)
        if result:
            # We've matched the sector search hint pattern so check to see if the hint is actually
            # a known sector. If it is then perform the search with just the world portion of the
            # search string and filter the results afterwards. If it's not a known sector then just
            # perform the search with the full search string as normal
            worldString = result.group(1)
            sectorString = result.group(2)

            # Sector name lookup is case insensitive. The sector name map stores sector names in
            # lower so search name should be converted to lower case before searching
            sectorString = sectorString.lower()
            searchLists = []

            if sectorString in self._sectorNameMap:
                # Search the worlds in the specified sector
                searchLists.append(self._sectorNameMap[sectorString])
                searchString = worldString

            if sectorString in self._subsectorNameMap:
                # Search the worlds in the specified subsector(s). There are multiple subsectors with
                # the same name so this may require searching multiple subsectors
                searchLists.extend(self._subsectorNameMap[sectorString])
                searchString = worldString

        if not searchLists:
            # Search the worlds in all sectors. This will happen if no sector/subsector is specified
            # _or_ if the specified sector/subsector is unknown
            searchLists = self._sectorList

        # Try to mimic the behaviour of Traveller Map where just typing the start of a world name
        # will match the world without needing to specify wild cards
        if searchString[-1:] != '*':
            searchString += '*'
        searchExpression = re.compile(
            fnmatch.translate(searchString),
            re.IGNORECASE)

        # Use a set for storing found worlds to avoid duplicates of the same world. This can happen
        # when the sector and subsector a world is in have the same name (e.g. Tristan is in the
        # Katoonah subsector in the Katoonah sector, this is actually an even more special case as
        # there is also a Tristan in the Kherrou subsector which is also in the Kherrou sector).
        foundWorlds: typing.Set[traveller.World] = set()
        for worldList in searchLists:
            for world in worldList:
                if searchExpression.match(world.name()):
                    foundWorlds.add(world)
                    if maxResults and len(foundWorlds) >= maxResults:
                        return list(foundWorlds)
        return list(foundWorlds) # Convert to a list for ease of use by consumers

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

        rawMetadata = travellermap.parseMetadata(
            content=metadataContent,
            metadataFormat=sectorInfo.metadataFormat(),
            identifier=sectorName)

        rawWorlds = travellermap.parseSector(
            content=sectorContent,
            fileFormat=sectorInfo.sectorFormat(),
            identifier=sectorName)

        for code, name in rawMetadata.subsectorNames().items():
            code = code.upper()
            assert(code in subsectorMap)
            subsectorMap[code] = name

        for code, name in rawMetadata.allegiances().items():
            code = code.upper()
            allegianceMap[code] = name

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
                    # TODO: This stripping should probably live somewhere ele (with code that parses economic/culture codes)
                    economics=rawWorld.attribute(travellermap.WorldAttribute.Economics).strip('()'),
                    culture=rawWorld.attribute(travellermap.WorldAttribute.Culture).strip('[]'),
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
