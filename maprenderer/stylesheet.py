import maprenderer
import math
import traveller
import travellermap
import typing

class StyleSheet(object):
    _DefaultFont = 'Arial'

    _SectorGridMinScale = 1 / 2 # Below this, no sector grid is shown
    _SectorGridFullScale = 4 # Above this, sector grid opaque
    _SectorNameMinScale = 1
    _SectorNameAllSelectedScale = 4 # At this point, "Selected" == "All"
    _SectorNameMaxScale = 16
    _PseudoRandomStarsMinScale = 1 # Below this, no pseudo-random stars
    _PseudoRandomStarsMaxScale = 4 # Above this, no pseudo-random stars
    _SubsectorsMinScale = 8
    _SubsectorNameMinScale = 24
    _SubsectorNameMaxScale = 64
    _MegaLabelMaxScale = 1 / 4
    _MacroWorldsMinScale = 1 / 2
    _MacroWorldsMaxScale = 4
    _MacroLabelMinScale = 1 / 2
    _MacroLabelMaxScale = 4
    _MacroRouteMinScale = 1 / 2
    _MacroRouteMaxScale = 4
    _MacroBorderMinScale = 1 / 32
    _MicroBorderMinScale = 4
    _MicroNameMinScale = 16
    _RouteMinScale = 8 # Below this, routes not rendered
    _ParsecMinScale = 16 # Below this, parsec edges not rendered
    _ParsecHexMinScale = 48 # Below this, hex numbers not rendered
    _WorldMinScale = 4 # Below this: no worlds; above this: dotmap
    _WorldBasicMinScale = 24 # Above this: atlas-style abbreviated data
    _WorldFullMinScale = 48 # Above this: full poster-style data
    _WorldUwpMinScale = 96 # Above this: UWP shown above name

    _CandyMinWorldNameScale = 64
    _CandyMinUwpScale = 256
    _CandyMaxWorldRelativeScale = 512
    _CandyMaxBorderRelativeScale = 32
    _CandyMaxRouteRelativeScale = 32

    _T5AllegianceCodeMinScale = 64

    class StyleElement(object):
        def __init__(self) -> None:
            self.visible = False
            # TODO: This should probably be an AbstractBrush to avoid having to create it all the time
            self.content = ''
            self.pen: typing.Optional[maprenderer.AbstractPen] = None
            self.fillBrush: typing.Optional[maprenderer.AbstractBrush] = None
            self.textBrush: typing.Optional[maprenderer.AbstractBrush] = None
            self.textHighlightBrush: typing.Optional[maprenderer.AbstractBrush] = None

            self.textStyle = maprenderer.LabelStyle()
            self.textBackgroundStyle = maprenderer.TextBackgroundStyle.NoStyle
            self.font: typing.Optional[maprenderer.AbstractFont] = None
            self.smallFont: typing.Optional[maprenderer.AbstractFont] = None
            self.mediumFont: typing.Optional[maprenderer.AbstractFont] = None
            self.largeFont: typing.Optional[maprenderer.AbstractFont] = None
            self.position = maprenderer.AbstractPointF()

    def __init__(
            self,
            scale: float,
            options: maprenderer.MapOptions,
            style: travellermap.Style,
            graphics: maprenderer.AbstractGraphics
            ):
        self._scale = scale
        self._options = options
        self._style = style
        self._graphics = graphics
        self._fontCache: typing.Dict[
            typing.Tuple[
                str, # Family
                int, # emSize
                maprenderer.FontStyle
                ],
            maprenderer.AbstractFont] = {}
        self._handleConfigUpdate()

    @property
    def scale(self) -> float:
        return self._scale
    @scale.setter
    def scale(self, scale: float) -> None:
        if scale == self._scale:
            return # Nothing to do
        self._scale = scale

        self._handleConfigUpdate()

    @property
    def options(self) -> maprenderer.MapOptions:
        return self._options
    @options.setter
    def options(self, options: maprenderer.MapOptions) -> None:
        if options == self._options:
            return # Nothing to do
        self._options = options
        self._handleConfigUpdate()

    @property
    def style(self) -> float:
        return self._style
    @scale.setter
    def style(self, style: float) -> None:
        if style == self._style:
            return # Nothing to do
        self._style = style
        self._handleConfigUpdate()

    @property
    def hasWorldOverlays(self) -> bool:
        return self.populationOverlay.visible or \
            self.importanceOverlay.visible or  \
            self.highlightWorlds.visible or \
            self.showStellarOverlay or \
            self.capitalOverlay.visible

    def _handleConfigUpdate(self) -> None:
        # Options

        # TODO: This should be changed to backgroundBrush
        self.backgroundBrush = self._graphics.createBrush(
            color=travellermap.MapColours.Black)

        self.showNebulaBackground = False
        self.showGalaxyBackground = False
        self.useWorldImages = False
        self.dimUnofficialSectors = False
        self.colorCodeSectorStatus = False

        self.deepBackgroundOpacity = 0.0 # TODO: Not sure about this

        self.grayscale = False
        self.lightBackground = False

        self.showRiftOverlay = False
        self.riftOpacity = 0.0 # TODO: Not sure about this

        self.hexContentScale = 1.0

        self.routeEndAdjust = 0.25

        self.t5AllegianceCodes = False

        self.highlightWorlds = StyleSheet.StyleElement()
        self.highlightWorldsPattern: typing.Optional[maprenderer.HighlightWorldPattern] = None

        self.droyneWorlds = StyleSheet.StyleElement()
        self.ancientsWorlds = StyleSheet.StyleElement()
        self.minorHomeWorlds = StyleSheet.StyleElement()

        # Worlds
        self.worlds = StyleSheet.StyleElement()
        self.showWorldDetailColors = False
        self.populationOverlay = StyleSheet.StyleElement()
        self.importanceOverlay = StyleSheet.StyleElement()
        self.capitalOverlay = StyleSheet.StyleElement()
        self.capitalOverlayAltA = StyleSheet.StyleElement()
        self.capitalOverlayAltB = StyleSheet.StyleElement()
        self.showStellarOverlay = False

        self.discPosition = maprenderer.AbstractPointF(0, 0)
        self.discRadius = 0.1
        self.gasGiantRadius = 0.05
        self.allegiancePosition = maprenderer.AbstractPointF(0, 0)
        self.baseTopPosition = maprenderer.AbstractPointF(0, 0)
        self.baseBottomPosition = maprenderer.AbstractPointF(0, 0)
        self.baseMiddlePosition = maprenderer.AbstractPointF(0, 0)

        self.uwp = StyleSheet.StyleElement()
        self.starport = StyleSheet.StyleElement()

        self.worldDetails: maprenderer.WorldDetails = maprenderer.WorldDetails.NoDetails
        self.lowerCaseAllegiance = False

        self.wingdingFont: typing.Optional[maprenderer.AbstractFont] = None
        self.glyphFont: typing.Optional[maprenderer.AbstractFont] = None

        self.showGasGiantRing = False

        self.showTL = False
        self.ignoreBaseBias = False
        self.showZonesAsPerimeters = False

        # Hex Coordinates
        self.hexNumber = StyleSheet.StyleElement()
        self.hexCoordinateStyle = maprenderer.HexCoordinateStyle.Sector
        self.numberAllHexes = False

        # Sector Name
        self.sectorName = StyleSheet.StyleElement()
        self.showSomeSectorNames = False
        self.showAllSectorNames = False

        self.capitals = StyleSheet.StyleElement()
        self.subsectorNames = StyleSheet.StyleElement()
        self.greenZone = StyleSheet.StyleElement()
        self.amberZone = StyleSheet.StyleElement()
        self.redZone = StyleSheet.StyleElement()
        self.sectorGrid = StyleSheet.StyleElement()
        self.subsectorGrid = StyleSheet.StyleElement()
        self.parsecGrid = StyleSheet.StyleElement()
        self.worldWater = StyleSheet.StyleElement()
        self.worldNoWater = StyleSheet.StyleElement()
        self.macroRoutes = StyleSheet.StyleElement()
        self.microRoutes = StyleSheet.StyleElement()
        self.macroBorders = StyleSheet.StyleElement()
        self.microBorders = StyleSheet.StyleElement()
        self.macroNames = StyleSheet.StyleElement()
        self.megaNames = StyleSheet.StyleElement()
        self.pseudoRandomStars = StyleSheet.StyleElement()
        self.placeholder = StyleSheet.StyleElement()
        self.anomaly = StyleSheet.StyleElement()
        self.gasGiant = StyleSheet.StyleElement()

        self.worldRichAgricultural = StyleSheet.StyleElement()
        self.worldAgricultural = StyleSheet.StyleElement()
        self.worldRich = StyleSheet.StyleElement()
        self.worldIndustrial = StyleSheet.StyleElement()
        self.worldHarshAtmosphere = StyleSheet.StyleElement()
        self.worldVacuum = StyleSheet.StyleElement()

        self.fillMicroBorders = False
        self.shadeMicroBorders = False
        self.showMicroNames = False
        self.microBorderStyle = maprenderer.MicroBorderStyle.Hex
        self.hexStyle = maprenderer.HexStyle.Hex
        self.overrideLineStyle: typing.Optional[maprenderer.LineStyle] = None

        self.layerOrder: typing.Dict[maprenderer.LayerId, int] = {}

        onePixel = 1.0 / self.scale

        self.subsectorGrid.visible = (self.scale >= StyleSheet._SubsectorsMinScale) and \
            ((self.options & maprenderer.MapOptions.SubsectorGrid) != 0)
        self.sectorGrid.visible = (self.scale >= StyleSheet._SectorGridMinScale) and \
            ((self._options & maprenderer.MapOptions.SectorGrid) != 0)
        self.parsecGrid.visible = (self.scale >= StyleSheet._ParsecMinScale)
        self.showSomeSectorNames = (self.scale >= StyleSheet._SectorNameMinScale) and \
            (self.scale <= StyleSheet._SectorNameMaxScale) and \
            ((self._options & maprenderer.MapOptions.SectorsMask) != 0)
        self.showAllSectorNames = self.showSomeSectorNames and \
            ((self.scale >= StyleSheet._SectorNameAllSelectedScale) or \
             ((self._options & maprenderer.MapOptions.SectorsAll) != 0))
        self.subsectorNames.visible = (self.scale >= StyleSheet._SubsectorNameMinScale) and \
            (self.scale <= StyleSheet._SubsectorNameMaxScale) and \
            ((self._options & maprenderer.MapOptions.SectorsMask) != 0)

        self.worlds.visible = self.scale >= StyleSheet._WorldMinScale
        self.pseudoRandomStars.visible = (StyleSheet._PseudoRandomStarsMinScale <= self.scale) and \
             (self.scale <= StyleSheet._PseudoRandomStarsMaxScale)
        self.showRiftOverlay = (self.scale <= StyleSheet._PseudoRandomStarsMaxScale) or \
             (StyleSheet.style == travellermap.Style.Candy)

        self.t5AllegianceCodes = self.scale >= StyleSheet._T5AllegianceCodeMinScale

        self.riftOpacity = StyleSheet._floatScaleInterpolate(
            minValue=0,
            maxValue=0.85,
            scale=self.scale,
            minScale=1 / 4,
            maxScale=4)

        self.deepBackgroundOpacity = StyleSheet._floatScaleInterpolate(
            minValue=1,
            maxValue=0,
            scale=self.scale,
            minScale=1 / 8,
            maxScale=2)

        self.macroRoutes.visible = (self.scale >= StyleSheet._MacroRouteMinScale) and \
            (self.scale <= StyleSheet._MacroRouteMaxScale)
        self.macroNames.visible = (self.scale >= StyleSheet._MacroLabelMinScale) and \
            (self.scale <= StyleSheet._MacroLabelMaxScale)
        self.megaNames.visible = self.scale <= StyleSheet._MegaLabelMaxScale and \
            ((self.options & maprenderer.MapOptions.NamesMask) != 0)
        self.showMicroNames = (self.scale >= StyleSheet._MicroNameMinScale) and \
            ((self.options & maprenderer.MapOptions.NamesMask) != 0)
        self.capitals.visible = (self.scale >= StyleSheet._MacroWorldsMinScale) and \
            (self.scale <= StyleSheet._MacroWorldsMaxScale)

        self.hexStyle = \
            maprenderer.HexStyle.Square \
            if ((self.options & maprenderer.MapOptions.ForceHexes) == 0) and \
                (self.scale < StyleSheet._ParsecHexMinScale) else \
            maprenderer.HexStyle.Hex
        self.microBorderStyle = \
            maprenderer.MicroBorderStyle.Square \
            if self.hexStyle == maprenderer.HexStyle.Square else \
            maprenderer.MicroBorderStyle.Hex

        self.macroBorders.visible = (self.scale >= StyleSheet._MacroBorderMinScale) and \
            (self.scale < StyleSheet._MicroBorderMinScale) and \
            ((self.options & maprenderer.MapOptions.BordersMask) != 0)
        self.microBorders.visible = (self.scale >= StyleSheet._MicroBorderMinScale) and \
            ((self.options & maprenderer.MapOptions.BordersMask) != 0)
        self.fillMicroBorders = self.microBorders.visible and \
            ((self.options & maprenderer.MapOptions.FilledBorders) != 0)
        self.microRoutes.visible = (self.scale >= StyleSheet._RouteMinScale)

        if self.scale < StyleSheet._WorldBasicMinScale:
            self.worldDetails = maprenderer.WorldDetails.Dotmap
        elif self.scale < StyleSheet._WorldFullMinScale:
            self.worldDetails = maprenderer.WorldDetails.Atlas
        else:
            self.worldDetails = maprenderer.WorldDetails.Poster

        self.discRadius = 0.1 if ((self.worldDetails & maprenderer.WorldDetails.Type) != 0) else  0.2

        self.showWorldDetailColors = self.worldDetails == maprenderer.WorldDetails.Poster and \
            ((self.options & maprenderer.MapOptions.WorldColors) != 0)
        self.populationOverlay.visible = (self.options & maprenderer.MapOptions.PopulationOverlay) != 0
        self.importanceOverlay.visible = (self.options & maprenderer.MapOptions.ImportanceOverlay) != 0
        self.capitalOverlay.visible = (self.options & maprenderer.MapOptions.CapitalOverlay) != 0
        self.showStellarOverlay = (self._options & maprenderer.MapOptions.StellarOverlay) != 0
        self.ancientsWorlds.visible = (self.options & maprenderer.MapOptions.AncientWorlds) != 0
        self.droyneWorlds.visible = (self.options & maprenderer.MapOptions.DroyneWorlds) != 0
        self.minorHomeWorlds.visible = (self.options & maprenderer.MapOptions.MinorHomeWorlds) != 0

        # Force ancient worlds, droyne worlds & minor home world overlays off
        # when zoomed out as it kills performance to the point it effectively
        # locks up the app
        # TODO: Look into why this is happening
        if self.scale < 2:
            self.ancientsWorlds.visible = self.droyneWorlds.visible = \
                self.minorHomeWorlds.visible = False

        self.lowerCaseAllegiance = (self.scale < StyleSheet._WorldFullMinScale)

        self.showGasGiantRing = (self.scale >= StyleSheet._WorldUwpMinScale)
        self.gasGiant.visible = True

        self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.Rectangle

        self.hexCoordinateStyle = maprenderer.HexCoordinateStyle.Sector
        self.numberAllHexes = False

        if self.scale < StyleSheet._WorldFullMinScale:
            # Atlas-style

            x = 0.225
            y = 0.125

            self.baseTopPosition = maprenderer.AbstractPointF(-x, -y)
            self.baseBottomPosition = maprenderer.AbstractPointF(-x, y)
            self.gasGiant.position =  maprenderer.AbstractPointF(x, -y)
            self.allegiancePosition = maprenderer.AbstractPointF(x, y)

            self.baseMiddlePosition = maprenderer.AbstractPointF(
                -0.35 if ((self.options & maprenderer.MapOptions.ForceHexes) != 0) else -0.2,
                0)
            self.starport.position = maprenderer.AbstractPointF(0, -0.24)
            self.uwp.position = maprenderer.AbstractPointF(0, 0.24)
            self.worlds.position = maprenderer.AbstractPointF(0, 0.4)
        else:
            # Poster-style

            x = 0.25
            y = 0.18

            self.baseTopPosition = maprenderer.AbstractPointF(-x, -y)
            self.baseBottomPosition = maprenderer.AbstractPointF(-x, y)
            self.gasGiant.position = maprenderer.AbstractPointF(x, -y)
            self.allegiancePosition = maprenderer.AbstractPointF(x, y)

            self.baseMiddlePosition = maprenderer.AbstractPointF(-0.35, 0)
            self.starport.position = maprenderer.AbstractPointF(0, -0.225)
            self.uwp.position = maprenderer.AbstractPointF(0, 0.225)
            self.worlds.position = maprenderer.AbstractPointF(0, 0.37)#  Don't hide hex bottom, leave room for UWP

        if self.scale >= StyleSheet._WorldUwpMinScale:
            self.worldDetails |= maprenderer.WorldDetails.Uwp
            self.baseBottomPosition.setY(0.1)
            self.baseMiddlePosition.setY((self.baseBottomPosition.y() + self.baseTopPosition.y()) / 2)
            self.allegiancePosition.setY(0.1)

        if self.worlds.visible:
            fontScale = \
                1 \
                if (self.scale <= 96) or (self.style == travellermap.Style.Candy) else \
                96 / min(self.scale, 192)

            self.worlds.font = self._createFont(
                families=StyleSheet._DefaultFont,
                emSize=0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.15 * fontScale),
                style=maprenderer.FontStyle.Bold)

            if self._graphics.supportsWingdings():
                self.wingdingsFont = self._createFont(
                    families='Wingdings',
                    emSize=0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.175 * fontScale))
                self.glyphCharMap = None
            self.glyphFont = self._createFont(
                families='Arial Unicode MS,Segoe UI Symbol,Arial',
                emSize=0.175 if self.scale < StyleSheet._WorldFullMinScale else (0.15 * fontScale),
                style=maprenderer.FontStyle.Bold)

            self.uwp.font = self.hexNumber.font = self._createFont(
                families=StyleSheet._DefaultFont,
                emSize=0.1 * fontScale)
            self.worlds.smallFont = self._createFont(
                families=StyleSheet._DefaultFont,
                emSize=0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.1 * fontScale))
            self.worlds.largeFont = self.worlds.font
            self.starport.font = \
                self.worlds.smallFont \
                if (self.scale < StyleSheet._WorldFullMinScale) else \
                self.worlds.font

        self.sectorName.font = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=5.5)
        self.subsectorNames.font = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=1.5)

        overlayFontSize = max(onePixel * 12, 0.375)
        self.droyneWorlds.font = self.ancientsWorlds.font = self.minorHomeWorlds.font = \
            self._createFont(StyleSheet._DefaultFont, overlayFontSize)

        self.droyneWorlds.content = "\u2605\u2606" # BLACK STAR / WHITE STAR
        self.minorHomeWorlds.content = "\u273B" # TEARDROP-SPOKED ASTERISK
        self.ancientsWorlds.content = "\u2600" # BLACK SUN WITH RAYS

        self.microBorders.font = self._createFont(
            families=StyleSheet._DefaultFont,
            # TODO: This was == rather tan <= but in my implementation scale isn't
            # usually going to be an integer value so <= seems more appropriate.
            # Just need to check it shouldn't be >=
            emSize=0.6 if self.scale <= StyleSheet._MicroNameMinScale else 0.25,
            style=maprenderer.FontStyle.Bold)
        self.microBorders.smallFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=0.15,
            style=maprenderer.FontStyle.Bold)
        self.microBorders.largeFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=0.75,
            style=maprenderer.FontStyle.Bold)

        self.macroNames.font = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=8 / 1.4,
            style=maprenderer.FontStyle.Bold)
        self.macroNames.smallFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=5 / 1.4,
            style=maprenderer.FontStyle.Regular)
        self.macroNames.mediumFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=6.5 / 1.4,
            style=maprenderer.FontStyle.Italic)

        megaNameScaleFactor = min(35, 0.75 * onePixel)
        self.megaNames.font = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=24 * megaNameScaleFactor,
            style=maprenderer.FontStyle.Bold)
        self.megaNames.mediumFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=22 * megaNameScaleFactor,
            style=maprenderer.FontStyle.Regular)
        self.megaNames.smallFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=18 * megaNameScaleFactor,
            style=maprenderer.FontStyle.Italic)

        # Cap pen widths when zooming in
        penScale = 1 if self.scale <= 64 else (64 / self.scale)

        borderPenWidth = 1
        if self.scale >= StyleSheet._MicroBorderMinScale and \
            self.scale >= StyleSheet._ParsecMinScale:
            borderPenWidth = 0.16 * penScale

        routePenWidth = 0.2 if self.scale <= 16 else (0.08 * penScale)

        self.capitals.fillBrush = self._graphics.createBrush(
            color=travellermap.MapColours.Wheat)
        self.capitals.textBrush = self._graphics.createBrush(
            color=travellermap.MapColours.TravellerRed)
        self.amberZone.visible = self.redZone.visible = True
        self.amberZone.pen = self._graphics.createPen(
            color=travellermap.MapColours.TravellerAmber,
            width=0.05 * penScale)
        self.redZone.pen = self._graphics.createPen(
            color=travellermap.MapColours.TravellerRed,
            width=0.05 * penScale)
        self.macroBorders.pen = self._graphics.createPen(
            color=travellermap.MapColours.TravellerRed,
            width=borderPenWidth)
        self.macroRoutes.pen = self._graphics.createPen(
            color=travellermap.MapColours.White,
            width=borderPenWidth,
            style=maprenderer.LineStyle.Dash)
        self.microBorders.pen = self._graphics.createPen(
            color=travellermap.MapColours.Gray,
            width=borderPenWidth)
        self.microBorders.textBrush = self._graphics.createBrush(
            color=travellermap.MapColours.TravellerAmber)
        self.microRoutes.pen = self._graphics.createPen(
            color=travellermap.MapColours.Gray,
            width=routePenWidth)

        self.worldWater.fillBrush = self._graphics.createBrush(
            color=travellermap.MapColours.DeepSkyBlue)
        self.worldWater.pen = None
        self.worldNoWater.fillBrush = self._graphics.createBrush(
            color=travellermap.MapColours.White)
        self.worldNoWater.pen = None

        gridColor = self._colorScaleInterpolate(
            scale=self.scale,
            minScale=StyleSheet._SectorGridMinScale,
            maxScale=StyleSheet._SectorGridFullScale,
            color=travellermap.MapColours.Gray)
        self.parsecGrid.pen = self._graphics.createPen(
            color=gridColor,
            width=onePixel)
        self.subsectorGrid.pen = self._graphics.createPen(
            color=gridColor,
            width=onePixel * 2)
        self.sectorGrid.pen = self._graphics.createPen(
            color=gridColor,
            width=(4 if self.subsectorGrid.visible else 2) * onePixel)

        self.microBorders.textStyle.rotation = 0
        self.microBorders.textStyle.translation = maprenderer.AbstractPointF(0, 0)
        self.microBorders.textStyle.scale = maprenderer.SizeF(1.0, 1.0)
        self.microBorders.textStyle.uppercase = False

        self.sectorName.textStyle.rotation = -50 # degrees
        self.sectorName.textStyle.translation = maprenderer.AbstractPointF(0, 0)
        self.sectorName.textStyle.scale = maprenderer.SizeF(0.75, 1.0)
        self.sectorName.textStyle.uppercase = False
        self.sectorName.textStyle.wrap = True

        self.subsectorNames.textStyle = self.sectorName.textStyle

        self.worlds.textStyle.rotation = 0
        self.worlds.textStyle.scale = maprenderer.SizeF(1.0, 1.0)
        self.worlds.textStyle.translation = maprenderer.AbstractPointF(self.worlds.position)
        self.worlds.textStyle.uppercase = False

        self.hexNumber.position = maprenderer.AbstractPointF(0, -0.5)

        self.showNebulaBackground = False
        self.showGalaxyBackground = self.deepBackgroundOpacity > 0.0
        self.useWorldImages = False

        self.populationOverlay.fillBrush = self._graphics.createBrush(
            color='#80FFFF00')
        self.importanceOverlay.fillBrush = self._graphics.createBrush(
            color='#2080FF00')
        self.highlightWorlds.fillBrush = self._graphics.createBrush(
            color='#80FF0000')

        self.populationOverlay.pen = self._graphics.createPen(
            color='#00FF00', # TODO: Color.Empty,
            width=0.03 * penScale,
            style=maprenderer.LineStyle.Dash)
        self.importanceOverlay.pen = self._graphics.createPen(
            color='#00FF00', # TODO: Color.Empty,
            width=0.03 * penScale,
            style=maprenderer.LineStyle.Dot)
        self.highlightWorlds.pen =self._graphics.createPen(
            color='#00FF00', # TODO: Color.Empty,
            width=0.03 * penScale,
            style=maprenderer.LineStyle.DashDot)

        self.capitalOverlay.fillBrush = self._graphics.createBrush(
            color=maprenderer.makeAlphaColor(
                alpha=0x80,
                color=travellermap.MapColours.TravellerGreen))
        self.capitalOverlayAltA.fillBrush = self._graphics.createBrush(
            color=maprenderer.makeAlphaColor(
                alpha=0x80,
                color=travellermap.MapColours.Blue))
        self.capitalOverlayAltB.fillBrush = self._graphics.createBrush(
            color=maprenderer.makeAlphaColor(
                alpha=0x80,
                color=travellermap.MapColours.TravellerAmber))

        fadeSectorSubsectorNames = True

        self.placeholder.content = "*"
        self.placeholder.font = self._createFont(
            families='Georgia',
            emSize=0.6)
        self.placeholder.position = maprenderer.AbstractPointF(0, 0.17)

        self.anomaly.content = "\u2316"; # POSITION INDICATOR
        self.anomaly.font = self._createFont(
            families='Arial Unicode MS,Segoe UI Symbol',
            emSize=0.6)

        # Generic colors; applied to various elements by default (see end of this method).
        # May be overridden by specific styles
        foregroundColor = travellermap.MapColours.White
        lightColor = travellermap.MapColours.LightGray
        darkColor = travellermap.MapColours.DarkGray
        dimColor = travellermap.MapColours.DimGray
        highlightColor = travellermap.MapColours.TravellerRed

        layers: typing.List[maprenderer.LayerId] = [
            #------------------------------------------------------------
            # Background
            #------------------------------------------------------------

            maprenderer.LayerId.Background_Solid,
            maprenderer.LayerId.Background_NebulaTexture,
            maprenderer.LayerId.Background_Galaxy,
            maprenderer.LayerId.Background_PseudoRandomStars,
            maprenderer.LayerId.Background_Rifts,

            #------------------------------------------------------------
            # Foreground
            #------------------------------------------------------------

            maprenderer.LayerId.Macro_Borders,
            maprenderer.LayerId.Macro_Routes,

            maprenderer.LayerId.Grid_Sector,
            maprenderer.LayerId.Grid_Subsector,
            maprenderer.LayerId.Grid_Parsec,

            maprenderer.LayerId.Names_Subsector,

            maprenderer.LayerId.Micro_BordersFill,
            maprenderer.LayerId.Micro_BordersShade,
            maprenderer.LayerId.Micro_BordersStroke,
            maprenderer.LayerId.Micro_Routes,
            maprenderer.LayerId.Micro_BorderExplicitLabels,

            maprenderer.LayerId.Names_Sector,

            maprenderer.LayerId.Macro_GovernmentRiftRouteNames,
            maprenderer.LayerId.Macro_CapitalsAndHomeWorlds,
            maprenderer.LayerId.Mega_GalaxyScaleLabels,

            maprenderer.LayerId.Worlds_Background,
            maprenderer.LayerId.Worlds_Foreground,
            maprenderer.LayerId.Worlds_Overlays,

            #------------------------------------------------------------
            # Overlays
            #------------------------------------------------------------

            maprenderer.LayerId.Overlay_DroyneChirperWorlds,
            maprenderer.LayerId.Overlay_MinorHomeworlds,
            maprenderer.LayerId.Overlay_AncientsWorlds,
            maprenderer.LayerId.Overlay_ReviewStatus]

        if self._style is travellermap.Style.Poster:
            pass
        elif self._style is travellermap.Style.Atlas:
            self.grayscale = True
            self.lightBackground = True

            self.capitals.fillBrush.setColor(travellermap.MapColours.DarkGray)
            self.capitals.textBrush.setColor(travellermap.MapColours.Black)
            self.amberZone.pen.setColor(travellermap.MapColours.LightGray)
            self.redZone.pen.setColor(travellermap.MapColours.Black)
            self.macroBorders.pen.setColor(travellermap.MapColours.Black)
            self.macroRoutes.pen.setColor(travellermap.MapColours.Gray)
            self.microBorders.pen.setColor(travellermap.MapColours.Black)
            self.microRoutes.pen.setColor(travellermap.MapColours.Gray)

            foregroundColor = travellermap.MapColours.Black
            self.backgroundBrush.setColor(travellermap.MapColours.White)
            lightColor = travellermap.MapColours.DarkGray
            darkColor = travellermap.MapColours.DarkGray
            dimColor = travellermap.MapColours.LightGray
            highlightColor = travellermap.MapColours.Gray
            self.microBorders.textBrush.setColor(travellermap.MapColours.Gray)
            self.worldWater.fillBrush.setColor(travellermap.MapColours.Black)
            self.worldNoWater.fillBrush.setColor(travellermap.MapColours.White)
            self.worldNoWater.pen = self._graphics.createPen(
                color=travellermap.MapColours.Black,
                width=onePixel)

            self.riftOpacity = min(self.riftOpacity, 0.70)

            self.showWorldDetailColors = False

            self.populationOverlay.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x40,
                color=highlightColor))
            self.populationOverlay.pen.setColor(travellermap.MapColours.Gray)

            self.importanceOverlay.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x20,
                color=highlightColor))
            self.importanceOverlay.pen.setColor(travellermap.MapColours.Gray)

            self.highlightWorlds.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x30,
                color=highlightColor))
            self.highlightWorlds.pen.setColor(travellermap.MapColours.Gray)
        elif self._style is travellermap.Style.Fasa:
            self.showGalaxyBackground = False
            self.deepBackgroundOpacity = 0
            self.riftOpacity = 0

            inkColor = '#5C4033'

            foregroundColor = inkColor
            self.backgroundBrush.setColor(travellermap.MapColours.White)

            # NOTE: This TODO came in from the Traveller Map code
            self.grayscale = True # TODO: Tweak to be "monochrome"
            self.lightBackground = True

            self.capitals.fillBrush.setColor(inkColor)
            self.capitals.textBrush.setColor(inkColor)
            self.amberZone.pen.setColor(inkColor)
            self.amberZone.pen.setWidth(onePixel * 2)
            self.redZone.pen = None
            self.redZone.fillBrush = self._graphics.createBrush(
                color=maprenderer.makeAlphaColor(
                        alpha=0x80,
                        color=inkColor))

            self.macroBorders.pen.setColor(inkColor)
            self.macroRoutes.pen.setColor(inkColor)

            self.microBorders.pen.setColor(inkColor)
            self.microBorders.pen.setWidth(onePixel * 2)
            self.microBorders.font = self._createFont(
                families=self.microBorders.font.family(),
                emSize=self.microBorders.font.emSize() * 0.6,
                style=maprenderer.FontStyle.Regular)

            self.microRoutes.pen.setColor(inkColor)

            lightColor = maprenderer.makeAlphaColor(
                alpha=0x80,
                color=inkColor)
            darkColor = inkColor
            dimColor = inkColor
            highlightColor = inkColor
            self.microBorders.textBrush.setColor(inkColor)
            self.hexStyle = maprenderer.HexStyle.Hex
            self.microBorderStyle = maprenderer.MicroBorderStyle.Curve

            self.parsecGrid.pen.setColor(lightColor)
            self.sectorGrid.pen.setColor(lightColor)
            self.subsectorGrid.pen.setColor(lightColor)

            self.worldWater.fillBrush.setColor(inkColor)
            self.worldNoWater.fillBrush.setColor(inkColor)
            self.worldWater.pen = None
            self.worldNoWater.pen = None

            self.showWorldDetailColors = False

            self.worldDetails &= ~maprenderer.WorldDetails.Starport
            self.worldDetails &= ~maprenderer.WorldDetails.Allegiance
            self.worldDetails &= ~maprenderer.WorldDetails.Bases
            self.worldDetails &= ~maprenderer.WorldDetails.GasGiant
            self.worldDetails &= ~maprenderer.WorldDetails.Highlight
            self.worldDetails &= ~maprenderer.WorldDetails.Uwp

            if self.worlds.visible:
                self.worlds.font = self._createFont(
                    families=self.worlds.font.family(),
                    emSize=self.worlds.font.emSize() * 0.85,
                    style=self.worlds.font.style())
                self.worlds.textStyle.translation = maprenderer.AbstractPointF(0, 0.25)

            self.numberAllHexes = True
            self.hexCoordinateStyle = maprenderer.HexCoordinateStyle.Subsector
            self.overrideLineStyle = maprenderer.LineStyle.Solid

            self.populationOverlay.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x40,
                color=highlightColor))
            self.populationOverlay.pen.setColor(travellermap.MapColours.Gray)

            self.importanceOverlay.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x20,
                color=highlightColor))
            self.importanceOverlay.pen.setColor(travellermap.MapColours.Gray)

            self.highlightWorlds.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x30,
                color=highlightColor))
            self.highlightWorlds.pen.setColor(travellermap.MapColours.Gray)
        elif self._style is travellermap.Style.Print:
            self.lightBackground = True

            foregroundColor = travellermap.MapColours.Black
            self.backgroundBrush.setColor(travellermap.MapColours.White)
            lightColor = travellermap.MapColours.DarkGray
            darkColor = travellermap.MapColours.DarkGray
            dimColor = travellermap.MapColours.LightGray
            self.microRoutes.pen.setColor(travellermap.MapColours.Gray)

            self.microBorders.textBrush.setColor(travellermap.MapColours.Brown)

            self.amberZone.pen.setColor(travellermap.MapColours.TravellerAmber)
            self.worldNoWater.fillBrush.setColor(travellermap.MapColours.White)
            self.worldNoWater.pen = self._graphics.createPen(
                color=travellermap.MapColours.Black,
                width=onePixel)

            self.riftOpacity = min(self.riftOpacity, 0.70)

            self.populationOverlay.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x40,
                color=self.populationOverlay.fillBrush.color()))
            self.populationOverlay.pen.setColor(travellermap.MapColours.Gray)

            self.importanceOverlay.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x20,
                color=self.importanceOverlay.fillBrush.color()))
            self.importanceOverlay.pen.setColor(travellermap.MapColours.Gray)

            self.highlightWorlds.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x30,
                color=self.highlightWorlds.fillBrush.color()))
            self.highlightWorlds.pen.setColor(travellermap.MapColours.Gray)
        elif self._style is travellermap.Style.Draft:
            # TODO: For some reason all text is getting underlining set
            inkOpacity = 0xB0

            self.showGalaxyBackground = False
            self.lightBackground = True

            self.deepBackgroundOpacity = 0

            # TODO: I Need to handle alpha here
            self.backgroundBrush.setColor(travellermap.MapColours.AntiqueWhite)
            foregroundColor = maprenderer.makeAlphaColor(
                alpha=inkOpacity,
                color=travellermap.MapColours.Black)
            highlightColor = maprenderer.makeAlphaColor(
                alpha=inkOpacity,
                color=travellermap.MapColours.TravellerRed)

            lightColor = maprenderer.makeAlphaColor(
                alpha=inkOpacity,
                color=travellermap.MapColours.DarkCyan)
            darkColor = maprenderer.makeAlphaColor(
                alpha=inkOpacity,
                color=travellermap.MapColours.Black)
            dimColor = maprenderer.makeAlphaColor(
                alpha=inkOpacity / 2,
                color=travellermap.MapColours.Black)

            self.subsectorGrid.pen.setColor(maprenderer.makeAlphaColor(
                alpha=inkOpacity,
                color=travellermap.MapColours.Firebrick))

            # TODO: This causes a lot of fonts to be thrown away and new ones created
            fontName = 'Comic Sans MS'

            # The large font needs to be updated before the standard font as the large
            # fonts size is dependent on the standard fonts old size (based on the
            # Traveller Map code)
            if self.worlds.visible:
                self.worlds.largeFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize() * 1.25,
                    style=self.worlds.largeFont.style() | maprenderer.FontStyle.Underline)
                self.worlds.smallFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.smallFont.emSize(),
                    style=self.worlds.smallFont.style())
                self.worlds.font = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize() * 0.8,
                    style=self.worlds.font.style())
                self.worlds.textStyle.uppercase = True
                # NOTE: This TODO came in from Traveller Map
                # TODO: Decide on this. It's nice to not overwrite the parsec grid, but
                # it looks very cluttered, especially amber/red zones.
                self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.NoStyle

                self.starport.font = self._createFont(
                    families=fontName,
                    emSize=self.starport.font.emSize(),
                    style=self.starport.font.style())

            # TODO: Why is syntax highlighting unhappy here
            self.macroNames.font = self._createFont(
                families=fontName,
                emSize=self.macroNames.font.emSize(),
                style=self.macroNames.font.style())
            self.macroNames.mediumFont = self._createFont(
                families=fontName,
                emSize=self.macroNames.mediumFont.emSize(),
                style=self.macroNames.mediumFont.style())
            self.macroNames.smallFont = self._createFont(
                families=fontName,
                emSize=self.macroNames.smallFont.emSize(),
                style=self.macroNames.smallFont.style())

            self.megaNames.font = self._createFont(
                families=fontName,
                emSize=self.megaNames.font.emSize(),
                style=self.megaNames.font.style())
            self.megaNames.mediumFont = self._createFont(
                families=fontName,
                emSize=self.megaNames.mediumFont.emSize(),
                style=self.megaNames.mediumFont.style())
            self.megaNames.smallFont = self._createFont(
                families=fontName,
                emSize=self.megaNames.smallFont.emSize(),
                style=self.megaNames.smallFont.style())

            # TODO: Why is syntax highlighting unhappy here
            self.microBorders.smallFont = self._createFont(
                families=fontName,
                emSize=self.microBorders.smallFont.emSize(),
                style=self.microBorders.smallFont.style())
            self.microBorders.largeFont = self._createFont(
                families=fontName,
                emSize=self.microBorders.largeFont.emSize(),
                style=self.microBorders.largeFont.style())
            self.microBorders.font = self._createFont(
                families=fontName,
                emSize=self.microBorders.font.emSize(),
                style=self.microBorders.font.style())
            self.microBorders.textStyle.uppercase = True
            self.microBorders.textBrush.setColor(maprenderer.makeAlphaColor(
                alpha=inkOpacity,
                color=travellermap.MapColours.Brown))

            self.subsectorNames.font = self._createFont(
                families=fontName,
                emSize=self.subsectorNames.font.emSize(),
                style=self.subsectorNames.font.style())
            self.subsectorNames.textStyle.uppercase = True
            # NOTE: This TODO came in from Traveller Map
            # TODO: Render small, around edges
            self.subsectorNames.visible = False

            self.sectorName.font = self._createFont(
                families=fontName,
                emSize=self.sectorName.font.emSize(),
                style=self.sectorName.font.style())
            self.sectorName.textStyle.uppercase = True

            self.worldDetails &= ~maprenderer.WorldDetails.Allegiance

            self.microBorders.pen.setWidth(onePixel * 4)
            self.microBorders.pen.setStyle(maprenderer.LineStyle.Dot)

            self.worldNoWater.fillBrush.setColor(foregroundColor)
            self.worldWater.fillBrush = None
            self.worldWater.pen = self._graphics.createPen(
                color=foregroundColor,
                width=onePixel * 2)

            self.amberZone.pen.setColor(foregroundColor)
            self.amberZone.pen.setWidth(onePixel)
            self.redZone.pen.setWidth(onePixel * 2)

            self.microRoutes.pen.setColor(travellermap.MapColours.Gray)

            self.parsecGrid.pen.setColor(lightColor)

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.numberAllHexes = True

            self.populationOverlay.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x40,
                color=self.populationOverlay.fillBrush.color()))
            self.populationOverlay.pen.setColor(travellermap.MapColours.Gray)

            self.importanceOverlay.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x20,
                color=self.importanceOverlay.fillBrush.color()))
            self.importanceOverlay.pen.setColor(travellermap.MapColours.Gray)

            self.highlightWorlds.fillBrush.setColor(maprenderer.makeAlphaColor(
                alpha=0x30,
                color=self.highlightWorlds.fillBrush.color()))
            self.highlightWorlds.pen.setColor(travellermap.MapColours.Gray)
        elif self._style is travellermap.Style.Candy:
            self.useWorldImages = True
            self.pseudoRandomStars.visible = False
            self.fadeSectorSubsectorNames = False

            self.showNebulaBackground = self.deepBackgroundOpacity < 0.5

            self.hexStyle = maprenderer.HexStyle.NoHex
            self.microBorderStyle = maprenderer.MicroBorderStyle.Curve

            self.sectorGrid.visible = self.sectorGrid.visible and (self.scale >= 4)
            self.subsectorGrid.visible = self.subsectorGrid.visible and (self.scale >= 32)
            self.parsecGrid.visible = False

            self.subsectorGrid.pen.setWidth(0.03 * (64.0 / self.scale))
            self.subsectorGrid.pen.setStyle(
                style=maprenderer.LineStyle.Custom,
                pattern=[10.0, 8.0])

            self.sectorGrid.pen.setWidth(0.03 * (64.0 / self.scale))
            self.sectorGrid.pen.setStyle(
                style=maprenderer.LineStyle.Custom,
                pattern=[10.0, 8.0])

            self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.Shadow

            self.worldDetails = self.worldDetails &  ~maprenderer.WorldDetails.Starport & \
                ~maprenderer.WorldDetails.Allegiance & ~maprenderer.WorldDetails.Bases & \
                ~maprenderer.WorldDetails.Hex

            if self.scale < StyleSheet._CandyMinWorldNameScale:
                self.worldDetails &= ~maprenderer.WorldDetails.KeyNames & \
                ~maprenderer.WorldDetails.AllNames
            if self.scale < StyleSheet._CandyMinUwpScale:
                self.worldDetails &= ~maprenderer.WorldDetails.Uwp

            self.amberZone.pen.setColor(travellermap.MapColours.Goldenrod)
            self.amberZone.pen.setWidth(0.035)
            self.redZone.pen.setWidth(0.035)

            self.sectorName.textStyle.rotation = 0
            self.sectorName.textStyle.translation = maprenderer.AbstractPointF(0, -0.25)
            self.sectorName.textStyle.scale = maprenderer.SizeF(0.5, 0.25)
            self.sectorName.textStyle.uppercase = True

            self.subsectorNames.textStyle.rotation = 0
            self.subsectorNames.textStyle.translation = maprenderer.AbstractPointF(0, -0.25)
            self.subsectorNames.textStyle.scale = maprenderer.SizeF(0.3, 0.15) #  Expand
            self.subsectorNames.textStyle.uppercase = True

            self.subsectorNames.textBrush = self._graphics.createBrush(
                color=maprenderer.makeAlphaColor(
                    alpha=128,
                    color=travellermap.MapColours.Goldenrod))
            self.sectorName.textBrush = self._graphics.createBrush(
                color=maprenderer.makeAlphaColor(
                    alpha=128,
                    color=travellermap.MapColours.Goldenrod))

            self.microBorders.textStyle.rotation = 0
            self.microBorders.textStyle.translation = maprenderer.AbstractPointF(0, 0.25)
            self.microBorders.textStyle.scale = maprenderer.SizeF(1.0, 0.5) # Expand
            self.microBorders.textStyle.uppercase = True

            self.microBorders.pen.setColor(maprenderer.makeAlphaColor(
                alpha=128,
                color=travellermap.MapColours.TravellerRed))
            self.microRoutes.pen.setWidth(
                routePenWidth if self.scale < StyleSheet._CandyMaxRouteRelativeScale else routePenWidth / 2)
            self.macroBorders.pen.setWidth(
                borderPenWidth if self.scale < StyleSheet._CandyMaxBorderRelativeScale else borderPenWidth / 4)
            self.microBorders.pen.setWidth(
                borderPenWidth if self.scale < StyleSheet._CandyMaxBorderRelativeScale else borderPenWidth / 4)

            self.worlds.textStyle.rotation = 0
            self.worlds.textStyle.scale = maprenderer.SizeF(1, 0.5) # Expand
            self.worlds.textStyle.translation = maprenderer.AbstractPointF(0, 0)
            self.worlds.textStyle.uppercase = True

            self.gasGiant.fillBrush = self._graphics.createBrush(
                color=highlightColor)
            self.gasGiant.pen = self._graphics.createPen(
                color=highlightColor,
                width=self.gasGiantRadius / 4)

            if (self.scale > StyleSheet._CandyMaxWorldRelativeScale):
                self.hexContentScale = StyleSheet._CandyMaxWorldRelativeScale / self.scale
        elif self._style is travellermap.Style.Terminal:
            self.fadeSectorSubsectorNames = False
            self.showGalaxyBackground = False
            self.lightBackground = False

            foregroundColor = travellermap.MapColours.Cyan
            highlightColor = travellermap.MapColours.White

            lightColor = travellermap.MapColours.LightBlue
            darkColor = travellermap.MapColours.DarkBlue
            dimColor = travellermap.MapColours.DimGray

            self.subsectorGrid.pen.setColor(travellermap.MapColours.Cyan)

            # TODO: This causes a lot of fonts to be thrown away and new ones created
            fontName = 'Courier New'

            # The large font needs to be updated before the standard font as the large
            # fonts size is dependent on the standard fonts old size (based on the
            # Traveller Map code)
            if self.worlds.visible:
                self.worlds.largeFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize() * 1.25,
                    style=self.worlds.largeFont.style() | maprenderer.FontStyle.Underline)
                self.worlds.smallFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.smallFont.emSize(),
                    style=self.worlds.smallFont.style())
                self.worlds.font = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize() * 0.8,
                    style=self.worlds.font.style())
                self.worlds.textStyle.uppercase = True
                self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.NoStyle

                self.starport.font = self._createFont(
                    families=fontName,
                    emSize=self.starport.font.emSize(),
                    style=self.starport.font.style())

            self.macroNames.font = self._createFont(
                families=fontName,
                emSize=self.macroNames.font.emSize(),
                style=self.macroNames.font.style())
            self.macroNames.mediumFont = self._createFont(
                families=fontName,
                emSize=self.macroNames.mediumFont.emSize(),
                style=self.macroNames.mediumFont.style())
            self.macroNames.smallFont = self._createFont(
                families=fontName,
                emSize=self.macroNames.smallFont.emSize(),
                style=self.macroNames.smallFont.style())

            self.megaNames.font = self._createFont(
                families=fontName,
                emSize=self.megaNames.font.emSize(),
                style=self.megaNames.font.style())
            self.megaNames.mediumFont = self._createFont(
                families=fontName,
                emSize=self.megaNames.mediumFont.emSize(),
                style=self.megaNames.mediumFont.style())
            self.megaNames.smallFont = self._createFont(
                families=fontName,
                emSize=self.megaNames.smallFont.emSize(),
                style=self.megaNames.smallFont.style())

            self.microBorders.smallFont = self._createFont(
                families=fontName,
                emSize=self.microBorders.smallFont.emSize(),
                style=self.microBorders.smallFont.style())
            self.microBorders.largeFont = self._createFont(
                families=fontName,
                emSize=self.microBorders.largeFont.emSize(),
                style=self.microBorders.largeFont.style())
            self.microBorders.font = self._createFont(
                families=fontName,
                emSize=self.microBorders.font.emSize(),
                style=self.microBorders.font.style() | maprenderer.FontStyle.Underline)
            self.microBorders.textStyle.uppercase = True
            self.microBorders.pen.setWidth(onePixel * 4)
            self.microBorders.pen.setStyle(maprenderer.LineStyle.Dot)

            self.sectorName.font = self._createFont(
                families=fontName,
                emSize=self.sectorName.font.emSize() * 0.5,
                style=self.sectorName.font.style() | maprenderer.FontStyle.Bold)
            self.sectorName.textBrush = self._graphics.createBrush(
                color=foregroundColor)
            self.sectorName.textStyle.scale = maprenderer.SizeF(1, 1)
            self.sectorName.textStyle.rotation = 0
            self.sectorName.textStyle.uppercase = True

            self.subsectorNames.font = self._createFont(
                families=fontName,
                emSize=self.subsectorNames.font.emSize() * 0.5,
                style=self.subsectorNames.font.style() | maprenderer.FontStyle.Bold)
            self.subsectorNames.textBrush = self._graphics.createBrush(
                color=foregroundColor)
            self.subsectorNames.textStyle.scale = maprenderer.SizeF(1, 1)
            self.subsectorNames.textStyle.rotation = 0
            self.subsectorNames.textStyle.uppercase = True

            self.worldNoWater.fillBrush.setColor(foregroundColor)
            self.worldWater.fillBrush = None
            self.worldWater.pen = self._graphics.createPen(
                color=foregroundColor,
                width=onePixel * 2)

            self.amberZone.pen.setColor(foregroundColor)
            self.amberZone.pen.setWidth(onePixel)
            self.redZone.pen.setWidth(onePixel * 2)

            self.microRoutes.pen.setColor(travellermap.MapColours.Gray)

            self.parsecGrid.pen.setColor(travellermap.MapColours.Plum)
            self.microBorders.textBrush.setColor(travellermap.MapColours.Cyan)

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.numberAllHexes = True

            if (self.scale >= 64):
                self.subsectorNames.visible = False
        elif self._style is travellermap.Style.Mongoose:
            self.showGalaxyBackground = False
            self.lightBackground = True
            self.showGasGiantRing = True
            self.showTL = True
            self.ignoreBaseBias = True
            self.shadeMicroBorders = True

            # TODO: Need to handle moving layers
            # Re-order these elements
            #layers.MoveAfter(LayerId.Worlds_Background, LayerId.Micro_BordersStroke);
            #layers.MoveAfter(LayerId.Worlds_Foreground, LayerId.Micro_Routes);

            self.deepBackgroundOpacity = 0

            self.backgroundBrush.setColor('#E6E7E8')
            foregroundColor = travellermap.MapColours.Black
            highlightColor = travellermap.MapColours.Red

            lightColor = travellermap.MapColours.Black
            darkColor = travellermap.MapColours.Black
            dimColor = travellermap.MapColours.Gray

            self.sectorGrid.pen.setColor(foregroundColor)
            self.subsectorGrid.pen.setColor(foregroundColor)
            self.parsecGrid.pen.setColor(foregroundColor)

            self.microBorders.textBrush.setColor(travellermap.MapColours.DarkSlateGray)

            fontName = 'Calibri,Arial'

            self.worldDetails &= ~maprenderer.WorldDetails.Allegiance

            if self.worlds.visible:
                self.worlds.font = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize(),
                    style=maprenderer.FontStyle.Regular)
                self.worlds.smallFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.smallFont.emSize(),
                    style=self.worlds.smallFont.style())
                self.worlds.largeFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.largeFont.emSize(),
                    style=maprenderer.FontStyle.Bold)
                self.worlds.textStyle.uppercase = True
                self.worlds.textStyle.translation = maprenderer.AbstractPointF(0, -0.04)
                self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.NoStyle

                self.starport.font = self._createFont(
                    families=fontName,
                    emSize=self.starport.font.emSize(),
                    style=maprenderer.FontStyle.Italic)
                self.starport.position = maprenderer.AbstractPointF(0.175, 0.17)

                self.hexNumber.font = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize(),
                    style=self.worlds.font.style())
                self.hexNumber.position.setY(-0.49)

                self.uwp.font = self.hexNumber.font
                self.uwp.textBackgroundStyle = maprenderer.TextBackgroundStyle.Filled
                self.uwp.position = maprenderer.AbstractPointF(0, 0.40)
                self.uwp.fillBrush = self._graphics.createBrush(
                    color=travellermap.MapColours.Black)
                self.uwp.textBrush = self._graphics.createBrush(
                    color=travellermap.MapColours.White)

            self.macroNames.font = self._createFont(
                families=fontName,
                emSize=self.macroNames.font.emSize(),
                style=self.macroNames.font.style())
            self.macroNames.mediumFont = self._createFont(
                families=fontName,
                emSize=self.macroNames.mediumFont.emSize(),
                style=self.macroNames.mediumFont.style())
            self.macroNames.smallFont = self._createFont(
                families=fontName,
                emSize=self.macroNames.smallFont.emSize(),
                style=self.macroNames.smallFont.style())

            self.megaNames.font = self._createFont(
                families=fontName,
                emSize=self.megaNames.font.emSize(),
                style=self.megaNames.font.style())
            self.megaNames.mediumFont = self._createFont(
                families=fontName,
                emSize=self.megaNames.mediumFont.emSize(),
                style=self.megaNames.mediumFont.style())
            self.megaNames.smallFont = self._createFont(
                families=fontName,
                emSize=self.megaNames.smallFont.emSize(),
                style=self.megaNames.smallFont.style())

            self.microBorders.smallFont = self._createFont(
                families=fontName,
                emSize=self.microBorders.smallFont.emSize(),
                style=self.microBorders.smallFont.style())
            self.microBorders.largeFont = self._createFont(
                families=fontName,
                emSize=self.microBorders.largeFont.emSize(),
                style=self.microBorders.largeFont.style())
            self.microBorders.font = self._createFont(
                families=fontName,
                emSize=self.microBorders.font.emSize(),
                style=self.microBorders.font.style())
            self.microBorders.textStyle.uppercase = True
            self.microBorders.pen.setWidth(0.11)
            self.microBorders.pen.setStyle(maprenderer.LineStyle.Dot)
            self.microBorders.textBrush.setColor(travellermap.MapColours.DarkSlateGray)

            self.sectorName.font = self._createFont(
                families=fontName,
                emSize=self.sectorName.font.emSize(),
                style=self.sectorName.font.style())
            self.sectorName.textStyle.uppercase = True

            self.subsectorNames.font = self._createFont(
                families=fontName,
                emSize=self.subsectorNames.font.emSize(),
                style=self.subsectorNames.font.style())
            self.subsectorNames.textStyle.uppercase = True
            self.subsectorNames.visible = False

            self.worldWater.fillBrush.setColor(travellermap.MapColours.MediumBlue)
            self.worldNoWater.fillBrush.setColor(travellermap.MapColours.DarkKhaki)
            self.worldWater.pen = self._graphics.createPen(
                color=travellermap.MapColours.DarkGray,
                width=onePixel * 2)
            self.worldNoWater.pen = self._graphics.createPen(
                color=travellermap.MapColours.DarkGray,
                width=onePixel * 2)

            self.showZonesAsPerimeters = True

            self.greenZone.visible = True
            self.greenZone.pen = self._graphics.createPen(
                color='#80C676',
                width=0.05)
            self.amberZone.pen.setColor('#FBB040')
            self.amberZone.pen.setWidth(0.05)
            self.redZone.pen.setColor(travellermap.MapColours.Red)
            self.redZone.pen.setWidth(0.05)

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.discRadius = 0.11
            self.gasGiant.position = maprenderer.AbstractPointF(0, -0.23)
            self.baseTopPosition = maprenderer.AbstractPointF(-0.22, -0.21)
            self.baseMiddlePosition = maprenderer.AbstractPointF(-0.32, 0.17)
            self.baseBottomPosition = maprenderer.AbstractPointF(0.22, -0.21)
            self.discPosition = maprenderer.AbstractPointF(-self.discRadius, 0.16)

        # NOTE: This TODO came in with traveller map
        # TODO: Do this with opacity.
        if fadeSectorSubsectorNames and \
            (not self.sectorName.textBrush or not self.subsectorNames.textBrush):
            if self.scale < 16:
                fadeColor = foregroundColor
            elif self.scale < 48:
                fadeColor = darkColor
            else:
                fadeColor = dimColor

            fadeBrush = self._graphics.createBrush(color=fadeColor)
            if not self.sectorName.textBrush:
                self.sectorName.textBrush = fadeBrush
            if not self.subsectorNames.textBrush:
                self.subsectorNames.textBrush = fadeBrush

        # Base element colors on foreground/light/dim/dark/highlight, if not specified by style.
        if not self.pseudoRandomStars.fillBrush:
            self.pseudoRandomStars.fillBrush = self._graphics.createBrush(
                color=foregroundColor)

        if not self.droyneWorlds.textBrush:
            self.droyneWorlds.textBrush = self.microBorders.textBrush
        if not self.minorHomeWorlds.textBrush:
            self.minorHomeWorlds.textBrush = self.microBorders.textBrush
        if not self.ancientsWorlds.textBrush:
            self.ancientsWorlds.textBrush = self.microBorders.textBrush

        if not self.megaNames.textBrush:
            self.megaNames.textBrush = self._graphics.createBrush(
                color=foregroundColor)
        if not self.megaNames.textHighlightBrush:
            self.megaNames.textHighlightBrush = self._graphics.createBrush(
                color=highlightColor)

        if not self.macroNames.textBrush:
            self.macroNames.textBrush = self._graphics.createBrush(
                color=foregroundColor)
        if not self.macroNames.textHighlightBrush:
            self.macroNames.textHighlightBrush = self._graphics.createBrush(
                color=highlightColor)

        if not self.macroRoutes.textBrush:
            self.macroRoutes.textBrush = self._graphics.createBrush(
                color=foregroundColor)
        if not self.macroRoutes.textHighlightBrush:
            self.macroRoutes.textHighlightBrush = self._graphics.createBrush(
                color=highlightColor)

        if not self.worlds.textBrush:
            self.worlds.textBrush = self._graphics.createBrush(
                color=foregroundColor)
        if not self.worlds.textHighlightBrush:
            self.worlds.textHighlightBrush = self._graphics.createBrush(
                color=highlightColor)

        if not self.hexNumber.textBrush:
            self.hexNumber.textBrush = self._graphics.createBrush(
                color=lightColor)
        if not self.uwp.textBrush:
            self.uwp.textBrush = self._graphics.createBrush(
                color=foregroundColor)

        if not self.placeholder.textBrush:
            self.placeholder.textBrush = self._graphics.createBrush(
                color=foregroundColor)
        if not self.anomaly.textBrush:
            self.anomaly.textBrush = self._graphics.createBrush(
                color=highlightColor)

        if not self.gasGiant.fillBrush:
            self.gasGiant.fillBrush = self.worlds.textBrush
        if not self.gasGiant.pen:
            self.gasGiant.pen = self._graphics.createPen(
                color=self.worlds.textBrush.color(),
                width=self.gasGiantRadius / 4)

        if self.showWorldDetailColors:
            self.worldRichAgricultural.fillBrush = self._graphics.createBrush(
                color=travellermap.MapColours.TravellerAmber)
            self.worldAgricultural.fillBrush = self._graphics.createBrush(
                color=travellermap.MapColours.TravellerGreen)
            self.worldRich.fillBrush = self._graphics.createBrush(
                color=travellermap.MapColours.Purple)
            self.worldIndustrial.fillBrush = self._graphics.createBrush(
                color='#888888') # Gray
            self.worldHarshAtmosphere.fillBrush = self._graphics.createBrush(
                color='#CC6626') # Rust
            self.worldVacuum.fillBrush = self._graphics.createBrush(
                color=travellermap.MapColours.Black)
            self.worldVacuum.fillBrush = self._graphics.createBrush(
                color=travellermap.MapColours.Black)
            self.worldVacuum.pen = self._graphics.createPen(
                color=travellermap.MapColours.White,
                width=self.worldWater.pen.width() if self.worldWater.pen else onePixel,
                style=self.worldWater.pen.style() if self.worldWater.pen else maprenderer.LineStyle.Solid,
                pattern=self.worldWater.pen.pattern()if self.worldWater.pen else None)

        # Convert list into a id -> index mapping.
        self.layerOrder.clear()
        for i, layer in enumerate(layers):
            self.layerOrder[layer] = i

    def _createFont(
            self,
            families: str,
            emSize: float,
            style: maprenderer.FontStyle = maprenderer.FontStyle.Regular
            ) -> maprenderer.AbstractFont:
        for family in families.split(','):
            key = (family, emSize, style)
            font = self._fontCache.get(key)
            if font:
                return font

            try:
                font = self._graphics.createFont(
                    family=family,
                    emSize=emSize,
                    style=style)
            except:
                # TODO: Log something at debug level
                continue

            if font:
                self._fontCache[key] = font
                return font

        raise RuntimeError(f'No font found out of families list "{families}"')

    @staticmethod
    def _floatScaleInterpolate(
            minValue: float,
            maxValue: float,
            scale: float,
            minScale: float,
            maxScale: float
            ) -> float:
        if scale <= minScale:
            return minValue
        if scale >= maxScale:
            return maxValue

        logscale = math.log2(scale)
        logmin = math.log2(minScale)
        logmax = math.log2(maxScale)
        p = (logscale - logmin) / (logmax - logmin)
        value = minValue + (maxValue - minValue) * p
        return value

    @staticmethod
    def _colorScaleInterpolate(
            scale: float,
            minScale: float,
            maxScale: float,
            color: str
            ) -> str:
        alpha = StyleSheet._floatScaleInterpolate(
            minValue=0,
            maxValue=255,
            scale=scale,
            minScale=minScale,
            maxScale=maxScale)
        return maprenderer.makeAlphaColor(
            alpha=alpha,
            color=color)