import enum
import logic
import traveller
import typing

class RouteOptimisation(enum.Enum):
    ShortestDistance = 'Shortest Distance'
    ShortestTime = 'Shortest Time'
    LowestCost = 'Lowest Cost'


# This was the cost function Traveller Map used to use. According to the changeset history (FindPath
# in PathFinder.cs) it was replaced as it gives asymmetrical results (i.e# the route from A->B is
# not the same as the route from B->A). The one advantage I found it has over other algorithms is it
# can take a lot less time to calculate the route. This is down to the fact it priorities search
# routes that head directly towards the finish world which is the what is required in most cases.
"""
class FastSearchCostCalculator(object):
    def calculate(
        self,
        currentWorld: traveller.World,
        nextWorld: traveller.World,
        startWorld: traveller.World,
        finishWorld: traveller.World
        ) -> None:
        return traveller.hexDistance(
            nextWorld.absoluteX(),
            nextWorld.absoluteY(),
            finishWorld.absoluteX(),
            finishWorld.absoluteY())
"""

# This cost function finds the route that covers the shortest distance but not necessarily the
# fewest number of jumps. The shortest distance route is important as uses the least fuel.
class ShortestDistanceCostCalculator(object):
    def calculate(
            self,
            currentWorld: traveller.World,
            nextWorld: traveller.World
            ) -> typing.Union[int, float]:
        return traveller.hexDistance(
            currentWorld.absoluteX(),
            currentWorld.absoluteY(),
            nextWorld.absoluteX(),
            nextWorld.absoluteY())

# This cost function finds the route with fewest jumps but not necessarily the shortest distance. The
# fewest jumps route is important as it takes the shortest time.
class ShortestTimeCostCalculator(object):
    def calculate(
            self,
            currentWorld: traveller.World,
            nextWorld: traveller.World
            ) -> typing.Union[int, float]:
        # Note this assumes next world is within jump range of the current world.
        return 1

# This cost function finds the route with the lowest cost. It works on the
# assumption that you're going to have to buy fuel on the world you jump to so
# the cost value is the price of buying one jumps worth of fuel on that world.
# Note that, if using a refuelling strategy that includes any type of wilderness
# refuelling, you may get unnecessarily long routes if the per jump cost is 0.
# This happens because the
class CheapestRouteCostCalculator(object):
    def __init__(
            self,
            shipTonnage: int,
            refuellingStrategy: logic.RefuellingStrategy,
            perJumpOverheads: int
            ) -> None:
        self._shipTonnage = shipTonnage
        self._refuellingStrategy = refuellingStrategy
        self._perJumpOverheads = perJumpOverheads

    def calculate(
            self,
            currentWorld: traveller.World,
            nextWorld: traveller.World
            ) -> typing.Union[int, float]:
        # For the route finder algorithm to work the cost for a jump can't be 0. To avoid this the
        # jump has a default cost of 1, this is the case even when the calculated cost for the
        # jump wouldn't have been 0. This is done so that it doesn't adversely effect what is seen
        # as the optimal route as all potential jumps are skewed by the same amount. A desirable
        # side effect of this is, in the case where there are multiple routes that have the same
        # lowest cost, then the route finder will choose the one with the lowest number of jumps.
        jumpCost = 1

        # Always add per jump overhead (but it may be 0)
        jumpCost += self._perJumpOverheads

        # Add refuelling costs if applicable
        refuellingType = logic.selectRefuellingType(currentWorld, self._refuellingStrategy)
        if refuellingType == logic.RefuellingType.Refined or \
                refuellingType == logic.RefuellingType.Unrefined:
            jumpDistance = traveller.hexDistance(
                absoluteX1=currentWorld.absoluteX(),
                absoluteY1=currentWorld.absoluteY(),
                absoluteX2=nextWorld.absoluteX(),
                absoluteY2=nextWorld.absoluteY())
            fuelRequired = traveller.calculateFuelRequiredForJump(
                jumpDistance=jumpDistance,
                shipTonnage=self._shipTonnage)

            # Add cost of buying fuel to jump to the next world
            fuelCostPerTon = traveller.starPortFuelCostPerTon(
                world=currentWorld,
                refinedFuel=refuellingType == logic.RefuellingType.Refined)
            assert(fuelCostPerTon != None) # World filter should prevent this
            jumpCost += fuelCostPerTon.value() * fuelRequired.value()

            # Add cost of berthing to buy the fuel
            berthingCost = traveller.starPortBerthingCost(currentWorld)
            jumpCost += berthingCost.worstCaseValue()
        elif refuellingType == logic.RefuellingType.Wilderness:
            # No refuelling costs for wilderness refuelling
            pass
        else:
            # This world doesn't match the refuelling strategy so we won't be refuelling
            # on it
            assert(not refuellingType) # Check I've not missed an enum
            pass

        return jumpCost
