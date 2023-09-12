import common
import heapq
import logic
import traveller
import typing

class _RouteNode(object):
    def __init__(
            self,
            world: traveller.World,
            gScore: int,
            fScore: int,
            isFuelWorld: bool,
            maxFuelRemaining: float,
            costContext: typing.Any,
            parent: typing.Optional['_RouteNode'] = None,
            ) -> None:
        self._world = world
        self._gScore = gScore
        self._fScore = fScore
        self._isFuelWorld = isFuelWorld
        self._maxFuelRemaining = maxFuelRemaining
        self._costContext = costContext
        self._parent = parent

    def world(self) -> traveller.World:
        return self._world

    def gScore(self) -> float:
        return self._gScore

    def fScore(self) -> float:
        return self._fScore

    def isFuelWorld(self) -> bool:
        return self._isFuelWorld

    def maxFuelRemaining(self) -> int:
        return self._maxFuelRemaining

    def costContext(self) -> typing.Any:
        return self._costContext

    def parent(self) -> '_RouteNode':
        return self._parent

    def __lt__(self, other: '_RouteNode') -> bool:
        # Order by fScore rather than gScore so that, in the case where two system have the same
        # gScore the system closest to the finish world will be processed first
        return self._fScore < other._fScore

class _ProgressTracker(object):
    def __init__(
            self,
            progressCallback: typing.Callable[[int, bool], typing.Any] = None
            ) -> None:
        self._progressCallback = progressCallback
        self._totalProgress = 0

    def updateStageProgress(
            self,
            stageProgress: int,
            isFinished: bool) -> None:
        if self._progressCallback:
            self._progressCallback(self._totalProgress + stageProgress, False)
        if isFinished:
            self._totalProgress += stageProgress

    def emitFinalProgress(self) -> None:
        if self._progressCallback:
            self._progressCallback(self._totalProgress, True)

class JumpCostCalculatorInterface(object):
    def initialise(
            startWorld: traveller.World
            ) -> typing.Any:
        raise RuntimeError('The initialise method should be overridden by classes derived from JumpCostCalculator')

    def calculate(
            currentWorld: traveller.World,
            nextWorld: traveller.World,
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
            refuellingStrategy: logic.RefuellingStrategy,
            shipFuelPerParsec: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            worldFilterCallback: typing.Optional[typing.Callable[[traveller.World], bool]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.Optional[logic.JumpRoute]:
        worldList = self._calculateRoute(
            startWorld=startWorld,
            finishWorld=finishWorld,
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
            refuellingStrategy: logic.RefuellingStrategy,
            shipFuelPerParsec: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            worldFilterCallback: typing.Optional[typing.Callable[[traveller.World], bool]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.Optional[logic.JumpRoute]:
        if not worldSequence:
            None
        if len(worldSequence) < 2:
            # The world sequence is a single world so its the "jump route"
            return worldSequence

        progressTracker = None
        onStageProgress = None
        if progressCallback:
            progressTracker = _ProgressTracker(progressCallback)
            onStageProgress = progressTracker.updateStageProgress

        finalWorldList = []
        for i in range(len(worldSequence) - 1):
            startWorld = worldSequence[i]
            finishWorld = worldSequence[i + 1]

            worldList = self._calculateRoute(
                startWorld=startWorld,
                finishWorld=finishWorld,
                shipTonnage=shipTonnage,
                shipJumpRating=shipJumpRating,
                shipFuelCapacity=shipFuelCapacity,
                shipFuelPerParsec=shipFuelPerParsec,
                shipCurrentFuel=shipCurrentFuel if i == 0 else 0, # TODO: Not sure how jumps after the first should be handled
                jumpCostCalculator=jumpCostCalculator,
                refuellingStrategy=refuellingStrategy,
                worldFilterCallback=worldFilterCallback,
                progressCallback=onStageProgress,
                isCancelledCallback=isCancelledCallback)
            if not worldList:
                return None # No route found

            if i != 0:
                # For all but the first stage remove the first world in the route as it will be the
                # same as the last world in the route for the previous stage
                worldList.pop(0)

            if worldList:
                finalWorldList.extend(worldList)

        if progressTracker:
            progressTracker.emitFinalProgress()

        return logic.JumpRoute(finalWorldList)

    # Reimplementation of code from Traveller Map source code (FindPath in PathFinder.cs).
    # Which in turn was based on code from AI for Game Developers, Bourg & Seemann,
    # O'Reilly Media, Inc., July 2004.
    def _calculateRoute(
            self,
            startWorld: traveller.World,
            finishWorld: traveller.World,
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipCurrentFuel: typing.Union[int, common.ScalarCalculation],
            jumpCostCalculator: JumpCostCalculatorInterface,
            refuellingStrategy: logic.RefuellingStrategy,
            shipFuelPerParsec: typing.Optional[typing.Union[int, float, common.ScalarCalculation]] = None,
            worldFilterCallback: typing.Optional[typing.Callable[[traveller.World], bool]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.List[traveller.World]:
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

        parsecsWithoutRefuelling = int(shipFuelCapacity // shipFuelPerParsec)
        if parsecsWithoutRefuelling < 1:
            raise ValueError('Ship\'s fuel capacity doesn\'t allow for jump-1')

        # A _LOT_ of the time we're asked to calculate a route the finish world is actually within
        # one jump of the start world (as finished worlds tend to come from nearby world searches).
        # Do a quick check for this case, if it's true we known the shortest distance/shortest time
        # and lowest cost route is a single direct jump.
        distance = traveller.hexDistance(
            startWorld.absoluteX(),
            startWorld.absoluteY(),
            finishWorld.absoluteX(),
            finishWorld.absoluteY())
        if distance <= shipJumpRating:
            if startWorld == finishWorld:
                return [startWorld]
            return [startWorld, finishWorld]

        # add the starting node to the open list
        openQueue: typing.List[_RouteNode] = []
        gScores: typing.Dict[traveller.World, float] = {}
        excludedWorlds: typing.Set[traveller.World] = set()

        isFuelWorld = logic.selectRefuellingType(
            world=startWorld,
            refuellingStrategy=refuellingStrategy) != None
        if isFuelWorld:
            maxFuelRemaining = shipFuelCapacity
        else:
            # TODO: For now assume you can always refuel on the start world
            #maxFuelRemaining = shipCurrentFuel
            maxFuelRemaining = shipFuelCapacity
            isFuelWorld = True

        startNode = _RouteNode(
            world=startWorld,
            gScore=0,
            fScore=0,
            isFuelWorld=isFuelWorld,
            maxFuelRemaining=maxFuelRemaining,
            costContext=jumpCostCalculator.initialise(startWorld=startWorld),
            parent=None)
        heapq.heappush(openQueue, startNode)
        gScores[startWorld] = 0

        # If a world filter was passed in wrap it in a lambda that prevents the start and finish
        # worlds from being filtered out
        worldFilter = None
        if worldFilterCallback:
            worldFilter = lambda world: \
                True if (world == startWorld) or (world == finishWorld) else worldFilterCallback(world)

        # Take a local reference to the WorldManager singleton to avoid repeated calls to instance()
        worldManager = traveller.WorldManager.instance()

        # while the open list is not empty
        while openQueue:
            if isCancelledCallback and isCancelledCallback():
                return None

            # current node = node from open list with the lowest cost
            currentNode: _RouteNode = heapq.heappop(openQueue)
            currentWorld = currentNode.world()

            # if current node = goal node then path complete
            if currentWorld == finishWorld:
                path = []

                node = currentNode
                path.append(node.world())

                while node.parent():
                    node = node.parent()
                    path.append(node.world())
                path.reverse()

                if progressCallback:
                    progressCallback(
                        len(gScores) + 1,
                        True) # Search is finished

                return path

            if progressCallback:
                # We haven't actually finished processing the world yet but notifying here makes it
                # easier with the various continues that are later in the function (and it doesn't
                # REALLY mater when it's done)
                progressCallback(
                    len(gScores) + 1,
                    False) # Search isn't finished

            # TODO: Need an option for no refuelling strategy to allow for routing in places like Foreven
            # TODO: Comment explaining this
            if currentNode.isFuelWorld():
                searchRadius = shipJumpRating
            else:
                searchRadius = min(
                    shipJumpRating,
                    int(currentNode.maxFuelRemaining() // shipFuelPerParsec))

            # Clamp the search radius to the max parsecs without refuelling. This is required for
            # ships that don't have the fuel capacity to perform their max jump. Not sure when
            # this would actually happen but it should be handled
            searchRadius = min(searchRadius, parsecsWithoutRefuelling)

            assert(searchRadius >= 0)

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

                # Check to see if this world has already been excluded by the world filter in a
                # previous iteration. This saves running the expensive world filter multiple times
                # for the same world
                if adjacentWorld in excludedWorlds:
                    continue

                jumpCost, costContext = jumpCostCalculator.calculate(
                    currentWorld,
                    adjacentWorld,
                    currentNode.costContext())
                if jumpCost == None:
                    continue

                tentativeScore = gScores[currentWorld] + jumpCost
                bestScore = gScores.get(adjacentWorld)

                # TODO: Remove debug code
                #print(f'{currentWorld.name()}->{adjacentWorld.name()} {jumpCost} {tentativeScore} {bestScore}')

                isFuelWorld = logic.selectRefuellingType(
                    world=adjacentWorld,
                    refuellingStrategy=refuellingStrategy) != None

                if (bestScore == None) or (tentativeScore < bestScore):
                    gScores[adjacentWorld] = tentativeScore

                    if worldFilter and not worldFilter(adjacentWorld):
                        excludedWorlds.add(adjacentWorld)
                        continue

                    jumpDistance = traveller.hexDistance(
                        currentWorld.absoluteX(),
                        currentWorld.absoluteY(),
                        adjacentWorld.absoluteX(),
                        adjacentWorld.absoluteY())
                    fuelForJump = jumpDistance * shipFuelPerParsec
                    if currentNode.isFuelWorld():
                        maxFuelRemaining = shipFuelCapacity - fuelForJump
                    else:
                        maxFuelRemaining = currentNode.maxFuelRemaining() - fuelForJump

                    jumpsToFinish = traveller.hexDistance(
                        absoluteX1=adjacentWorld.absoluteX(),
                        absoluteY1=adjacentWorld.absoluteY(),
                        absoluteX2=finishWorld.absoluteX(),
                        absoluteY2=finishWorld.absoluteY()) / parsecsWithoutRefuelling
                    newNode = _RouteNode(
                        world=adjacentWorld,
                        gScore=tentativeScore,
                        fScore=tentativeScore + jumpsToFinish,
                        isFuelWorld=isFuelWorld,
                        maxFuelRemaining=maxFuelRemaining,
                        costContext=costContext,
                        parent=currentNode)
                    heapq.heappush(openQueue, newNode)

        return None # No route found
