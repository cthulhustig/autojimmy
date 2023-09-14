import enum
import logic
import traveller
import typing

class RouteOptimisation(enum.Enum):
    ShortestDistance = 'Shortest Distance'
    ShortestTime = 'Shortest Time'
    LowestCost = 'Lowest Cost'

# This cost function finds the route that covers the shortest distance but not necessarily the
# fewest number of jumps. The shortest distance route is important as uses the least fuel.
class ShortestDistanceCostCalculator(logic.JumpCostCalculatorInterface):
    def initialise(
            self,
            startWorld: traveller.World
            ) -> typing.Any:
        return None

    def calculate(
            self,
            currentWorld: traveller.World,
            nextWorld: traveller.World,
            costContext: typing.Any
            ) -> typing.Tuple[typing.Optional[float], typing.Any]:
        jumpCost = traveller.hexDistance(
            currentWorld.absoluteX(),
            currentWorld.absoluteY(),
            nextWorld.absoluteX(),
            nextWorld.absoluteY())
        return (jumpCost, None)

# This cost function finds the route with fewest jumps but not necessarily the shortest distance. The
# fewest jumps route is important as it takes the shortest time.
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
            costContext: typing.Any
            ) -> typing.Tuple[typing.Optional[float], typing.Any]:
        # Note this assumes next world is within jump range of the current world.
        return (1, None)

# This cost function finds the route with the lowest cost. It works on the
# assumption that you're going to have to buy fuel on the world you jump to so
# the cost value is the price of buying one jumps worth of fuel on that world.
# Note that, if using a refuelling strategy that includes any type of wilderness
# refuelling, you may get unnecessarily long routes if the per jump cost is 0.
# This happens because the
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
            shipCurrentFuel: int,
            refuellingStrategy: logic.RefuellingStrategy,
            perJumpOverheads: int,
            shipFuelPerParsec: typing.Optional[typing.Union[int, float]] = None
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
            lastFuelWorld=startWorld,
            lastFuelParsecs=0, # TODO: This seems wrong if current world doesn't support refuelling type
            lastFuelType=refuellingType,
            lastFuelCost=fuelCostPerTon)

        # Reset ship current fuel so it won't be re-used when the same object
        # is used to calculate more routes (i.e. when using waypoints)
        self._shipCurrentFuel = 0

        return costContext

    def calculate(
            self,
            currentWorld: traveller.World,
            nextWorld: traveller.World,
            costContext: typing.Optional[_CostContext]
            ) -> typing.Tuple[typing.Optional[float], typing.Any]:
        assert(isinstance(costContext, CheapestRouteCostCalculator._CostContext))

        # For the route finder algorithm to work the cost for a jump can't be 0. To avoid this the
        # jump has a default cost of 1, this is the case even when the calculated cost for the
        # jump wouldn't have been 0. This is done so that it doesn't adversely effect what is seen
        # as the optimal route as all potential jumps are skewed by the same amount. A desirable
        # side effect of this is, in the case where there are multiple routes that have the same
        # lowest cost, then the route finder will choose the one with the lowest number of jumps.
        jumpCost = 1

        # Always add per jump overhead (but it may be 0)
        jumpCost += self._perJumpOverheads

        currentFuel = costContext.currentFuel()

        jumpDistance = traveller.hexDistance(
            absoluteX1=currentWorld.absoluteX(),
            absoluteY1=currentWorld.absoluteY(),
            absoluteX2=nextWorld.absoluteX(),
            absoluteY2=nextWorld.absoluteY())
        jumpFuel = jumpDistance * self._shipFuelPerParsec
        fuelDeficit = 0 if (jumpFuel < currentFuel) else (jumpFuel - currentFuel)

        refuellingType = logic.selectRefuellingType(
            world=currentWorld,
            refuellingStrategy=self._refuellingStrategy)
        fuelWorld = currentWorld
        fuelCostPerTon = 0

        if refuellingType == None:
            refuellingType = costContext.lastFuelType()
            fuelWorld = costContext.lastFuelWorld()
            fuelCostPerTon = costContext.lastFuelCost()
        elif logic.isStarPortRefuellingType(refuellingType):
            fuelCostPerTon = traveller.starPortFuelCostPerTon(
                world=currentWorld,
                refinedFuel=refuellingType == logic.RefuellingType.Refined)
            assert(fuelCostPerTon != None)
            fuelCostPerTon = fuelCostPerTon.value()

        if fuelDeficit > 0:
            if fuelCostPerTon == None:
                assert(False) # TODO: Can this happen?
                return (None, None)

            jumpCost += fuelCostPerTon * fuelDeficit
            currentFuel += fuelDeficit

            # TODO: I think this berthing costs are being applied multiple times if jumping through
            # a sequence of worlds that don't support the refuelling strategy. I think the downside
            # of this is these jumps will be costed overlay high
            if logic.isStarPortRefuellingType(refuellingType):
                berthingCost = traveller.starPortBerthingCost(fuelWorld)
                jumpCost += berthingCost.worstCaseValue()

        if refuellingType:
            lastFuelParsecs = jumpDistance
            lastFuelType = refuellingType
            lastFuelCost = fuelCostPerTon
        else:
            lastFuelParsecs = costContext.lastFuelParsecs() + jumpDistance
            if lastFuelParsecs <= self._parsecsWithoutRefuelling:
                lastFuelType = costContext.lastFuelType()
                lastFuelCost = costContext.lastFuelCost()
            else:
                assert(False) # TODO: Can this happen?
                fuelWorld = None
                lastFuelParsecs = None
                lastFuelType = None
                lastFuelCost = None

        newCostContext = CheapestRouteCostCalculator._CostContext(
            currentFuel=currentFuel - jumpFuel,
            lastFuelWorld=fuelWorld,
            lastFuelParsecs=lastFuelParsecs,
            lastFuelType=lastFuelType,
            lastFuelCost=lastFuelCost)

        # If the next world doesn't meet the refuelling strategy then add the cost of the fuel
        # to the last fuel system to the jump cost. This is a bit of a hack so, if the same,
        # world is reachable by multiple routes, how close it is to fuel and therefore how far
        # we will be able to continue without refuelling is taken into account. This is needed
        # so that, if the routes to reach the world have the same base cost, routes with the
        # potential for more onward travel will have a lower cost.
        refuellingType = logic.selectRefuellingType(
            world=nextWorld,
            refuellingStrategy=self._refuellingStrategy)
        if not refuellingType:
            if not lastFuelParsecs:
                assert(False) # TODO: Can this happen?
                return (None, None)

            jumpCost += lastFuelParsecs * fuelCostPerTon

        return (jumpCost, newCostContext)
