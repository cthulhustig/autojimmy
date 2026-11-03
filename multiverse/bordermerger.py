import common
import itertools
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

# TODO: Why is the border containing Reina in M1120 drawn as blue now when it used
# to be grey

class Segment(object):
    def __init__(
            self,
            hexes: typing.List[typing.Tuple[int, int]]
            ) -> None:
        self._hexes = hexes

    def hexes(self) -> typing.Sequence[typing.Tuple[int, int]]:
        return self._hexes

    def startHex(self) -> typing.Tuple[int, int]:
        return self._hexes[0]

    def finishHex(self) -> typing.Tuple[int, int]:
        return self._hexes[-1]

    def __iter__(self) -> typing.Iterator[typing.Tuple[int, int]]:
        return self._hexes.__iter__()

    def __next__(self) -> typing.Tuple[int, int]:
        return self._hexes.__next__()

    def __len__(self) -> int:
        return self._hexes.__len__()

    def __getitem__(self, key: int) -> typing.Tuple[int, int]:
        return self._hexes.__getitem__(key)

class Path(object):
    def __init__(
            self,
            hexes: typing.Optional[typing.List[typing.Tuple[int, int]]] = None
            ) -> None:
        self._hexes = hexes if hexes is not None else []

    def hexes(self) -> typing.Sequence[typing.Tuple[int, int]]:
        return self._hexes

    def stitchSegment(self, segment: Segment) -> typing.Tuple[int, int]:
        # NOTE: The last hex in a segment is the starting hex of the next
        # segment so don't include it when when generating the merged segment
        self._hexes.extend(itertools.islice(segment, 0, len(segment) - 1))
        return segment.finishHex()

    def appendHexes(self, hexes: typing.Sequence[typing.Tuple[int, int]]) -> None:
        self._hexes.extend(hexes)

    def createLoop(self) -> None:
        if self._hexes[0] != self._hexes[-1]:
            self._hexes.append(self._hexes[0])

    def removeLoop(self) -> None:
        if len(self._hexes) > 1 and self._hexes[0] == self._hexes[-1]:
            self._hexes.pop()

    def __iter__(self) -> typing.Iterator[typing.Tuple[int, int]]:
        return self._hexes.__iter__()

    def __next__(self) -> typing.Tuple[int, int]:
        return self._hexes.__next__()

    def __len__(self) -> int:
        return self._hexes.__len__()

    def __getitem__(self, key: int) -> typing.Tuple[int, int]:
        return self._hexes.__getitem__(key)

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

def _canonicalisePath(
        path: typing.Sequence[typing.Tuple[int, int]]
        ) -> typing.Sequence[typing.Tuple[int, int]]:
    # For the hole insertion algorithm to work, border outlines need to have
    # clockwise winding and holes need to have anti-clockwise winding. This
    # is enforced by making sure the input borders have clockwise winding
    if multiverse.calculatePathWinding(path) is multiverse.PathWinding.AntiClockwise:
        path = list(path)

    return path

def _createPathSegments(
        path: typing.Sequence[typing.Tuple[int, int]],
        sectorMinX: int,
        sectorMinY: int,
        sectorMaxX: int,
        sectorMaxY: int,
        oobHexes: typing.Set[typing.Tuple[int, int]]
        ) -> typing.Optional[typing.List[Segment]]:
    count = len(path)
    if count > 1 and path[0] == path[count - 1]:
        count -= 1 # Ignore path looping

    # If the border extends outside the sector, split the border path into segments
    # that are inside the sector with just the last hex being outside the sector. The
    # idea is this last point should be the start of a segment of the same border
    # defined in another sector.
    segments: typing.List[Segment] = []
    hexes = []
    isSimple = True
    for index in range(count):
        hex = path[index]
        x, y = hex
        if x >= sectorMinX and x <= sectorMaxX and y >= sectorMinY and y <= sectorMaxY:
            hexes.append(hex)
        else:
            if hexes:
                # NOTE: Include the first oob hex so we know which start hex to look
                # for in the next segment (i.e. a segment from an adjacent sector).
                hexes.append(hex)

                segments.append(Segment(hexes=hexes))
                hexes = []

            oobHexes.add(hex)
            isSimple = False

    if isSimple:
        # The border is completely contained within the sector so there is no need
        # to merge it
        return None

    # Complete the outstanding segment
    if hexes:
        # NOTE: Add the start hex at the end of the path. The merging algorithm
        # expects the last hex in the segment to be the start hex of the next
        # segment.
        hexes.append(path[0])
        segments.append(Segment(hexes=hexes))

    return segments

def _createSegmentStartMap(
        segments: typing.Iterable[Segment]
        ) -> typing.Dict[
            typing.Tuple[int, int],
            typing.List[Segment]]:
    startHexToSegmentMap: typing.Dict[
        typing.Tuple[int, int],
        typing.List[Segment]] = {}
    for segment in segments:
        startHex = segment.startHex()
        hexSegments = startHexToSegmentMap.get(startHex)
        if hexSegments is None:
            hexSegments = []
            startHexToSegmentMap[startHex] = hexSegments
        hexSegments.append(segment)

    return startHexToSegmentMap

# Find the segment containing the hex with the lowest x value, if
# there are multiple with the same x value, select the one with
# the lowest y value. Doing this causes the algorithm to work from
# top to bottom, left to right. This is important for some corner
# cases when walking oob data such as the borders either side of
# Mount in M1120.
# NOTE: This assumes there is at least 1 segment in startHexToSegmentMap
def _findStartSegment(
        startHexToSegmentMap: typing.Dict[
            typing.Tuple[int, int],
            typing.List[Segment]],
        ) -> Segment:
    startSegment = None
    minHex = None
    for segments in startHexToSegmentMap.values():
        for segment in segments:
            for hex in segment:
                if minHex is None or (hex[0] < minHex[0]) or (hex[0] == minHex[0] and hex[1] < minHex[1]):
                    startSegment = segment
                    minHex = hex
    startHex = startSegment[0]

    segments = startHexToSegmentMap[startHex]
    segments.remove(startSegment)
    if not segments:
        del startHexToSegmentMap[startHex]

    return startSegment

# Find the segment(s) that start at the new current hex. It's rare
# but there can be multiple segments that start at the same hex (see
# (76, -79) in M1120). When walking, if there is more than one segment
# with the same start hex, we want the one where the next hex after
# the start hex is closest clockwise from the last hex on the merged
# border
def _findNextSegment(
        prevHex: typing.Tuple[int, int],
        currentHex: typing.Tuple[int, int],
        startHexToSegmentMap: typing.Dict[
            typing.Tuple[int, int],
            typing.List[Segment]],
        ) -> Segment:
    possibleSegments = startHexToSegmentMap.get(currentHex)
    if not possibleSegments:
        raise RuntimeError(f'No segment was found starting at {currentHex}')

    if len(possibleSegments) == 1:
        # There is only one segment starting at the current hex so use it
        nextSegment = possibleSegments.pop()
    else:
        # There are multiple segments starting at the current hex so find
        # the one that is closest clockwise
        enterEdge = multiverse.connectingEdge(currentHex, prevHex)
        if enterEdge is None:
            raise RuntimeError(f'Hexes ({prevHex}) ({currentHex}) are not adjacent')

        nextEdge = multiverse.clockwiseHexEdge(enterEdge)
        segmentIndex = None
        while segmentIndex is None and nextEdge != enterEdge:
            nextHex = multiverse.absoluteNeighbourHex(currentHex, nextEdge)
            for index, segment in enumerate(possibleSegments):
                if segment[1] == nextHex:
                    segmentIndex = index
                    break
            nextEdge = multiverse.clockwiseHexEdge(nextEdge)

        if segmentIndex is None:
            raise RuntimeError(f'No valid next segment found for {currentHex}')
        nextSegment = possibleSegments.pop(segmentIndex)

    if not possibleSegments:
        del startHexToSegmentMap[currentHex]

    return nextSegment

# This walks the OOB hexes to find the path to the next segment, adding hexes to
# the border as it goes. If the walk finds the next segment, the starting hex for
# that segment is returned. If the walk finds the finish hex, None is returned.
def _walkOutOfBoundsPath(
        startHex: typing.Tuple[int, int],
        entryEdge: multiverse.HexEdge,
        oobHexes: typing.Set[typing.Tuple[int, int]],
        finishHex: typing.Tuple[int, int],
        startHexToSegmentMap: typing.Dict[
            typing.Tuple[int, int],
            typing.List[Segment]],
        borderPath: Path,
        ) -> typing.Tuple[int, int]:
    startEdge = entryEdge
    currentHex = startHex
    currentEdge = startEdge
    reentryHex = None
    walkHexes = []
    seenHexes = set()
    while True:
        walkHexes.append(currentHex)

        # Start at the first edge clockwise from the edge we walked into the
        # current hex and loop round clockwise checking if the neighbour hex
        # is the start of a segment or the finish. If it is, the walk is done
        checkEdge = currentEdge
        while True:
            checkEdge = multiverse.clockwiseHexEdge(checkEdge)
            neighbourHex = multiverse.absoluteNeighbourHex(currentHex, checkEdge)

            if neighbourHex == finishHex:
                reentryHex = neighbourHex # We've walked all the way to the finish
                break

            nextSegment = startHexToSegmentMap.get(neighbourHex)
            if nextSegment:
                reentryHex = neighbourHex # We've walked to the next segment
                break

            if checkEdge is currentEdge:
                break

        if reentryHex is not None:
            break

        # We didn't find the start of a segment or the finish so perform
        # the same loop around the edges of the current hex but this time
        # loop for an oob hex to continue the walk. This is done as a
        # separate pass after looking for a segment/finish as those should
        # take priority, even if there is an oob hex that is closer to the
        # entry edge in looping order. This is important for correctly
        # handling Irrgh Manifest, Glory of Taarskoerzn & Dzarrgh Federate
        # in M1120. They are meant to be 3 separate borders but would get
        # merged if we checked for oob as we looped round the edges looking
        # for a segment/finish rather than checking oob afterwards
        checkEdge = multiverse.clockwiseHexEdge(currentEdge)
        nextHex = None
        while checkEdge != currentEdge:
            neighbourHex = multiverse.absoluteNeighbourHex(currentHex, checkEdge)

            if neighbourHex in oobHexes and neighbourHex not in seenHexes:
                # We've found another out of bounds hex so walk to it
                seenHexes.add(neighbourHex)
                nextHex = neighbourHex
                break

            checkEdge = multiverse.clockwiseHexEdge(checkEdge)

        if nextHex is None:
            if currentHex == startHex:
                # We're on the start hex but haven't been able to find a next hex
                raise RuntimeError(f'No oob path found from {startHex}')

            # The current path walk has ended without finding a segment to connect
            # to or the finish. There may still be an alternate oob path going of
            # of a different edge on the start hex. Reset the path walk to the
            # start and try the next clockwise edge round the start hex.
            # This can happen when merging other borders on the same layer that are
            # touching has left small sections of oob data that don't go anywhere
            # (example merging the First Fleet of Dzo and Antares Pact borders from
            # Lishun and Antares in M1200)
            walkHexes.clear()
            startEdge = multiverse.clockwiseHexEdge(startEdge)
            currentHex = startHex
            currentEdge = startEdge
            continue

        currentHex = nextHex
        currentEdge = multiverse.oppositeHexEdge(checkEdge)

    borderPath.appendHexes(walkHexes)
    return reentryHex

def _stitchNextPath(
        startHexToSegmentMap: typing.Dict[
            typing.Tuple[int, int],
            typing.List[Segment]],
        oobHexes: typing.Set[typing.Tuple[int, int]],
        usedSegments: typing.Optional[typing.List[Segment]]
        ) -> Path:
    segment = _findStartSegment(startHexToSegmentMap=startHexToSegmentMap)
    startHex = segment.startHex()

    stitchedPath = Path()
    while True:
        currentHex = stitchedPath.stitchSegment(segment)

        # Hexes that are in the segment we just added might also appear in
        # the oob hex path, for example, when a border spans multiple sectors,
        # the start hex of the segment from one sector should always be in
        # the oob hexes added for the sector it connects to. By removing the
        # hexes after adding the segment it prevents oob path walks from
        # connecting back oob hexes that have already been used by a segment.
        # It's important not to remove the oob hex at the end of the segment
        # as it needs to be present in order for the oob hex walk to work.
        # This is needed to correctly merge cases like where the Antares Pact
        # border spanning Lishun and Antares in M1120
        oobHexes.difference_update(itertools.islice(segment, 0, len(segment) - 1))

        # Take note of the border that was just used
        if usedSegments is not None:
            usedSegments.append(segment)

        # If there is no segment starting at the current hex we need
        # to perform a path search in the oob hexes to try and find
        # the next segment. There is no need to do this if we've
        # already looped back to the start hex
        if currentHex not in startHexToSegmentMap and currentHex != startHex:
            if currentHex not in oobHexes:
                raise RuntimeError(f'Next hex {currentHex} is not in oob hexes')

            pervHex = stitchedPath[-1]
            enterEdge = multiverse.connectingEdge(currentHex, pervHex)
            if enterEdge is None:
                raise RuntimeError(f'Hexes ({pervHex}) ({currentHex}) are not adjacent')

            currentHex = _walkOutOfBoundsPath(
                startHex=currentHex,
                entryEdge=enterEdge,
                oobHexes=oobHexes,
                finishHex=startHex,
                startHexToSegmentMap=startHexToSegmentMap,
                borderPath=stitchedPath)

        # Check if we've looped back to the start. It's important to check
        # there is no other segment remaining in the segment map as there
        # could be multiple segments that start at the hex we started
        # walking from and we we've only hit the finish if we've processed
        # all of them
        if currentHex == startHex and currentHex not in startHexToSegmentMap:
            break

        segment = _findNextSegment(
            prevHex=stitchedPath[-1],
            currentHex=currentHex,
            startHexToSegmentMap=startHexToSegmentMap)

    return stitchedPath

def _findHoles(
        paths: typing.Collection[Path]
        ) -> typing.Dict[
            Path, # Parent
            typing.List[Path]]: # Holes
    results: typing.Dict[Path, typing.List[Path]] = {}

    # Hole paths have an anti-clockwise winding and are extremely rare.
    # Check there are any before doing anything to expensive
    windings = [multiverse.calculatePathWinding(path) for path in paths]
    hasHoles = False
    for winding in windings:
        if winding == multiverse.PathWinding.AntiClockwise:
            hasHoles = True
            break
    if not hasHoles:
        return results

    parents: typing.List[typing.Optional[int]] = [None] * len(paths)

    areas = [_pathArea(path) for path in paths]
    for childIndex, childPath in enumerate(paths):
        if windings[childIndex] != multiverse.PathWinding.AntiClockwise:
            continue

        containing: typing.List[int] = []
        for parentIndex, parentPath in enumerate(paths):
            if childIndex == parentIndex or areas[parentIndex] <= areas[childIndex]:
                continue
            if windings[parentIndex] != multiverse.PathWinding.Clockwise:
                continue
            if _pathIsInside(childPath, parentPath):
                containing.append(parentIndex)
        if containing:
            parents[childIndex] = min(containing, key=lambda index: areas[index])

    depths: typing.List[int] = []
    for parentIndex in range(len(paths)):
        depth = 0
        parentIndex = parents[parentIndex]
        while parentIndex is not None:
            depth += 1
            parentIndex = parents[parentIndex]
        depths.append(depth)

    for parentIndex, parentPath in enumerate(paths):
        if depths[parentIndex] % 2 != 0:
            continue

        holes = None
        for holeIndex, holePath in enumerate(paths):
            if parents[holeIndex] != parentIndex:
                continue

            if holes is None:
                holes = []
            holes.append(holePath)

        if holes:
            results[parentPath] = holes

    return results

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
def _insertHole(path: Path, hole: Path) -> Path:
    borderLength = len(path)
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
    for index, hex in enumerate(path):
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
                    path[loopBorderIndex(index)])
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

    # Generate the outward join path. This needs to be a full path search as
    # the out path needs to work around the in path
    outHoleIndex = loopHoleIndex(inHoleIndex - 1)
    outHoleHex = hole[outHoleIndex]
    outBorderIndex = loopBorderIndex(inBorderIndex + 1)
    outBorderHex = path[outBorderIndex]
    avoidHexes = set(inJoinPath)
    outJoinPath = multiverse.pathSearch(
        start=outHoleHex,
        target=outBorderHex,
        neighboursFn=lambda hex: [n for n in [multiverse.absoluteNeighbourHex(hex, e) for e in multiverse.HexEdge] if n not in avoidHexes])
    # Remove the outHoleHex and outBorderHex from the path
    outJoinPath = outJoinPath[1:-1]

    # Generate the border path with the hole inserted. This is ordered
    joinedPath: typing.List[typing.Tuple[int, int]] = []
    if inBorderIndex < outBorderIndex:
        joinedPath.extend(path[:outBorderIndex])
    else:
        joinedPath.extend(path[inBorderIndex:])

    if inJoinPath:
        joinedPath.extend(inJoinPath)
    elif hole[inHoleIndex] == path[inBorderIndex]:
        # The inward hole and border hexes are coincident so remove
        # the inward border hex to avoid duplicates
        joinedPath.pop()

    joinedPath.extend(hole[inHoleIndex:])
    joinedPath.extend(hole[:inHoleIndex])

    if outJoinPath:
        joinedPath.extend(outJoinPath)
    elif hole[outHoleIndex] == path[outBorderIndex]:
        # The outward hole and border hexes are coincident so remove
        # the outward hole hex to avoid duplicates
        joinedPath.pop()

    if inBorderIndex < outBorderIndex:
        joinedPath.extend(path[outBorderIndex:])
    else:
        joinedPath.extend(path[:inBorderIndex])

    return Path(hexes=joinedPath)

def _mergeAllegiances(
        usedBorders: typing.Collection[multiverse.DbBorder],
        allegianceMapper: multiverse.AllegianceMapper
        ) -> typing.Optional[multiverse.DbAllegiance]:
    usedAllegiances: typing.Optional[typing.Set[multiverse.DbAllegiance]] = None
    for border in usedBorders:
        allegianceId = border.allegianceId()
        if not allegianceId:
            continue

        allegiance = allegianceMapper.allegianceById(allegianceId)
        if allegiance:
            if usedAllegiances is None:
                usedAllegiances = set()

            usedAllegiances.add(allegiance)

    if not usedAllegiances:
        return None

    if len(usedAllegiances) == 1:
        return next(iter(usedAllegiances))

    allegianceUsages = common.InstanceCounter()
    for allegiance in usedAllegiances:
        baseCode = allegiance.base()
        if baseCode is None:
            continue

        baseAllegiance = allegianceMapper.lookupAllegiance(code=baseCode)
        if baseAllegiance is None:
            # TODO: This should log and continue
            print(f'No allegiance for base code {baseCode}')
            continue

        allegianceUsages.add(baseAllegiance)

        mostCommon = allegianceUsages.max()
        if len(mostCommon) == 1:
            # The allegiances all have the same base allegiance so use it
            return next(iter(allegianceUsages))

        for allegiance in usedAllegiances:
            isPartialName = True
            for otherAllegiance in usedAllegiances:
                if allegiance is otherAllegiance:
                    continue

                if not otherAllegiance.name().startswith(allegiance.name()):
                    isPartialName = False
                    break
            if isPartialName:
                # All the allegiance names start with the current allegiance name
                # so use it. This is working on the assumption this name is
                # something like "Comsentient Alliance" and the other names are
                # something like "Comsentient Alliance, Eslyat Magistracy"
                return allegiance

        return None

def _mergeBorderLabels(
        borders: typing.Collection[multiverse.DbBorder],
        ) -> typing.Optional[typing.List[multiverse.DbBorderLabel]]:
    mergedLabels = None
    for border in borders:
        labels = border.labels()
        if not labels:
            continue

        if mergedLabels is None:
            mergedLabels = []

        for label in labels:
            mergedLabels.append(multiverse.DbBorderLabel(
                worldX=label.worldX(),
                worldY=label.worldY(),
                text=label.text(),
                allegianceId=label.allegianceId(),
                show=label.show(),
                wrap=label.wrap()))

    return mergedLabels

def _mergeRegionLabels(
        regions: typing.Collection[multiverse.DbRegion],
        ) -> typing.Optional[typing.List[multiverse.DbRegionLabel]]:
    mergedLabels = None
    for region in regions:
        labels = region.labels()
        if not labels:
            continue

        if mergedLabels is None:
            mergedLabels = []

        for label in labels:
            mergedLabels.append(multiverse.DbRegionLabel(
                worldX=label.worldX(),
                worldY=label.worldY(),
                text=label.text(),
                show=label.show(),
                wrap=label.wrap()))

    return mergedLabels

def mergeBorders(
        borders: typing.Mapping[
            typing.Tuple[int, int], # Sector position
            typing.Collection[multiverse.DbBorder]],
        allegianceMapper: multiverse.AllegianceMapper
        ) -> typing.List[multiverse.DbBorder]:
    outputBorders: typing.List[multiverse.DbBorder] = []

    layerDataMap: typing.Dict[
        typing.Tuple[
            typing.Optional[str], # Style
            typing.Optional[str]], # Colour
        typing.Tuple[
            typing.List[Segment],
            typing.Set[typing.Tuple[int, int]] # OOB Hexes
        ]] = {}
    segmentToBorderMap: typing.Dict[Segment, multiverse.DbBorder] = {}

    for (sectorX, sectorY), sectorBorders in borders.items():
        sectorMinX, sectorMinY = multiverse.relativeSpaceToAbsoluteSpace((sectorX, sectorY, 1, 1))
        sectorMaxX = sectorMinX + (multiverse.SectorWidth - 1)
        sectorMaxY = sectorMinY + (multiverse.SectorHeight - 1)

        for border in sectorBorders:
            style = border.style()
            colour = border.colour()

            allegianceId = border.allegianceId()
            if allegianceId is not None:
                allegiance = allegianceMapper.allegianceById(allegianceId)
                if allegiance is None:
                    raise RuntimeError(f'Unknown allegiance {allegianceId}')
                if style is None:
                    style = allegiance.borderStyle()
                if colour is None:
                    colour = allegiance.borderColour()

            layer = (style, colour)
            layerData = layerDataMap.get(layer)
            if layerData is None:
                layerData = (list(), set())
                layerDataMap[layer] = layerData
            layerSegments, layerOOBHexes = layerData

            path = _canonicalisePath(path=border.hexes())
            segments = _createPathSegments(
                path=path,
                sectorMinX=sectorMinX,
                sectorMinY=sectorMinY,
                sectorMaxX=sectorMaxX,
                sectorMaxY=sectorMaxY,
                oobHexes=layerOOBHexes)
            if segments is None:
                # Border doesn't need merging
                outputBorders.append(border)
                continue

            layerSegments.extend(segments)
            for segment in segments:
                segmentToBorderMap[segment] = border

    for (style, colour), (segments, oobHexes) in layerDataMap.items():
        # Merge the segments on this layer until there are no more to merge
        startHexToSegmentMap = _createSegmentStartMap(segments=segments)
        pathToSegmentsMap: typing.Dict[Path, typing.List[Segment]] = {}
        while startHexToSegmentMap:
            try:
                usedSegments: typing.List[Segment] = []
                stitchedPath = _stitchNextPath(
                    startHexToSegmentMap=startHexToSegmentMap,
                    oobHexes=oobHexes,
                    usedSegments=usedSegments)

                pathToSegmentsMap[stitchedPath] = usedSegments
            except Exception as ex:
                # TODO: Better logging
                print(str(ex))

        parentToHolesMap = _findHoles(pathToSegmentsMap.keys())
        for path, holes in parentToHolesMap.items():
            try:
                holyPath = path
                for hole in holes:
                    holyPath = _insertHole(path=holyPath, hole=hole)

                # Combine the segments for the path and holes into a master list of segments
                # for the new path, removing the entries for the old path and the holes as
                # we go.
                segments = pathToSegmentsMap.pop(path)
                for hole in holes:
                    segments.extend(pathToSegmentsMap.pop(hole))
                pathToSegmentsMap[holyPath] = segments
            except Exception as ex:
                # TODO: Better logging
                print(str(ex))

        for path, segments in pathToSegmentsMap.items():
            try:
                path.createLoop() # Loop the path

                # Generate the list of sector borders that were merged to make
                # this border.
                usedBorders: typing.Set[multiverse.DbBorder] = set()
                for segment in segments:
                    border = segmentToBorderMap.get(segment)
                    if border is not None:
                        usedBorders.add(border)

                # Determine which allegiance to use for the border
                mergedAllegiance = _mergeAllegiances(
                    usedBorders=usedBorders,
                    allegianceMapper=allegianceMapper)

                # Generate list of labels from the used borders
                mergedLabels = _mergeBorderLabels(
                    borders=usedBorders)

                # Create the merged border
                outputBorders.append(multiverse.DbBorder(
                    hexes=path.hexes(),
                    allegianceId=mergedAllegiance.id() if mergedAllegiance else None,
                    style=style,
                    colour=colour,
                    labels=mergedLabels))
            except Exception as ex:
                # TODO: Better logging
                print(str(ex))

    return outputBorders

def mergeRegions(
        regions: typing.Mapping[
            typing.Tuple[int, int], # Sector position
            typing.Collection[multiverse.DbRegion]],
        ) -> typing.List[multiverse.DbRegion]:
    outputRegions: typing.List[multiverse.DbRegion] = []

    layerDataMap: typing.Dict[
        typing.Optional[str], # Colour
        typing.Tuple[
            typing.List[Segment],
            typing.Set[typing.Tuple[int, int]] # OOB Hexes
        ]] = {}

    segmentToRegionMap: typing.Dict[Segment, multiverse.DbRegion] = {}

    for (sectorX, sectorY), sectorRegions in regions.items():
        sectorMinX, sectorMinY = multiverse.relativeSpaceToAbsoluteSpace((sectorX, sectorY, 1, 1))
        sectorMaxX = sectorMinX + (multiverse.SectorWidth - 1)
        sectorMaxY = sectorMinY + (multiverse.SectorHeight - 1)

        for region in sectorRegions:
            colour = region.colour()

            layerData = layerDataMap.get(colour)
            if layerData is None:
                layerData = (list(), set())
                layerDataMap[colour] = layerData
            layerSegments, layerOOBHexes = layerData

            path = _canonicalisePath(path=region.hexes())
            segments = _createPathSegments(
                path=path,
                sectorMinX=sectorMinX,
                sectorMinY=sectorMinY,
                sectorMaxX=sectorMaxX,
                sectorMaxY=sectorMaxY,
                oobHexes=layerOOBHexes)
            if segments is None:
                # Border doesn't need merging
                outputRegions.append(region)
                continue

            layerSegments.extend(segments)
            for segment in segments:
                segmentToRegionMap[segment] = region

    for colour, (segments, oobHexes) in layerDataMap.items():
        # Merge the segments on this layer until there are no more to merge
        startHexToSegmentMap = _createSegmentStartMap(segments=segments)
        pathToSegmentsMap: typing.Dict[Path, typing.List[Segment]] = {}
        while startHexToSegmentMap:
            try:
                usedSegments: typing.List[Segment] = []
                stitchedPath = _stitchNextPath(
                    startHexToSegmentMap=startHexToSegmentMap,
                    oobHexes=oobHexes,
                    usedSegments=usedSegments)

                pathToSegmentsMap[stitchedPath] = usedSegments
            except Exception as ex:
                # TODO: Better logging
                print(str(ex))

        parentToHolesMap = _findHoles(pathToSegmentsMap.keys())
        for path, holes in parentToHolesMap.items():
            try:
                holyPath = path
                for hole in holes:
                    holyPath = _insertHole(path=holyPath, hole=hole)

                # Combine the segments for the path and holes into a master list of segments
                # for the new path, removing the entries for the old path and the holes as
                # we go.
                segments = pathToSegmentsMap.pop(path)
                for hole in holes:
                    segments.extend(pathToSegmentsMap.pop(hole))
                pathToSegmentsMap[holyPath] = segments
            except Exception as ex:
                # TODO: Better logging
                print(str(ex))

        for path, segments in pathToSegmentsMap.items():
            try:
                path.createLoop() # Loop the path

                # Generate the list of sector borders that were merged to make
                # this border.
                usedRegions: typing.Set[multiverse.DbRegion] = set()
                for segment in segments:
                    region = segmentToRegionMap.get(segment)
                    if region is not None:
                        usedRegions.add(region)

                # Generate list of labels from the used borders
                mergedLabels = _mergeRegionLabels(
                    regions=usedRegions)

                # Create the merged border
                outputRegions.append(multiverse.DbRegion(
                    hexes=path.hexes(),
                    colour=colour,
                    labels=mergedLabels))
            except Exception as ex:
                # TODO: Better logging
                print(str(ex))

    return outputRegions