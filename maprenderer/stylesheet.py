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
        def __init__(self):
            self.visible = False
            # TODO: This should probably be an AbstractBrush to avoid having to create it all the time
            self.fillColor = ''
            self.content = ''
            self.pen = maprenderer.AbstractPen()
            self.textColor = ''
            self.textHighlightColor = ''

            self.textStyle = maprenderer.LabelStyle()
            self.textBackgroundStyle = maprenderer.TextBackgroundStyle.NoStyle
            self.fontInfo = maprenderer.FontInfo()
            self.smallFontInfo = maprenderer.FontInfo()
            self.mediumFontInfo = maprenderer.FontInfo()
            self.largeFontInfo = maprenderer.FontInfo()
            self.position = maprenderer.AbstractPointF()

            # TODO: Still to fill out
            self._font = None
            self._smallFont = None
            self._mediumFont = None
            self._largeFont = None

        @property
        def font(self) -> maprenderer.AbstractFont:
            if not self._font:
                if not self.fontInfo:
                    raise RuntimeError('AbstractFont has no fontInfo')
                self._font = self.fontInfo.makeFont()
            return self._font
        @property
        def smallFont(self) -> maprenderer.AbstractFont:
            if not self._smallFont:
                if not self.smallFontInfo:
                    raise RuntimeError('AbstractFont has no font smallFontInfo')
                self._smallFont = self.smallFontInfo.makeFont()
            return self._smallFont
        @property
        def mediumFont(self) -> maprenderer.AbstractFont:
            if not self._mediumFont:
                if not self.mediumFontInfo:
                    raise RuntimeError('AbstractFont has no font mediumFontInfo')
                self._mediumFont = self.mediumFontInfo.makeFont()
            return self._mediumFont
        @property
        def largeFont(self) -> maprenderer.AbstractFont:
            if not self._largeFont:
                if not self.largeFontInfo:
                    raise RuntimeError('AbstractFont has no font largeFontInfo')
                self._largeFont = self.largeFontInfo.makeFont()
            return self._largeFont

    def __init__(
            self,
            scale: float,
            options: maprenderer.MapOptions,
            style: travellermap.Style
            ):
        self._scale = scale
        self._options = options
        self._style = style
        self._handleConfigUpdate()

    @property
    def scale(self) -> float:
        return self._scale
    @scale.setter
    def scale(self, scale: float) -> None:
        self._scale = scale
        self._handleConfigUpdate()

    @property
    def options(self) -> maprenderer.MapOptions:
        return self._options
    @options.setter
    def options(self, options: maprenderer.MapOptions) -> None:
        self._options = options
        self._handleConfigUpdate()

    @property
    def style(self) -> float:
        return self._style
    @scale.setter
    def style(self, style: float) -> None:
        self._style = style
        self._handleConfigUpdate()

    @property
    def hasWorldOverlays(self) -> bool:
        return self.populationOverlay.visible or \
            self.importanceOverlay.visible or  \
            self.highlightWorlds.visible or \
            self.showStellarOverlay or \
            self.capitalOverlay.visible

    def worldColors(
            self,
            world: traveller.World
            ) -> typing.Tuple[
                typing.Optional[str], # Pen colour
                typing.Optional[str]]: # Brush colour
        penColor = None
        brushColor = None

        if self.showWorldDetailColors:
            if maprenderer.WorldHelper.isAgricultural(world) and maprenderer.WorldHelper.isRich(world):
                penColor = brushColor = travellermap.MapColours.TravellerAmber
            elif maprenderer.WorldHelper.isAgricultural(world):
                penColor = brushColor = travellermap.MapColours.TravellerGreen
            elif maprenderer.WorldHelper.isRich(world):
                penColor = brushColor = travellermap.MapColours.Purple
            elif maprenderer.WorldHelper.isIndustrial(world):
                penColor = brushColor = '#888888' # Gray
            elif world.uwp().numeric(element=traveller.UWP.Element.Atmosphere, default=-1) > 10:
                penColor = brushColor = '#CC6626' # Rust
            elif maprenderer.WorldHelper.isVacuum(world):
                brushColor = travellermap.MapColours.Black
                penColor = travellermap.MapColours.White
            elif maprenderer.WorldHelper.hasWater(world):
                brushColor = self.worldWater.fillColor
                penColor = self.worldWater.pen.color
            else:
                brushColor = self.worldNoWater.fillColor
                penColor = self.worldNoWater.pen.color
        else:
            # Classic colors

            # World disc
            hasWater = maprenderer.WorldHelper.hasWater(world)
            brushColor = \
                self.worldWater.fillColor \
                if hasWater else \
                self.worldNoWater.fillColor
            penColor = \
                self.worldWater.pen.color \
                if hasWater else \
                self.worldNoWater.pen.color

        return (penColor, brushColor)

    def _handleConfigUpdate(self) -> None:
        # Options
        self.backgroundColor = travellermap.MapColours.Black

        self.imageBorderColor = ''
        self.imageBorderWidth = 0.2

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
        self.hexRotation = 0

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
        self.gasGiantPosition = maprenderer.AbstractPointF(0, 0)
        self.allegiancePosition = maprenderer.AbstractPointF(0, 0)
        self.baseTopPosition = maprenderer.AbstractPointF(0, 0)
        self.baseBottomPosition = maprenderer.AbstractPointF(0, 0)
        self.baseMiddlePosition = maprenderer.AbstractPointF(0, 0)

        self.uwp = StyleSheet.StyleElement()
        self.starport = StyleSheet.StyleElement()

        #self.glyphFont = FontInfo() # TODO: Need to figure out defaults
        self.worldDetails: maprenderer.WorldDetails = maprenderer.WorldDetails.NoDetails
        self.lowerCaseAllegiance = False
        #self.wingdingFont = FontInfo() # TODO: Need to figure out defaults
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
        self.macroNames = StyleSheet.StyleElement()
        self.megaNames = StyleSheet.StyleElement()
        self.pseudoRandomStars = StyleSheet.StyleElement()
        self.placeholder = StyleSheet.StyleElement()
        self.anomaly = StyleSheet.StyleElement()

        self.microBorders = StyleSheet.StyleElement()
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
            scale=self._scale,
            minScale=1 / 4,
            maxScale=4)

        self.deepBackgroundOpacity = StyleSheet._floatScaleInterpolate(
            minValue=1,
            maxValue=0,
            scale=self._scale,
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
        self.capitalOverlay.visible = (self.options & maprenderer.MapOptions.WorldColors) != 0
        self.showStellarOverlay = (self._options & maprenderer.MapOptions.StellarOverlay) != 0

        self.lowerCaseAllegiance = (self.scale < StyleSheet._WorldFullMinScale)
        self.showGasGiantRing = (self.scale >= StyleSheet._WorldUwpMinScale)

        self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.Rectangle

        self.hexCoordinateStyle = maprenderer.HexCoordinateStyle.Sector
        self.numberAllHexes = False

        if self.scale < StyleSheet._WorldFullMinScale:
            # Atlas-style

            x = 0.225
            y = 0.125

            self.baseTopPosition = maprenderer.AbstractPointF(-x, -y)
            self.baseBottomPosition = maprenderer.AbstractPointF(-x, y)
            self.gasGiantPosition =  maprenderer.AbstractPointF(x, -y)
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
            self.gasGiantPosition = maprenderer.AbstractPointF(x, -y)
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

            self.worlds.fontInfo = maprenderer.FontInfo(
                StyleSheet._DefaultFont,
                0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.15 * fontScale),
                maprenderer.FontStyle.Bold)
            self.wingdingFont = maprenderer.FontInfo(
                "Wingdings",
                0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.175 * fontScale))
            self.glyphFont = maprenderer.FontInfo(
                "Arial Unicode MS,Segoe UI Symbol,Arial",
                0.175 if self.scale < StyleSheet._WorldFullMinScale else (0.15 * fontScale),
                maprenderer.FontStyle.Bold)
            self.uwp.fontInfo = maprenderer.FontInfo(StyleSheet._DefaultFont, 0.1 * fontScale)
            self.hexNumber.fontInfo = maprenderer.FontInfo(StyleSheet._DefaultFont, 0.1 * fontScale)
            self.worlds.smallFontInfo = maprenderer.FontInfo(
                StyleSheet._DefaultFont,
                0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.1 * fontScale))
            self.worlds.largeFontInfo = maprenderer.FontInfo(self.worlds.fontInfo)
            self.starport.fontInfo = \
                maprenderer.FontInfo(self.worlds.smallFontInfo) \
                if (self.scale < StyleSheet._WorldFullMinScale) else \
                maprenderer.FontInfo(self.worlds.fontInfo)

        self.sectorName.fontInfo = maprenderer.FontInfo(StyleSheet._DefaultFont, 5.5)
        self.subsectorNames.fontInfo = maprenderer.FontInfo(StyleSheet._DefaultFont, 1.5)

        overlayFontSize = max(onePixel * 12, 0.375)
        self.droyneWorlds.fontInfo = maprenderer.FontInfo(StyleSheet._DefaultFont, overlayFontSize)
        self.ancientsWorlds.fontInfo = maprenderer.FontInfo(StyleSheet._DefaultFont, overlayFontSize)
        self.minorHomeWorlds.fontInfo = maprenderer.FontInfo(StyleSheet._DefaultFont, overlayFontSize)

        self.droyneWorlds.content = "\u2605\u2606" # BLACK STAR / WHITE STAR
        self.minorHomeWorlds.content = "\u273B" # TEARDROP-SPOKED ASTERISK
        self.ancientsWorlds.content = "\u2600" # BLACK SUN WITH RAYS

        self.microBorders.fontInfo = maprenderer.FontInfo(
            StyleSheet._DefaultFont,
            # TODO: This was == rather tan <= but in my implementation scale isn't
            # usually going to be an integer value so <= seems more appropriate.
            # Just need to check it shouldn't be >=
            0.6 if self.scale <= StyleSheet._MicroNameMinScale else 0.25,
            maprenderer.FontStyle.Bold)
        self.microBorders.smallFontInfo = maprenderer.FontInfo(
            families=StyleSheet._DefaultFont,
            size=0.15,
            style=maprenderer.FontStyle.Bold)
        self.microBorders.largeFontInfo = maprenderer.FontInfo(
            families=StyleSheet._DefaultFont,
            size=0.75,
            style=maprenderer.FontStyle.Bold)

        self.macroNames.fontInfo = maprenderer.FontInfo(
            families=StyleSheet._DefaultFont,
            size=8 / 1.4,
            style=maprenderer.FontStyle.Bold)
        self.macroNames.smallFontInfo = maprenderer.FontInfo(
            families=StyleSheet._DefaultFont,
            size=5 / 1.4,
            style=maprenderer.FontStyle.Regular)
        self.macroNames.mediumFontInfo = maprenderer.FontInfo(
            families=StyleSheet._DefaultFont,
            size=6.5 / 1.4,
            style=maprenderer.FontStyle.Italic)

        megaNameScaleFactor = min(35, 0.75 * onePixel)
        self.megaNames.fontInfo = maprenderer.FontInfo(
            StyleSheet._DefaultFont,
            24 * megaNameScaleFactor,
            maprenderer.FontStyle.Bold)
        self.megaNames.mediumFontInfo = maprenderer.FontInfo(
            StyleSheet._DefaultFont,
            22 * megaNameScaleFactor,
            maprenderer.FontStyle.Regular)
        self.megaNames.smallFontInfo = maprenderer.FontInfo(
            StyleSheet._DefaultFont,
            18 * megaNameScaleFactor,
            maprenderer.FontStyle.Italic)

        self.capitals.fillColor = travellermap.MapColours.Wheat
        self.capitals.textColor = travellermap.MapColours.TravellerRed
        self.amberZone.visible = self.redZone.visible = True
        self.amberZone.pen.color = travellermap.MapColours.TravellerAmber
        self.redZone.pen.color = travellermap.MapColours.TravellerRed
        self.macroBorders.pen.color = travellermap.MapColours.TravellerRed
        self.macroRoutes.pen.color = travellermap.MapColours.White
        self.microBorders.pen.color = travellermap.MapColours.Gray
        self.microRoutes.pen.color = travellermap.MapColours.Gray

        self.microBorders.textColor = travellermap.MapColours.TravellerAmber
        self.worldWater.fillColor = travellermap.MapColours.DeepSkyBlue
        self.worldNoWater.fillColor = travellermap.MapColours.White
        self.worldNoWater.pen.color = '#0000FF' # TODO: Color.Empty;

        gridColor = self._colorScaleInterpolate(
            scale=self.scale,
            minScale=StyleSheet._SectorGridMinScale,
            maxScale=StyleSheet._SectorGridFullScale,
            color=travellermap.MapColours.Gray)
        self.parsecGrid.pen = maprenderer.AbstractPen(gridColor, onePixel)
        self.subsectorGrid.pen = maprenderer.AbstractPen(gridColor, onePixel * 2)
        self.sectorGrid.pen = maprenderer.AbstractPen(
            gridColor,
            (4 if self.subsectorGrid.visible else 2) * onePixel)
        self.worldWater.pen = maprenderer.AbstractPen(
            '#0000FF', # TODO: Color.Empty,
            max(0.01, onePixel))

        self.microBorders.textStyle.rotation = 0
        self.microBorders.textStyle.translation = maprenderer.AbstractPointF(0, 0)
        self.microBorders.textStyle.scale = maprenderer.AbstractSizeF(1.0, 1.0)
        self.microBorders.textStyle.uppercase = False

        self.sectorName.textStyle.rotation = -50 # degrees
        self.sectorName.textStyle.translation = maprenderer.AbstractPointF(0, 0)
        self.sectorName.textStyle.scale = maprenderer.AbstractSizeF(0.75, 1.0)
        self.sectorName.textStyle.uppercase = False
        self.sectorName.textStyle.wrap = True

        self.subsectorNames.textStyle = self.sectorName.textStyle

        self.worlds.textStyle.rotation = 0
        self.worlds.textStyle.scale = maprenderer.AbstractSizeF(1.0, 1.0)
        self.worlds.textStyle.translation = maprenderer.AbstractPointF(self.worlds.position)
        self.worlds.textStyle.uppercase = False

        self.hexNumber.position = maprenderer.AbstractPointF(0, -0.5)

        self.showNebulaBackground = False
        self.showGalaxyBackground = self.deepBackgroundOpacity > 0.0
        self.useWorldImages = False

        # Cap pen widths when zooming in
        penScale = 1 if self.scale <= 64 else (64 / self.scale)

        borderPenWidth = 1
        if self.scale >= StyleSheet._MicroBorderMinScale and \
            self.scale >= StyleSheet._ParsecMinScale:
            borderPenWidth = 0.16 * penScale

        routePenWidth = 0.2 if self.scale <= 16 else (0.08 * penScale)

        self.microBorders.pen.width = borderPenWidth
        self.macroBorders.pen.width = borderPenWidth
        self.microRoutes.pen.width = routePenWidth

        self.amberZone.pen.width = self.redZone.pen.width = 0.05 * penScale

        self.macroRoutes.pen.width = borderPenWidth
        self.macroRoutes.pen.dashStyle = maprenderer.DashStyle.Dash

        self.populationOverlay.fillColor = '#80FFFF00'
        self.importanceOverlay.fillColor = '#2080FF00'
        self.highlightWorlds.fillColor = '#80FF0000'

        self.populationOverlay.pen = maprenderer.AbstractPen(
            color='#0000FF', # TODO: Color.Empty,
            width=0.03 * penScale,
            dashStyle=maprenderer.DashStyle.Dash)
        self.importanceOverlay.pen = maprenderer.AbstractPen(
            color='#0000FF', # TODO: Color.Empty,
            width=0.03 * penScale,
            dashStyle=maprenderer.DashStyle.Dot)
        self.highlightWorlds.pen = maprenderer.AbstractPen(
            color='#0000FF', # TODO: Color.Empty,
            width=0.03 * penScale,
            dashStyle=maprenderer.DashStyle.DashDot)

        self.capitalOverlay.fillColor = maprenderer.makeAlphaColor(
            alpha=0x80,
            color=travellermap.MapColours.TravellerGreen)
        self.capitalOverlayAltA.fillColor = maprenderer.makeAlphaColor(
            alpha=0x80,
            color=travellermap.MapColours.Blue)
        self.capitalOverlayAltB.fillColor = maprenderer.makeAlphaColor(
            alpha=0x80,
            color=travellermap.MapColours.TravellerAmber)

        fadeSectorSubsectorNames = True

        self.placeholder.content = "*"
        self.placeholder.fontInfo = maprenderer.FontInfo("Georgia", 0.6)
        self.placeholder.position = maprenderer.AbstractPointF(0, 0.17)

        self.anomaly.content = "\u2316"; # POSITION INDICATOR
        self.anomaly.fontInfo = maprenderer.FontInfo("Arial Unicode MS,Segoe UI Symbol", 0.6)

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

            self.capitals.fillColor = travellermap.MapColours.DarkGray
            self.capitals.textColor = travellermap.MapColours.Black
            self.amberZone.pen.color = travellermap.MapColours.LightGray
            self.redZone.pen.color = travellermap.MapColours.Black
            self.macroBorders.pen.color = travellermap.MapColours.Black
            self.macroRoutes.pen.color = travellermap.MapColours.Gray
            self.microBorders.pen.color = travellermap.MapColours.Black
            self.microRoutes.pen.color = travellermap.MapColours.Gray

            foregroundColor = travellermap.MapColours.Black
            self.backgroundColor = travellermap.MapColours.White
            lightColor = travellermap.MapColours.DarkGray
            darkColor = travellermap.MapColours.DarkGray
            dimColor = travellermap.MapColours.LightGray
            highlightColor = travellermap.MapColours.Gray
            self.microBorders.textColor = travellermap.MapColours.Gray
            self.worldWater.fillColor = travellermap.MapColours.Black
            self.worldNoWater.fillColor = '#0000FF' # TODO: Color.Empty

            self.worldNoWater.fillColor = travellermap.MapColours.White
            self.worldNoWater.pen = maprenderer.AbstractPen(travellermap.MapColours.Black, onePixel)

            self.riftOpacity = min(self.riftOpacity, 0.70)

            self.showWorldDetailColors = False

            self.populationOverlay.fillColor = maprenderer.makeAlphaColor(
                alpha=0x40,
                color=highlightColor)
            self.populationOverlay.pen.color = travellermap.MapColours.Gray

            self.importanceOverlay.fillColor = maprenderer.makeAlphaColor(
                alpha=0x20,
                color=highlightColor)
            self.importanceOverlay.pen.color = travellermap.MapColours.Gray

            self.highlightWorlds.fillColor = maprenderer.makeAlphaColor(
                alpha=0x30,
                color=highlightColor)
            self.highlightWorlds.pen.color = travellermap.MapColours.Gray
        elif self._style is travellermap.Style.Fasa:
            self.showGalaxyBackground = False
            self.deepBackgroundOpacity = 0
            self.riftOpacity = 0

            inkColor = '#5C4033'

            foregroundColor = inkColor
            self.backgroundColor = travellermap.MapColours.White

            # NOTE: This TODO came in from the Traveller Map code
            self.grayscale = True # TODO: Tweak to be "monochrome"
            self.lightBackground = True

            self.capitals.fillColor = inkColor
            self.capitals.textColor = inkColor
            self.amberZone.pen.color = inkColor
            self.amberZone.pen.width = onePixel * 2
            self.redZone.pen.color = '#0000FF' # TODO: Color.Empty
            self.redZone.fillColor = maprenderer.makeAlphaColor(
                alpha=0x80,
                color=inkColor)

            self.macroBorders.pen.color = inkColor
            self.macroRoutes.pen.color = inkColor

            self.microBorders.pen.color = inkColor
            self.microBorders.pen.width = onePixel * 2
            self.microBorders.fontInfo.size *= 0.6
            self.microBorders.fontInfo.style = maprenderer.FontStyle.Regular

            self.microRoutes.pen.color = inkColor

            lightColor = maprenderer.makeAlphaColor(
                alpha=0x80,
                color=inkColor)
            darkColor = inkColor
            dimColor = inkColor
            highlightColor = inkColor
            self.microBorders.textColor = inkColor
            self.hexStyle = maprenderer.HexStyle.Hex
            self.microBorderStyle = maprenderer.MicroBorderStyle.Curve

            self.parsecGrid.pen.color = lightColor
            self.sectorGrid.pen.color = lightColor
            self.subsectorGrid.pen.color = lightColor

            self.worldWater.fillColor = inkColor
            self.worldNoWater.fillColor = inkColor
            self.worldWater.pen.color = '#0000FF' # TODO: Color.Empty
            self.worldNoWater.pen.color = '#0000FF' # TODO: Color.Empty

            self.showWorldDetailColors = False

            self.worldDetails &= ~maprenderer.WorldDetails.Starport
            self.worldDetails &= ~maprenderer.WorldDetails.Allegiance
            self.worldDetails &= ~maprenderer.WorldDetails.Bases
            self.worldDetails &= ~maprenderer.WorldDetails.GasGiant
            self.worldDetails &= ~maprenderer.WorldDetails.Highlight
            self.worldDetails &= ~maprenderer.WorldDetails.Uwp
            self.worlds.fontInfo.size *= 0.85
            self.worlds.textStyle.translation = maprenderer.AbstractPointF(0, 0.25)

            self.numberAllHexes = True
            self.hexCoordinateStyle = maprenderer.HexCoordinateStyle.Subsector
            self.overrideLineStyle = maprenderer.LineStyle.Solid

            self.populationOverlay.fillColor = maprenderer.makeAlphaColor(
                alpha=0x40,
                color=highlightColor)
            self.populationOverlay.pen.color = travellermap.MapColours.Gray

            self.importanceOverlay.fillColor = maprenderer.makeAlphaColor(
                alpha=0x20,
                color=highlightColor)
            self.importanceOverlay.pen.color = travellermap.MapColours.Gray

            self.highlightWorlds.fillColor = maprenderer.makeAlphaColor(
                alpha=0x30,
                color=highlightColor)
            self.highlightWorlds.pen.color = travellermap.MapColours.Gray
        elif self._style is travellermap.Style.Print:
            self.lightBackground = True

            foregroundColor = travellermap.MapColours.Black
            self.backgroundColor = travellermap.MapColours.White
            lightColor = travellermap.MapColours.DarkGray
            darkColor = travellermap.MapColours.DarkGray
            dimColor = travellermap.MapColours.LightGray
            self.microRoutes.pen.color = travellermap.MapColours.Gray

            self.microBorders.textColor = travellermap.MapColours.Brown

            self.amberZone.pen.color = travellermap.MapColours.TravellerAmber
            self.worldNoWater.fillColor = travellermap.MapColours.White
            self.worldNoWater.pen = maprenderer.AbstractPen(travellermap.MapColours.Black, onePixel)

            self.riftOpacity = min(self.riftOpacity, 0.70)

            self.populationOverlay.fillColor = maprenderer.makeAlphaColor(
                alpha=0x40,
                color=self.populationOverlay.fillColor)
            self.populationOverlay.pen.color = travellermap.MapColours.Gray

            self.importanceOverlay.fillColor = maprenderer.makeAlphaColor(
                alpha=0x20,
                color=self.importanceOverlay.fillColor)
            self.importanceOverlay.pen.color = travellermap.MapColours.Gray

            self.highlightWorlds.fillColor = maprenderer.makeAlphaColor(
                alpha=0x30,
                color=self.highlightWorlds.fillColor)
            self.highlightWorlds.pen.color = travellermap.MapColours.Gray
        elif self._style is travellermap.Style.Draft:
            # TODO: For some reason all text is getting underlining set
            inkOpacity = 0xB0

            self.showGalaxyBackground = False
            self.lightBackground = True

            self.deepBackgroundOpacity = 0

            # TODO: I Need to handle alpha here
            self.backgroundColor = travellermap.MapColours.AntiqueWhite
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

            self.subsectorGrid.pen.color = maprenderer.makeAlphaColor(
                alpha=inkOpacity,
                color=travellermap.MapColours.Firebrick)

            fontName = "Comic Sans MS"
            self.worlds.fontInfo.families = fontName
            self.worlds.smallFontInfo.families = fontName
            self.starport.fontInfo.families = fontName
            self.worlds.largeFontInfo.families = fontName
            self.worlds.largeFontInfo.size = self.worlds.fontInfo.size * 1.25
            self.worlds.fontInfo.size *= 0.8

            self.macroNames.fontInfo.families = fontName
            self.macroNames.mediumFontInfo.families = fontName
            self.macroNames.smallFontInfo.families = fontName
            self.megaNames.fontInfo.families = fontName
            self.megaNames.mediumFontInfo.families = fontName
            self.megaNames.smallFontInfo.families = fontName
            self.microBorders.smallFontInfo.families = fontName
            self.microBorders.largeFontInfo.families = fontName
            self.microBorders.fontInfo.families = fontName
            self.macroBorders.fontInfo.families = fontName
            self.macroRoutes.fontInfo.families = fontName
            self.capitals.fontInfo.families = fontName
            self.macroBorders.smallFontInfo.families = fontName

            self.microBorders.textStyle.uppercase = True

            self.sectorName.textStyle.uppercase = True
            self.subsectorNames.textStyle.uppercase = True

            # NOTE: This TODO came in from Traveller Map
            # TODO: Render small, around edges
            self.subsectorNames.visible = False

            self.worlds.textStyle.uppercase = True

            # NOTE: This TODO came in from Traveller Map
            # TODO: Decide on this. It's nice to not overwrite the parsec grid, but
            # it looks very cluttered, especially amber/red zones.
            self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.NoStyle

            self.worldDetails &= ~maprenderer.WorldDetails.Allegiance

            self.subsectorNames.fontInfo.families = fontName
            self.sectorName.fontInfo.families = fontName

            self.worlds.largeFontInfo.style |= maprenderer.FontStyle.Underline

            self.microBorders.pen.width = onePixel * 4
            self.microBorders.pen.dashStyle = maprenderer.DashStyle.Dot

            self.worldNoWater.fillColor = foregroundColor
            self.worldWater.fillColor = '#0000FF' # TODO: Color.Empty
            self.worldWater.pen = maprenderer.AbstractPen(foregroundColor, onePixel * 2)

            self.amberZone.pen.color = foregroundColor
            self.amberZone.pen.width = onePixel
            self.redZone.pen.width = onePixel * 2

            self.microRoutes.pen.color = travellermap.MapColours.Gray

            self.parsecGrid.pen.color = lightColor
            self.microBorders.textColor = maprenderer.makeAlphaColor(
                alpha=inkOpacity,
                color=travellermap.MapColours.Brown)

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.numberAllHexes = True

            self.populationOverlay.fillColor = maprenderer.makeAlphaColor(
                alpha=0x40,
                color=self.populationOverlay.fillColor)
            self.populationOverlay.pen.color = travellermap.MapColours.Gray

            self.importanceOverlay.fillColor = maprenderer.makeAlphaColor(
                alpha=0x20,
                color=self.importanceOverlay.fillColor)
            self.importanceOverlay.pen.color = travellermap.MapColours.Gray

            self.highlightWorlds.fillColor = maprenderer.makeAlphaColor(
                alpha=0x30,
                color=self.highlightWorlds.fillColor)
            self.highlightWorlds.pen.color = travellermap.MapColours.Gray
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

            self.subsectorGrid.pen.width = 0.03 * (64.0 / self.scale)
            self.subsectorGrid.pen.dashStyle = maprenderer.DashStyle.Custom
            self.subsectorGrid.pen.customDashPattern = [10.0, 8.0]

            self.sectorGrid.pen.width = 0.03 * (64.0 / self.scale)
            self.sectorGrid.pen.dashStyle = maprenderer.DashStyle.Custom
            self.sectorGrid.pen.customDashPattern = [10.0, 8.0]

            self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.Shadow

            self.worldDetails = self.worldDetails &  ~maprenderer.WorldDetails.Starport & \
                ~maprenderer.WorldDetails.Allegiance & ~maprenderer.WorldDetails.Bases & \
                ~maprenderer.WorldDetails.Hex

            if self.scale < StyleSheet._CandyMinWorldNameScale:
                self.worldDetails &= ~maprenderer.WorldDetails.KeyNames & \
                ~maprenderer.WorldDetails.AllNames
            if self.scale < StyleSheet._CandyMinUwpScale:
                self.worldDetails &= ~maprenderer.WorldDetails.Uwp

            self.amberZone.pen.color = travellermap.MapColours.Goldenrod
            self.amberZone.pen.width = self.redZone.pen.width = 0.035

            self.sectorName.textStyle.rotation = 0
            self.sectorName.textStyle.translation = maprenderer.AbstractPointF(0, -0.25)
            self.sectorName.textStyle.scale = maprenderer.AbstractSizeF(0.5, 0.25)
            self.sectorName.textStyle.uppercase = True

            self.subsectorNames.textStyle.rotation = 0
            self.subsectorNames.textStyle.translation = maprenderer.AbstractPointF(0, -0.25)
            self.subsectorNames.textStyle.scale = maprenderer.AbstractSizeF(0.3, 0.15) #  Expand
            self.subsectorNames.textStyle.uppercase = True

            self.subsectorNames.textColor = self.sectorName.textColor = \
                maprenderer.makeAlphaColor(
                    alpha=128,
                    color=travellermap.MapColours.Goldenrod)

            self.microBorders.textStyle.rotation = 0
            self.microBorders.textStyle.translation = maprenderer.AbstractPointF(0, 0.25)
            self.microBorders.textStyle.scale = maprenderer.AbstractSizeF(1.0, 0.5) # Expand
            self.microBorders.textStyle.uppercase = True

            self.microBorders.pen.color = maprenderer.makeAlphaColor(
                alpha=128,
                color=travellermap.MapColours.TravellerRed)
            self.microRoutes.pen.width = \
                routePenWidth if self.scale < StyleSheet._CandyMaxRouteRelativeScale else routePenWidth / 2
            self.macroBorders.pen.width = \
                borderPenWidth if self.scale < StyleSheet._CandyMaxBorderRelativeScale else borderPenWidth / 4
            self.microBorders.pen.width = \
                borderPenWidth if self.scale < StyleSheet._CandyMaxBorderRelativeScale else borderPenWidth / 4

            self.worlds.textStyle.rotation = 0
            self.worlds.textStyle.scale = maprenderer.AbstractSizeF(1, 0.5) # Expand
            self.worlds.textStyle.translation = maprenderer.AbstractPointF(0, 0)
            self.worlds.textStyle.uppercase = True

            if (self.scale > StyleSheet._CandyMaxWorldRelativeScale):
                self.hexContentScale = StyleSheet._CandyMaxWorldRelativeScale / self.scale
        elif self._style is travellermap.Style.Terminal:
            self.fadeSectorSubsectorNames = False
            self.showGalaxyBackground = False
            self.lightBackground = False

            self.backgroundColor = travellermap.MapColours.Black
            foregroundColor = travellermap.MapColours.Cyan
            highlightColor = travellermap.MapColours.White

            lightColor = travellermap.MapColours.LightBlue
            darkColor = travellermap.MapColours.DarkBlue
            dimColor = travellermap.MapColours.DimGray

            self.subsectorGrid.pen.color = travellermap.MapColours.Cyan

            fontNames = "Courier New"
            self.worlds.fontInfo.families = fontNames
            self.worlds.smallFontInfo.families = fontNames
            self.starport.fontInfo.families = fontNames
            self.worlds.largeFontInfo.families = fontNames
            self.worlds.largeFontInfo.size = self.worlds.fontInfo.size * 1.25
            self.worlds.fontInfo.size *= 0.8

            self.macroNames.fontInfo.families = fontNames
            self.macroNames.mediumFontInfo.families = fontNames
            self.macroNames.smallFontInfo.families = fontNames
            self.megaNames.fontInfo.families = fontNames
            self.megaNames.mediumFontInfo.families = fontNames
            self.megaNames.smallFontInfo.families = fontNames
            self.microBorders.smallFontInfo.families = fontNames
            self.microBorders.largeFontInfo.families = fontNames
            self.microBorders.fontInfo.families = fontNames
            self.macroBorders.fontInfo.families = fontNames
            self.macroRoutes.fontInfo.families = fontNames
            self.capitals.fontInfo.families = fontNames
            self.macroBorders.smallFontInfo.families = fontNames

            self.worlds.textStyle.uppercase = True
            self.microBorders.textStyle.uppercase = True
            self.microBorders.fontInfo.style |= maprenderer.FontStyle.Underline

            self.sectorName.textColor = foregroundColor
            self.sectorName.textStyle.scale = maprenderer.AbstractSizeF(1, 1)
            self.sectorName.textStyle.rotation = 0
            self.sectorName.textStyle.uppercase = True
            self.sectorName.fontInfo.style |= maprenderer.FontStyle.Bold
            self.sectorName.fontInfo.size *= 0.5

            self.subsectorNames.textColor = foregroundColor
            self.subsectorNames.textStyle.scale = maprenderer.AbstractSizeF(1, 1)
            self.subsectorNames.textStyle.rotation = 0
            self.subsectorNames.textStyle.uppercase = True
            self.subsectorNames.fontInfo.style |= maprenderer.FontStyle.Bold
            self.subsectorNames.fontInfo.size *= 0.5

            self.worlds.textStyle.uppercase = True

            self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.NoStyle

            self.subsectorNames.fontInfo.families = fontNames
            self.sectorName.fontInfo.families = fontNames

            self.worlds.largeFontInfo.style |= maprenderer.FontStyle.Underline

            self.microBorders.pen.width = onePixel * 4
            self.microBorders.pen.dashStyle = maprenderer.DashStyle.Dot

            self.worldNoWater.fillColor = foregroundColor
            self.worldWater.fillColor = '#0000FF' # TODO: Color.Empty
            self.worldWater.pen = maprenderer.AbstractPen(foregroundColor, onePixel * 2)

            self.amberZone.pen.color = foregroundColor
            self.amberZone.pen.width = onePixel
            self.redZone.pen.width = onePixel * 2

            self.microRoutes.pen.color = travellermap.MapColours.Gray

            self.parsecGrid.pen.color = travellermap.MapColours.Plum
            self.microBorders.textColor = travellermap.MapColours.Cyan

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

            self.imageBorderWidth = 0.1
            self.deepBackgroundOpacity = 0

            self.backgroundColor = '#E6E7E8'
            foregroundColor = travellermap.MapColours.Black
            highlightColor = travellermap.MapColours.Red

            lightColor = travellermap.MapColours.Black
            darkColor = travellermap.MapColours.Black
            dimColor = travellermap.MapColours.Gray

            self.sectorGrid.pen.color = self.subsectorGrid.pen.color = self.parsecGrid.pen.color = foregroundColor

            self.microBorders.textColor = travellermap.MapColours.DarkSlateGray

            fontName = "Calibri,Arial"
            self.worlds.fontInfo.families = fontName
            self.worlds.smallFontInfo.families = fontName
            self.starport.fontInfo.families = fontName
            self.starport.fontInfo.style = maprenderer.FontStyle.Regular
            self.worlds.largeFontInfo.families = fontName

            self.worlds.fontInfo.style = maprenderer.FontStyle.Regular
            self.worlds.largeFontInfo.style = maprenderer.FontStyle.Bold

            self.hexNumber.fontInfo = maprenderer.FontInfo(self.worlds.fontInfo)
            self.hexNumber.position.setY(-0.49)
            self.starport.fontInfo.style = maprenderer.FontStyle.Italic

            self.macroNames.fontInfo.families = fontName
            self.macroNames.mediumFontInfo.families = fontName
            self.macroNames.smallFontInfo.families = fontName
            self.megaNames.fontInfo.families = fontName
            self.megaNames.mediumFontInfo.families = fontName
            self.megaNames.smallFontInfo.families = fontName
            self.microBorders.smallFontInfo.families = fontName
            self.microBorders.largeFontInfo.families = fontName
            self.microBorders.fontInfo.families = fontName
            self.macroBorders.fontInfo.families = fontName
            self.macroRoutes.fontInfo.families = fontName
            self.capitals.fontInfo.families = fontName
            self.macroBorders.smallFontInfo.families = fontName

            self.microBorders.textStyle.uppercase = True

            self.sectorName.textStyle.uppercase = True
            self.subsectorNames.textStyle.uppercase = True

            self.subsectorNames.visible = False

            self.worlds.textStyle.uppercase = True

            self.worldDetails &= ~maprenderer.WorldDetails.Allegiance

            self.subsectorNames.fontInfo.families = fontName
            self.sectorName.fontInfo.families = fontName

            self.microBorders.pen.width = 0.11
            self.microBorders.pen.dashStyle = maprenderer.DashStyle.Dot

            self.worldWater.fillColor = travellermap.MapColours.MediumBlue
            self.worldNoWater.fillColor = travellermap.MapColours.DarkKhaki
            self.worldWater.pen = maprenderer.AbstractPen(
                travellermap.MapColours.DarkGray,
                onePixel * 2)
            self.worldNoWater.pen = maprenderer.AbstractPen(
                travellermap.MapColours.DarkGray,
                onePixel * 2)

            self.showZonesAsPerimeters = True
            self.greenZone.visible = True
            self.greenZone.pen.width = self.amberZone.pen.width = self.redZone.pen.width = 0.05

            self.greenZone.pen.color = '#80C676'
            self.amberZone.pen.color = '#FBB040'
            self.redZone.pen.color = travellermap.MapColours.Red

            self.microBorders.textColor = travellermap.MapColours.DarkSlateGray

            self.riftOpacity = min(self.riftOpacity, 0.30)

            self.discRadius = 0.11
            self.gasGiantPosition = maprenderer.AbstractPointF(0, -0.23)
            self.baseTopPosition = maprenderer.AbstractPointF(-0.22, -0.21)
            self.baseMiddlePosition = maprenderer.AbstractPointF(-0.32, 0.17)
            self.baseBottomPosition = maprenderer.AbstractPointF(0.22, -0.21)
            self.starport.position = maprenderer.AbstractPointF(0.175, 0.17)
            self.uwp.position = maprenderer.AbstractPointF(0, 0.40)
            self.discPosition = maprenderer.AbstractPointF(-self.discRadius, 0.16)
            self.worlds.textStyle.translation = maprenderer.AbstractPointF(0, -0.04)

            self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.NoStyle

            self.uwp.fontInfo = maprenderer.FontInfo(self.hexNumber.fontInfo)
            self.uwp.fillColor = travellermap.MapColours.Black
            self.uwp.textColor = travellermap.MapColours.White
            self.uwp.textBackgroundStyle = maprenderer.TextBackgroundStyle.Filled

        # NOTE: This TODO came in with traveller map
        # TODO: Do this with opacity.
        if fadeSectorSubsectorNames:
            if self.scale < 16:
                self.sectorName.textColor = foregroundColor
                self.subsectorNames.textColor = foregroundColor
            elif self.scale < 48:
                self.sectorName.textColor = darkColor
                self.subsectorNames.textColor = darkColor
            else:
                self.sectorName.textColor = dimColor
                self.subsectorNames.textColor = dimColor

        # Base element colors on foreground/light/dim/dark/highlight, if not specified by style.
        if not self.pseudoRandomStars.fillColor:
            self.pseudoRandomStars.fillColor = foregroundColor

        if not self.droyneWorlds.textColor:
            self.droyneWorlds.textColor = self.microBorders.textColor
        if not self.minorHomeWorlds.textColor:
            self.minorHomeWorlds.textColor = self.microBorders.textColor
        if not self.ancientsWorlds.textColor:
            self.ancientsWorlds.textColor = self.microBorders.textColor


        if not self.megaNames.textColor:
            self.megaNames.textColor = foregroundColor
        if not self.megaNames.textHighlightColor:
            self.megaNames.textHighlightColor = highlightColor

        if not self.macroNames.textColor:
            self.macroNames.textColor = foregroundColor
        if not self.macroNames.textHighlightColor:
            self.macroNames.textHighlightColor = highlightColor

        if not self.macroRoutes.textColor:
            self.macroRoutes.textColor = foregroundColor
        if not self.macroRoutes.textHighlightColor:
            self.macroRoutes.textHighlightColor = highlightColor

        if not self.worlds.textColor:
            self.worlds.textColor = foregroundColor
        if not self.worlds.textHighlightColor:
            self.worlds.textHighlightColor = highlightColor

        if not self.hexNumber.textColor:
            self.hexNumber.textColor = lightColor
        if not self.uwp.textColor:
            self.uwp.textColor = foregroundColor

        if not self.placeholder.textColor:
            self.placeholder.textColor = foregroundColor
        if not self.anomaly.textColor:
            self.anomaly.textColor = highlightColor

        if not self.imageBorderColor:
            self.imageBorderColor = lightColor

        # Convert list into a id -> index mapping.
        self.layerOrder.clear()
        for i, layer in enumerate(layers):
            self.layerOrder[layer] = i

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

        logscale = math.log(scale, 2.0)
        logmin = math.log(minScale, 2.0)
        logmax = math.log(maxScale, 2.0)
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