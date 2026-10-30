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
            typing.List[typing.Tuple[int, int]]],
        borderPath: typing.List[typing.Tuple[int, int]],
        ) -> typing.Tuple[int, int]:
    startEdge = entryEdge
    currentHex = startHex
    currentEdge = startEdge
    reentryHex = None
    walkPath = []
    seenHexes = set()
    while True:
        walkPath.append(currentHex)

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
            walkPath.clear()
            startEdge = multiverse.clockwiseHexEdge(startEdge)
            currentHex = startHex
            currentEdge = startEdge
            continue

        currentHex = nextHex
        currentEdge = multiverse.oppositeHexEdge(checkEdge)

    borderPath.extend(walkPath)
    return reentryHex

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

    # Generate the outward join path. This needs to be a full path search as
    # the out path needs to work around the in path
    outHoleIndex = loopHoleIndex(inHoleIndex - 1)
    outHoleHex = hole[outHoleIndex]
    outBorderIndex = loopBorderIndex(inBorderIndex + 1)
    outBorderHex = border[outBorderIndex]
    avoidHexes = set(inJoinPath)
    outJoinPath = multiverse.pathSearch(
        start=outHoleHex,
        target=outBorderHex,
        neighboursFn=lambda hex: [n for n in [multiverse.absoluteNeighbourHex(hex, e) for e in multiverse.HexEdge] if n not in avoidHexes])
    # Remove the outHoleHex and outBorderHex from the path
    outJoinPath = outJoinPath[1:-1]

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
            # NOTE: Use the same id as the border the hole was merged into as it
            # is effectively replacing the old border. This means we can re-use
            # the labels from the old border rather than having to create copies.
            # If we didn't use the same id we'd get an exception saying the labels
            # were already attached to another border.
            id=border.id(),
            hexes=path,
            allegianceId=border.allegianceId(),
            style=border.style(),
            colour=border.colour(),
            labels=border.labels()))
    return result

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

def _mergeLabels(
        usedBorders: typing.Collection[multiverse.DbBorder],
        ) -> typing.Optional[typing.List[multiverse.DbBorderLabel]]:
    labels = None
    for border in usedBorders:
        borderLabels = border.labels()
        if not borderLabels:
            continue

        if labels is None:
            labels = []

        for label in borderLabels:
            labels.append(multiverse.DbBorderLabel(
                worldX=label.worldX(),
                worldY=label.worldY(),
                text=label.text(),
                allegianceId=label.allegianceId(),
                show=label.show(),
                wrap=label.wrap()))

    return labels

def mergeBorders(
        borders: typing.Mapping[
            typing.Tuple[int, int], # Sector position
            typing.Collection[multiverse.DbBorder]],
        allegianceMapper: multiverse.AllegianceMapper
        ) -> typing.List[multiverse.DbBorder]:
    merged: typing.List[multiverse.DbBorder] = []

    segmentStartToBorderMap: typing.Dict[
        typing.Tuple[int, int],
        multiverse.DbBorder
        ] = {}

    # TODO: The fact I removed allegiance from the key is known to cause an issue for a
    # border in M1120. Bersha and Courage are different allegiances and should be under
    # different borders (VIrM - Irrgh Manifest and VGoT - Glory of Taarskoerzn). I think
    # it was a problem for the big Imperial border in M1105 as parts of that borders have
    # different imperium based allegiances depending on which sector your in.I think the
    # thing to do might be to add allegiance back in but if the allegiance has a base
    # code, use it instead of the full code
    layerDataMap: typing.Dict[
        typing.Tuple[
            typing.Optional[str], # Style
            typing.Optional[str]], # Colour
        typing.Tuple[
            typing.List[typing.List[typing.Tuple[int, int]]], # Path Segment Hexes
            typing.Set[typing.Tuple[int, int]] # OOB Hexes
        ]] = {}

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

            count = len(hexes)
            if count > 1 and hexes[0] == hexes[count - 1]:
                count -= 1

            # If the border extends outside the sector, split the border path into segments
            # that are inside the sector with just the last hex being outside the sector. The
            # idea is this last point should be the start of a segment of the same border
            # defined in another sector.
            segments = []
            segment = []
            oobHexes = set()
            isSimple = True
            for index in range(count):
                hex = hexes[index]
                x, y = hex
                if x >= sectorMinX and x <= sectorMaxX and y >= sectorMinY and y <= sectorMaxY:
                    segment.append(hex)
                else:
                    if segment:
                        # NOTE: Include the first oob hex so we know which start hex to look
                        # for in the next segment (i.e. a segment from an adjacent sector).
                        segment.append(hex)

                        segments.append(segment)
                        segment = []

                    oobHexes.add(hex)
                    isSimple = False

            if isSimple:
                # The border is completely contained within the sector so there is no need
                # to merge it
                merged.append(border)
                continue

            # Complete the outstanding segment
            if segment:
                # NOTE: Add the start hex at the end of the path. The merging algorithm
                # expects the last hex in the segment to be the start hex of the next
                # segment.
                segment.append(hexes[0])
                segments.append(segment)

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
            layerSegments.extend(segments)
            layerOOBHexes.update(oobHexes)

            for segment in segments:
                segmentStartToBorderMap[segment[0]] = border

    for (style, colour), (segments, oobHexes) in layerDataMap.items():
        layerMerged: typing.List[multiverse.DbBorder] = []

        # Generate mapping of start position to segment. It's rare but
        # there can be multiple segments that start at the same hex
        # (see (76, -79) in M1120). When walking, if there is more than
        # on segment with the same start hex, the one where the second
        # hex in the segment is the closest clockwise to the hex that
        # was walked pervious to the segment start hex should be used
        # first. When choosing the start segment for the walk, if there
        # are multiple segments at the chosen start hex, it doesn't
        # mater which segment is used
        startHexToSegmentMap: typing.Dict[
            typing.Tuple[int, int],
            typing.List[typing.List[typing.Tuple[int, int]]]
            ] = {}
        for segment in segments:
            startHex = segment[0]

            hexSegments = startHexToSegmentMap.get(startHex)
            if hexSegments is None:
                hexSegments = []
                startHexToSegmentMap[startHex] = hexSegments
            hexSegments.append(segment)

        while startHexToSegmentMap:
            try:
                # Start with the segment that has the lowest x value, if there are
                # multiple segments with the same x, choose the one with the lowest
                # y value.
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

                mergedPath: typing.List[typing.Tuple[int, int]] = []
                usedBorders: typing.Set[multiverse.DbBorder] = set()
                segment = startSegment
                while True:
                    # NOTE: The last hex in a segment is the starting hex of the next
                    # segment so don't include it when when generating the merged segment
                    mergedPath.extend(itertools.islice(segment, 0, len(segment) - 1))
                    currentHex = segment[-1]

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

                    segmentBorder = segmentStartToBorderMap.get(segment[0])
                    if segmentBorder is not None:
                        usedBorders.add(segmentBorder)

                    # If there is no segment starting at the current hex we need
                    # to perform a path search in the oob hexes to try and find
                    # the next segment. There is no need to do this if we've
                    # already looped back to the start hex
                    if currentHex not in startHexToSegmentMap and currentHex != startHex:
                        if currentHex not in oobHexes:
                            raise RuntimeError(f'Next hex {currentHex} is not in oob hexes')

                        pervHex = mergedPath[-1]
                        enterEdge = multiverse.connectingEdge(currentHex, pervHex)
                        if enterEdge is None:
                            raise RuntimeError(f'Hexes ({pervHex}) ({currentHex}) are not adjacent')

                        currentHex = _walkOutOfBoundsPath(
                            startHex=currentHex,
                            entryEdge=enterEdge,
                            oobHexes=oobHexes,
                            finishHex=startHex,
                            startHexToSegmentMap=startHexToSegmentMap,
                            borderPath=mergedPath)

                    # Check if we've looped back to the start. It's important to
                    # check there is no other segment remaining in the segment map
                    # as there could be multiple segments that start at the hex
                    # we started walking from and we we've only hit the finish if
                    # we've processed all of them
                    if currentHex == startHex and currentHex not in startHexToSegmentMap:
                        break

                    possibleSegments = startHexToSegmentMap.get(currentHex)
                    if not possibleSegments:
                        raise RuntimeError(f'No segment was found starting at {currentHex}')

                    if len(possibleSegments) == 1:
                        segment = possibleSegments.pop()
                    else:
                        pervHex = mergedPath[-1]
                        enterEdge = multiverse.connectingEdge(currentHex, pervHex)
                        if enterEdge is None:
                            raise RuntimeError(f'Hexes ({pervHex}) ({currentHex}) are not adjacent')

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
                        segment = possibleSegments.pop(segmentIndex)

                    if not possibleSegments:
                        del startHexToSegmentMap[currentHex]

                if not mergedPath:
                    continue # No path so nothing to do

                # Loop the path
                mergedPath.append(mergedPath[0])

                # Determine which allegiance to use for the border
                mergedAllegiance = _mergeAllegiances(
                    usedBorders=usedBorders,
                    allegianceMapper=allegianceMapper)

                # Create final border labels merged from all borders that were
                # merged to create it
                mergedLabels = _mergeLabels(
                    usedBorders=usedBorders)

                # Create the merged border
                layerMerged.append(multiverse.DbBorder(
                    hexes=mergedPath,
                    allegianceId=mergedAllegiance.id() if mergedAllegiance else None,
                    style=style,
                    colour=colour,
                    labels=mergedLabels))
            except Exception as ex:
                # TODO: Better logging
                print(str(ex))

        merged.extend(_mergeLayerHoles(layerMerged))

    return merged
