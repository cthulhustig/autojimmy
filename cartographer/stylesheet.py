import common
import logging
import cartographer
import math
import travellermap
import typing

class LayerList(list):
    def __init__(self, other: typing.Optional[typing.Sequence[cartographer.LayerId]]):
        if other:
            self.extend(other)

    def copy(self) -> 'LayerList':
        return LayerList(self)

    def moveAfter(self, target: cartographer.LayerId, item: cartographer.LayerId) -> None:
        self.remove(item)
        index = self.index(target)
        self.insert(index + 1 if index >= 0 else len(self), item)

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

    _FontCacheSize = 100

    _DefaultLayerOrder = LayerList([
        # Background
        cartographer.LayerId.Background_Solid,
        cartographer.LayerId.Background_NebulaTexture,
        cartographer.LayerId.Background_Galaxy,
        cartographer.LayerId.Background_PseudoRandomStars,
        cartographer.LayerId.Background_Rifts,

        # Foreground
        cartographer.LayerId.Macro_Borders,
        cartographer.LayerId.Macro_Routes,
        cartographer.LayerId.Grid_Sector,
        cartographer.LayerId.Grid_Subsector,
        cartographer.LayerId.Grid_Parsec,
        cartographer.LayerId.Names_Subsector,
        cartographer.LayerId.Micro_BordersBackground,
        cartographer.LayerId.Micro_BordersForeground,
        cartographer.LayerId.Micro_Routes,
        cartographer.LayerId.Micro_BorderExplicitLabels,
        cartographer.LayerId.Names_Sector,
        cartographer.LayerId.Macro_GovernmentRiftRouteNames,
        cartographer.LayerId.Macro_CapitalsAndHomeWorlds,
        cartographer.LayerId.Mega_GalaxyScaleLabels,
        cartographer.LayerId.Worlds_Background,
        cartographer.LayerId.Worlds_Foreground,
        cartographer.LayerId.Worlds_Overlays,

        # Overlays
        cartographer.LayerId.Overlay_DroyneChirperWorlds,
        cartographer.LayerId.Overlay_MinorHomeworlds,
        cartographer.LayerId.Overlay_AncientsWorlds,
        cartographer.LayerId.Overlay_ReviewStatus])

    class StyleElement(object):
        def __init__(self) -> None:
            self.visible = False
            self.content = ''
            self.linePen: typing.Optional[cartographer.AbstractPen] = None
            self.fillBrush: typing.Optional[cartographer.AbstractBrush] = None
            self.textBrush: typing.Optional[cartographer.AbstractBrush] = None
            self.textHighlightBrush: typing.Optional[cartographer.AbstractBrush] = None

            self.textStyle = cartographer.LabelStyle()
            self.textBackgroundStyle = cartographer.TextBackgroundStyle.NoStyle
            self.font: typing.Optional[cartographer.AbstractFont] = None
            self.smallFont: typing.Optional[cartographer.AbstractFont] = None
            self.mediumFont: typing.Optional[cartographer.AbstractFont] = None
            self.largeFont: typing.Optional[cartographer.AbstractFont] = None
            self.position = cartographer.PointF()

    def __init__(
            self,
            scale: float,
            options: cartographer.RenderOptions,
            style: travellermap.MapStyle,
            graphics: cartographer.AbstractGraphics
            ):
        self._scale = scale
        self._options = options
        self._style = style
        self._graphics = graphics
        self._fontCache = common.LRUCache[
            typing.Tuple[
                str, # Family
                int, # emSize
                cartographer.FontStyle
                ],
            cartographer.AbstractFont](capacity=StyleSheet._FontCacheSize)
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
    def options(self) -> cartographer.RenderOptions:
        return self._options

    @options.setter
    def options(self, options: cartographer.RenderOptions) -> None:
        if options == self._options:
            return # Nothing to do
        self._options = options
        self._handleConfigUpdate()

    @property
    def style(self) -> travellermap.MapStyle:
        return self._style

    @style.setter
    def style(self, style: travellermap.MapStyle) -> None:
        if style == self._style:
            return # Nothing to do
        self._style = style
        self._handleConfigUpdate()

    @property
    def hasWorldOverlays(self) -> bool:
        return self.populationOverlay.visible or \
            self.importanceOverlay.visible or  \
            self.showStellarOverlay or \
            self.capitalOverlay.visible

    def _handleConfigUpdate(self) -> None:
        # Options

        self.backgroundBrush = self._graphics.createBrush(
            colour=common.HtmlColours.Black)

        self.showNebulaBackground = False
        self.showGalaxyBackground = False
        self.useWorldImages = False
        self.dimUnofficialSectors = False
        self.colourCodeSectorStatus = False

        self.deepBackgroundOpacity = 0.0

        self.grayscale = False
        self.lightBackground = False

        self.showRiftOverlay = False
        self.riftOpacity = 0.0

        self.hexContentScale = 1.0

        self.routeEndAdjust = 0.25

        self.t5AllegianceCodes = False

        self.droyneWorlds = StyleSheet.StyleElement()
        self.ancientsWorlds = StyleSheet.StyleElement()
        self.minorHomeWorlds = StyleSheet.StyleElement()

        # Worlds
        self.worlds = StyleSheet.StyleElement()
        self.showWorldDetailColours = False
        self.populationOverlay = StyleSheet.StyleElement()
        self.importanceOverlay = StyleSheet.StyleElement()
        self.capitalOverlay = StyleSheet.StyleElement()
        self.capitalOverlayAltA = StyleSheet.StyleElement()
        self.capitalOverlayAltB = StyleSheet.StyleElement()
        self.showStellarOverlay = False

        self.discPosition = cartographer.PointF(0, 0)
        self.discRadius = 0.1
        self.gasGiantRadius = 0.05
        self.allegiancePosition = cartographer.PointF(0, 0)
        self.baseTopPosition = cartographer.PointF(0, 0)
        self.baseBottomPosition = cartographer.PointF(0, 0)
        self.baseMiddlePosition = cartographer.PointF(0, 0)

        self.uwp = StyleSheet.StyleElement()
        self.starport = StyleSheet.StyleElement()

        self.worldDetails: cartographer.WorldDetails = cartographer.WorldDetails.NoDetails
        self.lowerCaseAllegiance = False

        self.wingdingFont: typing.Optional[cartographer.AbstractFont] = None
        self.glyphFont: typing.Optional[cartographer.AbstractFont] = None

        self.showGasGiantRing = False

        self.showTL = False
        self.ignoreBaseBias = False
        self.showZonesAsPerimeters = False

        # Hex Coordinates
        self.hexNumber = StyleSheet.StyleElement()
        self.hexCoordinateStyle = cartographer.HexCoordinateStyle.Sector
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
        self.microBorderStyle = cartographer.MicroBorderStyle.Hex
        self.overrideLineStyle: typing.Optional[cartographer.LineStyle] = None

        self.layerOrder = StyleSheet._DefaultLayerOrder.copy()

        onePixel = 1.0 / self.scale

        self.subsectorGrid.visible = (self.scale >= StyleSheet._SubsectorsMinScale) and \
            ((self.options & cartographer.RenderOptions.SubsectorGrid) != 0)
        self.sectorGrid.visible = (self.scale >= StyleSheet._SectorGridMinScale) and \
            ((self._options & cartographer.RenderOptions.SectorGrid) != 0)
        self.parsecGrid.visible = (self.scale >= StyleSheet._ParsecMinScale)
        self.showSomeSectorNames = (self.scale >= StyleSheet._SectorNameMinScale) and \
            (self.scale <= StyleSheet._SectorNameMaxScale) and \
            ((self._options & cartographer.RenderOptions.SectorsMask) != 0)
        self.showAllSectorNames = self.showSomeSectorNames and \
            ((self.scale >= StyleSheet._SectorNameAllSelectedScale) or \
             ((self._options & cartographer.RenderOptions.SectorsAll) != 0))
        self.subsectorNames.visible = (self.scale >= StyleSheet._SubsectorNameMinScale) and \
            (self.scale <= StyleSheet._SubsectorNameMaxScale) and \
            ((self._options & cartographer.RenderOptions.SectorsMask) != 0)

        self.worlds.visible = self.scale >= StyleSheet._WorldMinScale
        self.pseudoRandomStars.visible = (StyleSheet._PseudoRandomStarsMinScale <= self.scale) and \
            (self.scale <= StyleSheet._PseudoRandomStarsMaxScale)
        self.showRiftOverlay = (self.scale <= StyleSheet._PseudoRandomStarsMaxScale) or \
            (StyleSheet.style == travellermap.MapStyle.Candy)

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

        self.macroNames.visible = (self.scale >= StyleSheet._MacroLabelMinScale) and \
            (self.scale <= StyleSheet._MacroLabelMaxScale)
        self.megaNames.visible = self.scale <= StyleSheet._MegaLabelMaxScale and \
            ((self.options & cartographer.RenderOptions.NamesMask) != 0)
        self.showMicroNames = (self.scale >= StyleSheet._MicroNameMinScale) and \
            ((self.options & cartographer.RenderOptions.NamesMask) != 0)
        self.capitals.visible = (self.scale >= StyleSheet._MacroWorldsMinScale) and \
            (self.scale <= StyleSheet._MacroWorldsMaxScale)

        self.microBorderStyle = cartographer.MicroBorderStyle.Hex

        self.macroBorders.visible = (self.scale >= StyleSheet._MacroBorderMinScale) and \
            (self.scale < StyleSheet._MicroBorderMinScale) and \
            ((self.options & cartographer.RenderOptions.BordersMask) != 0)
        self.microBorders.visible = (self.scale >= StyleSheet._MicroBorderMinScale) and \
            ((self.options & cartographer.RenderOptions.BordersMask) != 0)
        self.fillMicroBorders = self.microBorders.visible and \
            ((self.options & cartographer.RenderOptions.FilledBorders) != 0)
        self.microRoutes.visible = (self.scale >= StyleSheet._RouteMinScale) and \
            ((self.options & cartographer.RenderOptions.RoutesMask) != 0)
        self.macroRoutes.visible = (self.scale >= StyleSheet._MacroRouteMinScale) and \
            (self.scale <= StyleSheet._MacroRouteMaxScale) and \
            ((self.options & cartographer.RenderOptions.RoutesMask) != 0)

        if self.scale < StyleSheet._WorldBasicMinScale:
            self.worldDetails = cartographer.WorldDetails.Dotmap
        elif self.scale < StyleSheet._WorldFullMinScale:
            self.worldDetails = cartographer.WorldDetails.Atlas
        else:
            self.worldDetails = cartographer.WorldDetails.Poster

        self.discRadius = 0.1 if ((self.worldDetails & cartographer.WorldDetails.Type) != 0) else  0.2

        self.showWorldDetailColours = self.worldDetails == cartographer.WorldDetails.Poster and \
            ((self.options & cartographer.RenderOptions.WorldColours) != 0)
        self.populationOverlay.visible = (self.options & cartographer.RenderOptions.PopulationOverlay) != 0
        self.importanceOverlay.visible = (self.options & cartographer.RenderOptions.ImportanceOverlay) != 0
        self.capitalOverlay.visible = (self.options & cartographer.RenderOptions.CapitalOverlay) != 0
        self.showStellarOverlay = (self._options & cartographer.RenderOptions.StellarOverlay) != 0
        self.ancientsWorlds.visible = (self.options & cartographer.RenderOptions.AncientWorlds) != 0
        self.droyneWorlds.visible = (self.options & cartographer.RenderOptions.DroyneWorlds) != 0
        self.minorHomeWorlds.visible = (self.options & cartographer.RenderOptions.MinorHomeWorlds) != 0

        # NOTE: Force ancient worlds, droyne worlds & minor home world overlays
        # off when zoomed out as the further you zoom out the longer it takes
        # to draw up to the point it locks everything up
        if self.scale < 2:
            self.ancientsWorlds.visible = self.droyneWorlds.visible = \
                self.minorHomeWorlds.visible = False

        self.lowerCaseAllegiance = (self.scale < StyleSheet._WorldFullMinScale)

        self.showGasGiantRing = (self.scale >= StyleSheet._WorldUwpMinScale)
        self.gasGiant.visible = True

        self.worlds.textBackgroundStyle = cartographer.TextBackgroundStyle.Rectangle

        self.hexCoordinateStyle = cartographer.HexCoordinateStyle.Sector
        self.numberAllHexes = False

        self.dimUnofficialSectors = (self.options & cartographer.RenderOptions.DimUnofficial) != 0
        self.colourCodeSectorStatus = (self.options & cartographer.RenderOptions.ColourCodeSectorStatus) != 0

        if self.scale < StyleSheet._WorldFullMinScale:
            # Atlas-style

            x = 0.225
            y = 0.125

            self.baseTopPosition = cartographer.PointF(-x, -y)
            self.baseBottomPosition = cartographer.PointF(-x, y)
            self.gasGiant.position = cartographer.PointF(x, -y)
            self.allegiancePosition = cartographer.PointF(x, y)

            self.baseMiddlePosition = cartographer.PointF(-0.2, 0)
            self.starport.position = cartographer.PointF(0, -0.24)
            self.uwp.position = cartographer.PointF(0, 0.24)
            self.worlds.position = cartographer.PointF(0, 0.4)
        else:
            # Poster-style

            x = 0.25
            y = 0.18

            self.baseTopPosition = cartographer.PointF(-x, -y)
            self.baseBottomPosition = cartographer.PointF(-x, y)
            self.gasGiant.position = cartographer.PointF(x, -y)
            self.allegiancePosition = cartographer.PointF(x, y)

            self.baseMiddlePosition = cartographer.PointF(-0.35, 0)
            self.starport.position = cartographer.PointF(0, -0.225)
            self.uwp.position = cartographer.PointF(0, 0.225)
            self.worlds.position = cartographer.PointF(0, 0.37)#  Don't hide hex bottom, leave room for UWP

        if self.scale >= StyleSheet._WorldUwpMinScale:
            self.worldDetails |= cartographer.WorldDetails.Uwp
            self.baseBottomPosition.setY(0.1)
            self.baseMiddlePosition.setY((self.baseBottomPosition.y() + self.baseTopPosition.y()) / 2)
            self.allegiancePosition.setY(0.1)

        if self.worlds.visible:
            fontScale = \
                1 \
                if (self.scale <= 96) or (self.style == travellermap.MapStyle.Candy) else \
                96 / min(self.scale, 192)

            self.worlds.font = self._createFont(
                families=StyleSheet._DefaultFont,
                emSize=0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.15 * fontScale),
                style=cartographer.FontStyle.Bold)

            if self._graphics.supportsWingdings():
                self.wingdingFont = self._createFont(
                    families='Wingdings',
                    emSize=0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.175 * fontScale))
                self.glyphCharMap = None
            self.glyphFont = self._createFont(
                families='Arial Unicode MS,Segoe UI Symbol,Arial',
                emSize=0.175 if self.scale < StyleSheet._WorldFullMinScale else (0.15 * fontScale),
                style=cartographer.FontStyle.Bold)

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
            emSize=0.6 if self.scale <= StyleSheet._MicroNameMinScale else 0.25,
            style=cartographer.FontStyle.Bold)
        self.microBorders.smallFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=0.15,
            style=cartographer.FontStyle.Bold)
        self.microBorders.largeFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=0.75,
            style=cartographer.FontStyle.Bold)

        self.macroNames.font = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=8 / 1.4,
            style=cartographer.FontStyle.Bold)
        self.macroNames.smallFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=5 / 1.4,
            style=cartographer.FontStyle.Regular)
        self.macroNames.mediumFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=6.5 / 1.4,
            style=cartographer.FontStyle.Italic)

        megaNameScaleFactor = min(35, 0.75 * onePixel)
        self.megaNames.font = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=24 * megaNameScaleFactor,
            style=cartographer.FontStyle.Bold)
        self.megaNames.mediumFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=22 * megaNameScaleFactor,
            style=cartographer.FontStyle.Regular)
        self.megaNames.smallFont = self._createFont(
            families=StyleSheet._DefaultFont,
            emSize=18 * megaNameScaleFactor,
            style=cartographer.FontStyle.Italic)

        # Cap pen widths when zooming in
        penScale = 1 if self.scale <= 64 else (64 / self.scale)

        borderPenWidth = 1
        if self.scale >= StyleSheet._MicroBorderMinScale and \
                self.scale >= StyleSheet._ParsecMinScale:
            borderPenWidth = 0.16 * penScale

        routePenWidth = 0.2 if self.scale <= 16 else (0.08 * penScale)

        self.capitals.fillBrush = self._graphics.createBrush(
            colour=common.HtmlColours.Wheat)
        self.capitals.textBrush = self._graphics.createBrush(
            colour=common.HtmlColours.TravellerRed)
        self.amberZone.visible = self.redZone.visible = True
        self.amberZone.linePen = self._graphics.createPen(
            colour=common.HtmlColours.TravellerAmber,
            width=0.05 * penScale)
        self.redZone.linePen = self._graphics.createPen(
            colour=common.HtmlColours.TravellerRed,
            width=0.05 * penScale)
        self.macroBorders.linePen = self._graphics.createPen(
            colour=common.HtmlColours.TravellerRed,
            width=borderPenWidth)
        self.macroRoutes.linePen = self._graphics.createPen(
            colour=common.HtmlColours.White,
            width=borderPenWidth,
            style=cartographer.LineStyle.Dash)
        self.microBorders.linePen = self._graphics.createPen(
            colour=common.HtmlColours.Gray,
            width=borderPenWidth)
        self.microBorders.textBrush = self._graphics.createBrush(
            colour=common.HtmlColours.TravellerAmber)
        self.microRoutes.linePen = self._graphics.createPen(
            colour=common.HtmlColours.Gray,
            width=routePenWidth)

        self.worldWater.fillBrush = self._graphics.createBrush(
            colour=common.HtmlColours.DeepSkyBlue)
        self.worldWater.linePen = None
        self.worldNoWater.fillBrush = self._graphics.createBrush(
            colour=common.HtmlColours.White)
        self.worldNoWater.linePen = None

        gridColour = self._colourScaleInterpolate(
            scale=self.scale,
            minScale=StyleSheet._SectorGridMinScale,
            maxScale=StyleSheet._SectorGridFullScale,
            colour=common.HtmlColours.Gray)
        self.parsecGrid.linePen = self._graphics.createPen(
            colour=gridColour,
            width=onePixel)
        self.subsectorGrid.linePen = self._graphics.createPen(
            colour=gridColour,
            width=onePixel * 2)
        self.sectorGrid.linePen = self._graphics.createPen(
            colour=gridColour,
            width=(4 if self.subsectorGrid.visible else 2) * onePixel)

        self.microBorders.textStyle.rotation = 0
        self.microBorders.textStyle.translation = cartographer.PointF(0, 0)
        self.microBorders.textStyle.scale = cartographer.SizeF(1.0, 1.0)
        self.microBorders.textStyle.uppercase = False

        self.sectorName.textStyle.rotation = -50 # degrees
        self.sectorName.textStyle.translation = cartographer.PointF(0, 0)
        self.sectorName.textStyle.scale = cartographer.SizeF(0.75, 1.0)
        self.sectorName.textStyle.uppercase = False
        self.sectorName.textStyle.wrap = True

        self.subsectorNames.textStyle = self.sectorName.textStyle

        self.worlds.textStyle.rotation = 0
        self.worlds.textStyle.scale = cartographer.SizeF(1.0, 1.0)
        self.worlds.textStyle.translation = cartographer.PointF(self.worlds.position)
        self.worlds.textStyle.uppercase = False

        self.hexNumber.position = cartographer.PointF(0, -0.5)

        self.showNebulaBackground = False
        self.showGalaxyBackground = self.deepBackgroundOpacity > 0.0
        self.useWorldImages = False

        self.populationOverlay.fillBrush = self._graphics.createBrush(
            colour='#80FFFF00')
        self.importanceOverlay.fillBrush = self._graphics.createBrush(
            colour='#2080FF00')

        self.capitalOverlay.fillBrush = self._graphics.createBrush(
            colour=cartographer.makeAlphaColour(
                alpha=0x80,
                colour=common.HtmlColours.TravellerGreen))
        self.capitalOverlayAltA.fillBrush = self._graphics.createBrush(
            colour=cartographer.makeAlphaColour(
                alpha=0x80,
                colour=common.HtmlColours.Blue))
        self.capitalOverlayAltB.fillBrush = self._graphics.createBrush(
            colour=cartographer.makeAlphaColour(
                alpha=0x80,
                colour=common.HtmlColours.TravellerAmber))

        fadeSectorSubsectorNames = True

        self.placeholder.content = "*"
        self.placeholder.font = self._createFont(
            families='Georgia',
            emSize=0.6)
        self.placeholder.position = cartographer.PointF(0, 0.17)

        self.anomaly.content = "\u2316"; # POSITION INDICATOR
        self.anomaly.font = self._createFont(
            families='Arial Unicode MS,Segoe UI Symbol',
            emSize=0.6)

        # Generic colours; applied to various elements by default (see end of this method).
        # May be overridden by specific styles
        foregroundColour = common.HtmlColours.White
        lightColour = common.HtmlColours.LightGray
        darkColour = common.HtmlColours.DarkGray
        dimColour = common.HtmlColours.DimGray
        highlightColour = common.HtmlColours.TravellerRed

        if self._style is travellermap.MapStyle.Poster:
            pass
        elif self._style is travellermap.MapStyle.Atlas:
            self.grayscale = True
            self.lightBackground = True

            self.capitals.fillBrush.setColour(common.HtmlColours.DarkGray)
            self.capitals.textBrush.setColour(common.HtmlColours.Black)
            self.amberZone.linePen.setColour(common.HtmlColours.LightGray)
            self.redZone.linePen.setColour(common.HtmlColours.Black)
            self.macroBorders.linePen.setColour(common.HtmlColours.Black)
            self.macroRoutes.linePen.setColour(common.HtmlColours.Gray)
            self.microBorders.linePen.setColour(common.HtmlColours.Black)
            self.microRoutes.linePen.setColour(common.HtmlColours.Gray)

            foregroundColour = common.HtmlColours.Black
            self.backgroundBrush.setColour(common.HtmlColours.White)
            lightColour = common.HtmlColours.DarkGray
            darkColour = common.HtmlColours.DarkGray
            dimColour = common.HtmlColours.LightGray
            highlightColour = common.HtmlColours.Gray
            self.microBorders.textBrush.setColour(common.HtmlColours.Gray)
            self.worldWater.fillBrush.setColour(common.HtmlColours.Black)
            self.worldNoWater.fillBrush.setColour(common.HtmlColours.White)
            self.worldNoWater.linePen = self._graphics.createPen(
                colour=common.HtmlColours.Black,
                width=onePixel)

            self.riftOpacity = min(self.riftOpacity, 0.70)

            self.showWorldDetailColours = False

            self.populationOverlay.fillBrush.setColour(cartographer.makeAlphaColour(
                alpha=0x40,
                colour=highlightColour))
            self.populationOverlay.linePen = self._graphics.createPen(
                colour=common.HtmlColours.Gray,
                width=0.03 * penScale,
                style=cartographer.LineStyle.Dash)

            self.importanceOverlay.fillBrush.setColour(cartographer.makeAlphaColour(
                alpha=0x20,
                colour=highlightColour))
            self.importanceOverlay.linePen = self._graphics.createPen(
                colour=common.HtmlColours.Gray,
                width=0.03 * penScale,
                style=cartographer.LineStyle.Dot)
        elif self._style is travellermap.MapStyle.Fasa:
            self.showGalaxyBackground = False
            self.deepBackgroundOpacity = 0
            self.riftOpacity = 0

            inkColour = '#5C4033'

            foregroundColour = inkColour
            self.backgroundBrush.setColour(common.HtmlColours.White)

            self.grayscale = True
            self.lightBackground = True

            self.capitals.fillBrush.setColour(inkColour)
            self.capitals.textBrush.setColour(inkColour)
            self.amberZone.linePen.setColour(inkColour)
            self.amberZone.linePen.setWidth(onePixel * 2)
            self.redZone.linePen = None
            self.redZone.fillBrush = self._graphics.createBrush(
                colour=cartographer.makeAlphaColour(
                    alpha=0x80,
                    colour=inkColour))

            self.macroBorders.linePen.setColour(inkColour)
            self.macroRoutes.linePen.setColour(inkColour)

            self.microBorders.linePen.setColour(inkColour)
            self.microBorders.linePen.setWidth(onePixel * 2)
            self.microBorders.font = self._createFont(
                families=self.microBorders.font.family(),
                emSize=self.microBorders.font.emSize() * 0.6,
                style=cartographer.FontStyle.Regular)

            self.microRoutes.linePen.setColour(inkColour)

            lightColour = cartographer.makeAlphaColour(
                alpha=0x80,
                colour=inkColour)
            darkColour = inkColour
            dimColour = inkColour
            highlightColour = inkColour
            self.microBorders.textBrush.setColour(inkColour)
            self.microBorderStyle = cartographer.MicroBorderStyle.Curve

            self.parsecGrid.linePen.setColour(lightColour)
            self.sectorGrid.linePen.setColour(lightColour)
            self.subsectorGrid.linePen.setColour(lightColour)

            self.worldWater.fillBrush.setColour(inkColour)
            self.worldNoWater.fillBrush.setColour(inkColour)
            self.worldWater.linePen = None
            self.worldNoWater.linePen = None

            self.showWorldDetailColours = False

            self.worldDetails &= ~cartographer.WorldDetails.Starport
            self.worldDetails &= ~cartographer.WorldDetails.Allegiance
            self.worldDetails &= ~cartographer.WorldDetails.Bases
            self.worldDetails &= ~cartographer.WorldDetails.GasGiant
            self.worldDetails &= ~cartographer.WorldDetails.Highlight
            self.worldDetails &= ~cartographer.WorldDetails.Uwp

            if self.worlds.visible:
                self.worlds.font = self._createFont(
                    families=self.worlds.font.family(),
                    emSize=self.worlds.font.emSize() * 0.85,
                    style=self.worlds.font.style())
                self.worlds.textStyle.translation = cartographer.PointF(0, 0.25)

            self.numberAllHexes = True
            self.hexCoordinateStyle = cartographer.HexCoordinateStyle.Subsector
            self.overrideLineStyle = cartographer.LineStyle.Solid

            self.populationOverlay.fillBrush.setColour(cartographer.makeAlphaColour(
                alpha=0x40,
                colour=highlightColour))
            self.populationOverlay.linePen = self._graphics.createPen(
                colour=common.HtmlColours.Gray,
                width=0.03 * penScale,
                style=cartographer.LineStyle.Dash)

            self.importanceOverlay.fillBrush.setColour(cartographer.makeAlphaColour(
                alpha=0x20,
                colour=highlightColour))
            self.importanceOverlay.linePen = self._graphics.createPen(
                colour=common.HtmlColours.Gray,
                width=0.03 * penScale,
                style=cartographer.LineStyle.Dot)
        elif self._style is travellermap.MapStyle.Print:
            self.lightBackground = True

            foregroundColour = common.HtmlColours.Black
            self.backgroundBrush.setColour(common.HtmlColours.White)
            lightColour = common.HtmlColours.DarkGray
            darkColour = common.HtmlColours.DarkGray
            dimColour = common.HtmlColours.LightGray
            self.microRoutes.linePen.setColour(common.HtmlColours.Gray)

            self.microBorders.textBrush.setColour(common.HtmlColours.Brown)

            self.amberZone.linePen.setColour(common.HtmlColours.TravellerAmber)
            self.worldNoWater.fillBrush.setColour(common.HtmlColours.White)
            self.worldNoWater.linePen = self._graphics.createPen(
                colour=common.HtmlColours.Black,
                width=onePixel)

            self.riftOpacity = min(self.riftOpacity, 0.70)

            self.populationOverlay.fillBrush.setColour(cartographer.makeAlphaColour(
                alpha=0x40,
                colour=self.populationOverlay.fillBrush.colour()))
            self.populationOverlay.linePen = self._graphics.createPen(
                colour=common.HtmlColours.Gray,
                width=0.03 * penScale,
                style=cartographer.LineStyle.Dash)

            self.importanceOverlay.fillBrush.setColour(cartographer.makeAlphaColour(
                alpha=0x20,
                colour=self.importanceOverlay.fillBrush.colour()))
            self.importanceOverlay.linePen = self._graphics.createPen(
                colour=common.HtmlColours.Gray,
                width=0.03 * penScale,
                style=cartographer.LineStyle.Dot)
        elif self._style is travellermap.MapStyle.Draft:
            inkOpacity = 0xB0

            self.showGalaxyBackground = False
            self.lightBackground = True

            self.deepBackgroundOpacity = 0

            self.backgroundBrush.setColour(common.HtmlColours.AntiqueWhite)
            foregroundColour = cartographer.makeAlphaColour(
                alpha=inkOpacity,
                colour=common.HtmlColours.Black)
            highlightColour = cartographer.makeAlphaColour(
                alpha=inkOpacity,
                colour=common.HtmlColours.TravellerRed)

            lightColour = cartographer.makeAlphaColour(
                alpha=inkOpacity,
                colour=common.HtmlColours.DarkCyan)
            darkColour = cartographer.makeAlphaColour(
                alpha=inkOpacity,
                colour=common.HtmlColours.Black)
            dimColour = cartographer.makeAlphaColour(
                alpha=inkOpacity / 2,
                colour=common.HtmlColours.Black)

            self.subsectorGrid.linePen.setColour(cartographer.makeAlphaColour(
                alpha=inkOpacity,
                colour=common.HtmlColours.Firebrick))

            fontName = 'Comic Sans MS'

            # The large font needs to be updated before the standard font as the large
            # fonts size is dependent on the standard fonts old size (based on the
            # Traveller Map code)
            if self.worlds.visible:
                self.worlds.largeFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize() * 1.25,
                    style=self.worlds.largeFont.style() | cartographer.FontStyle.Underline)
                self.worlds.smallFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.smallFont.emSize(),
                    style=self.worlds.smallFont.style())
                self.worlds.font = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize() * 0.8,
                    style=self.worlds.font.style())
                self.worlds.textStyle.uppercase = True
                self.worlds.textBackgroundStyle = cartographer.TextBackgroundStyle.NoStyle

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
                style=self.microBorders.font.style())
            self.microBorders.textStyle.uppercase = True
            self.microBorders.textBrush.setColour(cartographer.makeAlphaColour(
                alpha=inkOpacity,
                colour=common.HtmlColours.Brown))

            self.subsectorNames.font = self._createFont(
                families=fontName,
                emSize=self.subsectorNames.font.emSize(),
                style=self.subsectorNames.font.style())
            self.subsectorNames.textStyle.uppercase = True
            self.subsectorNames.visible = False

            self.sectorName.font = self._createFont(
                families=fontName,
                emSize=self.sectorName.font.emSize(),
                style=self.sectorName.font.style())
            self.sectorName.textStyle.uppercase = True

            self.worldDetails &= ~cartographer.WorldDetails.Allegiance

            self.microBorders.linePen.setWidth(onePixel * 4)
            self.microBorders.linePen.setStyle(cartographer.LineStyle.Dot)

            self.worldNoWater.fillBrush.setColour(foregroundColour)
            self.worldWater.fillBrush = None
            self.worldWater.linePen = self._graphics.createPen(
                colour=foregroundColour,
                width=onePixel * 2)

            self.amberZone.linePen.setColour(foregroundColour)
            self.amberZone.linePen.setWidth(onePixel)
            self.redZone.linePen.setWidth(onePixel * 2)

            self.microRoutes.linePen.setColour(common.HtmlColours.Gray)

            self.parsecGrid.linePen.setColour(lightColour)

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.numberAllHexes = True

            self.populationOverlay.fillBrush.setColour(cartographer.makeAlphaColour(
                alpha=0x40,
                colour=self.populationOverlay.fillBrush.colour()))
            self.populationOverlay.linePen = self._graphics.createPen(
                colour=common.HtmlColours.Gray,
                width=0.03 * penScale,
                style=cartographer.LineStyle.Dash)

            self.importanceOverlay.fillBrush.setColour(cartographer.makeAlphaColour(
                alpha=0x20,
                colour=self.importanceOverlay.fillBrush.colour()))
            self.importanceOverlay.linePen = self._graphics.createPen(
                colour=common.HtmlColours.Gray,
                width=0.03 * penScale,
                style=cartographer.LineStyle.Dot)
        elif self._style is travellermap.MapStyle.Candy:
            self.useWorldImages = True
            self.pseudoRandomStars.visible = False
            self.fadeSectorSubsectorNames = False

            self.showNebulaBackground = self.deepBackgroundOpacity < 0.5

            self.microBorderStyle = cartographer.MicroBorderStyle.Curve

            self.sectorGrid.visible = self.sectorGrid.visible and (self.scale >= 4)
            self.subsectorGrid.visible = self.subsectorGrid.visible and (self.scale >= 32)
            self.parsecGrid.visible = False

            self.subsectorGrid.linePen.setWidth(0.03 * (64.0 / self.scale))
            self.subsectorGrid.linePen.setStyle(
                style=cartographer.LineStyle.Custom,
                pattern=[10.0, 8.0])

            self.sectorGrid.linePen.setWidth(0.03 * (64.0 / self.scale))
            self.sectorGrid.linePen.setStyle(
                style=cartographer.LineStyle.Custom,
                pattern=[10.0, 8.0])

            self.worlds.textBackgroundStyle = cartographer.TextBackgroundStyle.Shadow

            self.worldDetails = self.worldDetails & ~cartographer.WorldDetails.Starport & \
                ~cartographer.WorldDetails.Allegiance & ~cartographer.WorldDetails.Bases & \
                ~cartographer.WorldDetails.Hex

            if self.scale < StyleSheet._CandyMinWorldNameScale:
                self.worldDetails &= ~cartographer.WorldDetails.KeyNames & \
                    ~cartographer.WorldDetails.AllNames
            if self.scale < StyleSheet._CandyMinUwpScale:
                self.worldDetails &= ~cartographer.WorldDetails.Uwp

            self.amberZone.linePen.setColour(common.HtmlColours.Goldenrod)
            self.amberZone.linePen.setWidth(0.035)
            self.redZone.linePen.setWidth(0.035)

            self.sectorName.textStyle.rotation = 0
            self.sectorName.textStyle.translation = cartographer.PointF(0, -0.25)
            self.sectorName.textStyle.scale = cartographer.SizeF(0.5, 0.25)
            self.sectorName.textStyle.uppercase = True

            self.subsectorNames.textStyle.rotation = 0
            self.subsectorNames.textStyle.translation = cartographer.PointF(0, -0.25)
            self.subsectorNames.textStyle.scale = cartographer.SizeF(0.3, 0.15) #  Expand
            self.subsectorNames.textStyle.uppercase = True

            self.subsectorNames.textBrush = self._graphics.createBrush(
                colour=cartographer.makeAlphaColour(
                    alpha=128,
                    colour=common.HtmlColours.Goldenrod))
            self.sectorName.textBrush = self._graphics.createBrush(
                colour=cartographer.makeAlphaColour(
                    alpha=128,
                    colour=common.HtmlColours.Goldenrod))

            self.microBorders.textStyle.rotation = 0
            self.microBorders.textStyle.translation = cartographer.PointF(0, 0.25)
            self.microBorders.textStyle.scale = cartographer.SizeF(1.0, 0.5) # Expand
            self.microBorders.textStyle.uppercase = True

            self.microBorders.linePen.setColour(cartographer.makeAlphaColour(
                alpha=128,
                colour=common.HtmlColours.TravellerRed))
            self.microRoutes.linePen.setWidth(
                routePenWidth if self.scale < StyleSheet._CandyMaxRouteRelativeScale else routePenWidth / 2)

            # HACK: Scaling the border pen like this is done to work around an
            # issue with micro borders. Micro borders are rendered as closed
            # polygons so that when border filling is enabled they can be
            # filled. When a logical border covers multiple sectors, each
            # sector has it's own closed polygons representing the area of that
            # sector that is within the border with edges of that polygons
            # running along the edges of the sector where it abuts other sectors
            # in the same logical boundary. When drawing the outline of borders
            # we don't want the polygon edges at the junction between sectors in
            # the same logical border to be shown as the are just a graphical
            # necessity rather than part of the logical boundary. When rendering
            # non-candy styles, not showing these edges is handled by clipping
            # to the sector outline when drawing borders for that sector. I
            # found this doesn't work reliably for candy due a combination of the
            # line width used for borders and the fact it uses curved borders so
            # the border outlines extend outside the hexes they contain. The end
            # result was at some scales (generally < linear 16) there would be
            # noticeable dotted lines running along the boundaries of sectors
            # inside the same border. Part of the solution to this issue is to
            # slightly reduce the width of the border outline compared to the
            # width Traveller Map would use. The other part is to disable the
            # oversizing of the sector bounding box done when rendering zoom
            # levels where the issue was seen.
            borderPenScale = 0.8

            self.macroBorders.linePen.setWidth(
                (borderPenWidth * borderPenScale) if self.scale < StyleSheet._CandyMaxBorderRelativeScale else borderPenWidth / 4)
            self.microBorders.linePen.setWidth(
                (borderPenWidth * borderPenScale) if self.scale < StyleSheet._CandyMaxBorderRelativeScale else borderPenWidth / 4)

            self.worlds.textStyle.rotation = 0
            self.worlds.textStyle.scale = cartographer.SizeF(1, 0.5) # Expand
            self.worlds.textStyle.translation = cartographer.PointF(0, 0)
            self.worlds.textStyle.uppercase = True

            self.gasGiant.fillBrush = self._graphics.createBrush(
                colour=highlightColour)
            self.gasGiant.linePen = self._graphics.createPen(
                colour=highlightColour,
                width=self.gasGiantRadius / 4)

            if (self.scale > StyleSheet._CandyMaxWorldRelativeScale):
                self.hexContentScale = StyleSheet._CandyMaxWorldRelativeScale / self.scale
        elif self._style is travellermap.MapStyle.Terminal:
            self.fadeSectorSubsectorNames = False
            self.showGalaxyBackground = False
            self.lightBackground = False

            foregroundColour = common.HtmlColours.Cyan
            highlightColour = common.HtmlColours.White

            lightColour = common.HtmlColours.LightBlue
            darkColour = common.HtmlColours.DarkBlue
            dimColour = common.HtmlColours.DimGray

            self.subsectorGrid.linePen.setColour(common.HtmlColours.Cyan)

            fontName = 'Courier New'

            # The large font needs to be updated before the standard font as the large
            # fonts size is dependent on the standard fonts old size (based on the
            # Traveller Map code)
            if self.worlds.visible:
                self.worlds.largeFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize() * 1.25,
                    style=self.worlds.largeFont.style() | cartographer.FontStyle.Underline)
                self.worlds.smallFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.smallFont.emSize(),
                    style=self.worlds.smallFont.style())
                self.worlds.font = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize() * 0.8,
                    style=self.worlds.font.style())
                self.worlds.textStyle.uppercase = True
                self.worlds.textBackgroundStyle = cartographer.TextBackgroundStyle.NoStyle

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
                style=self.microBorders.font.style() | cartographer.FontStyle.Underline)
            self.microBorders.textStyle.uppercase = True
            self.microBorders.linePen.setWidth(onePixel * 4)
            self.microBorders.linePen.setStyle(cartographer.LineStyle.Dot)

            self.sectorName.font = self._createFont(
                families=fontName,
                emSize=self.sectorName.font.emSize() * 0.5,
                style=self.sectorName.font.style() | cartographer.FontStyle.Bold)
            self.sectorName.textBrush = self._graphics.createBrush(
                colour=foregroundColour)
            self.sectorName.textStyle.scale = cartographer.SizeF(1, 1)
            self.sectorName.textStyle.rotation = 0
            self.sectorName.textStyle.uppercase = True

            self.subsectorNames.font = self._createFont(
                families=fontName,
                emSize=self.subsectorNames.font.emSize() * 0.5,
                style=self.subsectorNames.font.style() | cartographer.FontStyle.Bold)
            self.subsectorNames.textBrush = self._graphics.createBrush(
                colour=foregroundColour)
            self.subsectorNames.textStyle.scale = cartographer.SizeF(1, 1)
            self.subsectorNames.textStyle.rotation = 0
            self.subsectorNames.textStyle.uppercase = True

            self.worldNoWater.fillBrush.setColour(foregroundColour)
            self.worldWater.fillBrush = None
            self.worldWater.linePen = self._graphics.createPen(
                colour=foregroundColour,
                width=onePixel * 2)

            self.amberZone.linePen.setColour(foregroundColour)
            self.amberZone.linePen.setWidth(onePixel)
            self.redZone.linePen.setWidth(onePixel * 2)

            self.microRoutes.linePen.setColour(common.HtmlColours.Gray)

            self.parsecGrid.linePen.setColour(common.HtmlColours.Plum)
            self.microBorders.textBrush.setColour(common.HtmlColours.Cyan)

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.numberAllHexes = True

            if (self.scale >= 64):
                self.subsectorNames.visible = False
        elif self._style is travellermap.MapStyle.Mongoose:
            self.showGalaxyBackground = False
            self.lightBackground = True
            self.showGasGiantRing = True
            self.showTL = True
            self.ignoreBaseBias = True
            self.shadeMicroBorders = True

            self.layerOrder.moveAfter(
                target=cartographer.LayerId.Worlds_Background,
                item=cartographer.LayerId.Micro_BordersForeground)
            self.layerOrder.moveAfter(
                target=cartographer.LayerId.Worlds_Foreground,
                item=cartographer.LayerId.Micro_Routes)

            self.deepBackgroundOpacity = 0

            self.backgroundBrush.setColour('#E6E7E8')
            foregroundColour = common.HtmlColours.Black
            highlightColour = common.HtmlColours.Red

            lightColour = common.HtmlColours.Black
            darkColour = common.HtmlColours.Black
            dimColour = common.HtmlColours.Gray

            self.sectorGrid.linePen.setColour(foregroundColour)
            self.subsectorGrid.linePen.setColour(foregroundColour)
            self.parsecGrid.linePen.setColour(foregroundColour)

            self.microBorders.textBrush.setColour(common.HtmlColours.DarkSlateGray)

            fontName = 'Calibri,Arial'

            self.worldDetails &= ~cartographer.WorldDetails.Allegiance

            if self.worlds.visible:
                self.worlds.font = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize(),
                    style=cartographer.FontStyle.Regular)
                self.worlds.smallFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.smallFont.emSize(),
                    style=self.worlds.smallFont.style())
                self.worlds.largeFont = self._createFont(
                    families=fontName,
                    emSize=self.worlds.largeFont.emSize(),
                    style=cartographer.FontStyle.Bold)
                self.worlds.textStyle.uppercase = True
                self.worlds.textStyle.translation = cartographer.PointF(0, -0.04)
                self.worlds.textBackgroundStyle = cartographer.TextBackgroundStyle.NoStyle

                self.starport.font = self._createFont(
                    families=fontName,
                    emSize=self.starport.font.emSize(),
                    style=cartographer.FontStyle.Italic)
                self.starport.position = cartographer.PointF(0.175, 0.17)

                self.hexNumber.font = self._createFont(
                    families=fontName,
                    emSize=self.worlds.font.emSize(),
                    style=self.worlds.font.style())
                self.hexNumber.position.setY(-0.49)

                self.uwp.font = self.hexNumber.font
                self.uwp.textBackgroundStyle = cartographer.TextBackgroundStyle.Filled
                self.uwp.position = cartographer.PointF(0, 0.40)
                self.uwp.fillBrush = self._graphics.createBrush(
                    colour=common.HtmlColours.Black)
                self.uwp.textBrush = self._graphics.createBrush(
                    colour=common.HtmlColours.White)

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
            self.microBorders.linePen.setWidth(0.11)
            self.microBorders.linePen.setStyle(cartographer.LineStyle.Dot)
            self.microBorders.textBrush.setColour(common.HtmlColours.DarkSlateGray)

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

            self.worldWater.fillBrush.setColour(common.HtmlColours.MediumBlue)
            self.worldNoWater.fillBrush.setColour(common.HtmlColours.DarkKhaki)
            self.worldWater.linePen = self._graphics.createPen(
                colour=common.HtmlColours.DarkGray,
                width=onePixel * 2)
            self.worldNoWater.linePen = self._graphics.createPen(
                colour=common.HtmlColours.DarkGray,
                width=onePixel * 2)

            self.showZonesAsPerimeters = True

            self.greenZone.visible = True
            self.greenZone.linePen = self._graphics.createPen(
                colour='#80C676',
                width=0.05)
            self.amberZone.linePen.setColour('#FBB040')
            self.amberZone.linePen.setWidth(0.05)
            self.redZone.linePen.setColour(common.HtmlColours.Red)
            self.redZone.linePen.setWidth(0.05)

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.discRadius = 0.11
            self.gasGiant.position = cartographer.PointF(0, -0.23)
            self.baseTopPosition = cartographer.PointF(-0.22, -0.21)
            self.baseMiddlePosition = cartographer.PointF(-0.32, 0.17)
            self.baseBottomPosition = cartographer.PointF(0.22, -0.21)
            self.discPosition = cartographer.PointF(-self.discRadius, 0.16)

        if fadeSectorSubsectorNames and \
                (not self.sectorName.textBrush or not self.subsectorNames.textBrush):
            if self.scale < 16:
                fadeColour = foregroundColour
            elif self.scale < 48:
                fadeColour = darkColour
            else:
                fadeColour = dimColour

            fadeBrush = self._graphics.createBrush(colour=fadeColour)
            if not self.sectorName.textBrush:
                self.sectorName.textBrush = fadeBrush
            if not self.subsectorNames.textBrush:
                self.subsectorNames.textBrush = fadeBrush

        # Base element colours on foreground/light/dim/dark/highlight, if not specified by style.
        if not self.pseudoRandomStars.fillBrush:
            self.pseudoRandomStars.fillBrush = self._graphics.createBrush(
                colour=foregroundColour)

        if not self.droyneWorlds.textBrush:
            self.droyneWorlds.textBrush = self.microBorders.textBrush
        if not self.minorHomeWorlds.textBrush:
            self.minorHomeWorlds.textBrush = self.microBorders.textBrush
        if not self.ancientsWorlds.textBrush:
            self.ancientsWorlds.textBrush = self.microBorders.textBrush

        if not self.megaNames.textBrush:
            self.megaNames.textBrush = self._graphics.createBrush(
                colour=foregroundColour)
        if not self.megaNames.textHighlightBrush:
            self.megaNames.textHighlightBrush = self._graphics.createBrush(
                colour=highlightColour)

        if not self.macroNames.textBrush:
            self.macroNames.textBrush = self._graphics.createBrush(
                colour=foregroundColour)
        if not self.macroNames.textHighlightBrush:
            self.macroNames.textHighlightBrush = self._graphics.createBrush(
                colour=highlightColour)

        if not self.macroRoutes.textBrush:
            self.macroRoutes.textBrush = self._graphics.createBrush(
                colour=foregroundColour)
        if not self.macroRoutes.textHighlightBrush:
            self.macroRoutes.textHighlightBrush = self._graphics.createBrush(
                colour=highlightColour)

        if not self.worlds.textBrush:
            self.worlds.textBrush = self._graphics.createBrush(
                colour=foregroundColour)
        if not self.worlds.textHighlightBrush:
            self.worlds.textHighlightBrush = self._graphics.createBrush(
                colour=highlightColour)

        if not self.hexNumber.textBrush:
            self.hexNumber.textBrush = self._graphics.createBrush(
                colour=lightColour)
        if not self.uwp.textBrush:
            self.uwp.textBrush = self._graphics.createBrush(
                colour=foregroundColour)

        if not self.placeholder.textBrush:
            self.placeholder.textBrush = self._graphics.createBrush(
                colour=foregroundColour)
        if not self.anomaly.textBrush:
            self.anomaly.textBrush = self._graphics.createBrush(
                colour=highlightColour)

        if not self.gasGiant.fillBrush:
            self.gasGiant.fillBrush = self.worlds.textBrush
        if not self.gasGiant.linePen:
            self.gasGiant.linePen = self._graphics.createPen(
                colour=self.worlds.textBrush.colour(),
                width=self.gasGiantRadius / 4)

        if self.showWorldDetailColours:
            self.worldRichAgricultural.fillBrush = self._graphics.createBrush(
                colour=common.HtmlColours.TravellerAmber)
            self.worldAgricultural.fillBrush = self._graphics.createBrush(
                colour=common.HtmlColours.TravellerGreen)
            self.worldRich.fillBrush = self._graphics.createBrush(
                colour=common.HtmlColours.Purple)
            self.worldIndustrial.fillBrush = self._graphics.createBrush(
                colour='#888888') # Gray
            self.worldHarshAtmosphere.fillBrush = self._graphics.createBrush(
                colour='#CC6626') # Rust
            self.worldVacuum.fillBrush = self._graphics.createBrush(
                colour=common.HtmlColours.Black)
            self.worldVacuum.fillBrush = self._graphics.createBrush(
                colour=common.HtmlColours.Black)
            self.worldVacuum.linePen = self._graphics.createPen(
                colour=common.HtmlColours.White,
                width=self.worldWater.linePen.width() if self.worldWater.linePen else onePixel,
                style=self.worldWater.linePen.style() if self.worldWater.linePen else cartographer.LineStyle.Solid,
                pattern=self.worldWater.linePen.pattern()if self.worldWater.linePen else None)

    def _createFont(
            self,
            families: str,
            emSize: float,
            style: cartographer.FontStyle = cartographer.FontStyle.Regular
            ) -> cartographer.AbstractFont:
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
                continue

            if font:
                self._fontCache[key] = font
                return font

        raise RuntimeError(f'Failed to create {emSize} point font with style {int(style)} from families {families}')

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
    def _colourScaleInterpolate(
            scale: float,
            minScale: float,
            maxScale: float,
            colour: str
            ) -> str:
        alpha = StyleSheet._floatScaleInterpolate(
            minValue=0,
            maxValue=255,
            scale=scale,
            minScale=minScale,
            maxScale=maxScale)
        return cartographer.makeAlphaColour(
            alpha=alpha,
            colour=colour)
