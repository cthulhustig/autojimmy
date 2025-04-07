import json
import logging
import travellermap
import typing

class MainsFinder(object):
    # This is the value used by Traveller Map (tools\mains.js)
    _MinMainWorlds = 5

    _WorldsPerProgressStep = 100

    def __init__(self) -> None:
        self._worlds: typing.Set[travellermap.HexPosition] = set()

    def addWorld(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        self._worlds.add(hex)

    # Optimised version of algorithm used by Traveller Map (tools\mains.js)
    # Returns an iterable of mains, each main is an iterable of tuples
    # giving the sector x/y & hex x/y position of the world
    def search(
            self,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> typing.Iterable[typing.Iterable[travellermap.HexPosition]]:
        seen = set()
        mains = []

        progressStage = 'Generating Mains'
        totalWorlds = len(self._worlds)
        for progress, world in enumerate(self._worlds):
            if progressCallback and ((progress % MainsFinder._WorldsPerProgressStep) == 0):
                progressCallback(progressStage, progress, totalWorlds)

            if world in seen:
                continue

            main = [world]
            mains.append(main)

            index = 0
            while index < len(main):
                world = main[index]
                seen.add(world)
                index += 1

                for edge in travellermap.HexEdge:
                    neighbour = world.neighbourHex(edge=edge)
                    if (neighbour in self._worlds) and (neighbour not in seen):
                        main.append(neighbour)
                        seen.add(neighbour)

        # Drop mains that are under the required size
        mains = [main for main in mains if len(main) > MainsFinder._MinMainWorlds]

        # Sort mains from largest to smallest for consistency with how Traveller Map generates them
        mains = sorted(mains, key=lambda element: -len(element))

        if progressCallback:
            progressCallback(progressStage, totalWorlds, totalWorlds)

        return mains

class MainsGenerator(object):
    def __init__(self) -> None:
        self._defaultSectors = None

    def calculate(
            self,
            milieu: travellermap.Milieu,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> typing.Iterable[typing.Iterable[travellermap.HexPosition]]:
        # Traveller Map generates mains from M1105 world positions. The same
        # mains information is then use no mater which milieu you are viewing.
        # The unwritten rule seems to be that world positions can't change
        # between milieu. My addition of custom sectors breaks this logic as
        # world positions for a give sector can change completely depending on
        # the milieu. The approach used here is to use world positions from
        # milieu specific stock and custom sectors then, for sector positions
        # that don't have a milieu specific sector, take world locations from
        # _stock_ M1105 sectors
        if (milieu != travellermap.Milieu.M1105) and (self._defaultSectors == None):
            self._defaultSectors = self._loadSectorWorlds(
                milieu=travellermap.Milieu.M1105,
                stockOnly=True) # Custom sectors shouldn't be used for default sector data

        mainsGenerator = travellermap.MainsFinder()
        sectorWorlds = self._loadSectorWorlds(
            milieu=milieu,
            stockOnly=False) # Load custom sectors

        # If the milieu being updated isn't the base milieu then use worlds from the base milieu
        # for any locations where the base milieu has a sector but the current milieu doesn't.
        # This mimics the behaviour of Traveller Map but with support for custom sectors
        if milieu != travellermap.Milieu.M1105:
            seenSectors = set()
            for sectorInfo in sectorWorlds.keys():
                seenSectors.add((sectorInfo.x(), sectorInfo.y()))
            for sectorInfo in self._defaultSectors.keys():
                if (sectorInfo.x(), sectorInfo.y()) not in seenSectors:
                    sectorWorlds[sectorInfo] = self._defaultSectors[sectorInfo]

        for sectorInfo, worldList in sectorWorlds.items():
            for world in worldList:
                worldHex = world.attribute(travellermap.WorldAttribute.Hex)
                try:
                    if len(worldHex) != 4:
                        raise RuntimeError('Invalid hex length')
                    hexX = int(worldHex[:2])
                    hexY = int(worldHex[2:])
                except Exception as ex:
                    message = 'Mains generation skipping {world} ({sector}) due to invalid hex {hex}'.format(
                        world=world.attribute(travellermap.WorldAttribute.Name),
                        sector=sectorInfo.canonicalName(),
                        hex=worldHex)
                    logging.warning(message, exc_info=ex)
                    continue

                mainsGenerator.addWorld(travellermap.HexPosition(
                    sectorX=sectorInfo.x(),
                    sectorY=sectorInfo.y(),
                    offsetX=hexX,
                    offsetY=hexY))
        return mainsGenerator.search(progressCallback)

    def generateJson(
            self,
            milieu: travellermap.Milieu,
            progressCallback: typing.Optional[typing.Callable[[str, int, int], typing.Any]] = None
            ) -> str:
        mains = self.calculate(milieu=milieu, progressCallback=progressCallback)
        outputData = []
        for main in mains:
            outputMain = []
            for hex in main:
                outputMain.append(f'{hex.sectorX()}/{hex.sectorY()}/{hex.offsetX():02d}{hex.offsetY():02d}')
            outputData.append(outputMain)

        return json.dumps(outputData)

    @staticmethod
    def _loadSectorWorlds(
            milieu: travellermap.Milieu,
            stockOnly: bool
            ) -> typing.Mapping[travellermap.SectorInfo, typing.Iterable[travellermap.RawWorld]]:
        sectors = travellermap.DataStore.instance().sectors(
            milieu=milieu,
            stockOnly=stockOnly)
        sectorWorldMap = {}

        for sectorInfo in sectors:
            sectorData = travellermap.DataStore.instance().sectorFileData(
                sectorName=sectorInfo.canonicalName(),
                milieu=milieu,
                stockOnly=stockOnly)
            if not sectorData:
                continue
            sectorWorldMap[sectorInfo] = travellermap.readSector(
                content=sectorData,
                format=sectorInfo.sectorFormat(),
                identifier=sectorInfo.canonicalName())

        return sectorWorldMap
