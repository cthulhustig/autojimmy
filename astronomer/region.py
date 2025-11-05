import astronomer
import typing

class Region(object):
    _AntiClockwiseOffsets = {
        astronomer.HexEdge.Upper: (-0.5 + astronomer.HexWidthOffset, -0.5), # Upper left
        astronomer.HexEdge.UpperRight: (+0.5 - astronomer.HexWidthOffset, -0.5), # Upper right
        astronomer.HexEdge.LowerRight: (+0.5 + astronomer.HexWidthOffset, 0), # Center right
        astronomer.HexEdge.Lower: (+0.5 - astronomer.HexWidthOffset, +0.5), # Lower right
        astronomer.HexEdge.LowerLeft: (-0.5 + astronomer.HexWidthOffset, +0.5), # Lower Left
        astronomer.HexEdge.UpperLeft: (-0.5 - astronomer.HexWidthOffset, 0), # Center left
    }
    _AdjacentTransitionMap = {
        astronomer.HexEdge.Upper: astronomer.HexEdge.LowerLeft,
        astronomer.HexEdge.UpperRight: astronomer.HexEdge.UpperLeft,
        astronomer.HexEdge.LowerRight: astronomer.HexEdge.Upper,
        astronomer.HexEdge.Lower: astronomer.HexEdge.UpperRight,
        astronomer.HexEdge.LowerLeft: astronomer.HexEdge.LowerRight,
        astronomer.HexEdge.UpperLeft: astronomer.HexEdge.Lower
    }
    _HexOutlineOffsets = [
        (-0.5 - astronomer.HexWidthOffset, 0), # Center left
        (-0.5 + astronomer.HexWidthOffset, -0.5), # Upper left
        (+0.5 - astronomer.HexWidthOffset, -0.5), # Upper right
        (+0.5 + astronomer.HexWidthOffset, 0), # Center right
        (+0.5 - astronomer.HexWidthOffset, +0.5), # Lower right
        (-0.5 + astronomer.HexWidthOffset, +0.5), # Lower Left
    ]

    def __init__(
            self,
            hexList: typing.Iterable[astronomer.HexPosition],
            showLabel: bool,
            labelHex: typing.Optional[astronomer.HexPosition],
            labelOffsetX: typing.Optional[float],
            labelOffsetY: typing.Optional[float],
            label: typing.Optional[str],
            colour: typing.Optional[str]
            ) -> None:
        self._hexList = list(hexList)
        self._showLabel = showLabel
        self._labelHex = labelHex
        self._labelOffsetX = labelOffsetX
        self._labelOffsetY = labelOffsetY
        self._label = label
        self._colour = colour
        self._outline: typing.Optional[typing.List[typing.Tuple[float, float]]] = None

    def hexList(self) -> typing.Iterable[astronomer.HexPosition]:
        return self._hexList

    def showLabel(self) -> bool:
        return self._showLabel

    def labelHex(self) -> typing.Optional[astronomer.HexPosition]:
        return self._labelHex

    # Offset in world coordinates
    def labelOffsetX(self) -> typing.Optional[float]:
        return self._labelOffsetX

    def labelOffsetY(self) -> typing.Optional[float]:
        return self._labelOffsetY

    def label(self) -> typing.Optional[str]:
        return self._label

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def worldOutline(self) -> typing.Iterable[typing.Tuple[float, float]]:
        if self._outline is not None:
            return self._outline

        self._outline = []

        hexes = set(self._hexList)
        startHex, startEdge = Region._findOutlineStart(hexes=hexes)
        if not startEdge:
            # This is a single hex on it's own
            centerX, centerY = startHex.worldCenter()
            for offsetX, offsetY in Region._HexOutlineOffsets:
                self._outline.append((centerX + offsetX, centerY + offsetY))
            return self._outline

        hex = startHex
        edge = startEdge
        while True:
            adjacentHex = hex.neighbourHex(edge=edge)
            if adjacentHex in hexes:
                # There is an adjacent hex so transition to it
                hex = adjacentHex
                edge = Region._AdjacentTransitionMap[edge]
            else:
                # There is no adjacent hex so add the most anti-clockwise
                # point on the current edge and transition to the next
                # edge
                self._outline.append(Region._mostAntiClockwisePoint(
                    hex=hex,
                    edge=edge))
                edge = astronomer.anticlockwiseHexEdge(edge)

            if adjacentHex == startHex and edge == startEdge:
                # Finished this outline
                break

        return self._outline

    @staticmethod
    def _findOutlineStart(hexes: typing.Collection[astronomer.HexPosition]) -> typing.Tuple[
            astronomer.HexPosition,
            typing.Optional[astronomer.HexEdge]]:
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
        hex = bestHex.neighbourHex(edge=astronomer.HexEdge.LowerRight)
        if hex in hexes:
            return (bestHex, astronomer.HexEdge.Lower)
        hex = bestHex.neighbourHex(edge=astronomer.HexEdge.UpperRight)
        if hex in hexes:
            return (bestHex, astronomer.HexEdge.LowerRight)
        hex = bestHex.neighbourHex(edge=astronomer.HexEdge.Upper)
        if hex in hexes:
            return (bestHex, astronomer.HexEdge.UpperRight)
        return (bestHex, None) # This hex has no adjacent hexes so it's outline is the outline

    # Return the most anticlockwise point on the given edge
    @staticmethod
    def _mostAntiClockwisePoint(
            hex: astronomer.HexPosition,
            edge: astronomer.HexEdge
            ) -> typing.Tuple[float, float]:
        centerX, centerY = hex.worldCenter()
        offsetX, offsetY = Region._AntiClockwiseOffsets[edge]
        return (centerX + offsetX, centerY + offsetY)
