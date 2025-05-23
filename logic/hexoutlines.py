import travellermap
import typing

_HalfHexHeight = 0.5
_HalfHexMinWidth = (0.5 - travellermap.HexWidthOffset) * travellermap.ParsecScaleX
_HalfHexMaxWidth = (0.5 + travellermap.HexWidthOffset) * travellermap.ParsecScaleX

def _findStartingHex(
        hexes: typing.Iterable[travellermap.HexPosition]
        ) -> typing.Tuple[travellermap.HexPosition, typing.Optional[travellermap.HexEdge]]:
    # Find the hex with the lowest x value, if there are multiple with the
    # same x value, find the one with the largest y value. This finds a hex
    # that is guaranteed to be on the edge of a group of hexes. Visually
    # this will be the lowest hex on the left most row of hexes
    bestHex = None
    for hex in hexes:
        if bestHex == None:
            bestHex = hex
        elif hex.absoluteX() < bestHex.absoluteX():
            bestHex = hex
        elif hex.absoluteX() == bestHex.absoluteX() and hex.absoluteY() > bestHex.absoluteY():
            bestHex = hex

    # Find the edge to start processing on. This is the most anticlockwise
    # edge that doesn't have an adjacent hex. Due to the way the code above
    # works we know that there can only be adjacent hexes along the upper,
    # upper right and lower right edges. If this wasn't true then this
    # wouldn't be the hex with the lowest x value and largest y value.
    hex = bestHex.neighbourHex(edge=travellermap.HexEdge.LowerRight)
    if hex in hexes:
        return (bestHex, travellermap.HexEdge.Lower)
    hex = bestHex.neighbourHex(edge=travellermap.HexEdge.UpperRight)
    if hex in hexes:
        return (bestHex, travellermap.HexEdge.LowerRight)
    hex = bestHex.neighbourHex(edge=travellermap.HexEdge.Upper)
    if hex in hexes:
        return (bestHex, travellermap.HexEdge.UpperRight)
    return (bestHex, None) # This hex has no adjacent hexes so it's outline is the outline

def _floodRemove(
        hex: travellermap.HexPosition,
        hexes: typing.Set[travellermap.HexPosition]
        ) -> None:
    # Remove all hexes that touch hex, then remove all hexes that touch those hexes,
    # repeat until nothing else to remove (although there may still be hexes left on
    # the list)
    todo = [hex]
    hexes.remove(hex)
    while todo:
        hex = todo.pop(0)
        for edge in travellermap.HexEdge:
            adjacent = hex.neighbourHex(edge=edge)
            if adjacent in hexes:
                hexes.remove(adjacent)
                todo.append(adjacent)


_AntiClockwiseOffsets = {
    travellermap.HexEdge.Upper: (-_HalfHexMinWidth, _HalfHexHeight),
    travellermap.HexEdge.UpperRight: (_HalfHexMinWidth, _HalfHexHeight),
    travellermap.HexEdge.LowerRight: (_HalfHexMaxWidth, 0),
    travellermap.HexEdge.Lower: (_HalfHexMinWidth, -_HalfHexHeight),
    travellermap.HexEdge.LowerLeft: (-_HalfHexMinWidth, -_HalfHexHeight),
    travellermap.HexEdge.UpperLeft: (-_HalfHexMaxWidth, 0)
}

# Return the most anticlockwise point on the given edge
def _getAntiClockwisePoint(
        hex: travellermap.HexPosition,
        edge: travellermap.HexEdge
        ) -> typing.Tuple[float, float]:
    x, y = hex.mapSpace()
    offsetX, offsetY = _AntiClockwiseOffsets[edge]
    return (x + offsetX, y + offsetY)

# Return the outline of a single hex in map space
def _getHexOutline(
        hex: travellermap.HexPosition
        ) -> typing.Iterable[typing.Tuple[float, float]]:
    x, y = hex.mapSpace()
    return [
        (x - _HalfHexMinWidth, y - _HalfHexHeight),
        (x + _HalfHexMinWidth, y - _HalfHexHeight),
        (x + _HalfHexMaxWidth, y),
        (x + _HalfHexMinWidth, y + _HalfHexHeight),
        (x - _HalfHexMinWidth, y + _HalfHexHeight),
        (x - _HalfHexMaxWidth, y)
    ]


# Calculate the edge of the adjacent hex processing moves to if the adjacent
# hex bordered the specified edge
# NOTE: This assumes clockwise processing
_AdjacentTransitionMap = {
    travellermap.HexEdge.Upper: travellermap.HexEdge.LowerLeft,
    travellermap.HexEdge.UpperRight: travellermap.HexEdge.UpperLeft,
    travellermap.HexEdge.LowerRight: travellermap.HexEdge.Upper,
    travellermap.HexEdge.Lower: travellermap.HexEdge.UpperRight,
    travellermap.HexEdge.LowerLeft: travellermap.HexEdge.LowerRight,
    travellermap.HexEdge.UpperLeft: travellermap.HexEdge.Lower
}

# NOTE: This returns outlines in map coordinates
def calculateOuterHexOutlines(
        hexes: typing.Iterable[travellermap.HexPosition]
        ) -> typing.Iterable[typing.Iterable[typing.Tuple[float, float]]]:
    # NOTE: It's important this uses a set. As well as for performance I suspect you could
    # get into an infinite loop if the same position appeared more than once
    todo = set(hexes)
    borders = []
    while todo:
        startHex, startEdge = _findStartingHex(hexes=todo)
        if not startEdge:
            # This is a single hex on it's own
            borders.append(_getHexOutline(hex=startHex))
            todo.remove(startHex)
            continue

        border = []
        hex = startHex
        edge = startEdge
        while True:
            adjacentHex = hex.neighbourHex(edge=edge)
            if adjacentHex in todo:
                # There is an adjacent hex so transition to it
                hex = adjacentHex
                edge = _AdjacentTransitionMap[edge]
            else:
                # There is no adjacent hex so add the most anti-clockwise
                # point on the current edge and transition to the next
                # edge
                border.append(_getAntiClockwisePoint(
                    hex=hex,
                    edge=edge))
                edge = travellermap.anticlockwiseHexEdge(edge)

            if adjacentHex == startHex and edge == startEdge:
                # Finished this outline
                break
        borders.append(border)

        _floodRemove(startHex, todo)

    return borders

def calculateCompleteHexOutlines(
        hexes: typing.Iterable[travellermap.HexPosition]
        ) -> typing.Iterable[typing.Iterable[typing.Tuple[float, float]]]:
    hexDataMap = {hex: {} for hex in hexes}
    for hex in hexes:
        edgeMap = hexDataMap[hex]
        for edge in travellermap.HexEdge:
            if edge in edgeMap:
                # This edge has already been processed when the adjacent hex was
                # processed
                continue

            adjacentHex = hex.neighbourHex(edge=edge)
            adjacentEdgeMap = hexDataMap.get(adjacentHex)
            if adjacentEdgeMap != None:
                edgeMap[edge] = adjacentHex
                adjacentEdgeMap[travellermap.oppositeHexEdge(edge)] = hex

    borders = []
    while True:
        # Find the the first start hex/edge pair
        startHex = None
        startEdge = None
        for hex, edgeMap in hexDataMap.items():
            if len(edgeMap) == 6:
                # This hex is either completely internal or it has had all its
                # edges processed already
                continue
            nextEdge = None
            for edge in travellermap.HexEdge:
                # NOTE: The use of not in is important here rather than doing
                # something like using get and checking for null. The edge
                # not being present means the edge is an outer edge that needs
                # to be processed but hasn't been yet. The edge being set to
                # null means it's an outer edge that has been processed (i.e.
                # it's been included in a previous border)
                if edge not in edgeMap:
                    nextEdge = edge
                    break
            startHex = hex
            startEdge = nextEdge
            break
        if not startHex or not startEdge:
            break

        border = []
        hex = startHex
        edge = startEdge
        edgeMap = hexDataMap[hex]
        while True:
            adjacentHex = edgeMap.get(edge)
            if adjacentHex:
                # There is an adjacent hex so transition to it
                hex = adjacentHex
                edge = _AdjacentTransitionMap[edge]
                edgeMap = hexDataMap[hex]
            else:
                # There is no adjacent hex so add the most anti-clockwise
                # point on the current edge and transition to the next
                # edge
                edgeMap[edge] = None # Mark the current edge as processed
                border.append(_getAntiClockwisePoint(
                    hex=hex,
                    edge=edge))
                edge = travellermap.anticlockwiseHexEdge(edge)

            if hex == startHex and edge == startEdge:
                # Finished this outline
                break
        borders.append(border)

    return borders
