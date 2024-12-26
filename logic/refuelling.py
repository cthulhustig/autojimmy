import array
import common
import enum
import itertools
import logic
import math
import traveller
import travellermap
import typing

class RefuellingType(enum.Enum):
    Refined = 'Refined'
    Unrefined = 'Unrefined'
    Wilderness = 'Wilderness'
    FuelCache = 'Fuel Cache'
    Anomaly = 'Anomaly'

# NOTE: RefinedFuelPreferred will give the same results as UnrefinedFuelOnly if
# A/B class star ports are configured to sell unrefined fuel
class RefuellingStrategy(enum.Enum):
    RefinedFuelOnly = 'Refined Fuel Only'
    UnrefinedFuelOnly = 'Unrefined Fuel Only'
    GasGiantOnly = 'Gas Giant Only'
    WaterOnly = 'Water Only'
    WildernessOnly = 'Wilderness Only'
    RefinedFuelPreferred = 'Refined Fuel Preferred'
    UnrefinedFuelPreferred = 'Unrefined Fuel Preferred'
    GasGiantPreferred = 'Gas Giant Preferred'
    WaterPreferred = 'Water Preferred'
    WildernessPreferred = 'Wilderness Preferred'


# Fuel Caches are worlds that have the {Fuel} remark. From looking at the map
# data, the only place the remark is used in VoidBridges and Pirian Domain Fuel
# Factories and all worlds that have the {Fuel} remark also have the {Anomaly}
# remark.
# From the description of both the fuel is provided free. The description for
# VoidBridges says refined fuel is available but it doesn't say if unrefined
# fuel is available. I don't think it really matters for what I'm doing as using
# fuel caches can be turned on/off by the user.
# https://www.wiki.travellerrpg.com/VoidBridges
# https://www.wiki.travellerrpg.com/Pirian_Domain_Fuel_Factories
_FuelCacheFuelCostPerTon = common.ScalarCalculation(
    value=0,
    name='Fuel Cache Fuel Cost Per Ton')

# I'm working on the assumption that you have to berth in order to refuel,
# however, berthing doesn't cost anything as that would be weird when the fuel
# is free.
_FuelCacheBerthingCost = common.ScalarCalculation(
    value=0,
    name='Fuel Cache Berthing Cost')

class PitStopCostCalculator(object):
    def __init__(
            self,
            refuellingStrategy: RefuellingStrategy,
            useFuelCaches: bool,
            anomalyFuelCost: typing.Optional[typing.Union[int, common.ScalarCalculation]],
            anomalyBerthingCost: typing.Optional[typing.Union[int, common.ScalarCalculation]],
            rules: traveller.Rules
            ) -> None:
        if isinstance(anomalyFuelCost, int):
            anomalyFuelCost = common.ScalarCalculation(
                value=anomalyFuelCost,
                name='Anomaly Fuel Cost Per Ton')
        if isinstance(anomalyBerthingCost, int):
            anomalyBerthingCost = common.ScalarCalculation(
                value=anomalyBerthingCost,
                name='Anomaly Berthing Cost')

        self._refuellingStrategy = refuellingStrategy
        self._useFuelCaches = useFuelCaches
        self._anomalyFuelCost = anomalyFuelCost
        self._anomalyBerthingCost = anomalyBerthingCost
        self._rules = rules
        self._worldFuelTypes = {}

    def refuellingType(
            self,
            world: traveller.World
            ) -> typing.Optional[RefuellingType]:
        if world in self._worldFuelTypes:
            return self._worldFuelTypes[world]

        refuellingType = self._selectRefuellingType(world=world)
        self._worldFuelTypes[world] = refuellingType
        return refuellingType

    def fuelCost(
            self,
            world: traveller.World
            ) -> typing.Optional[common.ScalarCalculation]:
        refuellingType = self.refuellingType(world=world)
        if refuellingType is logic.RefuellingType.Refined:
            return traveller.RefinedFuelCostPerTon
        if refuellingType is logic.RefuellingType.Unrefined:
            return traveller.UnrefinedFuelCostPerTon
        if refuellingType is logic.RefuellingType.Wilderness:
            return traveller.WildernessFuelCostPerTon
        if refuellingType is logic.RefuellingType.FuelCache:
            return _FuelCacheFuelCostPerTon if self._useFuelCaches else None
        if refuellingType is logic.RefuellingType.Anomaly:
            return self._anomalyFuelCost
        return None

    def berthingCost(
            self,
            world: traveller.World,
            mandatory: bool = False, # Is berthing mandatory rather than based
                                     # on the refuelling type for the world
            diceRoller: typing.Optional[common.DiceRoller] = None
            ) -> typing.Optional[typing.Union[
                common.ScalarCalculation,
                common.RangeCalculation]]:
        if not mandatory:
            refuellingType = self.refuellingType(world=world)
            if (not refuellingType) or \
                    (refuellingType is logic.RefuellingType.Wilderness):
                return None

        berthingCost = traveller.starPortBerthingCost(
            world=world,
            diceRoller=diceRoller)
        if berthingCost:
            return berthingCost

        isFuelCache = world.isFuelCache()
        if self._useFuelCaches and isFuelCache:
            return _FuelCacheBerthingCost

        isAnomaly = world.isAnomaly()
        if self._anomalyBerthingCost and (isAnomaly and not isFuelCache):
            return self._anomalyBerthingCost

        return None

    def _selectRefuellingType(
            self,
            world: traveller.World
            ) -> typing.Optional[RefuellingType]:
        if self._refuellingStrategy == RefuellingStrategy.RefinedFuelOnly:
            if world.hasStarPortRefuelling(
                    includeUnrefined=False,
                    rules=self._rules):
                return RefuellingType.Refined
        elif self._refuellingStrategy == RefuellingStrategy.UnrefinedFuelOnly:
            if world.hasStarPortRefuelling(
                    includeRefined=False,
                    rules=self._rules):
                return RefuellingType.Unrefined
        elif self._refuellingStrategy == RefuellingStrategy.GasGiantOnly:
            if world.hasGasGiantRefuelling():
                return RefuellingType.Wilderness
        elif self._refuellingStrategy == RefuellingStrategy.WaterOnly:
            if world.hasWaterRefuelling():
                return RefuellingType.Wilderness
        elif self._refuellingStrategy == RefuellingStrategy.WildernessOnly:
            if world.hasWildernessRefuelling():
                return RefuellingType.Wilderness
        elif self._refuellingStrategy == RefuellingStrategy.RefinedFuelPreferred:
            if world.hasStarPortRefuelling(
                    includeUnrefined=False, # Check for refined fuel
                    rules=self._rules):
                return RefuellingType.Refined
            if world.hasStarPortRefuelling(
                    includeRefined=False, # Check for unrefined fuel
                    rules=self._rules):
                return RefuellingType.Unrefined
        elif self._refuellingStrategy == RefuellingStrategy.UnrefinedFuelPreferred:
            if world.hasStarPortRefuelling(
                    includeRefined=False, # Check for unrefined fuel
                    rules=self._rules):
                return RefuellingType.Unrefined
            if world.hasStarPortRefuelling(
                    includeUnrefined=False, # Check for refined fuel
                    rules=self._rules):
                return RefuellingType.Refined
        elif self._refuellingStrategy == RefuellingStrategy.GasGiantPreferred:
            if world.hasGasGiantRefuelling():
                return RefuellingType.Wilderness
            fallbackRefuelling = self._fallbackRefuellingType(
                world=world)
            if fallbackRefuelling is not None:
                return fallbackRefuelling
        elif self._refuellingStrategy == RefuellingStrategy.WaterPreferred:
            if world.hasWaterRefuelling():
                return RefuellingType.Wilderness
            fallbackRefuelling = self._fallbackRefuellingType(
                world=world)
            if fallbackRefuelling is not None:
                return fallbackRefuelling
        elif self._refuellingStrategy == RefuellingStrategy.WildernessPreferred:
            if world.hasWildernessRefuelling():
                return RefuellingType.Wilderness
            fallbackRefuelling = self._fallbackRefuellingType(
                world=world)
            if fallbackRefuelling is not None:
                return fallbackRefuelling
        else:
            assert(False) # Check I've not missed an enum

        isFuelCache = world.isFuelCache()
        if self._useFuelCaches and isFuelCache:
            return RefuellingType.FuelCache

        isAnomaly = world.isAnomaly()
        if self._anomalyFuelCost and (isAnomaly and not isFuelCache):
            return RefuellingType.Anomaly

        return None

    # Check for a fallback star port refuelling type when the world doesn't support
    # the preferred wilderness refuelling type. Unrefined fuel is taken in
    # preference to refined fuel as it's assumed any ship that could have performed
    # wilderness refuelling will have the equipment needed to process the unrefined
    # fuel they purchase.
    def _fallbackRefuellingType(
            self,
            world: traveller.World
            ) -> typing.Optional[RefuellingType]:
        if world.hasStarPortRefuelling(
                includeRefined=False, # Only check for unrefined fuel
                rules=self._rules):
            return RefuellingType.Unrefined
        if world.hasStarPortRefuelling(
                includeUnrefined=False, # Only check for refined fuel
                rules=self._rules):
            return RefuellingType.Refined
        return None

class PitStop(object):
    def __init__(
            self,
            jumpIndex: int, # Intentionally not a calculation as it's not used to calculate values
            world: traveller.World,
            refuellingType: typing.Optional[RefuellingType],
            tonsOfFuel: typing.Optional[common.ScalarCalculation],
            fuelCost: typing.Optional[common.ScalarCalculation],
            berthingCost: typing.Optional[typing.Union[common.ScalarCalculation, common.RangeCalculation]]
            ) -> None:
        self._jumpIndex = jumpIndex
        self._world = world
        self._refuellingType = refuellingType
        self._tonsOfFuel = tonsOfFuel
        self._fuelCost = fuelCost
        self._berthingCost = berthingCost

        # Cache total so we don't have to repeatedly calculate it. This assumes that a pit stop
        # is immutable
        calculationName = f'Pit Stop Cost on {self._world.name(includeSubsector=True)}'
        if self._fuelCost and  self._berthingCost:
            self._totalCost = common.Calculator.add(
                lhs=self._fuelCost,
                rhs=self._berthingCost,
                name=calculationName)
        elif self._fuelCost:
            self._totalCost = common.Calculator.equals(
                value=self._fuelCost,
                name=calculationName)
        elif self._berthingCost:
            self._totalCost = common.Calculator.equals(
                value=self._berthingCost,
                name=calculationName)
        else:
            self._totalCost = common.ScalarCalculation(
                value=0,
                name=calculationName)

    def jumpIndex(self) -> int:
        return self._jumpIndex

    def world(self) -> traveller.World:
        return self._world

    def hasRefuelling(self) -> bool:
        return self._refuellingType != None

    def hasBerthing(self) -> bool:
        return self._berthingCost != None

    def refuellingType(self) -> typing.Optional[RefuellingType]:
        return self._refuellingType

    def tonsOfFuel(self) -> typing.Optional[common.ScalarCalculation]:
        return self._tonsOfFuel

    def fuelCost(self) -> typing.Optional[common.ScalarCalculation]:
        return self._fuelCost

    def berthingCost(self) -> typing.Optional[typing.Union[common.ScalarCalculation, common.RangeCalculation]]:
        return self._berthingCost

    def totalCost(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._totalCost

class RefuellingPlan(object):
    def __init__(
            self,
            pitStops: typing.List[PitStop]
            ) -> None:
        self._pitStops = pitStops
        self._jumpIndexMap = {}
        for pitStop in self._pitStops:
            self._jumpIndexMap[pitStop.jumpIndex()] = pitStop

        # Cache totals so we don't have to repeatedly calculate them. This assumes that the list of
        # pit stops and the pit stops themselves are immutable
        fuelAmounts = []
        fuelCosts = []
        berthingCosts = []
        for pitStop in self._pitStops:
            fuelAmount = pitStop.tonsOfFuel()
            if fuelAmount:
                fuelAmounts.append(fuelAmount)

            fuelCost = pitStop.fuelCost()
            if fuelCost:
                fuelCosts.append(fuelCost)

            berthingCost = pitStop.berthingCost()
            if berthingCost:
                berthingCosts.append(berthingCost)

        self._pitStopCount = common.ScalarCalculation(
            value=len(self._pitStops),
            name='Pit Stop Count')
        self._totalTonsOfFuel = common.Calculator.sum(
            values=fuelAmounts,
            name='Total Fuel Tons')
        self._totalFuelCost = common.Calculator.sum(
            values=fuelCosts,
            name='Total Fuel Cost')
        assert(isinstance(self._totalFuelCost, common.ScalarCalculation))
        self._totalBerthingCosts = common.Calculator.sum(
            values=berthingCosts,
            name='Total Berthing Cost')
        self._totalPitStopCosts = common.Calculator.add(
            lhs=self._totalFuelCost,
            rhs=self._totalBerthingCosts,
            name='Total Refuelling Plan Cost')

    def pitStop(self, jumpIndex: int) -> typing.Optional[PitStop]:
        if jumpIndex not in self._jumpIndexMap:
            return None
        return self._jumpIndexMap[jumpIndex]

    def pitStopCount(self) -> common.ScalarCalculation:
        return self._pitStopCount

    def totalTonsOfFuel(self) -> common.ScalarCalculation:
        return self._totalTonsOfFuel

    def totalFuelCost(self) -> common.ScalarCalculation:
        return self._totalFuelCost

    def totalBerthingCosts(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._totalBerthingCosts

    def totalPitStopCosts(self) -> typing.Union[common.ScalarCalculation, common.RangeCalculation]:
        return self._totalPitStopCosts

    def __getitem__(self, index: int):
        return self._pitStops.__getitem__(index)

    def __iter__(self):
        return self._pitStops.__iter__()

    def __next__(self):
        return self._pitStops.__next__()

class _WorldContext(object):
    def __init__(
            self,
            index: int,
            world: traveller.World,
            isFinishWorld: bool,
            mandatoryBerthing: bool,
            pitCostCalculator: PitStopCostCalculator,
            reachableWorlds: typing.Iterable[typing.Tuple[int, float]],
            fuelToFinish: float
            ) -> None:
        self._index = index
        self._world = world
        self._isFinishWorld = isFinishWorld
        self._mandatoryBerthing = mandatoryBerthing
        self._pitCostCalculator = pitCostCalculator
        self._reachableWorlds = reachableWorlds
        self._fuelToFinish = fuelToFinish

        self._refuellingType = self._pitCostCalculator.refuellingType(
            world=world)

        cost = self._pitCostCalculator.fuelCost(world=world)
        self._fuelCostPerTon = cost.value() if cost else 0

        # NOTE: The worst case value to make the next world decision making
        # pessimistic
        cost = self._pitCostCalculator.berthingCost(world=world)
        self._berthingCost = cost.worstCaseValue() if cost else 0

        self._bestFinalCost = None
        self._bestCostSoFar = None
        self._bestFuelSoFar = None

    def index(self) -> int:
        return self._index

    def world(self) -> traveller.World:
        return self._world

    def isFinishWorld(self) -> bool:
        return self._isFinishWorld

    def mandatoryBerthing(self) -> bool:
        return self._mandatoryBerthing

    def refuellingType(self) -> typing.Optional[RefuellingType]:
        return self._refuellingType

    def fuelCostPerTon(self) -> typing.Optional[int]:
        return self._fuelCostPerTon

    def reachableWorlds(self) -> typing.Iterable[typing.Tuple[int, float]]:
        return self._reachableWorlds

    def fuelToFinish(self) -> float:
        return self._fuelToFinish

    def finalCost(self) -> typing.Optional[float]:
        return self._bestFinalCost

    def isViableOption(
            self,
            costSoFar: float,
            fuelSoFar: float
            ) -> bool:
        return ((self._bestCostSoFar == None) or (costSoFar < self._bestCostSoFar)) or \
            ((self._bestFuelSoFar == None) or (fuelSoFar > self._bestFuelSoFar))

    def checkForBetterFinalCost(
            self,
            finalCost: float,
            costSoFar: float,
            fuelSoFar: float
            ) -> None:
        if (self._bestFinalCost == None) or (finalCost < self._bestFinalCost):
            self._bestFinalCost = finalCost
            self._bestCostSoFar = costSoFar
            self._bestFuelSoFar = fuelSoFar

    def estimateRefuellingCosts(
            self,
            tonsOfFuel: float
            ) -> typing.Optional[float]:
        if not self._refuellingType:
            return None

        if self._refuellingType == RefuellingType.Wilderness:
            # No cost (fuel or berthing) when wilderness refuelling
            return 0

        refuellingCost = self._fuelCostPerTon * tonsOfFuel

        # Only include berthing costs if berthing isn't mandatory
        if not self._mandatoryBerthing:
            refuellingCost += self._berthingCost

        return refuellingCost

class _CalculationContext:
    _WorldSequenceDataType = 'I'
    _FuelSequenceDataType = 'd'

    def __init__(
            self,
            fuelCapacity: int,
            worldContexts: typing.List[_WorldContext]
            ) -> None:
        self._fuelCapacity = fuelCapacity
        self._worldContexts = worldContexts

        worldCount = len(self._worldContexts)
        self._worldSequence = array.array(_CalculationContext._WorldSequenceDataType, [0] * worldCount)
        self._fuelSequence = array.array(_CalculationContext._FuelSequenceDataType, [0] * worldCount)
        self._sequenceLength = 0

        self._bestCost = None
        self._bestWorldSequence = None
        self._bestFuelSequence = None

    def fuelCapacity(self) -> int:
        return self._fuelCapacity

    def worldContext(
            self,
            worldIndex: int
            ) -> _WorldContext:
        return self._worldContexts[worldIndex]

    def worldContexts(self) -> typing.List[_WorldContext]:
        return self._worldContexts

    def pushRefuelling(
            self,
            worldIndex: int,
            fuelAmount: float
            ) -> None:
        self._worldSequence[self._sequenceLength] = worldIndex
        self._fuelSequence[self._sequenceLength] = fuelAmount
        self._sequenceLength += 1

    def popRefuelling(self) -> None:
        assert(self._sequenceLength > 0)
        self._sequenceLength -= 1

    def hasBestSequence(self) -> bool:
        return self._bestCost != None

    def bestCost(self) -> typing.Optional[float]:
        return self._bestCost

    def bestWorldSequence(self) -> typing.Optional[array.array]:
        return self._bestWorldSequence

    def bestFuelSequence(self) -> typing.Optional[array.array]:
        return self._bestFuelSequence

    def checkForBetterSequence(
            self,
            finalCost: float
            ) -> bool:
        isBetter = False
        if self._bestCost == None or finalCost < self._bestCost:
            isBetter = True
        elif finalCost == self._bestCost and self._sequenceLength < len(self._bestWorldSequence):
            isBetter = True

        if isBetter:
            self._bestCost = finalCost
            self._bestWorldSequence = array.array(
                _CalculationContext._WorldSequenceDataType,
                itertools.islice(self._worldSequence, 0, self._sequenceLength))
            self._bestFuelSequence = array.array(
                _CalculationContext._FuelSequenceDataType,
                itertools.islice(self._fuelSequence, 0, self._sequenceLength))
        return isBetter

def calculateRefuellingPlan(
        jumpRoute: logic.JumpRoute,
        shipTonnage: typing.Union[int, common.ScalarCalculation],
        shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
        shipStartingFuel: typing.Union[float, common.ScalarCalculation],
        pitCostCalculator: PitStopCostCalculator,
        shipFuelPerParsec: typing.Optional[typing.Union[float, common.ScalarCalculation]] = None,
        # Optional set containing the integer indices of jump route worlds where berthing is required.
        requiredBerthingIndices: typing.Optional[typing.Set[int]] = None,
        # Specify if generated refuelling plan should include refuelling costs. If not included the
        # costs will still be taken into account when calculating the optimal pit stop worlds,
        # however the costs for fuel and berthing will be zero
        includeRefuellingCosts: bool = True,
        diceRoller: typing.Optional[common.DiceRoller] = None
        ) -> typing.Optional[RefuellingPlan]:
    if jumpRoute.worldCount() < 2:
        raise ValueError('Invalid jump route')

    # Convert arguments to integers for speed, they're not used for generating final calculations
    if isinstance(shipTonnage, common.ScalarCalculation):
        shipTonnage = shipTonnage.value()
    assert(isinstance(shipTonnage, int))

    if isinstance(shipFuelCapacity, common.ScalarCalculation):
        shipFuelCapacity = shipFuelCapacity.value()
    assert(isinstance(shipFuelCapacity, int))

    if isinstance(shipStartingFuel, common.ScalarCalculation):
        shipStartingFuel = shipStartingFuel.value()
    assert(isinstance(shipStartingFuel, (int, float)))

    if shipFuelCapacity > shipTonnage:
        raise ValueError('Ship\'s fuel capacity can\'t be larger than its total tonnage')
    if shipStartingFuel > shipFuelCapacity:
        raise ValueError('Ship\'s starting fuel can\'t be larger than its fuel capacity')

    if not shipFuelPerParsec:
        shipFuelPerParsec = traveller.calculateFuelRequiredForJump(
            jumpDistance=1,
            shipTonnage=shipTonnage)
    if isinstance(shipFuelPerParsec, common.ScalarCalculation):
        shipFuelPerParsec = shipFuelPerParsec.value()

    if shipFuelPerParsec <= 0:
        raise ValueError('Fuel per parsec must be greater than 0')

    if shipFuelCapacity < shipFuelPerParsec:
        raise ValueError(
            f'With a fuel capacity of {shipFuelCapacity} tons your ship can\'t carry ' + \
            f'the {shipFuelPerParsec} tons required to jump')

    parsecsWithoutRefuelling = math.floor(shipFuelCapacity / shipFuelPerParsec)
    assert(parsecsWithoutRefuelling > 0)

    calculationContext = _processRoute(
        jumpRoute=jumpRoute,
        shipFuelCapacity=shipFuelCapacity,
        shipStartingFuel=shipStartingFuel,
        shipFuelPerParsec=shipFuelPerParsec,
        parsecsWithoutRefuelling=parsecsWithoutRefuelling,
        pitCostCalculator=pitCostCalculator,
        requiredBerthingIndices=requiredBerthingIndices)
    if not calculationContext.hasBestSequence():
        return None

    return _createRefuellingPlan(
        calculationContext=calculationContext,
        pitCostCalculator=pitCostCalculator,
        includeRefuellingCosts=includeRefuellingCosts,
        diceRoller=diceRoller)

def _processRoute(
        jumpRoute: logic.JumpRoute,
        shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
        shipStartingFuel: typing.Union[float, common.ScalarCalculation],
        shipFuelPerParsec: float,
        parsecsWithoutRefuelling: int,
        pitCostCalculator: PitStopCostCalculator,
        requiredBerthingIndices: typing.Optional[typing.Set[int]],
        ) -> _CalculationContext:
    jumpWorldCount = jumpRoute.worldCount()
    finishWorldIndex = jumpWorldCount - 1
    fuelToFinish = jumpRoute.totalParsecs() * shipFuelPerParsec

    worldContexts: typing.List[_WorldContext] = []
    for worldIndex in range(len(jumpRoute)):
        # TODO: This needs updated as indexing into a jump route will return
        # a node. I also don't think it's used right now so should be moved
        # to after the while loop where it is used
        world = jumpRoute[worldIndex]

        # Find the worlds that match the refuelling requirements (i.e. have a
        # refuelling type) and are reachable from the current world without
        # refuelling. Worlds that don't match the refuelling requirements are
        # ignored as they don't affect where refuelling can take place (only
        # how much fuel needs taken on)
        # TODO: This will need updated to handle the fact the jump route can
        # contain dead space.
        # - Rename fromWorld/toWorld to fromNode/toNode
        # - Rename reachableWorldIndex to reachableNodeIndex
        # - Rename reachableWorlds to reachableNodes. It will generally only
        # contain the indices of nodes that contain worlds but it could be
        # the index of a dead space node if the finish node is a dead space
        # node
        # - Only add reachableWorldIndex to reachableWorlds if the node
        # contains a world that matches the refuelling strategy or it's the
        # finish node
        reachableWorlds = []
        totalParsecs = 0
        parsecsToNextWorld = None
        reachableWorldIndex = worldIndex + 1
        while reachableWorldIndex <= finishWorldIndex:
            fromWorld = jumpRoute[reachableWorldIndex - 1]
            toWorld = jumpRoute[reachableWorldIndex]
            parsecs = fromWorld.parsecsTo(toWorld)
            totalParsecs += parsecs
            if parsecsToNextWorld == None:
                parsecsToNextWorld = parsecs
            if totalParsecs > parsecsWithoutRefuelling:
                break

            toWorldRefuellingType = pitCostCalculator.refuellingType(world=toWorld)
            if toWorldRefuellingType or (reachableWorldIndex == finishWorldIndex):
                reachableWorlds.append((reachableWorldIndex, totalParsecs * shipFuelPerParsec))

            reachableWorldIndex += 1

        # TODO: _WorldContext needs updated to deal with nodes and there
        # needs to be one for EVERY node in the jump route later code
        # uses jump route indices to index into worldContexts
        mandatoryBerthing = (requiredBerthingIndices != None) and \
            (worldIndex in requiredBerthingIndices)
        worldContexts.append(_WorldContext(
            index=worldIndex,
            world=world,
            isFinishWorld=worldIndex == finishWorldIndex,
            mandatoryBerthing=mandatoryBerthing,
            pitCostCalculator=pitCostCalculator,
            reachableWorlds=reachableWorlds,
            fuelToFinish=fuelToFinish))

        if parsecsToNextWorld:
            fuelToFinish -= parsecsToNextWorld * shipFuelPerParsec

    calculationContext = _CalculationContext(
        fuelCapacity=shipFuelCapacity,
        worldContexts=worldContexts)

    # Start processing at the the first world in the route
    _processWorld(
        calculationContext=calculationContext,
        fromWorldContext=worldContexts[0],
        currentCost=0,
        currentFuel=shipStartingFuel)

    return calculationContext

# TODO: I think this will need a lot or renaming as it's mostly going
# to be dealing with nodes instead of worlds. Apart from that I think
# it might "just work" as long as _WorldContext has been updated to
# deal with nodes and estimateRefuellingCosts returns None if the node
# is dead space
def _processWorld(
        calculationContext: _CalculationContext,
        fromWorldContext: _WorldContext,
        currentCost: float,
        currentFuel: float
        ) -> float:
    if fromWorldContext.isFinishWorld():
        # We've hit the finish world
        calculationContext.checkForBetterSequence(finalCost=currentCost)
        return currentCost

    fromWorldIndex = fromWorldContext.index()
    fuelToFinish = fromWorldContext.fuelToFinish()
    fromWorldCost = fromWorldContext.estimateRefuellingCosts(tonsOfFuel=fuelToFinish)

    # Iterate over the worlds reachable from the current world in reverse order. This causes the
    # algorithm to try sequences with fewer pit stops first. This is important to minimize the
    # number of pit stops in cases where all the worlds have the same refuelling costs (e.g. when
    # using wilderness refuelling).
    # This has the added advantage that it can significantly speed up the search. I _think_ this is
    # because finding cheaper sequences earlier in the search process allows you to rule out more
    # sequences early. Testing shorter sequences first is more likely to achieve this as shorter
    # sequences are more likely to be cheaper as they require less berthing and are more likely to
    # skip over expensive worlds.
    bestFinalCost = None
    fromThreshold = fromWorldContext.estimateRefuellingCosts(tonsOfFuel=1)
    toThreshold = None
    for (toWorldIndex, fuelBetweenWorlds) in reversed(fromWorldContext.reachableWorlds()):
        toWorldContext = calculationContext.worldContext(worldIndex=toWorldIndex)

        if not toWorldContext.isFinishWorld():
            # If the cost of fuel (including any berthing costs) on the to world
            # is not less than the best cost seen for previously processed
            # worlds (i.e. worlds further along the jump route) _or_ less than
            # the from world fuel cost, then there is no point considering the
            # to world as a refuelling world as it can't possibly result in a
            # lower final cost.
            # This is an important optimisation for long routes for ships that
            # can make large numbers of jumps without refuelling and therefore
            # each node has a large reachable world count (e.g. ships with
            # custom fuel per parsec values or more advanced jump drives).
            costCheck = toWorldContext.estimateRefuellingCosts(tonsOfFuel=1)
            if (toThreshold == None) or (costCheck < toThreshold):
                toThreshold = costCheck
            elif (fromThreshold != None) and (costCheck >= fromThreshold):
                continue
            # If we get to here then to world cost is better than either the
            # from world or previous to world costs

        if fromWorldCost != None:
            if not toWorldContext.isFinishWorld():
                toWorldCost = toWorldContext.estimateRefuellingCosts(
                    tonsOfFuel=toWorldContext.fuelToFinish())

                if (toWorldCost == None) or (fromWorldCost <= toWorldCost):
                    # The next world is the same cost, more expensive or doesn't allow refuelling
                    # with the current refuelling strategy. Take on as much fuel as possible
                    # (limited by the amount required to reach the end of the jump route)
                    fuelToTakeOn = min(calculationContext.fuelCapacity() - currentFuel, fuelToFinish)
                else:
                    # The next world is cheaper so take on just enough fuel to reach it
                    fuelToTakeOn = max(fuelBetweenWorlds - currentFuel, 0)
            else:
                # The next world is the finish world so only take on enough fuel to reach it
                fuelToTakeOn = max(fuelBetweenWorlds - currentFuel, 0)
        else:
            # The current world doesn't allow refuelling with the current strategy so we need to
            # rely on the amount of fuel we have in the tank
            fuelToTakeOn = 0

        refuellingCosts = 0
        if fuelToTakeOn > 0:
            refuellingCosts = fromWorldContext.estimateRefuellingCosts(tonsOfFuel=fuelToTakeOn)
            assert(refuellingCosts != None) # The checks above should prevent this

        nextFuel = (currentFuel + fuelToTakeOn) - fuelBetweenWorlds
        if nextFuel < 0:
            # We can't take on enough fuel to reach the next world. As we're processing the worlds
            # from furthest away to closest continue to see if we can reach a closer world
            continue

        nextCost = currentCost + refuellingCosts

        if toWorldContext.isViableOption(costSoFar=nextCost, fuelSoFar=nextFuel):
            if fuelToTakeOn > 0:
                calculationContext.pushRefuelling(
                    worldIndex=fromWorldIndex,
                    fuelAmount=fuelToTakeOn)

            finalCost = _processWorld(
                calculationContext=calculationContext,
                fromWorldContext=toWorldContext,
                currentCost=nextCost,
                currentFuel=nextFuel)

            if fuelToTakeOn > 0:
                calculationContext.popRefuelling()

            if finalCost != None:
                toWorldContext.checkForBetterFinalCost(
                    finalCost=finalCost,
                    costSoFar=nextCost,
                    fuelSoFar=nextFuel)

        finalCost = toWorldContext.finalCost()
        if (finalCost != None) and ((bestFinalCost == None) or (finalCost < bestFinalCost)):
            bestFinalCost = finalCost

    return bestFinalCost

def _createRefuellingPlan(
        calculationContext: _CalculationContext,
        pitCostCalculator: PitStopCostCalculator,
        includeRefuellingCosts: bool,
        diceRoller: typing.Optional[common.DiceRoller]
        ) -> RefuellingPlan:
    if not calculationContext.hasBestSequence():
        return None

    worldSequence = calculationContext.bestWorldSequence()
    fuelSequence = calculationContext.bestFuelSequence()

    fuelMap = {}
    if worldSequence:
        for sequenceIndex in range(len(worldSequence)):
            fuelMap[worldSequence[sequenceIndex]] = fuelSequence[sequenceIndex]

    pitStops = []
    for worldContext in calculationContext.worldContexts():
        # TODO: This will need updated to handle the fact it will
        # be a node rather than a world. If the node doesn't
        # contain a world then I think all the code here can be
        # skipped
        world = worldContext.world()

        fuelAmount = fuelMap.get(worldContext.index())
        refuellingType = None
        fuelCost = None
        if fuelAmount:
            fuelAmount = common.ScalarCalculation(
                value=fuelAmount,
                name='Pit Stop Fuel Tonnage')

            refuellingType = worldContext.refuellingType()
            assert(refuellingType)

            fuelCostPerTon = worldContext.fuelCostPerTon()
            if fuelCostPerTon is not None:
                worldString = world.name(includeSubsector=True)
                fuelCostPerTon = common.ScalarCalculation(
                    value=fuelCostPerTon,
                    name=f'{refuellingType.value} Fuel Cost Per Ton On {worldString}')
                fuelCost = common.Calculator.multiply(
                    lhs=fuelCostPerTon,
                    rhs=fuelAmount,
                    name=f'Total Fuel Cost On {worldString}')

        mandatoryBerthing = worldContext.mandatoryBerthing()
        berthingCost = None
        if refuellingType or mandatoryBerthing:
            berthingCost = pitCostCalculator.berthingCost(
                world=world,
                mandatory=mandatoryBerthing,
                diceRoller=diceRoller)
            if berthingCost:
                berthingCost = common.Calculator.rename(
                    value=berthingCost,
                    name=f'Berthing Cost For {world.name(includeSubsector=True)}')

        # Only create a pit stop if we're refuelling or berthing
        if refuellingType or berthingCost:
            if not includeRefuellingCosts:
                if fuelCost:
                    fuelCost = common.Calculator.override(
                        old=fuelCost,
                        new=common.ScalarCalculation(value=0, name='Overridden Fuel Cost'),
                        name='Ignored Fuel Cost')

                if berthingCost:
                    berthingCost = common.Calculator.override(
                        old=berthingCost,
                        new=common.ScalarCalculation(value=0, name='Overridden Berthing Cost'),
                        name='Ignored Berthing Cost')

            pitStops.append(PitStop(
                jumpIndex=worldContext.index(),
                world=world,
                refuellingType=refuellingType,
                tonsOfFuel=fuelAmount,
                fuelCost=fuelCost,
                berthingCost=berthingCost))

    return RefuellingPlan(pitStops)
