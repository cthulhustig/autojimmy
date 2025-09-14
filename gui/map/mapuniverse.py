import cartographer
import traveller
import multiverse
import typing

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

    def subsectorName(self, code: str) -> typing.Optional[str]:
        subsector = self._sector.subsectorByCode(code)
        if not subsector:
            return None
        return subsector.name()

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
    def __init__(
            self,
            universe: multiverse.Universe
            ) -> None:
        self._universe = universe

        # TODO: Need to limit the number of wrappers maintained at any one time
        self._sectorWrappers: typing.Dict[
            multiverse.Milieu,
            typing.Dict[
                multiverse.SectorIndex,
                MapSector]] = {}

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

        sector = self._universe.sectorBySectorIndex(
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

        world = self._universe.worldByPosition(
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

        generator = self._universe.yieldSectorsInArea(
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

        generator = self._universe.yieldWorldsInArea(
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
        return self._universe.sectorHexToPosition(
            milieu=milieu,
            sectorHex=sectorHex)