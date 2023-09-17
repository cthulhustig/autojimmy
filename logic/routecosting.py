import enum
import logic
import traveller
import typing

class RouteOptimisation(enum.Enum):
    ShortestTime = 'Shortest Time'
    ShortestDistance = 'Shortest Distance'
    LowestCost = 'Lowest Cost'

# This cost function finds the route with fewest jumps but not necessarily the shortest distance.
# The fewest jumps route is important as it takes the shortest time.
class ShortestTimeCostCalculator(logic.JumpCostCalculatorInterface):
    def initialise(
            self,
            startWorld: traveller.World
            ) -> typing.Any:
        return None

    def calculate(
            self,
            currentWorld: traveller.World,
            nextWorld: traveller.World,
            jumpParsecs: int,
            costContext: typing.Any
            ) -> typing.Tuple[typing.Optional[float], typing.Any]:
        return (1, None)

# This cost function finds the route that covers the shortest distance but not necessarily the
# fewest number of jumps. The shortest distance route is important as uses the least fuel (although
# not necessarily the cheapest fuel).
class ShortestDistanceCostCalculator(logic.JumpCostCalculatorInterface):
    # A per jump constant is added to the jump distance to calculated the cost. This is done to
    # cause the algorithm to prefer routes with the lowest number of jumps when there are multiple
    # with the same distance. This constant needs to be small enough that it doesn't skew the
    # length of one route compared to another, as that could introduce spurious jumps, but large
    # enough that it doesn't get lost due to the inaccuracies of floating point math. The current
    # value should allow for routes up to 10000 parsecs without running the risk of introducing a
    # spurious jump
    _PerJumpConstant = 0.0001

    def initialise(
            self,
            startWorld: traveller.World
            ) -> typing.Any:
        return None

    def calculate(
            self,
            currentWorld: traveller.World,
            nextWorld: traveller.World,
            jumpParsecs: int,
            costContext: typing.Any
            ) -> typing.Tuple[typing.Optional[float], typing.Any]:
        return (jumpParsecs + ShortestDistanceCostCalculator._PerJumpConstant, None)

# This cost function finds the route with the lowest cost. It tracks the amount of fuel in the ship
# and the last world that fuel could have been taken on.
class CheapestRouteCostCalculator(logic.JumpCostCalculatorInterface):
    class _CostContext(object):
        def __init__(
                self,
                currentFuel: float,
                lastFuelWorld: traveller.World,
                lastFuelParsecs: int,
                lastFuelType: logic.RefuellingType,
                lastFuelCost: int
                ) -> None:
            self._currentFuel = currentFuel
            self._lastFuelWorld = lastFuelWorld
            self._lastFuelParsecs = lastFuelParsecs
            self._lastFuelType = lastFuelType
            self._lastFuelCost = lastFuelCost

        def currentFuel(self) -> float:
            return self._currentFuel

        def lastFuelWorld(self) -> traveller.World:
            return self._lastFuelWorld

        def lastFuelParsecs(self) -> int:
            return self._lastFuelParsecs

        def lastFuelType(self) -> logic.RefuellingType:
            return self._lastFuelType

        def lastFuelCost(self) -> int:
            return self._lastFuelCost

    def __init__(
            self,
            shipTonnage: int,
            shipFuelCapacity: int,
            shipCurrentFuel: float,
            perJumpOverheads: int,
            refuellingStrategy: typing.Optional[logic.RefuellingStrategy] = None,
            shipFuelPerParsec: typing.Optional[float] = None
            ) -> None:
        self._shipTonnage = shipTonnage
        self._shipFuelCapacity = shipFuelCapacity
        self._shipCurrentFuel = shipCurrentFuel
        self._shipFuelPerParsec = shipFuelPerParsec
        self._refuellingStrategy = refuellingStrategy
        self._perJumpOverheads = perJumpOverheads

        if not self._shipFuelPerParsec:
            self._shipFuelPerParsec = traveller.calculateFuelRequiredForJump(
                jumpDistance=1,
                shipTonnage=self._shipTonnage)
            self._shipFuelPerParsec = self._shipFuelPerParsec.value()

        self._parsecsWithoutRefuelling = int(self._shipFuelCapacity // self._shipFuelPerParsec)

    def initialise(
            self,
            startWorld: traveller.World
            ) -> typing.Any:
        if not self._refuellingStrategy:
            # Fuel based route calculation is disabled so the context isn't used
            return None

        refuellingType = logic.selectRefuellingType(
            world=startWorld,
            refuellingStrategy=self._refuellingStrategy)
        fuelCostPerTon = 0

        if logic.isStarPortRefuellingType(refuellingType):
            fuelCostPerTon = traveller.starPortFuelCostPerTon(
                world=startWorld,
                refinedFuel=refuellingType == logic.RefuellingType.Refined)
            assert(fuelCostPerTon != None)
            fuelCostPerTon = fuelCostPerTon.value()

        costContext = CheapestRouteCostCalculator._CostContext(
            currentFuel=self._shipCurrentFuel,
            lastFuelWorld=startWorld if refuellingType else None,
            lastFuelParsecs=0 if refuellingType else (self._parsecsWithoutRefuelling + 1),
            lastFuelType=refuellingType,
            lastFuelCost=fuelCostPerTon)

        return costContext

    def calculate(
            self,
            currentWorld: traveller.World,
            nextWorld: traveller.World,
            jumpParsecs: int,
            costContext: typing.Optional[_CostContext]
            ) -> typing.Tuple[typing.Optional[float], typing.Any]:
        # For the route finder algorithm to work the cost for a jump can't be 0. To avoid this the
        # jump has a default cost of 1, this is the case even when the calculated cost for the
        # jump wouldn't have been 0. This is done so that it doesn't adversely effect what is seen
        # as the optimal route as all potential jumps are skewed by the same amount. A desirable
        # side effect of this is, in the case where there are multiple routes that have the same
        # lowest cost, then the route finder will choose the one with the lowest number of jumps.
        jumpCost = 1

        # Always add per jump overhead (but it may be 0)
        jumpCost += self._perJumpOverheads

        if not self._refuellingStrategy:
            # Fuel based route calculation is disabled
            return (jumpCost, None)

        assert(isinstance(costContext, CheapestRouteCostCalculator._CostContext))

        currentFuel = costContext.currentFuel()
        jumpFuel = jumpParsecs * self._shipFuelPerParsec
        fuelDeficit = 0 if (jumpFuel <= currentFuel) else (jumpFuel - currentFuel)

        refuellingType = logic.selectRefuellingType(
            world=currentWorld,
            refuellingStrategy=self._refuellingStrategy)
        fuelWorld = currentWorld
        fuelCostPerTon = 0
        lastFuelParsecs = 0

        if refuellingType == None:
            refuellingType = costContext.lastFuelType()
            fuelWorld = costContext.lastFuelWorld()
            fuelCostPerTon = costContext.lastFuelCost()
            lastFuelParsecs = costContext.lastFuelParsecs()
        elif logic.isStarPortRefuellingType(refuellingType):
            fuelCostPerTon = traveller.starPortFuelCostPerTon(
                world=currentWorld,
                refinedFuel=refuellingType == logic.RefuellingType.Refined)
            assert(fuelCostPerTon != None)
            fuelCostPerTon = fuelCostPerTon.value()

        if fuelDeficit > 0:
            if lastFuelParsecs > self._parsecsWithoutRefuelling:
                # It's not possible to take on enough fuel to reach the world
                return (None, None)

            jumpCost += fuelCostPerTon * fuelDeficit
            currentFuel += fuelDeficit

            # TODO: The way this currently works means, if a fuel world is used to take on fuel for
            # multiple jumps, the berthing cost will be added to the route cost each time additional
            # fuel is taken on. This could happen for ships with high parsecs without refuelling
            # jumping through multiple worlds that don't support the refuelling strategy.
            # This seems obviously wrong, however, testing has shown that updating it so berthing
            # costs are only applied once results in noticeably higher cost routes being found over
            # long routes. In some cases it does generate lower cost routes but the majority of
            # times they're higher cost. I'm leaving it as is for now until I can work out what is
            # going on (I need an example of it happen that doesn't involve hundreds of worlds)
            if logic.isStarPortRefuellingType(refuellingType):
                berthingCost = traveller.starPortBerthingCost(fuelWorld)
                jumpCost += berthingCost.worstCaseValue()

        newCostContext = CheapestRouteCostCalculator._CostContext(
            currentFuel=currentFuel - jumpFuel,
            lastFuelWorld=fuelWorld,
            lastFuelParsecs=lastFuelParsecs + jumpParsecs,
            lastFuelType=refuellingType,
            lastFuelCost=fuelCostPerTon)

        return (jumpCost, newCostContext)
