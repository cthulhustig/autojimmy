import enum
import travellermap
import typing

class Region(object):
    _AntiClockwiseOffsets = {
        travellermap.HexEdge.Upper: (-0.5 + travellermap.HexWidthOffset, -0.5), # Upper left
        travellermap.HexEdge.UpperRight: (+0.5 - travellermap.HexWidthOffset, -0.5), # Upper right
        travellermap.HexEdge.LowerRight: (+0.5 + travellermap.HexWidthOffset, 0) ,# Center right
        travellermap.HexEdge.Lower: (+0.5 - travellermap.HexWidthOffset, +0.5), # Lower right
        travellermap.HexEdge.LowerLeft: (-0.5 + travellermap.HexWidthOffset, +0.5), # Lower Left
        travellermap.HexEdge.UpperLeft: (-0.5 - travellermap.HexWidthOffset, 0), # Center left
    }
    _AdjacentTransitionMap = {
        travellermap.HexEdge.Upper: travellermap.HexEdge.LowerLeft,
        travellermap.HexEdge.UpperRight: travellermap.HexEdge.UpperLeft,
        travellermap.HexEdge.LowerRight: travellermap.HexEdge.Upper,
        travellermap.HexEdge.Lower: travellermap.HexEdge.UpperRight,
        travellermap.HexEdge.LowerLeft: travellermap.HexEdge.LowerRight,
        travellermap.HexEdge.UpperLeft: travellermap.HexEdge.Lower
    }
    _HexOutlineOffsets = [
        (-0.5 - travellermap.HexWidthOffset, 0), # Center left
        (-0.5 + travellermap.HexWidthOffset, -0.5), # Upper left
        (+0.5 - travellermap.HexWidthOffset, -0.5), # Upper right
        (+0.5 + travellermap.HexWidthOffset, 0), # Center right
        (+0.5 - travellermap.HexWidthOffset, +0.5), # Lower right
        (-0.5 + travellermap.HexWidthOffset, +0.5), # Lower Left
    ]

    def __init__(
            self,
            hexList: typing.Iterable[travellermap.HexPosition],
            showLabel: bool,
            wrapLabel: bool,
            labelHex: typing.Optional[travellermap.HexPosition],
            labelOffsetX: typing.Optional[float],
            labelOffsetY: typing.Optional[float],
            label: typing.Optional[str],
            colour: typing.Optional[str]
            ) -> None:
        self._hexList = list(hexList)
        self._showLabel = showLabel
        self._wrapLabel = wrapLabel
        self._labelHex = labelHex
        self._labelOffsetX = labelOffsetX
        self._labelOffsetY = labelOffsetY
        self._label = label
        self._colour = colour
        self._outline: typing.Optional[typing.List[typing.Tuple[float, float]]] = None

    def hexList(self) -> typing.Iterable[travellermap.HexPosition]:
        return self._hexList

    def showLabel(self) -> bool:
        return self._showLabel

    def wrapLabel(self) -> bool:
        return self._wrapLabel

    def labelHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._labelHex

    # TODO: Make it clear what units these are in
    def labelOffsetX(self) -> typing.Optional[float]:
        return self._labelOffsetX

    def labelOffsetY(self) -> typing.Optional[float]:
        return self._labelOffsetY

    def label(self) -> typing.Optional[str]:
        return self._label

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def absoluteOutline(self) -> typing.Iterable[typing.Tuple[float, float]]:
        if self._outline is not None:
            return self._outline

        self._outline = []

        hexes = set(self._hexList)
        startHex, startEdge = Region._findOutlineStart(hexes=hexes)
        if not startEdge:
            # This is a single hex on it's own
            centerX, centerY = startHex.absoluteCenter()
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
                edge = travellermap.anticlockwiseHexEdge(edge)

            if adjacentHex == startHex and edge == startEdge:
                # Finished this outline
                break

        return self._outline

    @staticmethod
    def _findOutlineStart(hexes: typing.Collection[travellermap.HexPosition]) -> typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[travellermap.HexEdge]]:
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

    # Return the most anticlockwise point on the given edge
    @staticmethod
    def _mostAntiClockwisePoint(
            hex: travellermap.HexPosition,
            edge: travellermap.HexEdge
            ) -> typing.Tuple[float, float]:
        centerX, centerY = hex.absoluteCenter()
        offsetX, offsetY = Region._AntiClockwiseOffsets[edge]
        return (centerX + offsetX, centerY + offsetY)
