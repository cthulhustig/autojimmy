import array
import common
import enum
import itertools
import logic
import traveller
import typing

class RefuellingType(enum.Enum):
    Refined = 'Refined'
    Unrefined = 'Unrefined'
    Wilderness = 'Wilderness'

class RefuellingStrategy(enum.Enum):
    RefinedFuelOnly = 'Refined Fuel Only'
    UnrefinedFuelOnly = 'Unrefined Fuel Only'
    GasGiantOnly = 'Gas Giant Only'
    WaterOnly = 'Water Only'
    WildernessOnly = 'Wilderness Only'
    GasGiantPreferred = 'Gas Giant Preferred'
    WaterPreferred = 'Water Preferred'
    WildernessPreferred = 'Wilderness Preferred'

def selectRefuellingType(
        world: traveller.World,
        refuellingStrategy: RefuellingStrategy
        ) -> RefuellingType:
    if refuellingStrategy == RefuellingStrategy.RefinedFuelOnly:
        return RefuellingType.Refined if world.hasStarPortRefuelling(refinedFuelOnly=True) else None

    if refuellingStrategy == RefuellingStrategy.UnrefinedFuelOnly:
        return RefuellingType.Unrefined if world.hasStarPortRefuelling() else None

    if refuellingStrategy == RefuellingStrategy.GasGiantOnly:
        return RefuellingType.Wilderness if world.hasGasGiantRefuelling() else None

    if refuellingStrategy == RefuellingStrategy.WaterOnly:
        return RefuellingType.Wilderness if world.hasWaterRefuelling() else None

    if refuellingStrategy == RefuellingStrategy.WildernessOnly:
        return RefuellingType.Wilderness if world.hasWildernessRefuelling() else None

    if refuellingStrategy == RefuellingStrategy.GasGiantPreferred:
        if world.hasGasGiantRefuelling():
            return RefuellingType.Wilderness
        return RefuellingType.Unrefined if world.hasStarPortRefuelling() else None

    if refuellingStrategy == RefuellingStrategy.WaterPreferred:
        if world.hasWaterRefuelling():
            return RefuellingType.Wilderness
        return RefuellingType.Unrefined if world.hasStarPortRefuelling() else None

    if refuellingStrategy == RefuellingStrategy.WildernessPreferred:
        if world.hasWildernessRefuelling():
            return RefuellingType.Wilderness
        return RefuellingType.Unrefined if world.hasStarPortRefuelling() else None

    assert(False) # Check I've not missed an enum
    return None

class PitStop(object):
    def __init__(
            self,
            jumpIndex: int, # Intentionally not a calculation as it's not used to calculate values
            world: traveller.World,
            refuellingType: typing.Optional[RefuellingType],
            tonsOfFuel: typing.Optional[common.ScalarCalculation],
            fuelCost: typing.Optional[common.ScalarCalculation],
            berthingCost: typing.Optional[typing.Union[common.ScalarCalculation, common.RangeCalculation]],
            refuellingStrategyOverridden: bool
            ) -> None:
        self._jumpIndex = jumpIndex
        self._world = world
        self._refuellingType = refuellingType
        self._tonsOfFuel = tonsOfFuel
        self._fuelCost = fuelCost
        self._berthingCost = berthingCost
        self._refuellingStrategyOverridden = refuellingStrategyOverridden

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

    def isRefuellingStrategyOverridden(self):
        return self._refuellingStrategyOverridden

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
        self._refuellingStrategyOverridden = False
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

            if pitStop.isRefuellingStrategyOverridden():
                self._refuellingStrategyOverridden = True

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

    def isRefuellingStrategyOverridden(self):
        return self._refuellingStrategyOverridden

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
            berthingRequired: bool,
            refuellingType: RefuellingType,
            strategyOverridden: bool,
            reachableWorlds: typing.Iterable[typing.Tuple[int, int]],
            fuelToFinish: int
            ) -> None:
        self._index = index
        self._world = world
        self._berthingRequired = berthingRequired
        self._refuellingType = refuellingType
        self._strategyOverridden = strategyOverridden
        self._reachableWorlds = reachableWorlds
        self._fuelToFinish = fuelToFinish

        self._fuelCostPerTon = traveller.starPortFuelCostPerTon(
            world=world,
            refinedFuel=self._refuellingType == logic.RefuellingType.Refined)
        if self._fuelCostPerTon != None:
            self._fuelCostPerTon = self._fuelCostPerTon.value()

        self._berthingCost = traveller.starPortBerthingCost(world)
        # Use the worst case value to make the next world decision making pessimistic
        self._berthingCost = self._berthingCost.worstCaseValue()

        self._bestFinalCost = None
        self._bestCostSoFar = None
        self._bestFuelSoFar = None

    def index(self) -> int:
        return self._index

    def world(self) -> traveller.World:
        return self._world

    def isBerthingRequired(self) -> bool:
        return self._berthingRequired

    def refuellingType(self) -> RefuellingType:
        return self._refuellingType

    def isStrategyOverridden(self) -> bool:
        return self._strategyOverridden

    def isFinishWorld(self) -> bool:
        return not self._reachableWorlds

    def reachableWorlds(self) -> typing.Iterable[typing.Tuple[int, int]]:
        return self._reachableWorlds

    def fuelToFinish(self) -> int:
        return self._fuelToFinish

    def bestFinalCost(self) -> typing.Optional[int]:
        return self._bestFinalCost

    def isViableOption(
            self,
            costSoFar: int,
            fuelSoFar: int
            ) -> bool:
        return ((self._bestCostSoFar == None) or (costSoFar < self._bestCostSoFar)) or \
            ((self._bestFuelSoFar == None) or (fuelSoFar > self._bestFuelSoFar))

    def checkForBetterFinalCost(
            self,
            finalCost: int,
            costSoFar: int,
            fuelSoFar: int
            ) -> None:
        if (self._bestFinalCost == None) or (finalCost < self._bestFinalCost):
            self._bestFinalCost = finalCost
            self._bestCostSoFar = costSoFar
            self._bestFuelSoFar = fuelSoFar

    def calculateRefuellingCosts(
            self,
            tonsOfFuel: int
            ) -> typing.Optional[int]:
        if not self._refuellingType:
            return None

        if self._refuellingType == RefuellingType.Wilderness:
            # No cost (fuel or berthing) when wilderness refuelling
            return 0

        refuellingCost = self._fuelCostPerTon * tonsOfFuel

        # Only include berthing costs if berthing isn't mandatory
        if not self._berthingRequired:
            refuellingCost += self._berthingCost

        return refuellingCost

class _CalculationContext:
    def __init__(
            self,
            fuelCapacity: int,
            worldContexts: typing.List[_WorldContext]
            ) -> None:
        self._fuelCapacity = fuelCapacity
        self._worldContexts = worldContexts

        worldCount = len(self._worldContexts)
        self._worldSequence = array.array('I', [0] * worldCount)
        self._fuelSequence = array.array('I', [0] * worldCount)
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
            fuelAmount: int
            ) -> None:
        self._worldSequence[self._sequenceLength] = worldIndex
        self._fuelSequence[self._sequenceLength] = fuelAmount
        self._sequenceLength += 1

    def popRefuelling(self) -> None:
        assert(self._sequenceLength > 0)
        self._sequenceLength -= 1

    def hasBestSequence(self) -> bool:
        return self._bestCost != None

    def bestCost(self) -> typing.Optional[int]:
        return self._bestCost

    def bestWorldSequence(self) -> typing.Optional[array.array]:
        return self._bestWorldSequence

    def bestFuelSequence(self) -> typing.Optional[array.array]:
        return self._bestFuelSequence

    def checkForBetterSequence(
            self,
            finalCost: int
            ) -> bool:
        isBetter = False
        if self._bestCost == None or finalCost < self._bestCost:
            isBetter = True
        elif finalCost == self._bestCost and self._sequenceLength < len(self._bestWorldSequence):
            isBetter = True

        if isBetter:
            self._bestCost = finalCost
            self._bestWorldSequence = array.array('I', itertools.islice(self._worldSequence, 0, self._sequenceLength))
            self._bestFuelSequence = array.array('I', itertools.islice(self._fuelSequence, 0, self._sequenceLength))
        return isBetter

def calculateRefuellingPlan(
        jumpRoute: logic.JumpRoute,
        shipTonnage: typing.Union[int, common.ScalarCalculation],
        shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
        shipStartingFuel: typing.Union[int, common.ScalarCalculation],
        refuellingStrategy: RefuellingStrategy,
        refuellingStrategyOptional: bool = False,
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
    assert(isinstance(shipStartingFuel, int))

    if shipFuelCapacity > shipTonnage:
        raise ValueError('Ship\'s fuel capacity can\'t be larger than its total tonnage')
    if shipStartingFuel > shipFuelCapacity:
        raise ValueError('Ship\'s starting fuel can\'t be larger than its fuel capacity')

    fuelPerParsec = traveller.calculateFuelRequiredForJump(
        jumpDistance=1,
        shipTonnage=shipTonnage)
    fuelPerParsec = fuelPerParsec.value()

    if shipFuelCapacity < fuelPerParsec:
        raise ValueError(
            f'With a fuel capacity of {shipFuelCapacity} tons your ship can\'t carry ' + \
            f'the {fuelPerParsec} tons required to jump')

    parsecsWithoutRefuelling = int(shipFuelCapacity // fuelPerParsec)
    assert(parsecsWithoutRefuelling > 0)

    calculationContext = _processRoute(
        jumpRoute=jumpRoute,
        shipFuelCapacity=shipFuelCapacity,
        shipStartingFuel=shipStartingFuel,
        fuelPerParsec=fuelPerParsec,
        parsecsWithoutRefuelling=parsecsWithoutRefuelling,
        desiredRefuellingStrategy=refuellingStrategy,
        overrideRefuellingStrategies=None,
        requiredBerthingIndices=requiredBerthingIndices)
    if not calculationContext.hasBestSequence():
        # This world doesn't meet the refuelling strategy
        if not refuellingStrategyOptional:
            # The refuelling strategy is mandatory so bail
            return None

        # Try overriding the refuelling strategy to see if we find a refuelling plan
        overrideStrategies = []

        if refuellingStrategy == logic.RefuellingStrategy.RefinedFuelOnly:
            overrideStrategies.append(logic.RefuellingStrategy.UnrefinedFuelOnly)
            calculationContext = _processRoute(
                jumpRoute=jumpRoute,
                shipFuelCapacity=shipFuelCapacity,
                shipStartingFuel=shipStartingFuel,
                fuelPerParsec=fuelPerParsec,
                parsecsWithoutRefuelling=parsecsWithoutRefuelling,
                desiredRefuellingStrategy=refuellingStrategy,
                overrideRefuellingStrategies=overrideStrategies,
                requiredBerthingIndices=requiredBerthingIndices)

        if not calculationContext.hasBestSequence():
            overrideStrategies.append(logic.RefuellingStrategy.WildernessPreferred)
            calculationContext = _processRoute(
                jumpRoute=jumpRoute,
                shipFuelCapacity=shipFuelCapacity,
                shipStartingFuel=shipStartingFuel,
                fuelPerParsec=fuelPerParsec,
                parsecsWithoutRefuelling=parsecsWithoutRefuelling,
                desiredRefuellingStrategy=refuellingStrategy,
                overrideRefuellingStrategies=overrideStrategies,
                requiredBerthingIndices=requiredBerthingIndices)

    return _createRefuellingPlan(
        calculationContext=calculationContext,
        includeRefuellingCosts=includeRefuellingCosts,
        diceRoller=diceRoller)

def _processRoute(
        jumpRoute: logic.JumpRoute,
        shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
        shipStartingFuel: typing.Union[int, common.ScalarCalculation],
        fuelPerParsec: int,
        parsecsWithoutRefuelling: int,
        desiredRefuellingStrategy: RefuellingStrategy,
        overrideRefuellingStrategies: typing.Optional[typing.List[RefuellingStrategy]],
        requiredBerthingIndices: typing.Optional[typing.Set[int]],
        ) -> _CalculationContext:
    jumpWorldCount = jumpRoute.worldCount()
    finishWorldIndex = jumpWorldCount - 1
    fuelToFinish = jumpRoute.totalParsecs() * fuelPerParsec

    worldContexts: typing.List[_WorldContext] = []
    for worldIndex in range(len(jumpRoute)):
        world = jumpRoute[worldIndex]

        # Determine the refuelling type to be used for this world
        refuellingStrategyOverridden = False
        refuellingType = selectRefuellingType(
            world=world,
            refuellingStrategy=desiredRefuellingStrategy)
        if not refuellingType and overrideRefuellingStrategies:
            # The world doesn't allow for the desired refuelling strategy but override
            # strategies have been supplied. The list of strategies is expected to be
            # in priority order so just iterate over it until we find a match
            for overrideStrategy in overrideRefuellingStrategies:
                refuellingType = selectRefuellingType(
                    world=world,
                    refuellingStrategy=overrideStrategy)
                if refuellingType:
                    refuellingStrategyOverridden = True
                    break

        # Find the worlds that are reachable from the current world without refuelling
        reachableWorlds = []
        totalParsecs = 0
        parsecsToNextWorld = None
        reachableWorldIndex = worldIndex + 1
        while reachableWorldIndex <= finishWorldIndex:
            fromWorld = jumpRoute[reachableWorldIndex - 1]
            toWorld = jumpRoute[reachableWorldIndex]
            parsecs = traveller.hexDistance(
                absoluteX1=fromWorld.absoluteX(),
                absoluteY1=fromWorld.absoluteY(),
                absoluteX2=toWorld.absoluteX(),
                absoluteY2=toWorld.absoluteY())
            totalParsecs += parsecs
            if parsecsToNextWorld == None:
                parsecsToNextWorld = parsecs
            if totalParsecs > parsecsWithoutRefuelling:
                break

            reachableWorlds.append((reachableWorldIndex, totalParsecs * fuelPerParsec))

            reachableWorldIndex += 1

        worldContexts.append(_WorldContext(
            index=worldIndex,
            world=world,
            berthingRequired=(requiredBerthingIndices != None) and (worldIndex in requiredBerthingIndices),
            refuellingType=refuellingType,
            strategyOverridden=refuellingStrategyOverridden,
            reachableWorlds=reachableWorlds,
            fuelToFinish=fuelToFinish))

        if parsecsToNextWorld:
            fuelToFinish -= parsecsToNextWorld * fuelPerParsec
    assert(fuelToFinish == 0)

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

def _processWorld(
        calculationContext: _CalculationContext,
        fromWorldContext: _WorldContext,
        currentCost: typing.Union[int, float],
        currentFuel: int
        ) -> int:
    if fromWorldContext.isFinishWorld():
        # We've hit the finish world
        calculationContext.checkForBetterSequence(finalCost=currentCost)
        return currentCost

    fromWorldIndex = fromWorldContext.index()
    fuelToFinish = fromWorldContext.fuelToFinish()
    fromWorldCost = fromWorldContext.calculateRefuellingCosts(tonsOfFuel=fuelToFinish)

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
    for (toWorldIndex, fuelBetweenWorlds) in reversed(fromWorldContext.reachableWorlds()):
        toWorldContext = calculationContext.worldContext(worldIndex=toWorldIndex)

        if fromWorldCost != None:
            if not toWorldContext.isFinishWorld():
                toWorldCost = toWorldContext.calculateRefuellingCosts(
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
            refuellingCosts = fromWorldContext.calculateRefuellingCosts(tonsOfFuel=fuelToTakeOn)
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

        finalCost = toWorldContext.bestFinalCost()
        if (finalCost != None) and ((bestFinalCost == None) or (finalCost < bestFinalCost)):
            bestFinalCost = finalCost

    return bestFinalCost

def _createRefuellingPlan(
        calculationContext: _CalculationContext,
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
        world = worldContext.world()

        fuelAmount = fuelMap.get(worldContext.index())
        refuellingType = None
        fuelCost = None
        if fuelAmount != None:
            assert(fuelAmount > 0)

            fuelAmount = common.ScalarCalculation(
                value=fuelAmount,
                name='Pit Stop Fuel Tonnage')

            refuellingType = worldContext.refuellingType()
            assert(refuellingType != None)
            if refuellingType == RefuellingType.Refined or \
                    refuellingType == RefuellingType.Unrefined:
                fuelCostPerTon = traveller.starPortFuelCostPerTon(
                    world=world,
                    refinedFuel=refuellingType == RefuellingType.Refined)
                fuelCost = common.Calculator.multiply(
                    lhs=fuelCostPerTon,
                    rhs=fuelAmount,
                    name=f'Fuel Cost On {world.name(includeSubsector=True)}')

        berthingCost = None
        if fuelCost or worldContext.isBerthingRequired():
            berthingCost = traveller.starPortBerthingCost(
                world=world,
                diceRoller=diceRoller)
            berthingCost = common.Calculator.rename(
                value=berthingCost,
                name=f'Berthing Cost For {world.name(includeSubsector=True)}')

        # Only create a pit stop if we're refuelling or berthing
        if refuellingType or berthingCost:
            reportedFuelCost = fuelCost
            reportedBerthingCost = berthingCost
            if not includeRefuellingCosts:
                if reportedFuelCost:
                    reportedFuelCost = common.Calculator.override(
                        old=reportedFuelCost,
                        new=common.ScalarCalculation(value=0, name='Overridden Fuel Cost'),
                        name='Ignored Fuel Cost')

                if reportedBerthingCost:
                    reportedBerthingCost = common.Calculator.override(
                        old=reportedBerthingCost,
                        new=common.ScalarCalculation(value=0, name='Overridden Berthing Cost'),
                        name='Ignored Berthing Cost')

            pitStops.append(PitStop(
                jumpIndex=worldContext.index(),
                world=world,
                refuellingType=refuellingType,
                tonsOfFuel=fuelAmount,
                fuelCost=reportedFuelCost,
                berthingCost=reportedBerthingCost,
                refuellingStrategyOverridden=worldContext.isStrategyOverridden()))

    return RefuellingPlan(pitStops)
