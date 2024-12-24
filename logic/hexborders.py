import travellermap
import typing

_HalfHexHeight = 0.5
_HalfHexMinWidth = (0.5 - travellermap.HexWidthOffset) * travellermap.ParsecScaleX
_HalfHexMaxWidth = (0.5 + travellermap.HexWidthOffset) * travellermap.ParsecScaleX

def _findStartingHex(
        hexes: typing.Iterable[travellermap.HexPosition]
        ) -> typing.Tuple[travellermap.HexPosition, typing.Optional[travellermap.NeighbourDirection]]:
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
    pos = bestHex.neighbourHex(direction=travellermap.NeighbourDirection.LowerRight)
    if pos in hexes:
        return (bestHex, travellermap.NeighbourDirection.Lower)
    pos = bestHex.neighbourHex(direction=travellermap.NeighbourDirection.UpperRight)
    if pos in hexes:
        return (bestHex, travellermap.NeighbourDirection.LowerRight)
    pos = bestHex.neighbourHex(direction=travellermap.NeighbourDirection.Upper)
    if pos in hexes:
        return (bestHex, travellermap.NeighbourDirection.UpperRight)
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
        for edge in travellermap.NeighbourDirection:
            adjacent = hex.neighbourHex(direction=edge)
            if adjacent in hexes:
                hexes.remove(adjacent)
                todo.append(adjacent)

_AntiClockwiseOffsets = {
    travellermap.NeighbourDirection.Upper: (-_HalfHexMinWidth, _HalfHexHeight),
    travellermap.NeighbourDirection.UpperRight: (_HalfHexMinWidth, _HalfHexHeight),
    travellermap.NeighbourDirection.LowerRight: (_HalfHexMaxWidth, 0),
    travellermap.NeighbourDirection.Lower: (_HalfHexMinWidth, -_HalfHexHeight),
    travellermap.NeighbourDirection.LowerLeft: (-_HalfHexMinWidth, -_HalfHexHeight),
    travellermap.NeighbourDirection.UpperLeft: (-_HalfHexMaxWidth, 0)
}

# Return the most anticlockwise point on the given edge
def _getAntiClockwisePoint(
        hex: travellermap.HexPosition,
        edge: travellermap.NeighbourDirection
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
    travellermap.NeighbourDirection.Upper: travellermap.NeighbourDirection.LowerLeft,
    travellermap.NeighbourDirection.UpperRight: travellermap.NeighbourDirection.UpperLeft,
    travellermap.NeighbourDirection.LowerRight: travellermap.NeighbourDirection.Upper,
    travellermap.NeighbourDirection.Lower: travellermap.NeighbourDirection.UpperRight,
    travellermap.NeighbourDirection.LowerLeft: travellermap.NeighbourDirection.LowerRight,
    travellermap.NeighbourDirection.UpperLeft: travellermap.NeighbourDirection.Lower
}
_ContinueTransitionMap = {
    travellermap.NeighbourDirection.Upper: travellermap.NeighbourDirection.UpperRight,
    travellermap.NeighbourDirection.UpperRight: travellermap.NeighbourDirection.LowerRight,
    travellermap.NeighbourDirection.LowerRight: travellermap.NeighbourDirection.Lower,
    travellermap.NeighbourDirection.Lower: travellermap.NeighbourDirection.LowerLeft,
    travellermap.NeighbourDirection.LowerLeft: travellermap.NeighbourDirection.UpperLeft,
    travellermap.NeighbourDirection.UpperLeft: travellermap.NeighbourDirection.Upper
}

# NOTE: This takes hexes in absolute coordinates and returns outlines in
# map coordinates
def calculateHexBorders(
        hexes: typing.Iterable[travellermap.HexPosition]
        ) -> typing.Iterable[typing.Iterable[typing.Tuple[float, float]]]:
    # NOTE: It's important this uses a set. As well as for performance I suspect you could
    # get into an infinite loop if the same position appeared more than once
    todo = set(hexes)
    outlines = []
    while todo:
        startHex, edge = _findStartingHex(hexes=todo)
        if not edge:
            # This is a single hex on it's own
            outlines.append(_getHexOutline(hex=startHex))
            todo.remove(startHex)
            continue

        outline = []
        hex = startHex
        while True:
            adjacent = hex.neighbourHex(direction=edge)
            if adjacent == startHex:
                # Finished this outline
                break
            if adjacent in todo:
                # There is an adjacent hex so transition to it
                hex = adjacent
                edge = _AdjacentTransitionMap[edge]
            else:
                # There is no adjacent hex so add the most anti-clockwise
                # point on the current edge and transition to the next
                # edge
                outline.append(_getAntiClockwisePoint(
                    hex=hex,
                    edge=edge))
                edge = _ContinueTransitionMap[edge]
        outlines.append(outline)

        _floodRemove(startHex, todo)

    return outlines
