import astronomer
import gui
import logic
import math
import typing
from PyQt5 import QtCore, QtGui

_HexPolygon = QtGui.QPolygonF([
    # Upper left
    QtCore.QPointF(
        (-0.5 + astronomer.HexWidthOffset) * astronomer.ParsecScaleX,
        -0.5 * astronomer.ParsecScaleY),
    # Upper right
    QtCore.QPointF(
        (+0.5 - astronomer.HexWidthOffset) * astronomer.ParsecScaleX,
        -0.5 * astronomer.ParsecScaleY),
    # Center right
    QtCore.QPointF(
        (+0.5 + astronomer.HexWidthOffset) * astronomer.ParsecScaleX,
        0 * astronomer.ParsecScaleY) ,
    # Lower right
    QtCore.QPointF(
        (+0.5 - astronomer.HexWidthOffset) * astronomer.ParsecScaleX,
        +0.5 * astronomer.ParsecScaleY),
    # Lower Left
    QtCore.QPointF(
        (-0.5 + astronomer.HexWidthOffset) * astronomer.ParsecScaleX,
        +0.5 * astronomer.ParsecScaleY),
    # Center left
    QtCore.QPointF(
        (-0.5 - astronomer.HexWidthOffset) * astronomer.ParsecScaleX,
        0 * astronomer.ParsecScaleY),
])

class HexMapOverlay(gui.MapOverlay):
    def __init__(
            self,
            depth: int,
            hexes: typing.Optional[typing.Iterable[astronomer.HexPosition]] = None,
            lineColour: typing.Optional[QtGui.QColor] = None,
            lineWidth: typing.Optional[int] = None, # In pixels
            fillColour: typing.Optional[QtGui.QColor] = None,
            enabled: bool = True
            ) -> None:
        super().__init__(depth=depth, enabled=enabled)

        self._hexes = set(hexes) if hexes else set()
        self._translations: typing.Optional[typing.List[typing.Tuple[float, float]]] = None

        self._pen = self._brush = None
        if lineColour:
            self._pen = QtGui.QPen(
                lineColour,
                0) # Line width set at draw time as it's dependent on scale
            self._lineWidth = lineWidth
        if fillColour:
            self._brush = QtGui.QBrush(fillColour)

    def hexes(self) -> typing.Collection[astronomer.HexPosition]:
        return self._hexes

    def setHexes(
            self,
            hexes: typing.Optional[typing.Iterable[astronomer.HexPosition]]
            ) -> None:
        self._hexes.clear()
        if hexes:
            self._hexes.update(hexes)
        self._translations = None

    def addHex(self, hex: astronomer.HexPosition) -> None:
        if hex in self._hexes:
            return
        self._hexes.add(hex)
        self._translations = None

    def removeHex(self, hex: astronomer.HexPosition) -> None:
        self._hexes.discard(hex)
        self._translations = None

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> bool:
        if not self.isEnabled() or not self._hexes:
            return False

        if not self._translations:
            self._updateTranslations()
            if not self._translations:
                return False

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)

        if self._pen:
            self._pen.setWidthF(self._lineWidth / currentScale.linear)
        painter.setPen(self._pen if self._pen else QtCore.Qt.PenStyle.NoPen)

        painter.setBrush(self._brush if self._brush else QtCore.Qt.BrushStyle.NoBrush)

        for translateX, translateY in self._translations:
            with gui.PainterStateGuard(painter):
                transform = painter.transform()
                transform.translate(translateX, translateY)
                painter.setTransform(transform)
                painter.drawPolygon(_HexPolygon)

        return True # Something was drawn

    def _updateTranslations(self) -> None:
        if not self._hexes:
            return

        self._translations = []
        for hex in self._hexes:
            centerX, centerY = hex.worldCenter()
            self._translations.append((
                centerX * astronomer.ParsecScaleX,
                centerY * astronomer.ParsecScaleY))

class HexPointsMapOverlay(gui.MapOverlay):
    def __init__(
            self,
            depth: int,
            radius: float,
            colour: QtGui.QColor,
            hexes: typing.Optional[typing.Iterable[astronomer.HexPosition]] = None,
            enabled: bool = True
            ) -> None:
        super().__init__(depth=depth, enabled=enabled)

        self._hexes = set(hexes) if hexes else set()
        self._polygon: typing.Optional[QtGui.QPolygonF] = None

        self._pen = QtGui.QPen(
            colour,
            radius * 2,
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap)

    def hexes(self) -> typing.Collection[astronomer.HexPosition]:
        return self._hexes

    def setHexes(
            self,
            hexes: typing.Optional[typing.Iterable[astronomer.HexPosition]]
            ) -> None:
        self._hexes.clear()
        if hexes:
            self._hexes.update(hexes)
        self._polygon = None

    def addHex(self, hex: astronomer.HexPosition) -> None:
        if hex in self._hexes:
            return
        self._hexes.add(hex)
        self._polygon = None

    def addHexes(self, hexes: typing.Iterable[astronomer.HexPosition]) -> None:
        oldCount = len(self._hexes)
        self._hexes.update(hexes)
        newCount = len(self._hexes)
        if newCount != oldCount:
            self._polygon = None

    def removeHex(self, hex: astronomer.HexPosition) -> None:
        self._hexes.discard(hex)
        self._polygon = None

    def clearHexes(self) -> None:
        if not self._hexes:
            return
        self._hexes.clear()
        self._polygon = None

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> bool:
        if not self.isEnabled() or not self._hexes:
            return False

        if not self._polygon:
            self._updatePolygon()
            if not self._polygon:
                return False

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)

        painter.setPen(self._pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        painter.drawPoints(self._polygon)

        return True # Something was drawn

    def _updatePolygon(self) -> None:
        if not self._hexes:
            return

        self._polygon = QtGui.QPolygonF()
        for hex in self._hexes:
            centerX, centerY = hex.worldCenter()
            self._polygon.append(QtCore.QPointF(
                centerX * astronomer.ParsecScaleX,
                centerY * astronomer.ParsecScaleY))

class HexOutlineMapOverlay(gui.MapOverlay):
    def __init__(
            self,
            depth: int,
            hexes: typing.Optional[typing.Iterable[astronomer.HexPosition]] = None,
            includeInterior: bool = True,
            lineColour: typing.Optional[QtGui.QColor] = None,
            lineWidth: typing.Optional[int] = None, # In pixels
            fillColour: typing.Optional[QtGui.QColor] = None,
            enabled: bool = True
            ) -> None:
        super().__init__(depth=depth, enabled=enabled)

        self._hexes = set(hexes) if hexes else set()
        self._includeInterior = includeInterior
        self._polygons: typing.Optional[typing.List[QtGui.QPolygonF]] = None
        self._translations: typing.Optional[typing.List[typing.Tuple[float, float]]] = None

        self._pen = self._brush = None
        if lineColour:
            self._pen = QtGui.QPen(
                lineColour,
                0) # Line width set at draw time as it's dependent on scale
            self._lineWidth = lineWidth
        if fillColour:
            self._brush = QtGui.QBrush(fillColour)

    def hexes(self) -> typing.Collection[astronomer.HexPosition]:
        return self._hexes

    def setHexes(
            self,
            hexes: typing.Optional[typing.Iterable[astronomer.HexPosition]]
            ) -> None:
        self._hexes.clear()
        if hexes:
            self._hexes.update(hexes)
        self._polygons = self._translations = None

    def addHex(self, hex: astronomer.HexPosition) -> None:
        if hex in self._hexes:
            return

        self._hexes.add(hex)
        self._polygons = self._translations = None # Regenerate on demand

    def addHexes(self, hexes: typing.Iterable[astronomer.HexPosition]):
        oldCount = len(self._hexes)
        self._hexes.update(hexes)
        newCount = len(self._hexes)

        if newCount != oldCount:
            self._polygons = self._translations = None

    def removeHex(self, hex: astronomer.HexPosition) -> None:
        if hex not in self._hexes:
            return

        self._hexes.discard(hex)
        self._polygons = self._translations = None # Regenerate on demand

    def clear(self) -> None:
        if not self._hexes:
            return

        self._hexes.clear()
        self._polygons = self._translations = None # Regenerate on demand

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> bool:
        if not self.isEnabled() or not self._hexes:
            return False

        hasRendered = False

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)

        if self._brush and self._includeInterior:
            # When interior outlines and a fill are to be drawn, the fill needs to be
            # drawn as individual hexes as the interior and exterior outline polygons
            # are separate polygons rather than a single polygon. If this wasn't done,
            # if the selection made a loop with the center of the loop not selected,
            # the center hex would be incorrectly drawn filled (due to the interior
            # loop polygon getting filled)
            if self._translations is None:
                self._updateTranslations()

            if self._translations:
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(self._brush)
                for translateX, translateY in self._translations:
                    with gui.PainterStateGuard(painter):
                        transform = painter.transform()
                        transform.translate(translateX, translateY)
                        painter.setTransform(transform)
                        painter.drawPolygon(_HexPolygon)
                hasRendered = True

        fillPolygons = self._brush and not self._includeInterior
        if self._pen or fillPolygons:
            if self._polygons is None:
                self._updatePolygons()

            if self._polygons:
                if self._pen:
                    self._pen.setWidthF(self._lineWidth / currentScale.linear)
                painter.setPen(self._pen if self._pen else QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(self._brush if fillPolygons else QtCore.Qt.BrushStyle.NoBrush)

                for polygon in self._polygons:
                    painter.drawPolygon(polygon)
                hasRendered = True

        return hasRendered

    def _updateTranslations(self) -> None:
        if not self._hexes:
            return

        self._translations = []
        for hex in self._hexes:
            centerX, centerY = hex.worldCenter()
            self._translations.append((
                centerX * astronomer.ParsecScaleX,
                centerY * astronomer.ParsecScaleY))

    def _updatePolygons(self) -> None:
        if not self._hexes:
            return

        if self._includeInterior:
            outlines = logic.calculateCompleteHexOutlines(hexes=self._hexes)
        else:
            outlines = logic.calculateOuterHexOutlines(hexes=self._hexes)
        self._polygons: typing.List[QtGui.QPolygonF] = []
        for outline in outlines:
            polygon = QtGui.QPolygonF()
            for x, y in outline:
                polygon.append(QtCore.QPointF(x, y))
            self._polygons.append(polygon)

class HexRadiusMapOverlay(gui.MapOverlay):
    def __init__(
            self,
            center: astronomer.HexPosition,
            radius: int,
            depth: int,
            lineColour: typing.Optional[QtGui.QColor] = None,
            lineWidth: typing.Optional[int] = None, # In pixels
            fillColour: typing.Optional[QtGui.QColor] = None,
            enabled: bool = True
            ) -> None:
        super().__init__(depth=depth, enabled=enabled)
        self._center = center
        self._radius = radius
        self._overlay = HexOutlineMapOverlay(
            hexes=center.yieldRadiusHexes(radius=radius, includeInterior=False),
            includeInterior=False,
            depth=depth,
            lineColour=lineColour,
            lineWidth=lineWidth,
            fillColour=fillColour,
            enabled=enabled)

    def center(self) -> astronomer.HexPosition:
        return self._center

    def setCenter(
            self,
            center: astronomer.HexPosition,
            ) -> None:
        self._center = center
        self._overlay.setHexes(
            hexes=self._center.yieldRadiusHexes(radius=self._radius, includeInterior=False))

    def radius(self) -> int:
        return self._radius

    def setRadius(
            self,
            radius: int
            ) -> None:
        self._radius = radius
        self._overlay.setHexes(
            hexes=self._center.yieldRadiusHexes(radius=self._radius, includeInterior=False))

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> bool:
        return self._overlay.draw(painter=painter, currentScale=currentScale)

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self._overlay.setEnabled(enabled=enabled)

class WorldTaggingMapOverlay(gui.MapOverlay):
    def __init__(
            self,
            worldTagging: logic.WorldTagging,
            depth: int,
            worlds: typing.Optional[typing.Iterable[astronomer.World]] = None,
            desirableColour: typing.Optional[QtGui.QColor] = None,
            warningColour: typing.Optional[QtGui.QColor] = None,
            dangerColour: typing.Optional[QtGui.QColor] = None,
            enabled: bool = True
            ) -> None:
        super().__init__(depth=depth, enabled=enabled)

        self._worldTagging = worldTagging
        self._worlds = set(worlds) if worlds else set()
        self._levelOverlays: typing.Dict[logic.TagLevel, HexMapOverlay] = {}
        self._isDirty = True

        if desirableColour is not None:
            self._levelOverlays[logic.TagLevel.Desirable] = HexMapOverlay(
                depth=depth,
                fillColour=desirableColour,
                enabled=enabled)

        if warningColour is not None:
            self._levelOverlays[logic.TagLevel.Warning] = HexMapOverlay(
                depth=depth,
                fillColour=warningColour,
                enabled=enabled)

        if dangerColour is not None:
            self._levelOverlays[logic.TagLevel.Danger] = HexMapOverlay(
                depth=depth,
                fillColour=dangerColour,
                enabled=enabled)

    def setWorlds(
            self,
            worlds: typing.Optional[typing.Iterable[astronomer.World]]
            ) -> None:
        self._worlds.clear()
        if worlds:
            self._worlds.update(worlds)
        self._isDirty = True

    def addWorld(self, world: astronomer.World) -> None:
        if world in self._worlds:
            return
        self._worlds.add(world)
        self._isDirty = True

    def addWorlds(self, worlds: typing.Iterable[astronomer.World]) -> None:
        oldCount = len(self._worlds)
        self._worlds.update(worlds)
        newCount = len(self._worlds)
        if newCount != oldCount:
            self._isDirty = True

    def removeWorld(self, world: astronomer.World) -> None:
        self._worlds.discard(world)
        self._isDirty = True

    def clearWorlds(self) -> None:
        if not self._worlds:
            return
        self._worlds.clear()
        self._isDirty = True

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> bool:
        if not self.isEnabled():
            return False

        if self._isDirty:
            self._updateOverlays()
            self._isDirty = False

        result = False
        for overlay in self._levelOverlays.values():
            result |= overlay.draw(painter=painter, currentScale=currentScale)
        return result

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        for overlay in self._levelOverlays.values():
            overlay.setEnabled(enabled=enabled)

    def _updateOverlays(self) -> None:
        if not self._worlds:
            return

        levelHexes: typing.Dict[
            logic.TagLevel,
            typing.List[astronomer.HexPosition]
            ] = {level: [] for level in self._levelOverlays.keys()}

        for world in self._worlds:
            tagLevel = self._worldTagging.calculateWorldTagLevel(world=world)
            if tagLevel is None:
                continue

            hexes = levelHexes.get(tagLevel)
            if hexes is None:
                continue

            hexes.append(world.hex())

        for level, hexes in levelHexes.items():
            overlay = self._levelOverlays.get(level)
            if not overlay:
                continue
            overlay.setHexes(hexes=hexes)

class JumpRouteMapOverlay(gui.MapOverlay):
    _JumpRouteColour = QtGui.QColor('#7F048104')
    _PitStopColour = QtGui.QColor('#7F8080FF')
    _PitStopRadius = 0.4 # Default to slightly larger than the size of the highlights Traveller Map puts on jump worlds

    def __init__(
            self,
            depth: int,
            jumpRoute: typing.Optional[logic.JumpRoute] = None,
            refuellingPlan: typing.Optional[logic.RefuellingPlan] = None
            ) -> None:
        super().__init__(depth=depth)
        self._jumpRoute = jumpRoute
        self._refuellingPlan = refuellingPlan
        self._jumpRoutePath = None
        self._pitStopPoints = None

        self._jumpRoutePen = QtGui.QPen(
            JumpRouteMapOverlay._JumpRouteColour,
            1, # Width will be set when rendering as it's dependant on scale
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.FlatCap)
        self._jumpNodePen = QtGui.QPen(
            JumpRouteMapOverlay._JumpRouteColour,
            1, # Width will be set when rendering as it's dependant on scale
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap)
        self._pitStopPen = QtGui.QPen(
            JumpRouteMapOverlay._PitStopColour,
            JumpRouteMapOverlay._PitStopRadius * 2,
            QtCore.Qt.PenStyle.SolidLine,
            QtCore.Qt.PenCapStyle.RoundCap)

    def jumpRoute(self) -> typing.Optional[logic.JumpRoute]:
        return self._jumpRoute

    def refuellingPlan(self) -> typing.Optional[logic.RefuellingPlan]:
        return self._refuellingPlan

    def setRoute(
            self,
            jumpRoute: typing.Optional[logic.JumpRoute],
            refuellingPlan: typing.Optional[logic.RefuellingPlan] = None
            ) -> None:
        self._jumpRoute = jumpRoute
        self._refuellingPlan = refuellingPlan
        self._jumpRoutePath = self._pitStopPoints = None

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> bool:
        if not self.isEnabled() or self._jumpRoute is None:
            return False

        if self._jumpRoutePath is None:
            self._updateRoute()
            if self._jumpRoutePath is None:
                return False

        lowDetail = currentScale.log < 7
        routeLineWidth = 0.25 if not lowDetail else (15 / currentScale.linear)

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)

        self._jumpRoutePen.setWidthF(routeLineWidth)
        painter.setPen(self._jumpRoutePen)
        painter.drawPolyline(self._jumpRoutePath)

        self._jumpNodePen.setWidthF(routeLineWidth * 2)
        painter.setPen(self._jumpNodePen)
        if not lowDetail:
            painter.drawPoints(self._jumpRoutePath)
        else:
            painter.drawPoint(self._jumpRoutePath.at(0))
            painter.drawPoint(self._jumpRoutePath.at(self._jumpRoutePath.count() - 1))

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
        if self._pitStopPoints:
            painter.setPen(self._pitStopPen)
            painter.drawPoints(self._pitStopPoints)

        return True # Something was drawn

    def _updateRoute(self) -> None:
        if self._jumpRoute is None:
            return

        self._jumpRoutePath = QtGui.QPolygonF()
        for hex in self._jumpRoute:
            centerX, centerY = hex.worldCenter()
            self._jumpRoutePath.append(QtCore.QPointF(
                centerX * astronomer.ParsecScaleX,
                centerY * astronomer.ParsecScaleY))

        self._pitStopPoints = None
        if self._refuellingPlan:
            self._pitStopPoints = QtGui.QPolygonF()
            for pitStop in self._refuellingPlan:
                centerX, centerY = pitStop.hex().worldCenter()
                self._pitStopPoints.append(QtCore.QPointF(
                    centerX * astronomer.ParsecScaleX,
                    centerY * astronomer.ParsecScaleY))

# TODO: This needs to handle drawing the fill when includeInterior is true in a similar
# way to HexOutlineMapOverlay
class SectorOutlineMapOverlay(gui.MapOverlay):
    def __init__(
            self,
            depth: int,
            sectors: typing.Optional[typing.Iterable[astronomer.SectorIndex]] = None,
            includeInterior: bool = True,
            lineColour: typing.Optional[QtGui.QColor] = None,
            lineWidth: typing.Optional[int] = None, # In pixels
            fillColour: typing.Optional[QtGui.QColor] = None,
            enabled: bool = True
            ) -> None:
        super().__init__(depth=depth, enabled=enabled)

        self._sectors = set(sectors) if sectors else set()
        self._includeInterior = includeInterior
        self._polygons = None

        self._pen = self._brush = None
        if lineColour:
            self._pen = QtGui.QPen(
                lineColour,
                0) # Line width set at draw time as it's dependent on scale
            self._lineWidth = lineWidth
        if fillColour:
            self._brush = QtGui.QBrush(fillColour)

    def sectors(self) -> typing.Collection[astronomer.SectorIndex]:
        return self._sectors

    def setSectors(
            self,
            sectors: typing.Optional[typing.Iterable[astronomer.SectorIndex]]
            ) -> None:
        self._sectors.clear()
        if sectors:
            self._sectors.update(sectors)
        self._polygons = None

    def addSector(self, sector: astronomer.SectorIndex) -> None:
        if sector in self._sectors:
            return

        self._sectors.add(sector)
        self._polygons = None # Regenerate on demand

    def addSectors(self, sectors: typing.Iterable[astronomer.SectorIndex]):
        oldCount = len(self._sectors)
        self._sectors.update(sectors)
        newCount = len(self._sectors)

        if newCount != oldCount:
            self._polygons = None

    def removeSector(self, sector: astronomer.SectorIndex) -> None:
        if sector not in self._sectors:
            return

        self._sectors.discard(sector)
        self._polygons = None # Regenerate on demand

    def clear(self) -> None:
        if not self._sectors:
            return

        self._sectors.clear()
        self._polygons = None # Regenerate on demand

    def draw(
            self,
            painter: QtGui.QPainter,
            currentScale: gui.MapScale
            ) -> bool:
        if not self.isEnabled() or not self._sectors:
            return False

        if not self._polygons:
            self._updatePolygons()
            if not self._polygons:
                return False

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)

        if self._pen:
            self._pen.setWidthF(self._lineWidth / currentScale.linear)
        painter.setPen(self._pen if self._pen else QtCore.Qt.PenStyle.NoPen)

        painter.setBrush(self._brush if self._brush else QtCore.Qt.BrushStyle.NoBrush)

        for polygon in self._polygons:
            painter.drawPolygon(polygon)

        return True # Something was drawn

    def _updatePolygons(self) -> None:
        if not self._sectors:
            return

        if self._includeInterior:
            outlines = logic.calculateCompleteSectorOutlines(sectors=self._sectors)
        else:
            # TODO: This should be calculateOuterSectorOutlines when I've implemented it
            outlines = logic.calculateCompleteSectorOutlines(sectors=self._sectors)
        self._polygons: typing.List[QtGui.QPolygonF] = []
        for outline in outlines:
            polygon = QtGui.QPolygonF()
            for x, y in outline:
                polygon.append(QtCore.QPointF(x, y))
            self._polygons.append(polygon)
