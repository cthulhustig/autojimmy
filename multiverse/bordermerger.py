import collections
import itertools
import multiverse
import typing

# TODO: I probably need a healing step that fills in missing hexes if there are
# any in a border path that aren't adjacent (probably just do shorted path to the
# next hex). It will be important for editing borders that they are all in a
# canonical format
# - IMPORTANT: This needs done to simple borders that aren't getting merged as well
# - It should probably also remove duplicate points and make sure they loop

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
        outer: typing.Sequence[typing.Tuple[int, int]]
        ) -> bool:
    for point in inner:
        if not _pointInPath(point, outer):
            return False
    return True

def _pathArea(path: typing.Sequence[typing.Tuple[int, int]]) -> int:
    return abs(sum(
        path[index][0] * path[(index + 1) % len(path)][1] -
        path[(index + 1) % len(path)][0] * path[index][1]
        for index in range(len(path))))

def _hexNeighbours(
        hex: typing.Tuple[int, int]
        ) -> typing.Iterable[typing.Tuple[int, int]]:
    hexX, hexY = hex
    yield (hexX, hexY - 1)
    yield (hexX, hexY + 1)
    yield (hexX - 1, hexY + (0 if hexX % 2 else -1))
    yield (hexX - 1, hexY + (0 if hexX % 2 else 1))
    yield (hexX + 1, hexY + (0 if hexX % 2 else -1))
    yield (hexX + 1, hexY + (0 if hexX % 2 else 1))

def _triangleWinding(a: tuple[int, int],
                    b: tuple[int, int],
                    c: tuple[int, int]) -> typing.Optional[multiverse.PathWinding]:
    cross = ((b[0] - a[0]) * (c[1] - a[1])
           - (b[1] - a[1]) * (c[0] - a[0]))

    if cross > 0:
        return multiverse.PathWinding.Clockwise
    elif cross < 0:
        return multiverse.PathWinding.AntiClockwise

    return None

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
                outWinding = _triangleWinding(
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
