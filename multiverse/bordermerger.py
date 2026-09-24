import collections
import itertools
import math
import multiverse
import typing

# TODO: I probably need a healing step that fills in missing hexes if there are
# any in a border path that aren't adjacent (probably just do shorted path to the
# next hex). It will be important for editing borders that they are all in a
# canonical format
# - IMPORTANT: This needs done to simple borders that aren't getting merged as well
# - It should probably also remove duplicate points and make sure they loop

# TODO: Create a Traveller Map PR to update borders
# - I need to update other milieu before doing this

def _pathWithoutClosingHex(
        path: typing.Sequence[typing.Tuple[int, int]]
        ) -> typing.List[typing.Tuple[int, int]]:
    result = list(path)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return result

def _pointOnSegment(
        point: typing.Tuple[float, float],
        start: typing.Tuple[int, int],
        end: typing.Tuple[int, int]
        ) -> bool:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > 1e-9:
        return False
    return min(x1, x2) <= px <= max(x1, x2) and \
        min(y1, y2) <= py <= max(y1, y2)

def _pointInPath(
        point: typing.Tuple[float, float],
        path: typing.Sequence[typing.Tuple[int, int]]
        ) -> bool:
    inside = False
    for index, start in enumerate(path):
        end = path[(index + 1) % len(path)]
        if _pointOnSegment(point, start, end):
            return True

        startX, startY = start
        endX, endY = end
        if (startY > point[1]) != (endY > point[1]):
            crossingX = (endX - startX) * (point[1] - startY) / \
                (endY - startY) + startX
            if point[0] < crossingX:
                inside = not inside
    return inside

def _pathIsInside(
        inner: typing.Sequence[typing.Tuple[int, int]],
        outer: typing.Sequence[typing.Tuple[int, int]]) -> bool:
    return all(_pointInPath(point, outer) for point in inner)

def _pathArea(path: typing.Sequence[typing.Tuple[int, int]]) -> int:
    return abs(sum(
        path[index][0] * path[(index + 1) % len(path)][1] -
        path[(index + 1) % len(path)][0] * path[index][1]
        for index in range(len(path))))

# Holes are inserted by generating two vertical columns of parallel hexes
# that run upwards from the upper most edge of the hole to the edge of the
# boundary above it. One of the columns is the inward join and is ordered
# from the border to the hole, the other column is the outward join and runs
# from the hole back out to the border. It works on the assumption that the
# border hexes are wound clockwise and define the hexes around the inner edge
# of the border and hole hexes are wound anti-clockwise and define the border
# round the outer edge of the hole.
# Due to the nature of the flat topped hexes used in Traveller and the fact
# holes define the hexes around the outer border of the hole. We know that
# the hexes defining a hole always cover an area at least 3 hexes wide, 1
# hex for a minimum width hole and one hex either side defining the outline.
def _insertHole(
        border: typing.Sequence[typing.Tuple[int, int]],
        hole: typing.Sequence[typing.Tuple[int, int]]
        ) -> typing.Tuple[int, int]:
    borderLength = len(border)
    holeLength = len(hole)

    def loopBorderIndex(index) -> typing.Tuple[int, int]:
        return index % borderLength

    def loopHoleIndex(index) -> typing.Tuple[int, int]:
        return index % holeLength

    # Find the hex on the hole to connect the inward join column to. This
    # will be the most upper hole hex (minimum y value) that doesn't have
    # the same x value as the previous hex.
    # Hexes that have the same x value as the previous are ignored as the
    # algorithm requires 2 hexes on the hole, one for the inward join column
    # to connect to and one for the outward join column to connect to. The
    # algorithm uses the hole prior to the inward join hex as the outward
    # join hex so these hexes must have different x values, otherwise the 2
    # join columns would be coincident and the generated border would be
    # invalid
    inHoleIndex = None
    inHoleHex = None
    prevHoleX = hole[-1][0]
    for index, hex in enumerate(hole):
        if hex[0] == prevHoleX:
            continue
        prevHoleX = hex[0]

        if inHoleHex is not None and  hex[1] >= inHoleHex[1]:
            continue

        inHoleIndex = index
        inHoleHex = hex
    if inHoleHex is None:
        raise RuntimeError('No hole ingoing join hex found')

    # Find the border hex to connect the inward join column to. This is the
    # closest hex that is directly above the inward hole hex. If there are
    # multiple hexes on the border that are directly above the hex and have
    # the same distance (i.e. the same hex appears twice in the border), use
    # the one where the hexes that will join the outward path to the border
    # make a triangle with a clockwise winding.
    # Handling the inward border hex appearing multiple times in the border
    # is important as it can happen if the inward border hex is at the base
    # of a single hex wide column that extends upwards out the border. In
    # this case we want to connect the inward column to the apex of the
    # corner that winds anti-clockwise out of the column and the outward
    # join column will connect to the point after it. The result of this is
    # the new border hex list will continue to wind anti-clockwise into the
    # column as before but where it previously wound anti-clock out of the
    # column it will continue vertically down to the start of the hole, then
    # on the way out of the hole the join will wind clockwise back into the
    # border.
    inBorderIndex = None
    inBorderHex = None
    closestDistance = None
    for index, hex in enumerate(border):
        if hex[0] != inHoleHex[0] or hex[1] > inHoleHex[1]:
            # This border hex is not directly above the hole hex so ignore it
            continue

        distance = inHoleHex[1] - hex[1]
        if closestDistance is not None:
            if distance > closestDistance:
                continue
            elif distance == closestDistance:
                outWinding = multiverse.calculateTriangleWinding(
                    (inHoleHex[0] + 1, inHoleHex[1] + 1),
                    (inHoleHex[0] + 1, inHoleHex[1]),
                    border[loopBorderIndex(index)])
                if outWinding is multiverse.PathWinding.Clockwise:
                    # The current inward border hex would result in the outward
                    # join path winding clockwise into the border so use it rather
                    # than whatever this new hex is
                    continue

        inBorderIndex = index
        inBorderHex = hex
        closestDistance = distance
    if inBorderIndex is None:
        raise RuntimeError('No outer ingoing join hex found')

    # Generate the inward join path (ordered from border down to hole).
    inJoinX = inHoleHex[0]
    inJoinPath = [(inJoinX, y) for y in range(inBorderHex[1] + 1, inHoleHex[1])]

    # Generate the outward join path. this is done by stepping upwards
    # until we hit a hex that is adjacent to the outward border hex
    outHoleIndex = loopHoleIndex(inHoleIndex - 1)
    outHoleHex = hole[outHoleIndex]
    outBorderIndex = loopBorderIndex(inBorderIndex + 1)
    outBorderHex = border[outBorderIndex]
    outJoinPath = []
    currentJoinY = outHoleHex[1] - 1
    while currentJoinY > outBorderHex[1]:
        currentJoinHex = (outHoleHex[0], currentJoinY)
        outJoinPath.append(currentJoinHex)
        distance = multiverse.parsecsBetweenAbsoluteSpace(
            currentJoinHex,
            outBorderHex)
        if distance <= 1:
            break

        currentJoinY -= 1

    # Generate the border path with the hole inserted. This is ordered
    joinedPath = []
    if inBorderIndex < outBorderIndex:
        joinedPath.extend(border[:outBorderIndex])
    else:
        joinedPath.extend(border[inBorderIndex:])

    if inJoinPath:
        joinedPath.extend(inJoinPath)
    elif hole[inHoleIndex] == border[inBorderIndex]:
        # The inward hole and border hexes are coincident so remove
        # the inward border hex to avoid duplicates
        joinedPath.pop()

    joinedPath.extend(hole[inHoleIndex:])
    joinedPath.extend(hole[:inHoleIndex])

    if outJoinPath:
        joinedPath.extend(outJoinPath)
    elif hole[outHoleIndex] == border[outBorderIndex]:
        # The outward hole and border hexes are coincident so remove
        # the outward hole hex to avoid duplicates
        joinedPath.pop()

    if inBorderIndex < outBorderIndex:
        joinedPath.extend(border[outBorderIndex:])
    else:
        joinedPath.extend(border[:inBorderIndex])

    return joinedPath

# TODO: This can probably be optimised a LOT
# - I think there are a couple of additional assumptions I can make that may simplify things
#   - As the hexes for define the hexes that surround the hole, they must define a polygon with
#     an area, otherwise there would be no hole. This means holes always have an anti-clockwise
#     winding, they can't have no winding
#   - Borders with no winding can just be added to the output list with no further processing.
#     as stated above, they can't be holes as holes must have a winding, they also can't be
#     borders that will need holes inserted as they have no area so can't contain a hole
# - Winding is calculated multiple times for each polygon
# - The area of each border is calculated multiple times
# - In the majority of cases we can take an early out if all borders have a
# clockwise winding. We need to continue if they have an anti-clockwise winding
# (as they are known holes) _OR_ if they have no winding (as they may be holes)
# - When inserting a hole there is a check to see if the path needs to be
# reversed but I don't think it ever will (or it always will). As borders always
# have clockwise winding and holes always have anti-clockwise, I think holes
# are naturally in the correct order to be inserted
def _mergeLayerHoles(
        borders: typing.Sequence[multiverse.DbBorder]
        ) -> typing.List[multiverse.DbBorder]:
    paths = [_pathWithoutClosingHex(border.hexes()) for border in borders]
    parents: typing.List[typing.Optional[int]] = [None] * len(paths)

    for childIndex, childPath in enumerate(paths):
        containing = []
        for parentIndex, parentPath in enumerate(paths):
            if childIndex == parentIndex or _pathArea(parentPath) <= _pathArea(childPath):
                continue
            if multiverse.calculatePathWinding(parentPath) != multiverse.PathWinding.Clockwise or \
                    multiverse.calculatePathWinding(childPath) != multiverse.PathWinding.AntiClockwise:
                continue
            if _pathIsInside(childPath, parentPath):
                containing.append(parentIndex)
        if containing:
            parents[childIndex] = min(containing, key=lambda index: _pathArea(paths[index]))

    depths: typing.List[int] = []
    for pathIndex in range(len(paths)):
        depth = 0
        parentIndex = parents[pathIndex]
        while parentIndex is not None:
            depth += 1
            parentIndex = parents[parentIndex]
        depths.append(depth)

    result = []
    for pathIndex, path in enumerate(paths):
        if depths[pathIndex] % 2 != 0:
            continue

        hasHole = False
        for holeIndex, holePath in enumerate(paths):
            if parents[holeIndex] != pathIndex:
                continue

            path = _insertHole(path, holePath)
            hasHole = True

        if not hasHole:
            # No holes inserted so just use the original border
            result.append(borders[pathIndex])
            continue

        if path[-1] != path[0]:
            path.append(path[0])
        border = borders[pathIndex]
        result.append(multiverse.DbBorder(
            hexes=path,
            allegianceId=border.allegianceId(),
            style=border.style(),
            colour=border.colour(),
            label=border.label(),
            labelWorldX=border.labelWorldX(),
            labelWorldY=border.labelWorldY(),
            showLabel=border.showLabel(),
            wrapLabel=border.wrapLabel()))
    return result

def mergeBorders(
        borders: typing.Mapping[
            typing.Tuple[int, int], # Sector position
            typing.Collection[multiverse.DbBorder]],
        allegiances: typing.Mapping[
            str,
            multiverse.DbAllegiance]
        ) -> typing.List[multiverse.DbBorder]:
    merged: typing.List[multiverse.DbBorder] = []

    # TODO: The fact I removed allegiance from the key will probably cause issues for "Smade's Planet" (Solomani Rim)
    # as it will likely get detected as a hole in the larger border as it ends up on the same layer as it's the
    # same colour (but a different allegiance)
    layerToSegmentsMap: typing.Dict[
        typing.Tuple[
            typing.Optional[str], # Style
            typing.Optional[str]], # Colour
        typing.List[typing.Tuple[
            int, # Number of hexes inside the sector
            typing.List[typing.Tuple[int, int]]]]
        ] = {}

    for (sectorX, sectorY), sectorBorders in borders.items():
        sectorMinX, sectorMinY = multiverse.relativeSpaceToAbsoluteSpace((sectorX, sectorY, 1, 1))
        sectorMaxX = sectorMinX + (multiverse.SectorWidth - 1)
        sectorMaxY = sectorMinY + (multiverse.SectorHeight - 1)

        for border in sectorBorders:
            hexes = border.hexes()

            # For the hole insertion algorithm to work, border outlines need to have
            # clockwise winding and holes need to have anti-clockwise winding. This
            # is enforced by making sure the input borders have clockwise winding
            if multiverse.calculatePathWinding(hexes) is multiverse.PathWinding.AntiClockwise:
                hexes = list(reversed(hexes))

            start = 0
            count = len(hexes)

            if count > 1 and hexes[0] == hexes[count - 1]:
                count -= 1

            # Ignore any out of bounds hexes at the start of the border path
            for x, y in hexes:
                if x >= sectorMinX and x <= sectorMaxX and y >= sectorMinY and y <= sectorMaxY:
                    break
                start += 1

            if start >= count:
                # The sector is completely inside the border so its part of the border
                # can be ignored
                continue

            # If the border extends outside the sector, split the border path into segments
            # that are inside the sector with just the last hex being outside the sector. The
            # idea is this last point should be the start of a segment of the same border
            # defined in another sector.
            segments = []
            segmentPath = []
            internalCount = 0
            hasOOB = False
            isSimple = True
            for index in range(start, count):
                hex = hexes[index]
                x, y = hex
                if x >= sectorMinX and x <= sectorMaxX and y >= sectorMinY and y <= sectorMaxY:
                    if hasOOB:
                        segmentPath.append(hex)
                        segments.append((internalCount, segmentPath))
                        segmentPath = []
                        internalCount = 0
                        hasOOB = False
                    segmentPath.append(hex)
                    internalCount += 1
                    continue

                segmentPath.append(hex)
                hasOOB = True
                isSimple = False

            if start > 0:
                segmentPath.extend(itertools.islice(hexes, 0, start))
                isSimple = False

            if segmentPath:
                segmentPath.append(hexes[start])
                segments.append((internalCount, segmentPath))

            if not isSimple:
                style = border.style()
                colour = border.colour()

                allegianceId = border.allegianceId()
                if allegianceId is not None:
                    allegiance = allegiances.get(allegianceId)
                    if allegiance is None:
                        raise RuntimeError(f'Unknown allegiance {allegianceId}')
                    if style is None:
                        style = allegiance.borderStyle()
                    if colour is None:
                        colour = allegiance.borderColour()

                layer = (style, colour)
                layerSegments = layerToSegmentsMap.get(layer)
                if layerSegments is None:
                    layerSegments = []
                    layerToSegmentsMap[layer] = layerSegments
                layerSegments.extend(segments)
            else:
                merged.append(border)

    for (style, colour), segments in layerToSegmentsMap.items():
        layerMerged: typing.List[multiverse.DbBorder] = []
        startHexToSegmentMap: typing.Dict[
            typing.Tuple[int, int],
            typing.Tuple[
                int,
                typing.List[typing.Tuple[int, int]]]
            ] = {}
        for segment in segments:
            internalCount, segmentPath = segment
            startHex = segmentPath[0]
            if startHex in startHexToSegmentMap:
                # TODO: Not sure what is best to do here. It should never happen with valid
                # data but borders in the stock sectors can get messed up
                raise RuntimeError(f'Duplicate start position {startHex}')

            startHexToSegmentMap[startHex] = segment

        while startHexToSegmentMap:
            try:
                startHex = next(iter(startHexToSegmentMap))
                segment = startHexToSegmentMap.pop(startHex)
                internalCount, segmentPath = segment

                currentHex = startHex
                borderPath = list(segmentPath)
                confirmedCount = internalCount
                while True:
                    currentHex = borderPath[confirmedCount]
                    if currentHex == startHex:
                        if confirmedCount < len(borderPath):
                            # Drop any pending points from the path
                            borderPath = borderPath[:confirmedCount + 1]
                        break
                    segment = startHexToSegmentMap.pop(currentHex, None)
                    if segment is None:
                        lastIndex = len(borderPath) - 1
                        if lastIndex > confirmedCount:
                            confirmedCount = lastIndex
                            #confirmedCount += 1
                            continue

                        raise RuntimeError(f'Incomplete path at {currentHex}')

                    internalCount, segmentPath = segment
                    borderPath = borderPath[:confirmedCount]
                    borderPath.extend(segmentPath)
                    confirmedCount += internalCount

                if borderPath:
                    layerMerged.append(multiverse.DbBorder(
                        hexes=borderPath,
                        # TODO: Allegiance is being lost
                        allegianceId=None,
                        style=style,
                        colour=colour,
                        # TODO: Label information is being lost
                        label=None,
                        labelWorldX=None,
                        labelWorldY=None,
                        showLabel=False,
                        wrapLabel=False))
            except Exception as ex:
                # TODO: Better logging
                print(str(ex))

        merged.extend(_mergeLayerHoles(layerMerged))

    return merged

def _chooseBestNextIndex(
        path: typing.Sequence[typing.Tuple[int, int]],
        pathLength: int,
        currentIndex: int,
        optionIndices: typing.Collection[typing.Tuple[int, int]]
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
            currentHex,
            optionHex,
            followingHex)
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
        path: typing.Sequence[typing.Tuple[int, int]],
        pathLength: int,
        startIndex: int,
        startEdge: multiverse.HexEdge,
        hexOccurrenceMap: typing.Dict[
            typing.Tuple[int, int],
            typing.List[int]],
        ) -> typing.Tuple[
            typing.List[typing.Tuple[int, int]], # Outline hexes
            typing.Optional[typing.List[typing.Tuple[int, int]]]]: # Joint indices
    def loopPathIndex(index) -> typing.Tuple[int, int]:
        return index % pathLength

    seenIndices = set()

    currentIndex = startIndex
    currentEdge = startEdge
    currentHex = path[currentIndex]
    outline = []
    joints = None
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
            neighbourHex = multiverse.absoluteNeighbourHex(hex=currentHex, edge=searchEdge)
            if neighbourHex in hexOccurrenceMap:
                nextHex = neighbourHex
                nextEdge = multiverse.clockwiseHexEdge(multiverse.oppositeHexEdge(searchEdge))
                break
            searchEdge = multiverse.clockwiseHexEdge(searchEdge)
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

# Split a hex list that defines a polygon into a hex list that defines the
# outer border of the polygon and, if there are any, a list of hex lists
# that define the holes in the polygon.
# The input path is expected to be wound clockwise and specify the hexes
# running along the INSIDE edge of the polygon. The output border and holes
# will be wound clockwise. The border will specify the hexes running along
# the INSIDE edge of the border and the holes will specify the hexes running
# along the OUTSIDE edge of the hole
def extractHexRings(
        path: typing.Sequence[typing.Tuple[int, int]]
        ) -> typing.Tuple[
            typing.Sequence[typing.Tuple[int, int]],
            typing.Optional[typing.Collection[typing.Sequence[typing.Tuple[int, int]]]]]:
    pathLength = len(path)
    if pathLength > 1 and path[0] == path[-1]:
        pathLength -= 1

    if pathLength <= 1:
        return (path, None)

    def loopPathIndex(index) -> typing.Tuple[int, int]:
        return index % pathLength

    hexOccurrenceMap: typing.Dict[
        typing.Tuple[int, int],
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

        if (startHex is None) or (currentHex[0] < startHex[0]) or (currentHex[0] == startHex[0] and currentHex[1] > startHex[1]):
            winding = multiverse.calculateTriangleWinding(
                prevHex,
                currentHex,
                nextHex)
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
        startEdge=multiverse.HexEdge.BottomLeft,
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
        enterEdge = multiverse.connectingEdge(path[currentIndex], path[inIndex])
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
            exitEdge = multiverse.connectingEdge(currentHex, path[nextIndex])
            if exitEdge is None:
                print(f'No hole connecting edge found {path}')
                return (path, None)

            # Loop clockwise around the neighbours of the current hex starting at the
            # edge after after the edge where it connects to the previous hex. If we
            # find an empty hex before we hit the edge where it connects to the next
            # hex, then we've found our hole
            checkEdge = multiverse.clockwiseHexEdge(enterEdge)
            while checkEdge != exitEdge:
                neighbourHex = multiverse.absoluteNeighbourHex(currentHex, checkEdge)
                if neighbourHex not in hexOccurrenceMap:
                    holeStartIndex = currentIndex
                    holeStartEdge = checkEdge
                    break
                checkEdge = multiverse.clockwiseHexEdge(checkEdge)

            if holeStartIndex is not None:
                break

            currentIndex = nextIndex
            enterEdge = multiverse.oppositeHexEdge(exitEdge)

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