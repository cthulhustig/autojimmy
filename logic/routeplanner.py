import common
import enum
import heapq
import logic
import math
import traveller
import travellermap
import typing

# NOTE: The name of these enums is stored in the app config
class RoutingType(enum.Enum):
    Basic = 'Basic'
    FuelBased = 'Fuel Based'
    DeadSpace = 'Dead Space'

class _RouteNode(object):
    def __init__(
            self,
            targetIndex: int,
            hex: travellermap.HexPosition,
            world: typing.Optional[traveller.World],
            gScore: float,
            fScore: float,
            isFuelWorld: bool,
            fuelParsecs: int,
            costContext: typing.Any,
            parent: typing.Optional['_RouteNode'] = None,
            ) -> None:
        self._targetIndex = targetIndex
        self._hex = hex
        self._world = world
        self._gScore = gScore
        self._fScore = fScore
        self._isFuelWorld = isFuelWorld
        self._fuelParsecs = fuelParsecs
        self._costContext = costContext
        self._parent = parent

    def targetIndex(self) -> int:
        return self._targetIndex

    def hex(self) -> travellermap.HexPosition:
        return self._hex

    def world(self) -> typing.Optional[traveller.World]:
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
            startHex: travellermap.HexPosition,
            startWorld: typing.Optional[traveller.World]
            ) -> typing.Any:
        raise RuntimeError(f'{type(self)} is derived from JumpCostCalculatorInterface so must implement initialise')

    # Calculate the cost of the jump from the current world to the next world
    def calculate(
            self,
            currentHex: travellermap.HexPosition,
            currentWorld: typing.Optional[traveller.World],
            nextHex: travellermap.HexPosition,
            nextWorld: typing.Optional[traveller.World],
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

class HexFilterInterface(object):
    def match(
            self,
            hex: travellermap.HexPosition,
            world: typing.Optional[traveller.World]
            ) -> float:
        raise RuntimeError(f'{type(self)} is derived from HexFilterInterface so must implement match')

class RoutePlanner(object):
    def calculateDirectRoute(
            self,
            routingType: RoutingType,
            startHex: travellermap.HexPosition,
            finishHex: travellermap.HexPosition,
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipCurrentFuel: typing.Union[float, common.ScalarCalculation],
            jumpCostCalculator: JumpCostCalculatorInterface,
            pitCostCalculator: typing.Optional[logic.PitStopCostCalculator] = None, # None disables fuel based route calculation
            shipFuelPerParsec: typing.Optional[typing.Union[float, common.ScalarCalculation]] = None,
            hexFilter: typing.Optional[HexFilterInterface] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.Optional[logic.JumpRoute]:
        return self._calculateRoute(
            routingType=routingType,
            hexSequence=[startHex, finishHex],
            shipTonnage=shipTonnage,
            shipJumpRating=shipJumpRating,
            shipFuelCapacity=shipFuelCapacity,
            shipCurrentFuel=shipCurrentFuel,
            shipFuelPerParsec=shipFuelPerParsec,
            jumpCostCalculator=jumpCostCalculator,
            pitCostCalculator=pitCostCalculator,
            hexFilter=hexFilter,
            progressCallback=progressCallback,
            isCancelledCallback=isCancelledCallback)

    def calculateSequenceRoute(
            self,
            routingType: RoutingType,
            hexSequence: typing.Sequence[travellermap.HexPosition],
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipCurrentFuel: typing.Union[float, common.ScalarCalculation],
            jumpCostCalculator: JumpCostCalculatorInterface,
            pitCostCalculator: typing.Optional[logic.PitStopCostCalculator] = None, # None disables fuel based route calculation
            shipFuelPerParsec: typing.Optional[typing.Union[float, common.ScalarCalculation]] = None,
            hexFilter: typing.Optional[HexFilterInterface] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.Optional[logic.JumpRoute]:
        return self._calculateRoute(
            routingType=routingType,
            hexSequence=hexSequence,
            shipTonnage=shipTonnage,
            shipJumpRating=shipJumpRating,
            shipFuelCapacity=shipFuelCapacity,
            shipCurrentFuel=shipCurrentFuel,
            shipFuelPerParsec=shipFuelPerParsec,
            jumpCostCalculator=jumpCostCalculator,
            pitCostCalculator=pitCostCalculator,
            hexFilter=hexFilter,
            progressCallback=progressCallback,
            isCancelledCallback=isCancelledCallback)

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
            routingType: RoutingType,
            hexSequence: typing.Sequence[travellermap.HexPosition],
            shipTonnage: typing.Union[int, common.ScalarCalculation],
            shipJumpRating: typing.Union[int, common.ScalarCalculation],
            shipFuelCapacity: typing.Union[int, common.ScalarCalculation],
            shipCurrentFuel: typing.Union[float, common.ScalarCalculation],
            jumpCostCalculator: JumpCostCalculatorInterface,
            pitCostCalculator: typing.Optional[logic.PitStopCostCalculator] = None, # Required for fuel based and dead space routing
            shipFuelPerParsec: typing.Optional[typing.Union[float, common.ScalarCalculation]] = None,
            hexFilter: typing.Optional[HexFilterInterface] = None,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            isCancelledCallback: typing.Optional[typing.Callable[[], bool]] = None
            ) -> typing.Optional[logic.JumpRoute]:
        if (routingType is not RoutingType.Basic) and (not pitCostCalculator):
            raise ValueError(f'{routingType.value} routing requires a pit stop cost calculator')

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

        # Take a local reference to the WorldManager singleton to avoid repeated calls to instance()
        worldManager = traveller.WorldManager.instance()

        sequenceLength = len(hexSequence)
        assert(sequenceLength >= 2)
        finishWorldIndex = sequenceLength - 1

        startHex = hexSequence[0]
        startWorld = worldManager.worldByPosition(hex=startHex)

        finishHex = hexSequence[finishWorldIndex]
        finishWorld = worldManager.worldByPosition(hex=finishHex)

        startWorldFuelType = None
        if routingType is RoutingType.Basic:
            # Fuel based route calculation is disabled so use the max capacity as the max starting
            # fuel. The intended effect is to have it possible to jump to any world within jump
            # range (fuel capacity allowing).
            isCurrentFuelWorld = False
            maxStartingFuel = shipFuelCapacity
        else:
            if startWorld:
                startWorldFuelType = pitCostCalculator.refuellingType(world=startWorld)
            isCurrentFuelWorld = startWorldFuelType != None
            maxStartingFuel = shipFuelCapacity if isCurrentFuelWorld else shipCurrentFuel

        # Handle early outs when dealing with direct world to world routes
        if sequenceLength == 2:
            # Handle corner case where the start and finish are the same world
            if startHex == finishHex:
                return logic.JumpRoute([(startHex, startWorld)])

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
            distance = startHex.parsecsTo(finishHex)
            if distance <= shipJumpRating:
                if routingType is RoutingType.Basic:
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
                    return logic.JumpRoute([
                        (startHex, startWorld),
                        (finishHex, finishWorld)])

        openQueue: typing.List[_RouteNode] = []
        targetStates: typing.List[
            typing.Tuple[
                typing.Set[travellermap.HexPosition], # Closed hexes
                typing.Dict[
                    travellermap.HexPosition,
                    typing.Tuple[
                        float, # Best gScore for a route reaching this hex
                        int, # Best remaining fuel for a route reaching this hex
                        int # Parsecs from hex to target (note target not necessarily finish)
                    ]],
                int # Min parsecs from target to finish (going via all waypoints)
                ]] = []
        filterResultCache: typing.Set[
            travellermap.HexPosition, # Hex position
            bool # Cached filter result
            ] = {}

        minRouteParsecs = 0
        for index in range(sequenceLength - 1):
            currentHex = hexSequence[index]
            targetHex = hexSequence[index + 1]
            minRouteParsecs += currentHex.parsecsTo(targetHex)

        startToCurrentParsecs = 0
        for index in range(sequenceLength):
            targetStates.append((set(), dict(), minRouteParsecs - startToCurrentParsecs))

            if index != finishWorldIndex:
                currentHex = hexSequence[index]
                targetHex = hexSequence[index + 1]
                startToCurrentParsecs += currentHex.parsecsTo(targetHex)

        # Add the starting node to the open list
        fuelParsecs = math.floor(maxStartingFuel / shipFuelPerParsec)
        startNode = _RouteNode(
            targetIndex=1,
            hex=startHex,
            world=startWorld,
            gScore=0,
            fScore=0,
            isFuelWorld=isCurrentFuelWorld,
            fuelParsecs=fuelParsecs,
            costContext=jumpCostCalculator.initialise(
                startHex=startHex,
                startWorld=startWorld),
            parent=None)
        heapq.heappush(openQueue, startNode)

        targetHex = hexSequence[1]
        currentToTargetParsecs = startHex.parsecsTo(targetHex)
        targetStates[1][1][startHex] = (0, fuelParsecs, currentToTargetParsecs)

        # Process nodes while the open list is not empty
        closedRoutes = 0
        while openQueue:
            if isCancelledCallback and isCancelledCallback():
                return None

            # current node = node from open list with the lowest cost
            currentNode: _RouteNode = heapq.heappop(openQueue)
            currentHex = currentNode.hex()
            targetIndex = currentNode.targetIndex()
            targetHex = hexSequence[targetIndex]

            targetClosedSet, targetHexData, targetToFinishMinParsecs = targetStates[targetIndex]
            targetClosedSet.add(currentHex)

            # if current node = goal node then path complete
            if currentHex == targetHex:
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
                    newTargetHex = hexSequence[targetIndex]
                    if newTargetHex != targetHex:
                        targetHex = newTargetHex
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
                targetClosedSet, targetHexData, targetToFinishMinParsecs = targetStates[targetIndex]
                currentHexBestScore, currentHexBestFuelParsecs, currentToTargetParsecs = \
                    targetHexData.get(currentHex, (None, None, None))

                currentHexBestScore = currentNode.gScore() \
                    if currentHexBestScore == None else \
                    min(currentNode.gScore(), currentHexBestScore)

                currentHexBestFuelParsecs = currentNode.fuelParsecs() \
                    if currentHexBestFuelParsecs == None else \
                    max(currentNode.fuelParsecs(), currentHexBestFuelParsecs)

                if currentToTargetParsecs == None:
                    currentToTargetParsecs = currentHex.parsecsTo(targetHex)

                targetHexData[currentHex] = \
                    (currentHexBestScore, currentHexBestFuelParsecs, currentToTargetParsecs)

            if progressCallback:
                progressCallback(closedRoutes, False) # Search isn't finished

            potentialsIterator = self._yieldPotentialHexes(
                routingType=routingType,
                currentNode=currentNode,
                targetHex=targetHex,
                shipJumpRating=shipJumpRating,
                shipParsecsWithoutRefuelling=shipParsecsWithoutRefuelling,
                closedSet=targetClosedSet,
                hexData=targetHexData,
                worldManager=worldManager,
                pitCostCalculator=pitCostCalculator,
                hexFilter=hexFilter,
                filterResultCache=filterResultCache)
            possibleRoutes = 0
            addedRoutes = 0
            for potential in potentialsIterator:
                nearbyHex = potential[0]
                nearbyWorld = potential[1]
                nearbyParsecs = potential[2]
                isNearbyFuelWorld = potential[3]
                nearbyHexBestScore = potential[4]
                nearbyHexBestFuelParsecs = potential[5]
                nearbyToTargetMinParsecs = potential[6]
                fuelParsecs = potential[7]
                possibleRoutes += 1

                # Calculate the cost of jumping to the adjacent world
                jumpCost, costContext = jumpCostCalculator.calculate(
                    currentHex=currentHex,
                    currentWorld=currentNode.world(),
                    nextHex=nearbyHex,
                    nextWorld=nearbyWorld,
                    jumpParsecs=nearbyParsecs,
                    costContext=currentNode.costContext())
                if jumpCost == None:
                    continue

                tentativeScore = currentNode.gScore() + jumpCost
                isBetter = (nearbyHexBestScore == None) or \
                    (tentativeScore < nearbyHexBestScore) or \
                    (fuelParsecs > nearbyHexBestFuelParsecs)

                if isBetter:
                    nearbyHexBestScore = tentativeScore \
                        if nearbyHexBestScore == None else \
                        min(tentativeScore, nearbyHexBestScore)

                    nearbyHexBestFuelParsecs = fuelParsecs \
                        if nearbyHexBestFuelParsecs == None else \
                        max(fuelParsecs, nearbyHexBestFuelParsecs)

                    if nearbyToTargetMinParsecs == None:
                        nearbyToTargetMinParsecs = nearbyHex.parsecsTo(targetHex)

                    targetHexData[nearbyHex] = \
                        (nearbyHexBestScore, nearbyHexBestFuelParsecs, nearbyToTargetMinParsecs)

                    # For estimating the cost of the remaining portion of the
                    # route, use min distance from the adjacent world to the
                    # finish going via all remaining waypoints
                    remainingEstimate = jumpCostCalculator.estimate(
                        parsecsToFinish=nearbyToTargetMinParsecs + targetToFinishMinParsecs)

                    newNode = _RouteNode(
                        targetIndex=targetIndex,
                        hex=nearbyHex,
                        world=nearbyWorld,
                        gScore=tentativeScore,
                        fScore=tentativeScore + remainingEstimate,
                        isFuelWorld=isNearbyFuelWorld,
                        fuelParsecs=fuelParsecs,
                        costContext=costContext,
                        parent=currentNode)
                    heapq.heappush(openQueue, newNode)
                    addedRoutes += 1

            closedRoutes += possibleRoutes - addedRoutes

        return None # No route found

    def _yieldPotentialHexes(
            self,
            routingType: RoutingType,
            currentNode: _RouteNode,
            targetHex: travellermap.HexPosition,
            shipJumpRating: int,
            shipParsecsWithoutRefuelling: int,
            closedSet: typing.Set[travellermap.HexPosition],
            hexData: typing.Dict[
                travellermap.HexPosition,
                typing.Tuple[
                    float, # Best gScore for a route reaching this hex
                    int, # Best remaining fuel for a route reaching this hex
                    int # Parsecs from hex to target (note target not necessarily finish)
                ]],
            worldManager: traveller.WorldManager,
            pitCostCalculator: typing.Optional[logic.PitStopCostCalculator],
            hexFilter: typing.Optional[HexFilterInterface] = None,
            filterResultCache: typing.Optional[typing.Dict[travellermap.HexPosition, bool]] = None
            ) -> typing.Generator[
                typing.Tuple[
                    travellermap.HexPosition, # Potential next hex
                    typing.Optional[traveller.World], # World at hex
                    int, # Parsecs from current hex to potential hex
                    bool, # True if potential hex is a fuel world
                    float, # Current best score for potential hex
                    int, # Current best fuel parsecs for potential hex
                    int, # Current best parsecs to target for potential hex
                    int], # Max fuel remaining in tank if ship travels to hex
                None,
                None]:
        # IMPORTANT: When calculating the search radius it's important that it's
        # not clamped by the distance to the target. This might _seem_ like an
        # optimisation but for best cost route optimisation, if the target is a
        # waypoint, it can actually be better to jump to a world that is past
        # the target to refuel then to the target and on to the next world. If
        # it could actually result in a better route depends on a lot of
        # variables (refuelling type of target world, refuelling type of further
        # away but potentially better world, ship fuel capacity etc) and it's
        # only relevant in the case where the target world is within the ships
        # current range so it's not really worth trying to do anything about it.
        if routingType is RoutingType.Basic:
            # Fuel based route calculation is disabled so always search for the
            # full ship jump rating
            searchRadius = shipJumpRating
        else:
            # Set search area based on the max distance we could jump from the
            # current world. If it's a world where fuel could be taken then the
            # search area is the ship jump rating. If it's not a world where
            # fuel can be taken on then the search radius is determined by the
            # amount of fuel in the ship (limited by jump rating)
            if currentNode.isFuelWorld():
                searchRadius = shipJumpRating
            else:
                searchRadius = min(shipJumpRating, currentNode.fuelParsecs())

            # Clamp the search radius to the max parsecs without refuelling.
            # This is required for ships that don't have the fuel capacity to
            # perform their max jump. Not sure when this would actually happen
            # but it should be handled
            searchRadius = min(searchRadius, shipParsecsWithoutRefuelling)
            if searchRadius <= 0:
                return

        currentHex = currentNode.hex()
        alreadyProcessed: typing.Optional[typing.Set[travellermap.HexPosition]] = None
        if routingType is RoutingType.DeadSpace:
            alreadyProcessed = set()

        for nearbyWorld in worldManager.yieldWorldsInRadius(center=currentHex, radius=searchRadius):
            nearbyHex = nearbyWorld.hex()

            if nearbyHex == currentHex:
                # No point processing the current hex again. This assumes the
                # current hex is never the hex. This is done before updating
                # the already processed set as there is no point adding the
                # current hex to the set as the later dead space processing
                # code that uses the set naturally avoids looking at the current
                # hex
                continue

            # Ordering here is important. We only want to take note of worlds
            # that weren't excluded.
            if alreadyProcessed != None:
                alreadyProcessed.add(nearbyHex)

            nearbyParsecs = currentHex.parsecsTo(nearbyHex)

            # Work out the max amount of fuel the ship can have in the tank
            # after completing the jump from the current hex to the nearby hex
            if routingType is RoutingType.Basic:
                # Fuel based route calculation is disabled.
                isNearbyFuelWorld = False
                fuelParsecs = shipJumpRating
            else:
                nearbyRefuellingType = pitCostCalculator.refuellingType(world=nearbyWorld)
                isNearbyFuelWorld = nearbyRefuellingType != None

                if currentNode.isFuelWorld():
                    fuelParsecs = shipParsecsWithoutRefuelling - nearbyParsecs
                else:
                    fuelParsecs = currentNode.fuelParsecs() - nearbyParsecs

                if fuelParsecs < 0:
                    # If the fuel parsecs is negative it means, when following
                    # this route, there is no way to take on enough fuel to
                    # reach the adjacent world
                    continue

                if (not isNearbyFuelWorld) and (fuelParsecs < 1) and (nearbyHex != targetHex):
                    # The nearby world isn't a fuel world and the ship won't
                    # have enough fuel to jump on so there is no point
                    # continuing the route
                    continue

            nearbyHexBestScore, nearbyHexBestFuelParsecs, nearbyToTargetMinParsecs = \
                hexData.get(nearbyHex, (None, None, None))

            # Skip worlds that have already been reached with a BETTER cost
            # unless this route means the ship will have have more fuel for the
            # onward journey. If the adjacent world is a previously processed
            # world but we've found a route with better fuelling potential, the
            # adjacent world will be added to queue with standard g/f scores.
            # This will mean it will be prioritised lower than the previous
            # route that had a better cost but worse fuelling potential. This
            # route will only get further processing if that better cost route
            # fails due to running out of fuel.
            # In the case that fuel based routing is disabled, the new fuel
            # parsecs and best fuel parsecs will always be the ship jump rating
            # (i.e. the same) so the closed worlds set will always be checked.
            isBetter = (nearbyHexBestFuelParsecs == None) or \
                (fuelParsecs > nearbyHexBestFuelParsecs) or \
                (nearbyHex not in closedSet)
            if not isBetter:
                continue

            # If the adjacent world isn't the current target world, check if
            # it's been excluded
            if hexFilter and (nearbyHex != targetHex):
                isMatched = filterResultCache.get(nearbyHex)
                if isMatched == None:
                    isMatched = hexFilter.match(hex=nearbyHex, world=nearbyWorld)
                    filterResultCache[nearbyHex] = isMatched
                if not isMatched:
                    continue # Hex has been excluded

            yield (
                nearbyHex,
                nearbyWorld,
                nearbyParsecs,
                isNearbyFuelWorld,
                nearbyHexBestScore,
                nearbyHexBestFuelParsecs,
                nearbyToTargetMinParsecs,
                fuelParsecs)

        if routingType is RoutingType.DeadSpace:
            nearbyParsecs = 1
            hitTarget = False
            while nearbyParsecs <= searchRadius:
                # Calculate the max fuel the ship can have left in the tank if
                # it jumps to this radius
                if currentNode.isFuelWorld():
                    fuelParsecs = shipParsecsWithoutRefuelling - nearbyParsecs
                else:
                    fuelParsecs = currentNode.fuelParsecs() - nearbyParsecs
                if fuelParsecs < 1:
                    # If the ship jumps to a hex at this radius it won't have
                    # enough fuel in the tank to jump on and this code is only
                    # dealing with dead space hexes so there will be no way to
                    # take on more fuel. As such there is no point in taking
                    # this any further.
                    # If the target hex is a dead space hex within the search
                    # radius it will be processed later due to hitTarget not
                    # being set
                    break

                for nearbyHex in currentHex.yieldRadiusHexes(radius=nearbyParsecs, includeInterior=False):
                    isTarget = nearbyHex == targetHex
                    if isTarget:
                        hitTarget = True

                    # Check if the hex has already been processed due to it
                    # containing a world. If it has been there is no need to
                    # process it again
                    if nearbyHex in alreadyProcessed:
                        continue

                    # If we get to here it means the hex is dead space

                    # Skip hexes that already have a better route. See code that
                    # processes worlds in the search area for more details
                    nearbyHexBestScore, nearbyHexBestFuelParsecs, nearbyToTargetMinParsecs = \
                        hexData.get(nearbyHex, (None, None, None))
                    isBetter = (nearbyHexBestFuelParsecs == None) or \
                        (fuelParsecs > nearbyHexBestFuelParsecs) or \
                        (nearbyHex not in closedSet)
                    if not isBetter:
                        continue

                    # Check if hex is filtered. This check is skipped for the
                    # target as it can't be filtered
                    if hexFilter and not isTarget:
                        isMatched = filterResultCache.get(nearbyHex)
                        if isMatched == None:
                            isMatched = hexFilter.match(hex=nearbyHex, world=None)
                            filterResultCache[nearbyHex] = isMatched
                        if not isMatched:
                            continue # Hex has been excluded

                    yield (
                        nearbyHex,
                        None, # We know this is dead space
                        nearbyParsecs,
                        False, # Dead space is not a fuel world
                        nearbyHexBestScore,
                        nearbyHexBestFuelParsecs,
                        nearbyToTargetMinParsecs,
                        fuelParsecs)

                nearbyParsecs += 1

            if not hitTarget:
                parsecsToTarget = currentHex.parsecsTo(targetHex)
                if parsecsToTarget <= searchRadius:
                    # The target is dead space and is within the specified search
                    # radius but wasn't previously processed

                    # Calculate the max fuel the ship can have left in the tank
                    # once it jumps to this world. As this is the target world
                    # there is no check to see if we could then jump onwards
                    # from the world. If the target is a waypoint and not a fuel
                    # world then this route will naturally be killed of
                    if currentNode.isFuelWorld():
                        fuelParsecs = shipParsecsWithoutRefuelling - parsecsToTarget
                    else:
                        fuelParsecs = currentNode.fuelParsecs() - parsecsToTarget

                    # Skip hexes that already have a better route. See code that
                    # processes worlds in the search area for more details
                    nearbyHexBestScore, nearbyHexBestFuelParsecs, nearbyToTargetMinParsecs = \
                        hexData.get(targetHex, (None, None, None))
                    isBetter = (nearbyHexBestFuelParsecs == None) or \
                        (fuelParsecs > nearbyHexBestFuelParsecs) or \
                        (nearbyHex not in closedSet)
                    if isBetter:
                        yield (
                            targetHex,
                            None, # We know this is dead space
                            parsecsToTarget,
                            False, # Dead space is not a fuel world
                            nearbyHexBestScore,
                            nearbyHexBestFuelParsecs,
                            nearbyToTargetMinParsecs,
                            fuelParsecs)

    def _finaliseRoute(
            self,
            finishNode: _RouteNode,
            progressCount: int,
            progressCallback: typing.Optional[typing.Callable[[int, bool], typing.Any]] = None,
            ) -> logic.JumpRoute:
        # We've found the lowest cost route that goes through all the worlds in the sequence.
        # Process it to generate the final list of route worlds then bail
        path = []

        node = finishNode
        path.append((node.hex(), node.world()))

        while node.parent():
            node = node.parent()
            path.append((node.hex(), node.world()))
        path.reverse()

        if progressCallback:
            progressCallback(progressCount, True) # Search is finished

        return logic.JumpRoute(path)
