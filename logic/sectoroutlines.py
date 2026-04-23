import astronomer
import typing

_SectorEdges = [
    astronomer.RectilinearNeighbour.Top,
    astronomer.RectilinearNeighbour.Right,
    astronomer.RectilinearNeighbour.Bottom,
    astronomer.RectilinearNeighbour.Left
]

_ClockwiseEdgeTransitions = {
    astronomer.RectilinearNeighbour.Top: astronomer.RectilinearNeighbour.Right,
    astronomer.RectilinearNeighbour.Right: astronomer.RectilinearNeighbour.Bottom,
    astronomer.RectilinearNeighbour.Bottom: astronomer.RectilinearNeighbour.Left,
    astronomer.RectilinearNeighbour.Left: astronomer.RectilinearNeighbour.Top
}

_AntiClockwiseEdgeTransitions = {
    astronomer.RectilinearNeighbour.Top: astronomer.RectilinearNeighbour.Left,
    astronomer.RectilinearNeighbour.Right: astronomer.RectilinearNeighbour.Top,
    astronomer.RectilinearNeighbour.Bottom: astronomer.RectilinearNeighbour.Right,
    astronomer.RectilinearNeighbour.Left: astronomer.RectilinearNeighbour.Bottom
}

_EdgeToBitFlag = {
    astronomer.RectilinearNeighbour.Top: 1,
    astronomer.RectilinearNeighbour.Right: 2,
    astronomer.RectilinearNeighbour.Bottom: 4,
    astronomer.RectilinearNeighbour.Left: 8
}
_AllEdgesMask = \
    _EdgeToBitFlag[astronomer.RectilinearNeighbour.Top] | \
    _EdgeToBitFlag[astronomer.RectilinearNeighbour.Right] | \
    _EdgeToBitFlag[astronomer.RectilinearNeighbour.Bottom] | \
    _EdgeToBitFlag[astronomer.RectilinearNeighbour.Left]

_HalfHexHeight = 0.5 * astronomer.ParsecScaleY
_HorzGapLength = (astronomer.HexWidthOffset * 2) * astronomer.ParsecScaleX
_HorzEdgeLength = (1 - (astronomer.HexWidthOffset * 2)) * astronomer.ParsecScaleX
def _edgePoints(
        sector: astronomer.SectorPosition,
        edge: astronomer.RectilinearNeighbour
        ) -> typing.List[typing.Tuple[float, float]]:
    left, top, width, height = sector.isotropicBounds()
    right = left + width
    bottom = top + height
    points = []

    if edge is astronomer.RectilinearNeighbour.Top:
        x = right - _HorzGapLength
        for index in range(astronomer.SectorWidth):
            y = top if index % 2 else top + _HalfHexHeight
            points.append((x, y))
            x -= _HorzEdgeLength
            points.append((x, y))
            x -= _HorzGapLength
    elif edge is astronomer.RectilinearNeighbour.Right:
        x = right - _HorzGapLength
        y = bottom - _HalfHexHeight
        for _ in range(astronomer.SectorHeight):
            points.append((right, y))
            y -= _HalfHexHeight
            points.append((x, y))
            y -= _HalfHexHeight
    elif edge is astronomer.RectilinearNeighbour.Bottom:
        x = left + _HorzGapLength
        for index in range(astronomer.SectorWidth):
            y = bottom if index % 2 else bottom - _HalfHexHeight
            points.append((x, y))
            x += _HorzEdgeLength
            points.append((x, y))
            x += _HorzGapLength
    elif edge is astronomer.RectilinearNeighbour.Left:
        x = left + _HorzGapLength
        y = top + _HalfHexHeight
        for _ in range(astronomer.SectorHeight):
            points.append((left, y))
            y += _HalfHexHeight
            points.append((x, y))
            y += _HalfHexHeight

    return points

def _sectorOutline(
        sector: astronomer.SectorPosition
        ) -> typing.List[typing.Tuple[float, float]]:
    points = []
    points.extend(_edgePoints(sector=sector, edge=astronomer.RectilinearNeighbour.Left))
    points.extend(_edgePoints(sector=sector, edge=astronomer.RectilinearNeighbour.Bottom))
    points.extend(_edgePoints(sector=sector, edge=astronomer.RectilinearNeighbour.Right))
    points.extend(_edgePoints(sector=sector, edge=astronomer.RectilinearNeighbour.Top))
    return points

# TODO: Update this and the hex variants to take a polygon factory interface that
# can be used to construct whatever type of polygons are required. These functions
# and the factory interface should probably work in world coordinates. The overlays
# can then have their own polygon factory that takes the positions in world coordinate
# and converts them to isotropic coordinates
def calculateCompleteSectorOutlines(
        sectors: typing.Iterable[astronomer.SectorPosition]
        ) -> typing.List[typing.List[typing.Tuple[float, float]]]:
    sectors = set(sectors)
    outlines: typing.List[typing.List[typing.Tuple[float, float]]] = []

    sectorEdgeFlags: typing.Dict[astronomer.SectorPosition, int] = {}
    for sector in sectors:
        edgeFlags = 0
        for edge in _SectorEdges:
            neighbour = sector.neighbour(neighbour=edge)
            if neighbour not in sectors:
                edgeFlags |= _EdgeToBitFlag[edge]

        if edgeFlags == 0:
            # This sector has sectors on each side so can be ignored
            continue
        if edgeFlags == _AllEdgesMask:
            # This sector has no neighbours so just add it as an outline
            outlines.append(_sectorOutline(sector=sector))
            continue

        # The sector has at least one neighbour sector so the outline needs
        # to be walked
        sectorEdgeFlags[sector] = edgeFlags

    while sectorEdgeFlags:
        startSector = next(iter(sectorEdgeFlags))
        edgeFlags = sectorEdgeFlags[startSector]

        for startEdge, flag in _EdgeToBitFlag.items():
            if flag & edgeFlags != 0:
                break

        outline: typing.List[typing.Tuple[float, float]] = []
        sector = startSector
        edge = startEdge
        while True:
            outline.extend(_edgePoints(sector=sector, edge=edge))

            edgeFlags = sectorEdgeFlags[sector]
            edgeFlags &= ~_EdgeToBitFlag[edge]
            if edgeFlags:
                sectorEdgeFlags[sector] = edgeFlags
            else:
                del sectorEdgeFlags[sector]

            nextEdgeACW = _AntiClockwiseEdgeTransitions[edge]
            nextSectorACW = sector.neighbour(neighbour=nextEdgeACW)
            if nextSectorACW in sectors:
                nextSectorCW = nextSectorACW.neighbour(
                    neighbour=_ClockwiseEdgeTransitions[nextEdgeACW])
                if nextSectorCW in sectors:
                    # Move clockwise onto the next sector
                    sector = nextSectorCW
                    edge = _ClockwiseEdgeTransitions[edge]
                else:
                    # Continue on the same edge along the next sector
                    sector = nextSectorACW
            else:
                # Continue on the next anti-clockwise edge of the current
                # sector
                edge = nextEdgeACW

            if sector == startSector and edge == startEdge:
                break

        outlines.append(outline)

    return outlines


