import itertools
import multiverse
import typing

# TODO: Inserting holes

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
                    merged.append(multiverse.DbBorder(
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


    return merged
