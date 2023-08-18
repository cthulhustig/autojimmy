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
            parent: typing.Optional['_RouteNode'] = None,
            ) -> None:
        self._world = world
        self._gScore = gScore
        self._fScore = fScore
        self._parent = parent

    def world(self) -> traveller.World:
        return self._world

    def gScore(self) -> typing.Union[int, float]:
        return self._gScore

    def fScore(self) -> typing.Union[int, float]:
        return self._fScore

    def parent(self) -> '_RouteNode':
        return self._parent

    def __lt__(self, other: '_RouteNode') -> bool:
        # Order by fScore as that is it gives the best estimate of what the total
        # cost will start to finish
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

class RoutePlanner(object):
    def calculateDirectRoute(
            self,
            startWorld: traveller.World,
            finishWorld: traveller.World,
            jumpRating: typing.Union[int, common.ScalarCalculation],
            jumpCostCallback: typing.Optional[typing.Callable[[traveller.World, traveller.World], int]] = None,
            worldFilterCallback: typing.Optional[typing.Callable[[traveller.World], bool]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.Optional[logic.JumpRoute]:
        worldList = self._calculateRoute(
            startWorld=startWorld,
            finishWorld=finishWorld,
            jumpRating=jumpRating,
            jumpCostCallback=jumpCostCallback,
            worldFilterCallback=worldFilterCallback,
            progressCallback=progressCallback,
            isCancelledCallback=isCancelledCallback)
        if not worldList:
            return None # No route found

        return logic.JumpRoute(worldList)

    def calculateSequenceRoute(
            self,
            worldSequence: typing.List[traveller.World],
            jumpRating: typing.Union[int, common.ScalarCalculation],
            jumpCostCallback: typing.Optional[typing.Callable[[traveller.World, traveller.World], int]] = None,
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
                jumpRating=jumpRating,
                jumpCostCallback=jumpCostCallback,
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
            jumpRating: typing.Union[int, common.ScalarCalculation],
            jumpCostCallback: typing.Optional[typing.Callable[[traveller.World, traveller.World], int]] = None,
            worldFilterCallback: typing.Optional[typing.Callable[[traveller.World], bool]] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.List[traveller.World]:
        # If the jump rating is a calculation covert it to it's raw value as we don't need to
        # track calculations here
        if isinstance(jumpRating, common.ScalarCalculation):
            jumpRating = jumpRating.value()

        # Default jump cost function to the one that will use the least fuel
        defaultCostCalculator = None
        if not jumpCostCallback:
            defaultCostCalculator = logic.ShortestDistanceCostCalculator()
            jumpCostCallback = defaultCostCalculator.calculate

        # A _LOT_ of the time we're asked to calculate a route the finish world is actually within
        # one jump of the start world (as finished worlds tend to come from nearby world searches).
        # Do a quick check for this case, if it's true we known the shortest distance/shortest time
        # and lowest cost route is a single direct jump.
        distance = traveller.hexDistance(
            startWorld.absoluteX(),
            startWorld.absoluteY(),
            finishWorld.absoluteX(),
            finishWorld.absoluteY())
        if distance <= jumpRating:
            if startWorld == finishWorld:
                return [startWorld]
            return [startWorld, finishWorld]

        # add the starting node to the open list
        openQueue: typing.List[_RouteNode] = []
        gScores: typing.Dict[traveller.World, typing.Union[int, float]] = {}
        excludedWorlds: typing.Set[traveller.World] = set()

        startNode = _RouteNode(world=startWorld, gScore=0, fScore=0, parent=None)
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

            # This node has already been surpassed by a better route to this world, no point taking
            # it any further. This check is needed as it's not possible to remove an entry from a
            # heapq or change the cost of an entry.
            bestScore = gScores.get(currentWorld)
            if (bestScore != None) and (currentNode.gScore() > bestScore):
                continue

            if progressCallback:
                # We haven't actually finished processing the world yet but notifying here makes it
                # easier with the various continues that are later in the function (and it doesn't
                # REALLY mater when it's done)
                progressCallback(
                    len(gScores) + 1,
                    False) # Search isn't finished

            # examine each node adjacent to the current node. The world filter isn't passed in
            # as it's quicker to use the open and closed set to filter out large numbers of
            # them before calling the more expensive world filter
            adjacent = worldManager.worldsInArea(
                sectorName=currentWorld.sectorName(),
                worldX=currentWorld.x(),
                worldY=currentWorld.y(),
                searchRadius=jumpRating)
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

                tentativeScore = gScores[currentWorld] + jumpCostCallback(currentWorld, adjacentWorld)
                bestScore = gScores.get(adjacentWorld)
                if (bestScore == None) or (tentativeScore < bestScore):
                    gScores[adjacentWorld] = tentativeScore

                    if worldFilter and not worldFilter(adjacentWorld):
                        excludedWorlds.add(adjacentWorld)
                        continue

                    jumpsToFinish = traveller.hexDistance(
                        absoluteX1=adjacentWorld.absoluteX(),
                        absoluteY1=adjacentWorld.absoluteY(),
                        absoluteX2=finishWorld.absoluteX(),
                        absoluteY2=finishWorld.absoluteY()) / jumpRating
                    newNode = _RouteNode(
                        world=adjacentWorld,
                        gScore=tentativeScore,
                        fScore=tentativeScore + jumpsToFinish,
                        parent=currentNode)
                    heapq.heappush(openQueue, newNode)

        return None # No route found
