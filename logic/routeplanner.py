import common
import heapq
import logic
import math
import traveller
import travellermap
import typing

# TODO: This will need updated to allow jump routes to pass through
# dead space.
class _RouteNode(object):
    def __init__(
            self,
            targetIndex: int,
            world: traveller.World,
            gScore: float,
            fScore: float,
            isFuelWorld: bool,
            fuelParsecs: int,
            costContext: typing.Any,
            parent: typing.Optional['_RouteNode'] = None,
            ) -> None:
        self._targetIndex = targetIndex
        self._world = world
        self._gScore = gScore
        self._fScore = fScore
        self._isFuelWorld = isFuelWorld
        self._fuelParsecs = fuelParsecs
        self._costContext = costContext
        self._parent = parent

    def targetIndex(self) -> int:
        return self._targetIndex

    def world(self) -> traveller.World:
        return self._world

    def gScore(self) -> float:
        return self._gScore

    def fScore(self) -> float:
        return self._fScore

    def isFuelWorld(self) -> bool:
        return self._isFuelWorld

    # This is max number of parsecs worth of fuel the ship can have in its tank when
    # reaching this world
    def fuelParsecs(self) -> int:
        return self._fuelParsecs

    def costContext(self) -> typing.Any:
        return self._costContext

    def parent(self) -> '_RouteNode':
        return self._parent

    def __lt__(self, other: '_RouteNode') -> bool:
        # NOTE: This function is used for ordering of nodes by the potential
        # it's really a "better than" function rather than a "less than" one.
        # Ordering here is VERY important for fuel based routing to work. The
        # fScore (known cost so far + estimated cost remaining) is the primary
        # key. If they are equal then the max fuel that the ship could have in
        # it's tank when reaching this world is used. In the case that fScore
        # and remaining fuel are equal, the nodes have the same priority
        if self._fScore < other._fScore:
            return True
        elif self._fScore > other._fScore:
            return False

        return self._fuelParsecs > other._fuelParsecs

class JumpCostCalculatorInterface(object):
    def initialise(
            self,
            startWorld: traveller.World
            ) -> typing.Any:
        raise RuntimeError(f'{type(self)} is derived from JumpCostCalculatorInterface so must implement initialise')

    # Calculate the cost of the jump from the current world to the next world
    def calculate(
            self,
            currentWorld: traveller.World,
            nextWorld: traveller.World,
            jumpParsecs: int,
            costContext: typing.Any
            ) -> typing.Tuple[
                typing.Optional[float], # Cost from current to next world, None
                                        # means it's not possible to reach it
                typing.Any]: # New cost context
        raise RuntimeError(f'{type(self)} is derived from JumpCostCalculatorInterface so must implement calculate')

    # Estimate the cost of travelling remaining distance to the target. For
    # the algorithm to work it's important that the estimated cost never
    # exceeds the actual cost
    def estimate(
            self,
            parsecsToFinish: int
            ) -> float:
        raise RuntimeError(f'{type(self)} is derived from JumpCostCalculatorInterface so must implement estimate')

class RoutePlanner(object):
    def calculateDirectRoute(
            self,
            startWorld: traveller.World,
            finishWorld: traveller.World,
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipCurrentFuel: typing.Union[float, common.ScalarCalculation],
            jumpCostCalculator: JumpCostCalculatorInterface,
            pitCostCalculator: typing.Optional[logic.PitStopCostCalculator] = None, # None disables fuel based route calculation
            shipFuelPerParsec: typing.Optional[typing.Union[float, common.ScalarCalculation]] = None,
            worldFilterCallback: typing.Optional[typing.Callable[[traveller.World], bool]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.Optional[logic.JumpRoute]:
        worldList = self._calculateRoute(
            worldSequence=[startWorld, finishWorld],
            shipTonnage=shipTonnage,
            shipJumpRating=shipJumpRating,
            shipFuelCapacity=shipFuelCapacity,
            shipCurrentFuel=shipCurrentFuel,
            shipFuelPerParsec=shipFuelPerParsec,
            jumpCostCalculator=jumpCostCalculator,
            pitCostCalculator=pitCostCalculator,
            worldFilterCallback=worldFilterCallback,
            progressCallback=progressCallback,
            isCancelledCallback=isCancelledCallback)
        if not worldList:
            return None # No route found

        return logic.JumpRoute(worldList)

    def calculateSequenceRoute(
            self,
            worldSequence: typing.List[traveller.World],
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipCurrentFuel: typing.Union[float, common.ScalarCalculation],
            jumpCostCalculator: JumpCostCalculatorInterface,
            pitCostCalculator: typing.Optional[logic.PitStopCostCalculator] = None, # None disables fuel based route calculation
            shipFuelPerParsec: typing.Optional[typing.Union[float, common.ScalarCalculation]] = None,
            worldFilterCallback: typing.Optional[typing.Callable[[traveller.World], bool]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.Optional[logic.JumpRoute]:
        if not worldSequence:
            None
        if len(worldSequence) < 2:
            # The world sequence is a single world so it's the "jump route"
            return worldSequence

        worldList = self._calculateRoute(
            worldSequence=worldSequence,
            shipTonnage=shipTonnage,
            shipJumpRating=shipJumpRating,
            shipFuelCapacity=shipFuelCapacity,
            shipCurrentFuel=shipCurrentFuel,
            shipFuelPerParsec=shipFuelPerParsec,
            jumpCostCalculator=jumpCostCalculator,
            pitCostCalculator=pitCostCalculator,
            worldFilterCallback=worldFilterCallback,
            progressCallback=progressCallback,
            isCancelledCallback=isCancelledCallback)
        if not worldList:
            return None # No route found

        return logic.JumpRoute(worldList)

    # Reimplementation of code from Traveller Map source code (FindPath in PathFinder.cs). This in
    # turn was based on code from AI for Game Developers, Bourg & Seemann, O'Reilly Media, Inc.,
    # July 2004.
    # I've since expanded the algorithm to allow it to be fuel aware. When enabled it means the
    # algorithm will only generate routes where it would be possible to take on the amount of fuel
    # required to complete the route. Which worlds can be used to take on fuel is determined by the
    # specified refuelling strategy. Not that this on it's own doesn't make any claims about how
    # cost effective the route will be (compared to other possible routes), that will be determined
    # by the supplied jump cost calculator.
    # TODO: Algorithm wise I think jumping through dead space should be _relatively_ simple. If
    # dead space routing is enabled, whenever yieldWorldsInArea is currently being called I need
    # to also process the hexes that form a ring round the current position with a radius of the
    # ship jump rating (limited by available fuel and distance to target world). The thinking
    # being there is no reason to jump less than that.
    # - IMPORTANT: This ring logic is slightly flawed. The one reason there could be a benefit
    #   for looking at dead space that is closer than this outer ring is if I allow the user
    #   to specify dead space hexes to avoid and one of those hexes is on the ring. In that case
    #   we may need to check closer dead space hexes as they may give a better route
    # - IMPORTANT: This thinking may be even more flawed. If I'm saying the costing function will
    #   be passed nodes rather than worlds and can return whatever cost it wants then it could
    #   return different costs for different dead space hexes
    def _calculateRoute(
            self,
            # TODO: This will need updated to take a list of nodes. It should probably also be
            # be an abstract type rather than a List
            worldSequence: typing.List[traveller.World],
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipCurrentFuel: typing.Union[float, common.ScalarCalculation],
            # TODO: The cost calculator will need updated to deal with nodes rather than worlds
            # It might make sense for them to take either and handle the difference internally
            jumpCostCalculator: JumpCostCalculatorInterface,
            pitCostCalculator: typing.Optional[logic.PitStopCostCalculator] = None, # None disables fuel based route calculation
            shipFuelPerParsec: typing.Optional[typing.Union[float, common.ScalarCalculation]] = None,
            # TODO: The world filter will need updated to deal with nodes rather than worlds.
            # It might make sense for them to take either and handle the difference internally
            worldFilterCallback: typing.Optional[typing.Callable[[traveller.World], bool]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.Optional[typing.List[traveller.World]]:
        # If the jump rating is a calculation covert it to it's raw value as we don't need to
        # track calculations here
        if isinstance(shipJumpRating, common.ScalarCalculation):
            shipJumpRating = shipJumpRating.value()

        if isinstance(shipFuelCapacity, common.ScalarCalculation):
            shipFuelCapacity = shipFuelCapacity.value()

        if isinstance(shipCurrentFuel, common.ScalarCalculation):
            shipCurrentFuel = shipCurrentFuel.value()

        if not shipFuelPerParsec:
            shipFuelPerParsec = traveller.calculateFuelRequiredForJump(
                jumpDistance=1,
                shipTonnage=shipTonnage)
        if isinstance(shipFuelPerParsec, common.ScalarCalculation):
            shipFuelPerParsec = shipFuelPerParsec.value()

        shipParsecsWithoutRefuelling = math.floor(shipFuelCapacity / shipFuelPerParsec)
        if shipParsecsWithoutRefuelling < 1:
            raise ValueError('Ship\'s fuel capacity doesn\'t allow for jump-1')

        sequenceLength = len(worldSequence)
        assert(sequenceLength >= 2)
        finishWorldIndex = sequenceLength - 1
        startWorld = worldSequence[0]
        finishWorld = worldSequence[finishWorldIndex]

        if pitCostCalculator:
            # TODO: This will need updated to only check for fuel type if
            # the start node contains a world. The rest of the code is still
            # valid
            startWorldFuelType = pitCostCalculator.refuellingType(world=startWorld)
            isCurrentFuelWorld = startWorldFuelType != None
            maxStartingFuel = shipFuelCapacity if isCurrentFuelWorld else shipCurrentFuel
        else:
            # Fuel based route calculation is disabled so use the max capacity as the max starting
            # fuel. The intended effect is to have it possible to jump to any world within jump
            # range (fuel capacity allowing).
            startWorldFuelType = None
            isCurrentFuelWorld = False
            maxStartingFuel = shipFuelCapacity

        # Handle early outs when dealing with direct world to world routes
        if sequenceLength == 2:
            # Handle corner case where the start and finish are the same world
            if startWorld == finishWorld:
                return [startWorld]

            # A _LOT_ of the time we're asked to calculate a route the finish
            # world is actually within one jump of the start world (as finished
            # worlds tend to come from nearby world searches). Do a quick check
            # for this case, if it's true we known the shortest lowest cost and
            # distance/shortest time is a single direct jump.
            # This optimisation is only done if the world can be reached with
            # the starting fuel _or_ the start world and refuelling strategy
            # allow for wilderness refuelling. If non-wilderness fuel needs to
            # be taken on then a full route check must be performed to
            # guarantee the optimal route is found. Technically it's only lowest
            # cost that really needs the full check as it's possible that it may
            # be better to jump to a world where fuel is cheaper to first,
            # whereas adding an extra jump will never result in a shorter
            # distance or time.
            distance = startWorld.parsecsTo(finishWorld)
            if distance <= shipJumpRating:
                if not pitCostCalculator:
                    # Fuel based routing is disabled so use ships fuel capacity
                    # as the 'available fuel'
                    availableFuel = shipFuelCapacity
                elif startWorldFuelType == logic.RefuellingType.Wilderness:
                    # Wilderness refuelling is possible on the start world. The
                    # best route is always going to be to fill the tank and jump
                    # straight there.
                    availableFuel = shipFuelCapacity
                else:
                    # It's either not possible to take on fuel on the start
                    # world or fuel costs money. Either way, we can only bail
                    # early if the ship can jump straight to the finish world
                    # with the fuel that's in its tank.
                    availableFuel = shipCurrentFuel

                fuelToFinish = distance * shipFuelPerParsec
                if fuelToFinish <= availableFuel:
                    # TODO: This will need updated to return a list of 2 nodes
                    return [startWorld, finishWorld]

        # TODO: This typing stuff will need updated to deal with nodes
        openQueue: typing.List[_RouteNode] = []
        targetStates: typing.List[
            typing.Tuple[
                typing.Set[traveller.World], # Closed worlds
                typing.Dict[traveller.World, typing.Tuple[
                    float, # Best gScore for a route reaching this world
                    int, # Best remaining fuel for a route reaching this world
                    int]], # Parsecs from world to target (note target not necessarily finish)
                int # Min parsecs from target to finish (going via all waypoints)
                ]] = []
        # TODO: This will need updated to be a set of nodes
        excludedWorlds: typing.Set[traveller.World] = set()

        minRouteParsecs = 0
        for index in range(sequenceLength - 1):
            currentWorld = worldSequence[index]
            targetWorld = worldSequence[index + 1]
            minRouteParsecs += currentWorld.parsecsTo(targetWorld)

        startToCurrentParsecs = 0
        for index in range(sequenceLength):
            targetStates.append((set(), dict(), minRouteParsecs - startToCurrentParsecs))

            if index != finishWorldIndex:
                currentWorld = worldSequence[index]
                targetWorld = worldSequence[index + 1]
                startToCurrentParsecs += currentWorld.parsecsTo(targetWorld)

        # Add the starting node to the open list
        fuelParsecs = math.floor(maxStartingFuel / shipFuelPerParsec)
        startNode = _RouteNode(
            targetIndex=1,
            world=startWorld,
            gScore=0,
            fScore=0,
            isFuelWorld=isCurrentFuelWorld,
            fuelParsecs=fuelParsecs,
            costContext=jumpCostCalculator.initialise(startWorld=startWorld),
            parent=None)
        heapq.heappush(openQueue, startNode)

        targetWorld = worldSequence[1]
        currentToTargetParsecs = startWorld.parsecsTo(targetWorld)
        targetStates[1][1][startWorld] = (0, fuelParsecs, currentToTargetParsecs)

        # Take a local reference to the WorldManager singleton to avoid repeated calls to instance()
        worldManager = traveller.WorldManager.instance()

        # Process nodes while the open list is not empty
        closedRoutes = 0
        while openQueue:
            if isCancelledCallback and isCancelledCallback():
                return None

            # current node = node from open list with the lowest cost
            currentNode: _RouteNode = heapq.heappop(openQueue)
            currentWorld = currentNode.world()
            targetIndex = currentNode.targetIndex()
            targetWorld = worldSequence[targetIndex]

            targetClosedSet, targetWorldData, targetToFinishMinParsecs = targetStates[targetIndex]
            targetClosedSet.add(currentWorld)

            # if current node = goal node then path complete
            if currentWorld == targetWorld:
                # We've reached the target world for this segment of the jump route
                if targetIndex == finishWorldIndex:
                    # We've found the lowest cost route that goes through all the worlds in the sequence.
                    # Process it to generate the final list of route worlds then bail
                    return self._finaliseRoute(
                        finishNode=currentNode,
                        progressCount=closedRoutes + 1, # +1 for this route
                        progressCallback=progressCallback)

                # We've reached the current target for the node but there are still more worlds
                # in the sequence. Increment the target index, skipping runs of the same target
                # world, then continue to processing this node.
                while True:
                    targetIndex += 1
                    newTargetWorld = worldSequence[targetIndex]
                    if newTargetWorld != targetWorld:
                        targetWorld = newTargetWorld
                        break

                    # There is a run of waypoints for the target world. If we've reached the end
                    # of the world sequence then we're done and the current route is the lowest
                    # cost route. If we've not reached the end of the world sequence then just
                    # loop in order to skip this world
                    if targetIndex >= finishWorldIndex:
                        return self._finaliseRoute(
                            finishNode=currentNode,
                            progressCount=closedRoutes + 1, # +1 for this route
                            progressCallback=progressCallback)

                # Update the best scores for entry for the current world
                # NOTE: It's important to get the state for the new target
                targetClosedSet, targetWorldData, targetToFinishMinParsecs = targetStates[targetIndex]
                currentWorldBestScore, currentWorldBestFuelParsecs, currentToTargetParsecs = \
                    targetWorldData.get(currentWorld, (None, None, None))

                currentWorldBestScore = currentNode.gScore() \
                    if currentWorldBestScore == None else \
                    min(currentNode.gScore(), currentWorldBestScore)

                currentWorldBestFuelParsecs = currentNode.fuelParsecs() \
                    if currentWorldBestFuelParsecs == None else \
                    max(currentNode.fuelParsecs(), currentWorldBestFuelParsecs)

                if currentToTargetParsecs == None:
                    currentToTargetParsecs = currentWorld.parsecsTo(targetWorld)

                targetWorldData[currentWorld] = \
                    (currentWorldBestScore, currentWorldBestFuelParsecs, currentToTargetParsecs)

            if progressCallback:
                progressCallback(closedRoutes, False) # Search isn't finished

            if pitCostCalculator:
                # Set search area based on the max distance we could jump from the current world. If
                # it's a world where fuel could be taken then the search area is the ship jump
                # rating. If it's not a world where fuel can be taken on then the search radius is
                # determined by the amount of fuel in the ship (limited by jump rating)
                if currentNode.isFuelWorld():
                    searchRadius = shipJumpRating
                else:
                    searchRadius = min(shipJumpRating, currentNode.fuelParsecs())

                # Clamp the search radius to the max parsecs without refuelling. This is required for
                # ships that don't have the fuel capacity to perform their max jump. Not sure when
                # this would actually happen but it should be handled
                searchRadius = min(searchRadius, shipParsecsWithoutRefuelling)
                if searchRadius <= 0:
                    closedRoutes += 1
                    continue
            else:
                # Fuel based route calculation is disabled so always search for the full ship jump
                # rating
                searchRadius = shipJumpRating

            adjacentIterator = worldManager.yieldWorldsInArea(
                centerPos=currentWorld.hexPosition(),
                searchRadius=searchRadius)
            possibleRoutes = 0
            addedRoutes = 0
            for adjacentWorld in adjacentIterator:
                possibleRoutes += 1

                adjacentParsecs = currentWorld.parsecsTo(adjacentWorld)

                # Work out the max amount of fuel the ship can have in the tank after completing
                # the jump from the current world to the adjacent world.
                if pitCostCalculator:
                    isAdjacentFuelWorld = pitCostCalculator.refuellingType(
                        world=adjacentWorld) != None
                    if currentNode.isFuelWorld():
                        fuelParsecs = shipParsecsWithoutRefuelling - adjacentParsecs
                    else:
                        fuelParsecs = currentNode.fuelParsecs() - adjacentParsecs

                    if fuelParsecs < 0:
                        # If the fuel parsecs is negative it means, when following this route, there
                        # is no way to take on enough fuel to reach the adjacent world
                        continue

                    if (not isAdjacentFuelWorld) and (fuelParsecs < 1) and (adjacentWorld != finishWorld):
                        # The adjacent world isn't a fuel world and the ship won't have enough
                        # fuel to jump on so there is no point continuing the route
                        continue
                else:
                    isAdjacentFuelWorld = False
                    # Fuel based route calculation is disabled. These values have no effect but
                    # must be set to something
                    fuelParsecs = shipJumpRating

                adjacentWorldBestScore, adjacentWorldBestFuelParsecs, adjacentToTargetMinParsecs = \
                    targetWorldData.get(adjacentWorld, (None, None, None))

                # Skip worlds that have already been reached with a BETTER cost unless they this
                # route means the ship will have have more fuel for the onward journey. If the
                # adjacent world is a previously processed world but we've found a route with
                # better fuelling potential, the adjacent world will be added to queue with
                # standard g/f scores. This will mean it will be prioritised lower than the
                # previous route that had a better cost but worse fuelling potential. This route
                # will only get further processing if that better cost route fails due to running
                # out of fuel.
                # In the case that fuel based routing is disabled, the new fuel parsecs and best
                # fuel parsecs will always be the ship jump rating (i.e. the same) so the closed
                # worlds set will always be checked.
                if (adjacentWorldBestFuelParsecs != None) and (fuelParsecs <= adjacentWorldBestFuelParsecs) and \
                        (adjacentWorld in targetClosedSet):
                    continue

                # If the adjacent world isn't the current target world, check if it's been excluded
                if worldFilterCallback and (adjacentWorld != targetWorld):
                    if adjacentWorld in excludedWorlds:
                        continue # World has already been excluded

                    # Apply custom world filter. This may be expensive so should be applied after lower
                    # cost filters.
                    if not worldFilterCallback(adjacentWorld):
                        excludedWorlds.add(adjacentWorld)
                        continue

                # Calculate the cost of jumping to the adjacent world
                jumpCost, costContext = jumpCostCalculator.calculate(
                    currentWorld,
                    adjacentWorld,
                    adjacentParsecs,
                    currentNode.costContext())
                if jumpCost == None:
                    continue

                tentativeScore = currentNode.gScore() + jumpCost
                isBetter = (adjacentWorldBestScore == None) or \
                    (tentativeScore < adjacentWorldBestScore) or \
                    (fuelParsecs > adjacentWorldBestFuelParsecs)

                if isBetter:
                    adjacentWorldBestScore = tentativeScore \
                        if adjacentWorldBestScore == None else \
                        min(tentativeScore, adjacentWorldBestScore)

                    adjacentWorldBestFuelParsecs = fuelParsecs \
                        if adjacentWorldBestFuelParsecs == None else \
                        max(fuelParsecs, adjacentWorldBestFuelParsecs)

                    if adjacentToTargetMinParsecs == None:
                        adjacentToTargetMinParsecs = adjacentWorld.parsecsTo(targetWorld)

                    targetWorldData[adjacentWorld] = \
                        (adjacentWorldBestScore, adjacentWorldBestFuelParsecs, adjacentToTargetMinParsecs)

                    # For estimating the cost of the remaining portion of the
                    # route, use min distance from the adjacent world to the
                    # finish going via all remaining waypoints
                    remainingEstimate = jumpCostCalculator.estimate(
                        parsecsToFinish=adjacentToTargetMinParsecs + targetToFinishMinParsecs)

                    newNode = _RouteNode(
                        targetIndex=targetIndex,
                        world=adjacentWorld,
                        gScore=tentativeScore,
                        fScore=tentativeScore + remainingEstimate,
                        isFuelWorld=isAdjacentFuelWorld,
                        fuelParsecs=fuelParsecs,
                        costContext=costContext,
                        parent=currentNode)
                    heapq.heappush(openQueue, newNode)
                    addedRoutes += 1

            closedRoutes += possibleRoutes - addedRoutes

        return None # No route found

    # TODO: This will need updated to return a list of nodes rather than worlds
    def _finaliseRoute(
            self,
            finishNode: _RouteNode,
            progressCount: int,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            ) -> typing.List[traveller.World]:
        # We've found the lowest cost route that goes through all the worlds in the sequence.
        # Process it to generate the final list of route worlds then bail
        path = []

        node = finishNode
        path.append(node.world())

        while node.parent():
            node = node.parent()
            path.append(node.world())
        path.reverse()

        if progressCallback:
            progressCallback(progressCount, True) # Search is finished

        return path
