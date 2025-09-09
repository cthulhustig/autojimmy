import multiverse
import typing

class Region(object):
    _AntiClockwiseOffsets = {
        multiverse.HexEdge.Upper: (-0.5 + multiverse.HexWidthOffset, -0.5), # Upper left
        multiverse.HexEdge.UpperRight: (+0.5 - multiverse.HexWidthOffset, -0.5), # Upper right
        multiverse.HexEdge.LowerRight: (+0.5 + multiverse.HexWidthOffset, 0), # Center right
        multiverse.HexEdge.Lower: (+0.5 - multiverse.HexWidthOffset, +0.5), # Lower right
        multiverse.HexEdge.LowerLeft: (-0.5 + multiverse.HexWidthOffset, +0.5), # Lower Left
        multiverse.HexEdge.UpperLeft: (-0.5 - multiverse.HexWidthOffset, 0), # Center left
    }
    _AdjacentTransitionMap = {
        multiverse.HexEdge.Upper: multiverse.HexEdge.LowerLeft,
        multiverse.HexEdge.UpperRight: multiverse.HexEdge.UpperLeft,
        multiverse.HexEdge.LowerRight: multiverse.HexEdge.Upper,
        multiverse.HexEdge.Lower: multiverse.HexEdge.UpperRight,
        multiverse.HexEdge.LowerLeft: multiverse.HexEdge.LowerRight,
        multiverse.HexEdge.UpperLeft: multiverse.HexEdge.Lower
    }
    _HexOutlineOffsets = [
        (-0.5 - multiverse.HexWidthOffset, 0), # Center left
        (-0.5 + multiverse.HexWidthOffset, -0.5), # Upper left
        (+0.5 - multiverse.HexWidthOffset, -0.5), # Upper right
        (+0.5 + multiverse.HexWidthOffset, 0), # Center right
        (+0.5 - multiverse.HexWidthOffset, +0.5), # Lower right
        (-0.5 + multiverse.HexWidthOffset, +0.5), # Lower Left
    ]

    def __init__(
            self,
            hexList: typing.Iterable[multiverse.HexPosition],
            showLabel: bool,
            labelHex: typing.Optional[multiverse.HexPosition],
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

    def hexList(self) -> typing.Iterable[multiverse.HexPosition]:
        return self._hexList

    def showLabel(self) -> bool:
        return self._showLabel

    def labelHex(self) -> typing.Optional[multiverse.HexPosition]:
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
                edge = multiverse.anticlockwiseHexEdge(edge)

            if adjacentHex == startHex and edge == startEdge:
                # Finished this outline
                break

        return self._outline

    @staticmethod
    def _findOutlineStart(hexes: typing.Collection[multiverse.HexPosition]) -> typing.Tuple[
            multiverse.HexPosition,
            typing.Optional[multiverse.HexEdge]]:
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
        hex = bestHex.neighbourHex(edge=multiverse.HexEdge.LowerRight)
        if hex in hexes:
            return (bestHex, multiverse.HexEdge.Lower)
        hex = bestHex.neighbourHex(edge=multiverse.HexEdge.UpperRight)
        if hex in hexes:
            return (bestHex, multiverse.HexEdge.LowerRight)
        hex = bestHex.neighbourHex(edge=multiverse.HexEdge.Upper)
        if hex in hexes:
            return (bestHex, multiverse.HexEdge.UpperRight)
        return (bestHex, None) # This hex has no adjacent hexes so it's outline is the outline

    # Return the most anticlockwise point on the given edge
    @staticmethod
    def _mostAntiClockwisePoint(
            hex: multiverse.HexPosition,
            edge: multiverse.HexEdge
            ) -> typing.Tuple[float, float]:
        centerX, centerY = hex.worldCenter()
        offsetX, offsetY = Region._AntiClockwiseOffsets[edge]
        return (centerX + offsetX, centerY + offsetY)
