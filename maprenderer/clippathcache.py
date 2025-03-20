import enum
import maprenderer
import travellermap
import typing

# TODO: Should probably move this into SectorCache
class ClipPathCache(object):
    class PathType(enum.Enum):
        Hex = 0
        Square = 1

    # NOTE: These offsets assume a clockwise winding
    _TopOffsets = [
        (-0.5 - travellermap.HexWidthOffset, 0), # Center left
        (-0.5 + travellermap.HexWidthOffset, -0.5), # Upper left
        (+0.5 - travellermap.HexWidthOffset, -0.5), # Upper right
        (+0.5 + travellermap.HexWidthOffset, 0) # Center right
    ]

    _RightOffsets = [
        (+0.5 - travellermap.HexWidthOffset, -0.5), # Upper right
        (+0.5 + travellermap.HexWidthOffset, 0), # Center right
        (+0.5 - travellermap.HexWidthOffset, +0.5), # Lower right
        (+0.5 + travellermap.HexWidthOffset, 1) # Center right of next hex
    ]

    _BottomOffsets = [
        (+0.5 + travellermap.HexWidthOffset, 0), # Center right
        (+0.5 - travellermap.HexWidthOffset, +0.5), # Lower right
        (-0.5 + travellermap.HexWidthOffset, +0.5), # Lower Left
        (-0.5 - travellermap.HexWidthOffset, 0) # Center left
    ]

    _LeftOffsets = [
        (-0.5 + travellermap.HexWidthOffset, +0.5), # Lower Left
        (-0.5 - travellermap.HexWidthOffset, 0), # Center left
        (-0.5 + travellermap.HexWidthOffset, -0.5), # Upper left
        (-0.5 - travellermap.HexWidthOffset, -1) # Center left of next hex
    ]

    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics
            ) -> None:
        self._graphics = graphics
        self._sectorClipPaths: typing.Mapping[
            typing.Tuple[
                int, # Sector X position
                int, # Sector Y position
                ClipPathCache.PathType
            ],
            maprenderer.AbstractPath
        ] = {}

    def sectorClipPath(
            self,
            sectorX: int,
            sectorY: int,
            pathType: PathType
            ) -> maprenderer.AbstractPath:
        key = (sectorX, sectorY, pathType)
        clipPath = self._sectorClipPaths.get(key)
        if clipPath:
            return clipPath

        originX, originY = travellermap.relativeSpaceToAbsoluteSpace(
            (sectorX, sectorY, 1, 1))

        points = []

        count = len(ClipPathCache._TopOffsets)
        y=0
        for x in range(0, travellermap.SectorWidth, 2):
            for i in range(count):
                offsetX, offsetY = ClipPathCache._TopOffsets[i]
                points.append(maprenderer.PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=((originY + y) - 0.5) + offsetY))

        last = travellermap.SectorHeight - 2
        count = len(ClipPathCache._RightOffsets)
        x = travellermap.SectorWidth - 1
        for y in range(0, travellermap.SectorHeight, 2):
            if y == last:
                count -= 1
            for i in range(count):
                offsetX, offsetY = ClipPathCache._RightOffsets[i]
                points.append(maprenderer.PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=(originY + y) + offsetY))

        count = len(ClipPathCache._BottomOffsets)
        y = travellermap.SectorHeight - 1
        for x in range(travellermap.SectorWidth - 1, -1, -2):
            for i in range(count):
                offsetX, offsetY = ClipPathCache._BottomOffsets[i]
                points.append(maprenderer.PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=(originY + y) + offsetY))

        last = travellermap.SectorHeight - 2
        count = len(ClipPathCache._LeftOffsets)
        x = 0
        for y in range(travellermap.SectorHeight - 1, -1, -2):
            if y == last:
                count -= 1
            for i in range(count):
                offsetX, offsetY = ClipPathCache._LeftOffsets[i]
                points.append(maprenderer.PointF(
                    x=((originX + x) - 0.5) + offsetX,
                    y=((originY + y) - 0.5) + offsetY))

        types = [maprenderer.PathPointType.Start]
        types.extend([maprenderer.PathPointType.Line] * (len(points) - 2))
        types.append([maprenderer.PathPointType.Line | maprenderer.PathPointType.CloseSubpath])

        path = self._graphics.createPath(points=points, types=types, closed=True)
        self._sectorClipPaths[key] = path
        return path
