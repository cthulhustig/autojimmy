import astronomer
import multiverse
import typing

def _chooseBestNextIndex(
        path: typing.Sequence[astronomer.HexPosition],
        pathLength: int,
        currentIndex: int,
        optionIndices: typing.Collection[int]
        ) -> int:
    if len(optionIndices) == 1:
        return optionIndices[0]

    currentHex = path[currentIndex]

    # Sort the option indices so they're ordered from nearest to furthest
    # from the current index.
    optionIndices = sorted(optionIndices, key=lambda index: (index - currentIndex) % pathLength)

    optionData: typing.List[typing.Tuple[
        int, # Option index
        multiverse.PathWinding # Option winding
        ]] = []
    for optionIndex in optionIndices:
        optionHex = path[optionIndex]
        followingHex = path[(optionIndex + 1) % pathLength]
        winding = multiverse.calculateTriangleWinding(
            currentHex.absolute(),
            optionHex.absolute(),
            followingHex.absolute())
        optionData.append((optionIndex, winding))

    # First check for next indices that would result in an anti-clockwise triangle
    for option in optionData:
        if option[1] is multiverse.PathWinding.AntiClockwise:
            return option[0]

    # Now check for where the next index would be collinear
    for option in optionData:
            if option[1] is not None:
                continue

            followingHex = path[(option[0] + 1) % pathLength]
            if followingHex != currentHex:
                return option[0]

    # Finally check for next indices that would result in a clockwise triangle
    for option in optionData:
        if option[1] is multiverse.PathWinding.Clockwise:
            return option[0]

    # TODO: I don't think this should ever happen with a valid input hex list.
    # If we get to here it means the hexes that follow each of the option hexes
    # is the same as the current hex (i.e. they would all cause the path being
    # generated to double back on itself), doubling back is valid (trivial
    # example of three hexes stacked vertically, hex order would be top, middle
    # bottom, middle, top), but it shouldn't be possible for there ever to be
    # multiple options that all result in doubling back
    # TODO: Probably shouldn't have this in the final release
    assert(False)

def _tracePathOutline(
        path: typing.Sequence[astronomer.HexPosition],
        pathLength: int,
        startIndex: int,
        startEdge: astronomer.HexEdge,
        hexOccurrenceMap: typing.Dict[
            astronomer.HexPosition,
            typing.List[int]],
        ) -> typing.Tuple[
            typing.List[astronomer.HexPosition], # Outline hexes
            typing.Optional[typing.List[typing.Tuple[int, int]]]]: # Joint indices
    def loopPathIndex(index) -> int:
        return index % pathLength

    seenIndices = set()

    currentIndex = startIndex
    currentEdge = startEdge
    currentHex = path[currentIndex]
    outline: typing.List[astronomer.HexPosition] = []
    joints: typing.Optional[typing.List[typing.Tuple[int, int]]] = None
    while True:
        if currentIndex in seenIndices:
            # TODO: Better error message?
            raise ValueError('Path is re-entrant')

        outline.append(currentHex)
        seenIndices.add(currentIndex)

        searchEdge = currentEdge
        nextHex = None
        nextEdge = None
        while True:
            neighbourHex = currentHex.neighbour(searchEdge)
            if neighbourHex in hexOccurrenceMap:
                nextHex = neighbourHex
                nextEdge = astronomer.clockwiseHexEdge(astronomer.oppositeHexEdge(searchEdge))
                break
            searchEdge = astronomer.clockwiseHexEdge(searchEdge)
            if searchEdge is currentEdge:
                break

        if nextHex is None:
            # We've reached the end of the outline
            break

        nextIndex = _chooseBestNextIndex(
            path=path,
            pathLength=pathLength,
            currentIndex=currentIndex,
            optionIndices=hexOccurrenceMap[nextHex])

        # If the next index isn't a simple increment of the current index it
        # means we're stepping over the point a hole is being joined to the
        # rest of the path _or_ a hole has looped back to the start. If it's
        # not a hole looping back to the start, add the indices to the list
        # of holes to be processed.
        if nextIndex != loopPathIndex(currentIndex + 1):
            # This transition is stepping over the point a hole is jointed
            # to the rest of the path
            if joints is None:
                joints = []
            joints.append((currentIndex, nextIndex))

        if nextIndex == startIndex:
            break

        currentIndex = nextIndex
        currentEdge = nextEdge
        currentHex = nextHex

    outline.append(outline[0])

    return (outline, joints)

# Split a complex border/region style hex path into a hex list that defines
# the outer border and, if there are any, a list of hex lists that define
# the holes in it.
# The input path is expected to be wound CLOCKWISE and specify the hexes
# running along the INSIDE edge of the area. The input path can be self
# touching but not self intersecting.
# The output border is also wound CLOCKWISE and specifies the hexes running
# along the INSIDE edge. Holes are wound ANTI-CLOCKWISE and specify the
# hexes running along the OUTSIDE edge of the hole.
def decomposeHexPath(
        path: typing.Sequence[astronomer.HexPosition]
        ) -> typing.Tuple[
            typing.Sequence[astronomer.HexPosition],
            typing.Optional[typing.Collection[typing.Sequence[astronomer.HexPosition]]]]:
    pathLength = len(path)
    if pathLength > 1 and path[0] == path[-1]:
        pathLength -= 1

    if pathLength <= 1:
        return (path, None)

    def loopPathIndex(index) -> int:
        return index % pathLength

    # Find a starting hex for tracing the outer border. This needs to be a hex
    # that is on the outer edge of the polygon being processed (i.e. it can't
    # be a hex that is part of a hole or part of an 'internal' self touching
    # edge). To achieve this we find the hex that is positioned lowest in the
    # left most column, due y increasing downwards this is the hex with the
    # lowest x and largest y value.
    # Hexes can legitimately occur multiple times in a path (simple example,
    # 2 hexes stacked on top of each other have a a valid path of (0, 0),
    # (0, -1), (0, 0). In this case there are multiple options of where in
    # the path we start, which we choose doesn't matter so the first is used.
    hexOccurrenceMap: typing.Dict[
        typing.Tuple[astronomer.HexPosition],
        typing.List[int]
        ] = {}
    startIndex = None
    startHex = None
    for index in range(pathLength):
        currentHex = path[index]
        occurrences = hexOccurrenceMap.get(currentHex)
        if occurrences is None:
            occurrences = []
            hexOccurrenceMap[currentHex] = occurrences
        occurrences.append(index)

        prevHex = path[loopPathIndex(index - 1)]
        nextHex = path[loopPathIndex(index + 1)]

        if ((startHex is None) or
            (currentHex.absoluteX() < startHex.absoluteX()) or
            (currentHex.absoluteX() == startHex.absoluteX() and currentHex.absoluteY() > startHex.absoluteY())):
            winding = multiverse.calculateTriangleWinding(
                prevHex.absolute(),
                currentHex.absolute(),
                nextHex.absolute())
            if winding is not multiverse.PathWinding.AntiClockwise:
                startIndex = index
                startHex = currentHex

    if startHex is None:
        # TODO: Do something better
        print(f'No start found {path}')
        return (path, None)

    outline, joints = _tracePathOutline(
        path=path,
        pathLength=pathLength,
        startIndex=startIndex,
        startEdge=astronomer.HexEdge.BottomLeft,
        hexOccurrenceMap=hexOccurrenceMap)
    if not joints:
        # There are no joints so no holes, just return the generated outline
        return (outline, None)

    # Given well formed data, checking for all previously seen joints shouldn't
    # be required, all we really care about is not adding joints for holes if
    # they're the reverse of the joint being processed. However, a badly formed
    # input path could result in an infinite loop so we check all joints
    seenJoints = set()

    holes = None
    while joints:
        joint = joints.pop()
        inIndex, outIndex = joint
        seenJoints.add(joint)
        seenJoints.add((outIndex, inIndex))

        # Find the start of the hole. To do this we follow the path from the in join
        # index until we hit a hex where the in and out join paths split apart to
        # allow space for the hole. We can detect where this by working clockwise
        # from the edge after the edge the hex was entered on until we hit the
        # edge the hex will be exited on, if any of the hexes neighbouring those
        # edges are not on the path, then this hex is the start of a hole
        currentIndex = loopPathIndex(inIndex + 1)
        # NOTE: Order of arguments is important when calling connectingEdge as we
        # want the edge relative to the current hex
        enterEdge = path[currentIndex].connectingEdge(path[inIndex])
        if enterEdge is None:
            # TODO: Do something better
            print(f'No hole start edge found {path}')
            return (path, None)
        holeStartIndex = None
        holeStartEdge = None
        while currentIndex != outIndex:
            currentHex = path[currentIndex]

            nextIndex = loopPathIndex(currentIndex + 1)
            # NOTE: Order of arguments is important when calling connectingEdge as we
            # want the edge relative to the current hex
            exitEdge = currentHex.connectingEdge(path[nextIndex])
            if exitEdge is None:
                print(f'No hole connecting edge found {path}')
                return (path, None)

            # Loop clockwise around the neighbours of the current hex starting at the
            # edge after after the edge where it connects to the previous hex. If we
            # find an empty hex before we hit the edge where it connects to the next
            # hex, then we've found our hole
            checkEdge = astronomer.clockwiseHexEdge(enterEdge)
            while checkEdge != exitEdge:
                neighbourHex = currentHex.neighbour(checkEdge)
                if neighbourHex not in hexOccurrenceMap:
                    holeStartIndex = currentIndex
                    holeStartEdge = checkEdge
                    break
                checkEdge = astronomer.clockwiseHexEdge(checkEdge)

            if holeStartIndex is not None:
                break

            currentIndex = nextIndex
            enterEdge = astronomer.oppositeHexEdge(exitEdge)

        if holeStartIndex is None:
            # No hole was found at the end of the join. This could happen if inward
            # join path just doubles back and connects to the outward join hex. This
            # is a completely redundant portion of the path so can just be ignored.
            continue

        hole, newJoints = _tracePathOutline(
            path=path,
            pathLength=pathLength,
            startIndex=holeStartIndex,
            startEdge=holeStartEdge,
            hexOccurrenceMap=hexOccurrenceMap)
        if holes is None:
            holes = []
        holes.append(hole)

        if newJoints:
            for newJoint in newJoints:
                if newJoint not in seenJoints:
                    joints.append(newJoint)

    return (outline, holes)