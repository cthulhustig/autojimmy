import cartographer
import traveller
import multiverse
import typing

# TODO: I think I want to do some reshuffling so this isn't needed
# 1. Move WorldManager, World, Sector & Subsector into a new universe namespace
#   - Probably other stuff as well (Borders, Allegiances, UWP, PBG etc)
#   - Basically everything that's used to define the universe data
# 2. What's left in the current traveller & travellermap directories will be
#    split between logic and a new rules directory
#   - Stuff that is just capturing the traveller rules (berthing, refuelling etc)
#     should go in rules
#   - Stuff built on top of the rules and universe should go in logic
# 3. I'm not sure where the abstract universe should live, probably outside of
#    the cartographer (probably in the new universe directory)

class MapWorld(cartographer.AbstractWorld):
    def __init__(
            self,
            universe: 'MapUniverse',
            world: multiverse.World
            ) -> None:
        self._universe = universe
        self._world = world

    def milieu(self) -> multiverse.Milieu:
        return self._world.milieu()

    def hex(self) -> multiverse.HexPosition:
        return self._world.hex()

    def name(self) -> typing.Optional[str]:
        return self._world.name() if not self._world.isNameGenerated() else None

    def sector(self) -> 'MapSector':
        return self._universe.sectorAt(
            milieu=self._world.milieu(),
            index=self._world.hex().sectorIndex())

    def uwp(self) -> multiverse.UWP:
        return self._world.uwp()

    def population(self) -> int:
        return self._world.population()

    def zone(self) -> typing.Optional[multiverse.ZoneType]:
        return self._world.zone()

    def isAnomaly(self) -> bool:
        return self._world.isAnomaly()

    def allegiance(self) -> str:
        return self._world.allegiance()

    def legacyAllegiance(self) -> typing.Optional[str]:
        return multiverse.AllegianceManager.instance().legacyCode(
            milieu=self._world.milieu(),
            code=self._world.allegiance())

    def basesAllegiance(self) -> typing.Optional[str]:
        return multiverse.AllegianceManager.instance().basesCode(
            milieu=self._world.milieu(),
            code=self._world.allegiance())

    def bases(self) -> multiverse.Bases:
        return self._world.bases()

    def stellar(self) -> multiverse.Stellar:
        return self._world.stellar()

    def remarks(self) -> multiverse.Remarks:
        return self._world.remarks()

    def hasWaterRefuelling(self) -> bool:
        return traveller.worldHasWaterRefuelling(world=self._world)

    def hasGasGiantRefuelling(self) -> bool:
        return traveller.worldHasGasGiantRefuelling(world=self._world)

    # NOTE: It's important that different instances of this class wrapping
    # the same object are seen as the same. This allows the the universe
    # implementation to discard instances of the wrapper that it doesn't
    # need and recreate them later without worrying about caches in the
    # renderer getting messed up
    def __hash__(self) -> int:
        return self._world.__hash__()

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, MapWorld):
            return self._world == other._world
        return NotImplemented

class MapSubsector(cartographer.AbstractSubsector):
    def __init__(
            self,
            universe: 'MapUniverse',
            subsector: multiverse.Subsector
            ) -> None:
        self._universe = universe
        self._subsector = subsector

    def milieu(self) -> multiverse.Milieu:
        return self._subsector.milieu()

    def index(self) -> multiverse.SubsectorIndex:
        return self._subsector.index()

    def sector(self) -> 'MapSector':
        return self._universe.sectorAt(
            milieu=self._subsector.milieu(),
            index=self._subsector.index().sectorIndex())

    def name(self) -> typing.Optional[str]:
        return self._subsector.name() if not self._subsector.isNameGenerated() else None

    def worlds(self) -> typing.Iterable[MapWorld]:
        for world in self._subsector.yieldWorlds():
            wrapper = self._universe.worldAt(
                milieu=world.milieu(),
                hex=world.hex())
            if wrapper:
                yield wrapper

    def worldHexes(self) -> typing.Iterable[multiverse.HexPosition]:
        for world in self._subsector.yieldWorlds():
            yield world.hex()

    # NOTE: It's important that different instances of this class wrapping
    # the same object are seen as the same. This allows the the universe
    # implementation to discard instances of the wrapper that it doesn't
    # need and recreate them later without worrying about caches in the
    # renderer getting messed up
    def __hash__(self) -> int:
        return self._subsector.__hash__()

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, MapSubsector):
            return self._subsector == other._subsector
        return NotImplemented

class MapSector(cartographer.AbstractSector):
    def __init__(
            self,
            universe: 'MapUniverse',
            sector: multiverse.Sector
            ) -> None:
        self._universe = universe
        self._sector = sector

    def milieu(self) -> multiverse.Milieu:
        return self._sector.milieu()

    def index(self) -> multiverse.SectorIndex:
        return self._sector.index()

    def name(self) -> str:
        return self._sector.name()

    def sectorLabel(self) -> typing.Optional[str]:
        return self._sector.sectorLabel()

    def isSelected(self) -> bool:
        return self._sector.selected()

    def tagging(self) -> multiverse.SectorTagging:
        return self._sector.tagging()

    def worlds(self) -> typing.Iterable[MapWorld]:
        for world in self._sector.yieldWorlds():
            wrapper = self._universe.worldAt(
                milieu=world.milieu(),
                hex=world.hex())
            if wrapper:
                yield wrapper

    def worldHexes(self) -> typing.Iterable[multiverse.HexPosition]:
        for world in self._sector.yieldWorlds():
            yield world.hex()

    def regions(self) -> typing.Iterable[multiverse.Region]:
        return self._sector.yieldRegions()

    def borders(self) -> typing.Iterable[multiverse.Border]:
        return self._sector.yieldBorders()

    def routes(self) -> typing.Iterable[multiverse.Route]:
        return self._sector.yieldRoutes()

    def labels(self) -> typing.Iterable[multiverse.Label]:
        return self._sector.yieldLabels()

    # NOTE: It's important that different instances of this class wrapping
    # the same object are seen as the same. This allows the the universe
    # implementation to discard instances of the wrapper that it doesn't
    # need and recreate them later without worrying about caches in the
    # renderer getting messed up
    def __hash__(self) -> int:
        return self._sector.__hash__()

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, MapSector):
            return self._sector == other._sector
        return NotImplemented

class MapUniverse(cartographer.AbstractUniverse):
    def __init__(self) -> None:
        # TODO: Need to limit the number of wrappers maintained at any one time
        self._sectorWrappers: typing.Dict[
            multiverse.Milieu,
            typing.Dict[
                multiverse.SectorIndex,
                MapSector]] = {}

        self._subsectorWrappers: typing.Dict[
            multiverse.Milieu,
            typing.Dict[
                multiverse.SubsectorIndex,
                MapSubsector]] = {}

        self._worldWrappers: typing.Dict[
            multiverse.Milieu,
            typing.Dict[
                multiverse.HexPosition,
                MapWorld]] = {}

    def sectorAt(
            self,
            milieu: multiverse.Milieu,
            index: multiverse.SectorIndex,
            includePlaceholders: bool = False
            ) -> typing.Optional[MapSector]:
        milieuSectors = self._sectorWrappers.get(milieu)
        if milieuSectors is not None:
            wrapper = milieuSectors.get(index)
            if wrapper:
                return wrapper if includePlaceholders or wrapper.milieu() is milieu else None
        else:
            milieuSectors = {}
            self._sectorWrappers[milieu] = milieuSectors

        sector = multiverse.WorldManager.instance().sectorBySectorIndex(
            milieu=milieu,
            index=index,
            includePlaceholders=includePlaceholders)
        if not sector:
            return None

        wrapper = MapSector(universe=self, sector=sector)
        milieuSectors[index] = wrapper
        return wrapper

    def worldAt(
            self,
            milieu: multiverse.Milieu,
            hex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.Optional[MapWorld]:
        milieuWorlds = self._worldWrappers.get(milieu)
        if milieuWorlds is not None:
            wrapper = milieuWorlds.get(hex)
            if wrapper:
                return wrapper if includePlaceholders or wrapper.milieu() is milieu else None
        else:
            milieuWorlds = {}
            self._worldWrappers[milieu] = milieuWorlds

        world = multiverse.WorldManager.instance().worldByPosition(
            milieu=milieu,
            hex=hex,
            includePlaceholders=includePlaceholders)
        if not world:
            return None

        wrapper = MapWorld(universe=self, world=world)
        milieuWorlds[hex] = wrapper
        return wrapper

    def sectorsInArea(
            self,
            milieu: multiverse.Milieu,
            ulHex: multiverse.HexPosition,
            lrHex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.List[MapSector]:
        milieuSectors = self._sectorWrappers.get(milieu)
        if milieuSectors is None:
            milieuSectors = {}
            self._sectorWrappers[milieu] = milieuSectors

        generator = multiverse.WorldManager.instance().yieldSectorsInArea(
            milieu=milieu,
            upperLeft=ulHex,
            lowerRight=lrHex,
            includePlaceholders=includePlaceholders)
        results = []
        for sector in generator:
            index = sector.index()
            wrapper = milieuSectors.get(index)
            if not wrapper:
                wrapper = MapSector(universe=self, sector=sector)
                milieuSectors[index] = wrapper
            results.append(wrapper)
        return results

    def subsectorsInArea(
            self,
            milieu: multiverse.Milieu,
            ulHex: multiverse.HexPosition,
            lrHex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.List[MapSubsector]:
        milieuSubsectors = self._subsectorWrappers.get(milieu)
        if milieuSubsectors is None:
            milieuSubsectors = {}
            self._subsectorWrappers[milieu] = milieuSubsectors

        generator = multiverse.WorldManager.instance().yieldSubsectorsInArea(
            milieu=milieu,
            upperLeft=ulHex,
            lowerRight=lrHex,
            includePlaceholders=includePlaceholders)
        results = []
        for subsector in generator:
            index = subsector.index()
            wrapper = milieuSubsectors.get(index)
            if not wrapper:
                wrapper = MapSubsector(universe=self, subsector=subsector)
                milieuSubsectors[index] = wrapper
            results.append(wrapper)
        return results

    def worldsInArea(
            self,
            milieu: multiverse.Milieu,
            ulHex: multiverse.HexPosition,
            lrHex: multiverse.HexPosition,
            includePlaceholders: bool = False
            ) -> typing.List[MapWorld]:
        milieuWorlds = self._worldWrappers.get(milieu)
        if milieuWorlds is None:
            milieuWorlds = {}
            self._worldWrappers[milieu] = milieuWorlds

        generator = multiverse.WorldManager.instance().yieldWorldsInArea(
            milieu=milieu,
            upperLeft=ulHex,
            lowerRight=lrHex,
            includePlaceholders=includePlaceholders)
        results = []
        for world in generator:
            hex = world.hex()
            wrapper = milieuWorlds.get(hex)
            if not wrapper:
                wrapper = MapWorld(universe=self, world=world)
                milieuWorlds[hex] = wrapper
            results.append(wrapper)
        return results

    def sectorHexToPosition(
            self,
            milieu: multiverse.Milieu,
            sectorHex: str
            ) -> multiverse.HexPosition:
        return multiverse.WorldManager.instance().sectorHexToPosition(
            milieu=milieu,
            sectorHex=sectorHex)