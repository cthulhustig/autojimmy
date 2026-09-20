import astronomer
import common
import survey
import typing

class Region(astronomer.Entity):
    _AntiClockwiseOffsets = {
        astronomer.HexEdge.Top: (-0.5 + astronomer.HexWidthOffset, -0.5), # Upper left
        astronomer.HexEdge.TopRight: (+0.5 - astronomer.HexWidthOffset, -0.5), # Upper right
        astronomer.HexEdge.BottomRight: (+0.5 + astronomer.HexWidthOffset, 0), # Center right
        astronomer.HexEdge.Bottom: (+0.5 - astronomer.HexWidthOffset, +0.5), # Lower right
        astronomer.HexEdge.BottomLeft: (-0.5 + astronomer.HexWidthOffset, +0.5), # Lower Left
        astronomer.HexEdge.TopLeft: (-0.5 - astronomer.HexWidthOffset, 0), # Center left
    }
    _AdjacentTransitionMap = {
        astronomer.HexEdge.Top: astronomer.HexEdge.BottomLeft,
        astronomer.HexEdge.TopRight: astronomer.HexEdge.TopLeft,
        astronomer.HexEdge.BottomRight: astronomer.HexEdge.Top,
        astronomer.HexEdge.Bottom: astronomer.HexEdge.TopRight,
        astronomer.HexEdge.BottomLeft: astronomer.HexEdge.BottomRight,
        astronomer.HexEdge.TopLeft: astronomer.HexEdge.Bottom
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
            entityId: str,
            hexes: typing.Sequence[astronomer.HexPosition],
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> None:
        super().__init__(entityId=entityId)

        common.validateSequence(name='hexes', value=hexes, elementType=astronomer.HexPosition, allowEmpty=False)
        survey.validateHtmlColour(name='colour', value=colour, allowNone=True)
        common.validateStr(name='label', value=label, allowEmpty=False, allowNone=True)
        common.validateFloat(name='labelWorldX', value=labelWorldX, allowNone=True)
        common.validateFloat(name='labelWorldY', value=labelWorldY, allowNone=True)
        common.validateBool(name='showLabel', value=showLabel)
        common.validateBool(name='wrapLabel', value=wrapLabel)

        self._hexes = list(hexes)
        self._colour = colour
        self._label = label
        self._labelWorldX = labelWorldX
        self._labelWorldY = labelWorldY
        self._showLabel = showLabel
        self._wrapLabel = wrapLabel
        self._outline: typing.Optional[typing.List[typing.Tuple[float, float]]] = None

    def hexes(self) -> typing.Iterable[astronomer.HexPosition]:
        return self._hexes

    def colour(self) -> typing.Optional[str]:
        return self._colour

    def label(self) -> typing.Optional[str]:
        return self._label

    # Offset from top left of sector in world coordinates
    def labelWorldX(self) -> typing.Optional[float]:
        return self._labelWorldX

    def labelWorldY(self) -> typing.Optional[float]:
        return self._labelWorldY

    def showLabel(self) -> bool:
        return self._showLabel

    def wrapLabel(self) -> bool:
        return self._wrapLabel

    # TODO: Rename this and get rid of the old version once I've moved regions to the universe
    def worldOutline2(self) -> typing.Iterable[typing.Tuple[float, float]]:
        if self._outline is not None:
            return self._outline

        self._outline = []

        hexCount = len(self._hexes)
        if hexCount > 1 and self._hexes[0] == self._hexes[-1]:
            # Ignore the last hex if it's just looping back to the original hex
            # as the algorithm does that automatically
            hexCount -= 1

        if hexCount == 1:
            # This is a single hex on it's own
            centerX, centerY = self._hexes[0].worldCenter()
            for offsetX, offsetY in Region._HexOutlineOffsets:
                self._outline.append((centerX + offsetX, centerY + offsetY))
            return self._outline

        uniqueHexes = set(self._hexes)
        if astronomer.HexPosition(118, 29) in uniqueHexes:
            pass # TODO: Remove debug code

        startHex = self._hexes[0]
        finishHex = self._hexes[hexCount - 1]

        startEdge = startHex.connectingEdge(finishHex)
        if startEdge is None:
            # TODO: Not sure what to do here. Probably need checks somewhere
            # that stops invalid hex lists getting this far
            print(f'({startHex}) ({finishHex})') # TODO: Remove debug code
            raise RuntimeError('Route hex list doesn\'t loop')
        startEdge = astronomer.clockwiseHexEdge(startEdge)

        for index in range(hexCount):
            currentHex = self._hexes[index]
            nextHex = self._hexes[(index + 1) % hexCount]
            if currentHex == nextHex:
                continue # Skip runs of the same hex

            connectingEdge = currentHex.connectingEdge(nextHex)
            if connectingEdge is None:
                # TODO Not sure what to do here
                #raise RuntimeError('Route hex list is not contiguous')
                continue

            edge = startEdge
            while True:
                if edge == connectingEdge:
                    break
                self._outline.append(Region._mostAntiClockwisePoint(hex=currentHex, edge=edge))
                edge = astronomer.clockwiseHexEdge(edge=edge)

            startEdge = astronomer.clockwiseHexEdge(
                astronomer.oppositeHexEdge(connectingEdge))

        return self._outline

    def worldOutline(self) -> typing.Iterable[typing.Tuple[float, float]]:
        if self._outline is not None:
            return self._outline

        self._outline = []

        hexes = set(self._hexes)
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
            adjacentHex = hex.neighbour(edge=edge)
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
                edge = astronomer.clockwiseHexEdge(edge)

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
        hex = bestHex.neighbour(edge=astronomer.HexEdge.BottomRight)
        if hex in hexes:
            return (bestHex, astronomer.HexEdge.Bottom)
        hex = bestHex.neighbour(edge=astronomer.HexEdge.TopRight)
        if hex in hexes:
            return (bestHex, astronomer.HexEdge.BottomRight)
        hex = bestHex.neighbour(edge=astronomer.HexEdge.Top)
        if hex in hexes:
            return (bestHex, astronomer.HexEdge.TopRight)
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
