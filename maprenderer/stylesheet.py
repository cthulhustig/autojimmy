import maprenderer
import math
import traveller
import travellermap
import typing

class FontInfo():
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, other: 'FontInfo') -> None: ...
    @typing.overload
    def __init__(
        self,
        families: str,
        size: float,
        style: maprenderer.FontStyle = maprenderer.FontStyle.Regular
        ) -> None: ...

    def __init__(self, *args, **kwargs):
        if not args and not kwargs:
            self.families = ''
            self.size = 0
            self.style = maprenderer.FontStyle.Regular
        elif len(args) + len(kwargs) == 1:
            other = args[0] if len(args) > 0 else kwargs['other']
            if not isinstance(other, FontInfo):
                raise TypeError('The other parameter must be a FontInfo')
            self.copyFrom(other)
        else:
            self.families = args[0] if len(args) > 0 else kwargs['families']
            self.size = float(args[1] if len(args) > 1 else kwargs['size'])
            self.style = args[2] if len(args) > 2 else kwargs.get('style', maprenderer.FontStyle.Regular)

    def copyFrom(self, other: 'FontInfo') -> None:
        self.families = other.families
        self.size = other.size
        self.style = other.style

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
        def __init__(
                self,
                graphics: maprenderer.AbstractGraphics
                ) -> None:
            self.visible = False
            # TODO: This should probably be an AbstractBrush to avoid having to create it all the time
            self.content = ''
            self.pen: typing.Optional[maprenderer.AbstractPen] = None
            self.fillBrush: typing.Optional[maprenderer.AbstractBrush] = None
            self.textBrush: typing.Optional[maprenderer.AbstractBrush] = None
            self.textHighlightBrush: typing.Optional[maprenderer.AbstractBrush] = None

            self.textStyle = maprenderer.LabelStyle()
            self.textBackgroundStyle = maprenderer.TextBackgroundStyle.NoStyle
            self.fontInfo = maprenderer.FontInfo()
            self.smallFontInfo = maprenderer.FontInfo()
            self.mediumFontInfo = maprenderer.FontInfo()
            self.largeFontInfo = maprenderer.FontInfo()
            self.position = maprenderer.AbstractPointF()

            self._graphics = graphics
            self._font = None
            self._smallFont = None
            self._mediumFont = None
            self._largeFont = None

        @property
        def font(self) -> maprenderer.AbstractFont:
            if not self._font:
                if not self.fontInfo:
                    raise RuntimeError('AbstractFont has no fontInfo')
                self._font = self._graphics.createFont(
                    families=self.fontInfo.families,
                    emSize=self.fontInfo.size,
                    style=self.fontInfo.style)
            return self._font
        @property
        def smallFont(self) -> maprenderer.AbstractFont:
            if not self._smallFont:
                if not self.smallFontInfo:
                    raise RuntimeError('AbstractFont has no font smallFontInfo')
                self._smallFont = self._graphics.createFont(
                    families=self.smallFontInfo.families,
                    emSize=self.smallFontInfo.size,
                    style=self.smallFontInfo.style)
            return self._smallFont
        @property
        def mediumFont(self) -> maprenderer.AbstractFont:
            if not self._mediumFont:
                if not self.mediumFontInfo:
                    raise RuntimeError('AbstractFont has no font mediumFontInfo')
                self._mediumFont = self._graphics.createFont(
                    families=self.mediumFontInfo.families,
                    emSize=self.mediumFontInfo.size,
                    style=self.mediumFontInfo.style)
            return self._mediumFont
        @property
        def largeFont(self) -> maprenderer.AbstractFont:
            if not self._largeFont:
                if not self.largeFontInfo:
                    raise RuntimeError('AbstractFont has no font largeFontInfo')
                self._largeFont = self._graphics.createFont(
                    families=self.largeFontInfo.families,
                    emSize=self.largeFontInfo.size,
                    style=self.largeFontInfo.style)
            return self._largeFont

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
                brushColor = self.worldWater.fillBrush.color()
                penColor = self.worldWater.pen.color()
            else:
                brushColor = self.worldNoWater.fillBrush.color()
                penColor = self.worldNoWater.pen.color()
        else:
            # Classic colors

            # World disc
            hasWater = maprenderer.WorldHelper.hasWater(world)
            brushColor = \
                self.worldWater.fillBrush.color() \
                if hasWater else \
                self.worldNoWater.fillBrush.color()
            penColor = \
                self.worldWater.pen.color() \
                if hasWater else \
                self.worldNoWater.pen.color()

        return (penColor, brushColor)

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
        # TODO: Is hex rotation actually used for anything? Removing it
        # would reduce the number of transforms
        self.hexRotation = 0

        self.routeEndAdjust = 0.25

        self.t5AllegianceCodes = False

        self.highlightWorlds = StyleSheet.StyleElement(graphics=self._graphics)
        self.highlightWorldsPattern: typing.Optional[maprenderer.HighlightWorldPattern] = None

        self.droyneWorlds = StyleSheet.StyleElement(graphics=self._graphics)
        self.ancientsWorlds = StyleSheet.StyleElement(graphics=self._graphics)
        self.minorHomeWorlds = StyleSheet.StyleElement(graphics=self._graphics)

        # Worlds
        self.worlds = StyleSheet.StyleElement(graphics=self._graphics)
        self.showWorldDetailColors = False
        self.populationOverlay = StyleSheet.StyleElement(graphics=self._graphics)
        self.importanceOverlay = StyleSheet.StyleElement(graphics=self._graphics)
        self.capitalOverlay = StyleSheet.StyleElement(graphics=self._graphics)
        self.capitalOverlayAltA = StyleSheet.StyleElement(graphics=self._graphics)
        self.capitalOverlayAltB = StyleSheet.StyleElement(graphics=self._graphics)
        self.showStellarOverlay = False

        self.discPosition = maprenderer.AbstractPointF(0, 0)
        self.discRadius = 0.1
        self.gasGiantPosition = maprenderer.AbstractPointF(0, 0)
        self.allegiancePosition = maprenderer.AbstractPointF(0, 0)
        self.baseTopPosition = maprenderer.AbstractPointF(0, 0)
        self.baseBottomPosition = maprenderer.AbstractPointF(0, 0)
        self.baseMiddlePosition = maprenderer.AbstractPointF(0, 0)

        self.uwp = StyleSheet.StyleElement(graphics=self._graphics)
        self.starport = StyleSheet.StyleElement(graphics=self._graphics)

        self.worldDetails: maprenderer.WorldDetails = maprenderer.WorldDetails.NoDetails
        self.lowerCaseAllegiance = False

        self.wingdingFont: typing.Optional[maprenderer.AbstractFont] = None
        self.glyphFont: typing.Optional[maprenderer.AbstractFont] = None

        self.showGasGiantRing = False

        self.showTL = False
        self.ignoreBaseBias = False
        self.showZonesAsPerimeters = False

        # Hex Coordinates
        self.hexNumber = StyleSheet.StyleElement(graphics=self._graphics)
        self.hexCoordinateStyle = maprenderer.HexCoordinateStyle.Sector
        self.numberAllHexes = False

        # Sector Name
        self.sectorName = StyleSheet.StyleElement(graphics=self._graphics)
        self.showSomeSectorNames = False
        self.showAllSectorNames = False

        self.capitals = StyleSheet.StyleElement(graphics=self._graphics)
        self.subsectorNames = StyleSheet.StyleElement(graphics=self._graphics)
        self.greenZone = StyleSheet.StyleElement(graphics=self._graphics)
        self.amberZone = StyleSheet.StyleElement(graphics=self._graphics)
        self.redZone = StyleSheet.StyleElement(graphics=self._graphics)
        self.sectorGrid = StyleSheet.StyleElement(graphics=self._graphics)
        self.subsectorGrid = StyleSheet.StyleElement(graphics=self._graphics)
        self.parsecGrid = StyleSheet.StyleElement(graphics=self._graphics)
        self.worldWater = StyleSheet.StyleElement(graphics=self._graphics)
        self.worldNoWater = StyleSheet.StyleElement(graphics=self._graphics)
        self.macroRoutes = StyleSheet.StyleElement(graphics=self._graphics)
        self.microRoutes = StyleSheet.StyleElement(graphics=self._graphics)
        self.macroBorders = StyleSheet.StyleElement(graphics=self._graphics)
        self.macroNames = StyleSheet.StyleElement(graphics=self._graphics)
        self.megaNames = StyleSheet.StyleElement(graphics=self._graphics)
        self.pseudoRandomStars = StyleSheet.StyleElement(graphics=self._graphics)
        self.placeholder = StyleSheet.StyleElement(graphics=self._graphics)
        self.anomaly = StyleSheet.StyleElement(graphics=self._graphics)

        self.microBorders = StyleSheet.StyleElement(graphics=self._graphics)
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

            if self._graphics.supportsWingdings():
                self.wingdingsFont = self._graphics.createFont(
                    families='Wingdings',
                    emSize=0.2 if self.scale < StyleSheet._WorldFullMinScale else (0.175 * fontScale))
                self.glyphCharMap = None
            self.glyphFont = self._graphics.createFont(
                families='Arial Unicode MS,Segoe UI Symbol,Arial',
                emSize=0.175 if self.scale < StyleSheet._WorldFullMinScale else (0.15 * fontScale),
                style=maprenderer.FontStyle.Bold)

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
        self.microRoutes.pen = self._graphics.createPen(
            color=travellermap.MapColours.Gray,
            width=routePenWidth)

        self.microBorders.textBrush = self._graphics.createBrush(
            color=travellermap.MapColours.TravellerAmber)
        self.worldWater.fillBrush = self._graphics.createBrush(
            color=travellermap.MapColours.DeepSkyBlue)
        self.worldNoWater.fillBrush = self._graphics.createBrush(
            color=travellermap.MapColours.White)
        self.worldNoWater.pen = self._graphics.createPen(
            color='#0000FF', # TODO: Color.Empty;
            width=onePixel)

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
        self.worldWater.pen = self._graphics.createPen(
            color='#0000FF', # TODO: Color.Empty,
            width=max(0.01, onePixel))

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
            color='#0000FF', # TODO: Color.Empty,
            width=0.03 * penScale,
            style=maprenderer.LineStyle.Dash)
        self.importanceOverlay.pen = self._graphics.createPen(
            color='#0000FF', # TODO: Color.Empty,
            width=0.03 * penScale,
            style=maprenderer.LineStyle.Dot)
        self.highlightWorlds.pen =self._graphics.createPen(
            color='#0000FF', # TODO: Color.Empty,
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
            self.worldNoWater.fillBrush.setColor('#0000FF') # TODO: Color.Empty

            self.worldNoWater.fillBrush.setColor(travellermap.MapColours.White)
            self.worldNoWater.pen.setColor(travellermap.MapColours.Black)
            self.worldNoWater.pen.setWidth(onePixel)

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
            self.redZone.pen.setColor('#0000FF') # TODO: Color.Empty
            self.redZone.fillBrush = self._graphics.createBrush(
                color=maprenderer.makeAlphaColor(
                        alpha=0x80,
                        color=inkColor))

            self.macroBorders.pen.setColor(inkColor)
            self.macroRoutes.pen.setColor(inkColor)

            self.microBorders.pen.setColor(inkColor)
            self.microBorders.pen.setWidth(onePixel * 2)
            self.microBorders.fontInfo.size *= 0.6
            self.microBorders.fontInfo.style = maprenderer.FontStyle.Regular

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
            self.worldWater.pen.setColor('#0000FF') # TODO: Color.Empty
            self.worldNoWater.pen.setColor('#0000FF') # TODO: Color.Empty

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

            self.microBorders.pen.setWidth(onePixel * 4)
            self.microBorders.pen.setStyle(maprenderer.LineStyle.Dot)

            self.worldNoWater.fillBrush.setColor(foregroundColor)
            self.worldWater.fillBrush.setColor('#0000FF') # TODO: Color.Empty
            self.worldWater.pen = self._graphics.createPen(
                color=foregroundColor,
                width=onePixel * 2)

            self.amberZone.pen.setColor(foregroundColor)
            self.amberZone.pen.setWidth(onePixel)
            self.redZone.pen.setWidth(onePixel * 2)

            self.microRoutes.pen.setColor(travellermap.MapColours.Gray)

            self.parsecGrid.pen.setColor(lightColor)
            self.microBorders.textBrush.setColor(maprenderer.makeAlphaColor(
                alpha=inkOpacity,
                color=travellermap.MapColours.Brown))

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

            if (self.scale > StyleSheet._CandyMaxWorldRelativeScale):
                self.hexContentScale = StyleSheet._CandyMaxWorldRelativeScale / self.scale
        elif self._style is travellermap.Style.Terminal:
            self.fadeSectorSubsectorNames = False
            self.showGalaxyBackground = False
            self.lightBackground = False

            self.backgroundBrush.setColor(travellermap.MapColours.Black)
            foregroundColor = travellermap.MapColours.Cyan
            highlightColor = travellermap.MapColours.White

            lightColor = travellermap.MapColours.LightBlue
            darkColor = travellermap.MapColours.DarkBlue
            dimColor = travellermap.MapColours.DimGray

            self.subsectorGrid.pen.setColor(travellermap.MapColours.Cyan)

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

            self.sectorName.textBrush = self._graphics.createBrush(
                color=foregroundColor)
            self.sectorName.textStyle.scale = maprenderer.SizeF(1, 1)
            self.sectorName.textStyle.rotation = 0
            self.sectorName.textStyle.uppercase = True
            self.sectorName.fontInfo.style |= maprenderer.FontStyle.Bold
            self.sectorName.fontInfo.size *= 0.5

            self.subsectorNames.textBrush = self._graphics.createBrush(
                color=foregroundColor)
            self.subsectorNames.textStyle.scale = maprenderer.SizeF(1, 1)
            self.subsectorNames.textStyle.rotation = 0
            self.subsectorNames.textStyle.uppercase = True
            self.subsectorNames.fontInfo.style |= maprenderer.FontStyle.Bold
            self.subsectorNames.fontInfo.size *= 0.5

            self.worlds.textStyle.uppercase = True

            self.worlds.textBackgroundStyle = maprenderer.TextBackgroundStyle.NoStyle

            self.subsectorNames.fontInfo.families = fontNames
            self.sectorName.fontInfo.families = fontNames

            self.worlds.largeFontInfo.style |= maprenderer.FontStyle.Underline

            self.microBorders.pen.setWidth(onePixel * 4)
            self.microBorders.pen.setStyle(maprenderer.LineStyle.Dot)

            self.worldNoWater.fillBrush.setColor(foregroundColor)
            self.worldWater.fillBrush.setColor('#0000FF') # TODO: Color.Empty
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

            self.microBorders.pen.setWidth(0.11)
            self.microBorders.pen.setStyle(maprenderer.LineStyle.Dot)

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

            self.microBorders.textBrush.setColor(travellermap.MapColours.DarkSlateGray)

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
            self.uwp.fillBrush = self._graphics.createBrush(
                color=travellermap.MapColours.Black)
            self.uwp.textBrush = self._graphics.createBrush(
                color=travellermap.MapColours.White)
            self.uwp.textBackgroundStyle = maprenderer.TextBackgroundStyle.Filled

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