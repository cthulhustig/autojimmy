import maprenderer
import traveller
import travellermap
import typing

class SectorOutline(object):
    def __init__(
            self,
            path: maprenderer.AbstractPath,
            color: typing.Optional[str],
            style: typing.Optional[maprenderer.LineStyle]
            ) -> None:
        self._path = path
        self._color = color
        self._style = style

    def path(self) -> maprenderer.AbstractPath:
        return self._path

    def color(self) -> typing.Optional[str]:
        return self._color

    def style(self) -> typing.Optional[maprenderer.LineStyle]:
        return self._style

    def bounds(self) -> maprenderer.AbstractRectangleF:
        return self._path.bounds()

# TODO: Should probably flatten style cache into this code as I think it's
# the only thing that actually uses it
class SectorCache(object):
    def __init__(
            self,
            graphics: maprenderer.AbstractGraphics,
            styleCache: maprenderer.DefaultStyleCache
            ) -> None:
        self._graphics = graphics
        self._styleCache = styleCache
        self._worldsCache: typing.Dict[
            typing.Union[int, int], # Sector x/y
            maprenderer.AbstractPointList
        ] = {}
        self._borderCache: typing.Dict[
            typing.Union[int, int], # Sector x/y
            typing.List[SectorOutline]
        ] = {}
        self._regionCache: typing.Dict[
            typing.Union[int, int], # Sector x/y
            typing.List[SectorOutline]
        ] = {}

    def isotropicWorldPoints(
            self,
            x: int,
            y: int
            ) -> typing.Optional[maprenderer.AbstractPointList]:
        key = (x, y)
        worlds = self._worldsCache.get(key)
        if worlds is not None:
            return worlds

        sector = traveller.WorldManager.instance().sectorByPosition(
            hex=travellermap.HexPosition(sectorX=x, sectorY=y, offsetX=1, offsetY=1))
        if not sector:
            # Don't cache the fact the sector doesn't exist to avoid memory bloat
            return None

        points = []
        for world in sector.worlds():
            hex = world.hex()
            centerX, centerY = hex.absoluteCenter()
            points.append(maprenderer.AbstractPointF(
                # Scale center point by parsec scale to convert to isotropic coordinates
                x=centerX * travellermap.ParsecScaleX,
                y=centerY * travellermap.ParsecScaleY))

        worlds = self._graphics.createPointList(points=points)
        self._worldsCache[key] = worlds
        return worlds

    def borderOutlines(
            self,
            x: int,
            y: int
            ) -> typing.Optional[typing.List[SectorOutline]]:
        key = (x, y)
        borders = self._borderCache.get(key)
        if borders is not None:
            return borders

        sector = traveller.WorldManager.instance().sectorByPosition(
            hex=travellermap.HexPosition(sectorX=x, sectorY=y, offsetX=1, offsetY=1))
        if not sector:
            # Don't cache the fact the sector doesn't exist to avoid memory bloat
            return None

        borders = []
        for border in sector.borders():
            borders.append(self._createOutline(source=border))
        self._borderCache[key] = borders
        return borders

    def regionOutlines(
            self,
            x: int,
            y: int
            ) -> typing.Optional[typing.List[SectorOutline]]:
        key = (x, y)
        regions = self._regionCache.get(key)
        if regions is not None:
            return regions

        sector = traveller.WorldManager.instance().sectorByPosition(
            hex=travellermap.HexPosition(sectorX=x, sectorY=y, offsetX=1, offsetY=1))
        if not sector:
            # Don't cache the fact the sector doesn't exist to avoid memory bloat
            return None

        regions = []
        for region in sector.regions():
            regions.append(self._createOutline(source=region))
        self._regionCache[key] = regions
        return regions

    def _createOutline(
            self,
            source: typing.Union[traveller.Region, traveller.Border]
            ) -> SectorOutline:
        color = source.colour()
        style = None

        if isinstance(source, traveller.Border):
            if source.style() is traveller.Border.Style.Solid:
                style = maprenderer.LineStyle.Solid
            elif source.style() is traveller.Border.Style.Dashed:
                style = maprenderer.LineStyle.Dash
            elif source.style() is traveller.Border.Style.Dotted:
                style = maprenderer.LineStyle.Dot

            if not color or not style:
                defaultColor, defaultStyle = self._styleCache.defaultBorderStyle(source.allegiance())
                if not color:
                    color = defaultColor
                if not style:
                    style = defaultStyle

        outline = source.absoluteOutline()
        drawPath = []
        for x, y in outline:
            drawPath.append(maprenderer.AbstractPointF(x=x, y=y))
        types = [maprenderer.PathPointType.Start]
        for _ in range(len(outline) - 1):
            types.append(maprenderer.PathPointType.Line)
        types[-1] |= maprenderer.PathPointType.CloseSubpath
        outline = self._graphics.createPath(points=drawPath, types=types, closed=True)

        return SectorOutline(path=outline, color=color, style=style)