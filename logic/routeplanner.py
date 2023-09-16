import common
import heapq
import logic
import traveller
import typing

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

    def setTargetIndex(self, index: int) -> None:
        self._targetIndex = index

    def world(self) -> traveller.World:
        return self._world

    def gScore(self) -> float:
        return self._gScore

    def fScore(self) -> float:
        return self._fScore

    def isFuelWorld(self) -> bool:
        return self._isFuelWorld

    # This is the max number of parsecs that can be jumped if this world isn't used for refuelling
    def fuelParsecs(self) -> int:
        return self._fuelParsecs

    def costContext(self) -> typing.Any:
        return self._costContext

    def parent(self) -> '_RouteNode':
        return self._parent

    def __lt__(self, other: '_RouteNode') -> bool:
        # Order by fScore rather than gScore so that, in the case where two system have the same
        # gScore the system closest to the finish world will be processed first
        if self._fScore < other._fScore:
            return True
        elif self._fScore > other._fScore:
            return False

        return self._fuelParsecs > other._fuelParsecs

class JumpCostCalculatorInterface(object):
    def initialise(
            startWorld: traveller.World
            ) -> typing.Any:
        raise RuntimeError('The initialise method should be overridden by classes derived from JumpCostCalculator')

    def calculate(
            currentWorld: traveller.World,
            nextWorld: traveller.World,
            jumpParsecs: int,
            costContext: typing.Any
            ) -> typing.Tuple[typing.Optional[float], typing.Any]: # (Jump Cost, New Cost Context)
        raise RuntimeError('The calculate method should be overridden by classes derived from JumpCostCalculator')

class RoutePlanner(object):
    def calculateDirectRoute(
            self,
            startWorld: traveller.World,
            finishWorld: traveller.World,
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipCurrentFuel: typing.Union[int, common.ScalarCalculation],
            jumpCostCalculator: JumpCostCalculatorInterface,
            refuellingStrategy: typing.Optional[logic.RefuellingStrategy] = None, # None disables fuel based route calculation
            shipFuelPerParsec: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
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
            refuellingStrategy=refuellingStrategy,
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
            shipCurrentFuel: typing.Union[int, common.ScalarCalculation],
            jumpCostCalculator: JumpCostCalculatorInterface,
            refuellingStrategy: typing.Optional[logic.RefuellingStrategy] = None, # None disables fuel based route calculation
            shipFuelPerParsec: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
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
            refuellingStrategy=refuellingStrategy,
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
    def _calculateRoute(
            self,
            worldSequence: typing.List[traveller.World],
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipCurrentFuel: typing.Union[int, common.ScalarCalculation],
            jumpCostCalculator: JumpCostCalculatorInterface,
            refuellingStrategy: typing.Optional[logic.RefuellingStrategy] = None, # None disables fuel based route calculation
            shipFuelPerParsec: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
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

        shipParsecsWithoutRefuelling = int(shipFuelCapacity // shipFuelPerParsec)
        if shipParsecsWithoutRefuelling < 1:
            raise ValueError('Ship\'s fuel capacity doesn\'t allow for jump-1')

        sequenceLength = len(worldSequence)
        assert(sequenceLength >= 2)
        startWorld = worldSequence[0]
        finishWorld = worldSequence[-1]

        refuellingTypeCache = None

        if refuellingStrategy:
            refuellingTypeCache = logic.RefuellingTypeCache(
                refuellingStrategy=refuellingStrategy)
            isFuelWorld = refuellingTypeCache.selectRefuellingType(
                world=startWorld) != None
            maxStartingFuel = shipFuelCapacity if isFuelWorld else shipCurrentFuel
        else:
            # Fuel based route calculation is disabled so use the max capacity as the max starting
            # fuel. The intended effect is to have it possible to jump to any world within jump
            # range (fuel capacity allowing).
            isFuelWorld = False
            maxStartingFuel = shipFuelCapacity

        # Handle early outs when dealing with direct world to world routes
        if sequenceLength == 2:
            # Handle corner case where the start and finish are the same world
            if startWorld == finishWorld:
                return [startWorld]

            # A _LOT_ of the time we're asked to calculate a route the finish world is actually within
            # one jump of the start world (as finished worlds tend to come from nearby world searches).
            # Do a quick check for this case, if it's true we known the shortest distance/shortest time
            # and lowest cost route is a single direct jump.
            # This check is only done if the world can be reached with the max starting fuel. This means
            # either the world meets the refuelling strategy or there is enough fuel in the tank to reach
            # it. If not, a full route check is performed as it may be possible to find a better route
            # depending on the costing function (i.e. lowest cost). I suspect there may be some corner
            # cases where this doesn't hold but until I know they actually exist I'm going to go with the
            # performance increase
            distance = traveller.hexDistance(
                startWorld.absoluteX(),
                startWorld.absoluteY(),
                finishWorld.absoluteX(),
                finishWorld.absoluteY())
            if distance <= shipJumpRating:
                fuelToFinish = distance * shipFuelPerParsec
                if fuelToFinish <= maxStartingFuel:
                    return [startWorld, finishWorld]

        # add the starting node to the open list
        openQueue: typing.List[_RouteNode] = []
        bestValues: typing.Dict[int, typing.Dict[traveller.World, typing.Tuple[float, int]]] = {}
        excludedWorlds: typing.Set[traveller.World] = set()

        fuelParsecs = int(maxStartingFuel // shipFuelPerParsec)
        startNode = _RouteNode(
            targetIndex=1,
            world=startWorld,
            gScore=0,
            fScore=0,
            isFuelWorld=isFuelWorld,
            fuelParsecs=fuelParsecs,
            costContext=jumpCostCalculator.initialise(startWorld=startWorld),
            parent=None)
        heapq.heappush(openQueue, startNode)
        bestValues[1] = {}
        bestValues[1][startWorld] = (0, fuelParsecs) # Best gScore, Best Max Jump Parsecs

        # If a world filter was passed in wrap it in a lambda that prevents worlds that are explicitly in
        # the sequence being filtered out
        worldFilter = None
        if worldFilterCallback:
            mandatoryWorlds = set(worldSequence)
            worldFilter = lambda world: True if (world in mandatoryWorlds) else worldFilterCallback(world)

        # Take a local reference to the WorldManager singleton to avoid repeated calls to instance()
        worldManager = traveller.WorldManager.instance()

        # Process nodes while the open list is not empty
        finishWorldIndex = sequenceLength - 1
        progressCount = 0
        while openQueue:
            if isCancelledCallback and isCancelledCallback():
                return None

            progressCount += 1

            # current node = node from open list with the lowest cost
            currentNode: _RouteNode = heapq.heappop(openQueue)
            currentWorld = currentNode.world()

            # if current node = goal node then path complete
            targetIndex = currentNode.targetIndex()
            targetWorld = worldSequence[targetIndex]
            if currentWorld == targetWorld:
                # We've reached the target world for this segment of the jump route
                if targetIndex == finishWorldIndex:
                    # We've found the lowest cost route that goes through all the worlds in the sequence.
                    # Process it to generate the final list of route worlds then bail
                    return self._finaliseRoute(
                        finishNode=currentNode,
                        progressCount=progressCount,
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
                            progressCount=progressCount,
                            progressCallback=progressCallback)

                # Set the new target for the current node
                currentNode.setTargetIndex(targetIndex)

                # Add a score map for the new target index if one doesn't exist already
                bestValuesForTarget = bestValues.get(targetIndex)
                if bestValuesForTarget == None:
                    bestValuesForTarget = {}
                    bestValues[targetIndex] = bestValuesForTarget

                # Update the best scores for entry for the current world
                currentWorldBestScore, currentWorldBestFuelParsecs = \
                    bestValuesForTarget.get(currentWorld, (None, None))
                currentWorldBestScore = currentNode.gScore() \
                    if currentWorldBestScore == None else \
                    min(currentNode.gScore(), currentWorldBestScore)
                currentWorldBestFuelParsecs = currentNode.fuelParsecs() \
                    if currentWorldBestFuelParsecs == None else \
                    max(currentNode.fuelParsecs(), currentWorldBestFuelParsecs)
                bestValuesForTarget[currentWorld] = \
                    (currentWorldBestScore, currentWorldBestFuelParsecs)
            else:
                bestValuesForTarget = bestValues[targetIndex]

            if progressCallback:
                progressCallback(progressCount, False) # Search isn't finished

            if refuellingStrategy:
                # Set search area based on the max distance we could jump from the current world. If
                # it's a world where fuel could be taken then the search area is the ship jump
                # rating. If it's not a world where fuel can be taken on then the search radius is
                # determined by the amount of fuel in the ship (limited by jump rating)
                if currentNode.isFuelWorld():
                    searchRadius = shipJumpRating
                else:
                    searchRadius = min(shipJumpRating, currentNode.fuelParsecs())
            else:
                # Fuel based route calculation is disabled so always search for the full ship jump
                # rating
                searchRadius = shipJumpRating

            # Clamp the search radius to the max parsecs without refuelling. This is required for
            # ships that don't have the fuel capacity to perform their max jump. Not sure when
            # this would actually happen but it should be handled
            searchRadius = min(searchRadius, shipParsecsWithoutRefuelling)
            if searchRadius <= 0:
                continue

            # examine each node adjacent to the current node. The world filter isn't passed in
            # as it's quicker to use the open and closed set to filter out large numbers of
            # them before calling the more expensive world filter
            adjacent = worldManager.worldsInArea(
                sectorName=currentWorld.sectorName(),
                worldX=currentWorld.x(),
                worldY=currentWorld.y(),
                searchRadius=searchRadius)
            if not adjacent:
                continue

            for adjacentWorld in adjacent:
                # WorldsInArea always returns the current world in the search area but it shouldn't
                # be processed as an adjacent world
                if adjacentWorld == currentWorld:
                    continue

                # Check to see if this world has is excluded. A set of previously excluded worlds is
                # maintained to avoid running the potentially expensive world filter multiple times
                # for the same world
                if adjacentWorld in excludedWorlds:
                    continue
                if worldFilter and not worldFilter(adjacentWorld):
                    excludedWorlds.add(adjacentWorld)
                    continue

                jumpDistance = traveller.hexDistance(
                    currentWorld.absoluteX(),
                    currentWorld.absoluteY(),
                    adjacentWorld.absoluteX(),
                    adjacentWorld.absoluteY())

                # Calculate the cost of jumping to the adjacent world
                jumpCost, costContext = jumpCostCalculator.calculate(
                    currentWorld,
                    adjacentWorld,
                    jumpDistance,
                    currentNode.costContext())
                if jumpCost == None:
                    continue

                if refuellingStrategy:
                    isFuelWorld = refuellingTypeCache.selectRefuellingType(
                        world=adjacentWorld) != None

                    if currentNode.isFuelWorld():
                        fuelParsecs = shipParsecsWithoutRefuelling - jumpDistance
                    else:
                        fuelParsecs = currentNode.fuelParsecs() - jumpDistance

                    if (not isFuelWorld) and (fuelParsecs <= 0) and (adjacentWorld != finishWorld):
                        # The adjacent world can't be used for refuelling and the ship won't have enough
                        # fuel to jump on when it gets there so abandon this route early
                        continue
                else:
                    # Fuel based route calculation is disabled. These values have no effect but
                    # must be set to something
                    isFuelWorld = False
                    fuelParsecs = shipJumpRating

                tentativeScore = currentNode.gScore() + jumpCost
                adjacentWorldBestScore, adjacentWorldBestFuelParsecs = \
                    bestValuesForTarget.get(adjacentWorld, (None, None))
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
                    bestValuesForTarget[adjacentWorld] = \
                        (adjacentWorldBestScore, adjacentWorldBestFuelParsecs)

                    # Use number of jumps between adjacent world and finish world as fScore
                    # modifier. In the case that two worlds have the same gScore this will cause
                    # the one that is closer to the finish world to be processed first
                    fScoreModifier = traveller.hexDistance(
                        absoluteX1=adjacentWorld.absoluteX(),
                        absoluteY1=adjacentWorld.absoluteY(),
                        absoluteX2=finishWorld.absoluteX(),
                        absoluteY2=finishWorld.absoluteY()) / shipJumpRating
                    newNode = _RouteNode(
                        targetIndex=targetIndex,
                        world=adjacentWorld,
                        gScore=tentativeScore,
                        fScore=tentativeScore + fScoreModifier,
                        isFuelWorld=isFuelWorld,
                        fuelParsecs=fuelParsecs,
                        costContext=costContext,
                        parent=currentNode)
                    heapq.heappush(openQueue, newNode)

        return None # No route found

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
