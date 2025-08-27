import app
import base64
import enum
import functools
import gui
import logic
import logging
import os
import traveller
import travellermap
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

_OverlayBkAlpha = 220
_OverlayTextAlpha = 255
_OverlayHighlightAlpha = 230
_OverlayBorderWidth = 2

def _overlayBkColour() -> str:
    colour = QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Base)
    colour.setAlpha(_OverlayBkAlpha)
    return gui.colourToString(colour)

def _overlayTextColour() -> str:
    colour = QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Text)
    colour.setAlpha(_OverlayTextAlpha)
    return gui.colourToString(colour)

def _overlayHighlightColour() -> str:
    colour = QtWidgets.QApplication.palette().color(QtGui.QPalette.ColorRole.Highlight)
    colour.setAlpha(_OverlayHighlightAlpha)
    return gui.colourToString(colour)

# Force a min font size of 10pt. That was the default before I added font
# scaling and the change to a user not using scaling is quite jarring
def _setMinFontSize(widget: QtWidgets.QWidget):
    font = widget.font()
    if font.pointSize() < 10:
        font.setPointSize(10)
        widget.setFont(font)

class MapOverlayLabel(QtWidgets.QLabel):
    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ..., flags: typing.Union[QtCore.Qt.WindowFlags, QtCore.Qt.WindowType] = ...) -> None: ...
    @typing.overload
    def __init__(self, text: str, parent: typing.Optional[QtWidgets.QWidget] = ..., flags: typing.Union[QtCore.Qt.WindowFlags, QtCore.Qt.WindowType] = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setStyleSheet(f'background-color:#00000000')
        _setMinFontSize(widget=self)

class _EnumSelectAction(QtWidgets.QAction):
    valueSelected = QtCore.pyqtSignal([enum.Enum])

    def __init__(
            self,
            value: enum.Enum,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(value.value, parent)

        self._value = value
        self.setCheckable(True)

        # It's important that this is connected to the trigger signal before any instances
        # of TravellerMapWidget. This call needs to made first as it will write the updated
        # setting to the config so the instances of TravellerMapWidget can read it back when
        # updating their URL.
        self.triggered.connect(self._actionTriggered)

    def _actionTriggered(self) -> None:
        if self.isChecked():
            self.valueSelected.emit(self._value)

class _EnumSelectActionGroup(QtWidgets.QActionGroup):
    selectionChanged = QtCore.pyqtSignal([enum.Enum])

    def __init__(
            self,
            enumType: typing.Type[enum.Enum],
            current: enum.Enum,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(parent)

        self.setExclusive(True)

        self._actionMap: typing.Dict[enum.Enum, QtWidgets.QAction] = {}
        for e in enumType:
            action = _EnumSelectAction(value=e)
            action.setChecked(e is current)
            action.valueSelected.connect(self._valueSelected)
            self.addAction(action)
            self._actionMap[e] = action

    def setCurrent(self, current: enum.Enum) -> None:
        action = self._actionMap.get(current)
        if action:
            action.setChecked(True)

    def _valueSelected(self, value: enum.Enum) -> None:
        self.selectionChanged.emit(value)

class _MapStyleActionGroup(_EnumSelectActionGroup):
    def __init__(self, current, parent = None):
        super().__init__(
            enumType=travellermap.Style,
            current=current,
            parent=parent)

class _MapOptionAction(QtWidgets.QAction):
    optionChanged = QtCore.pyqtSignal([travellermap.Option, bool])

    def __init__(
            self,
            option: travellermap.Option,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(option.value, parent)

        self._option = option

        self.setCheckable(True)

        # NOTE: The use of toggled here (rather than triggered) is important as
        # we want to be notified if the action has been changed programmatically
        # or by the user. For sector names, two of these actions are used in an
        # exclusive group. If the user checks one action while the other is
        # checked, the other action will automatically be unchecked and we want
        # to be notified so that we can disable the option for the other action
        # in the config
        self.toggled.connect(self._actionToggled)

    def _actionToggled(self, checked: bool) -> None:
        self.optionChanged.emit(self._option, checked)

class _ExclusiveMapOptionsActionGroup(QtWidgets.QActionGroup):
    optionChanged = QtCore.pyqtSignal([travellermap.Option, bool])

    def __init__(
            self,
            options: typing.Iterable[travellermap.Option],
            current: travellermap.Option,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self.setExclusive(True)
        if gui.minPyQtVersionCheck(minVersion='5.14'):
            # HACK: This is a horrible, horrible hack. The setExclusionPolicy method
            # was added in 5.14 which means it's not available on macOS Sierra. By
            # not calling the method if the version is to low it means we don't throw
            # an exception but the sector name toggle buttons won't work properly but
            # should work well enough to be usable
            self.setExclusionPolicy(
                QtWidgets.QActionGroup.ExclusionPolicy.ExclusiveOptional)

        self._optionActions: typing.Dict[travellermap.Option, _MapOptionAction] = {}
        for option in options:
            action = _MapOptionAction(option=option)
            action.setChecked(option is current)
            action.optionChanged.connect(self._optionChanged)
            self.addAction(action)
            self._optionActions[option] = action

    def setSelection(self, option: typing.Optional[travellermap.Option]) -> None:
        for actionOption, action in self._optionActions.items():
            action.setChecked(option is actionOption)

    def _optionChanged(
            self,
            option: travellermap.Option,
            checked: bool
            ) -> None:
        self.optionChanged.emit(option, checked)

class _RenderingTypeActionGroup(_EnumSelectActionGroup):
    def __init__(
            self,
            current: app.MapRendering,
            parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(
            enumType=app.MapRendering,
            current=current,
            parent=parent)

class _SearchComboBox(gui.HexSelectComboBox):
    def __init__(
            self,
            milieu: travellermap.Milieu,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(milieu=milieu, parent=parent)

        self.setStyleSheet(_SearchComboBox._formatComboStyle())
        self.view().setStyleSheet(_SearchComboBox._formatListStyle())
        self.enableAutoComplete(True)

    @staticmethod
    def _formatComboStyle() -> str:
        return 'border: {borderWidth}px solid {borderColour}; color:{textColour}; background-color:{bkColour}'.format(
            borderWidth=_OverlayBorderWidth,
            borderColour=_overlayHighlightColour(),
            textColour=_overlayTextColour(),
            bkColour=_overlayBkColour())

    @staticmethod
    def _formatListStyle() -> str:
        return 'border: {borderWidth}px solid {bkColour}; color:{textColour}; background-color:{bkColour}'.format(
            borderWidth=_OverlayBorderWidth,
            textColour=_overlayTextColour(),
            bkColour=_overlayBkColour())

class _CustomIconButton(gui.IconButton):
    def __init__(
            self,
            icon: QtGui.QIcon,
            size: QtCore.QSize,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(icon=icon, parent=parent)

        spacing = int(6 * gui.interfaceScale())

        self.setFixedSize(size)
        self.setIconSize(QtCore.QSize(size.width() - spacing, size.height() - spacing))

        self.setStyleSheet(
            'border: {borderWidth}px solid {borderColour}; background-color:{bkColour}'.format(
                borderWidth=_OverlayBorderWidth,
                borderColour=_overlayHighlightColour(),
                bkColour=_overlayBkColour()))

class _CustomScrollArea(QtWidgets.QScrollArea):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Preferred)

    def sizeHint(self) -> QtCore.QSize:
        contentSize = self.widget().sizeHint()

        margins = self.contentsMargins()
        expandWidth = margins.left() + margins.right()
        expandHeight = margins.top() + margins.bottom()

        verticalScrollbar = self.verticalScrollBar()
        if verticalScrollbar.isVisible():
            expandWidth += verticalScrollbar.sizeHint().width()

        horizontalScrollbar = self.horizontalScrollBar()
        if horizontalScrollbar.isVisible():
            expandHeight += horizontalScrollbar.sizeHint().height()

        return QtCore.QSize(
            contentSize.width() + expandWidth,
            contentSize.height() + expandHeight)

    def horizontalScrollBarHeight(self) -> int:
        return self.horizontalScrollBar().sizeHint().height()

    def verticalScrollBarWidth(self) -> int:
        return self.verticalScrollBar().sizeHint().width()

class _GripperWidget(QtWidgets.QWidget):
    _GripperWidth = 4

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(_GripperWidget._GripperWidth)
        self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)

    def paintEvent(self, event: QtGui.QPaintEvent):
        super().paintEvent(event)

        colour = QtGui.QColor(_overlayHighlightColour())

        event.rect()

        painter = QtGui.QPainter(self)
        painter.setPen(colour)
        painter.setBrush(colour)

        rect = QtCore.QRectF(event.rect())
        rect.setLeft(rect.left() - rect.width())
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, rect.width() / 2, rect.width() / 2)
        painter.drawPath(path)

class _InfoWidget(QtWidgets.QWidget):
    # Spacing between text content and right edge of the widget. Used to keep the
    # text away from the scroll bar
    _ContentRightMargin = 10

    # Grabber height offset
    _GrabberHeightOffset = 40

    def __init__(
            self,
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._milieu = milieu
        self._rules = traveller.Rules(rules)
        self._worldTagging = logic.WorldTagging(worldTagging) if worldTagging else None
        self._taggingColours = app.TaggingColours(taggingColours) if taggingColours else None

        self._resizeAnchor = None
        self._resizeBaseWidth = None
        self._resizeMinWidth = None
        self._resizeMaxWidth = None

        self._hex = None

        self._label = MapOverlayLabel()
        self._label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self._label.setWordWrap(True)
        self._label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._label.setMinimumHeight(0)
        self._label.setMaximumHeight(100000)

        self._scroller = _CustomScrollArea()
        self._scroller.setWidgetResizable(True)
        self._scroller.setWidget(self._label)
        self._scroller.setMinimumHeight(0)
        self._scroller.setMaximumHeight(100000)
        self._scroller.installEventFilter(self)

        self._gripper = _GripperWidget()
        self._gripper.setMouseTracking(True)
        self._gripper.installEventFilter(self)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._scroller, 1)
        layout.addWidget(self._gripper, 0)

        self.setStyleSheet(
            'color:{textColour}; background-color:{bkColour}'.format(
                textColour=_overlayTextColour(),
                bkColour=_overlayBkColour()))
        self.setMinimumHeight(0)
        self.setLayout(layout)
        self.setAutoFillBackground(True)

    def setMilieu(
            self,
            milieu: travellermap.Milieu,
            ) -> None:
        if milieu is self._milieu:
            return
        self._milieu = milieu
        self._updateContent(self._label.width())

    def setRules(
            self,
            rules: traveller.Rules,
            ) -> None:
        if rules == self._rules:
            return
        self._rules = traveller.Rules(rules)
        self._updateContent(self._label.width())

    def setWorldTagging(
            self,
            tagging: typing.Optional[logic.WorldTagging],
            ) -> None:
        if tagging == self._worldTagging:
            return
        self._worldTagging = logic.WorldTagging(tagging) if tagging else None
        self._updateContent(self._label.width())

    def setTaggingColours(
            self,
            colours: typing.Optional[app.TaggingColours]
            ) -> None:
        if colours == self._taggingColours:
            return
        self._taggingColours = app.TaggingColours(colours) if colours else None
        self._updateContent(self._label.width())

    def setHex(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._hex = hex
        self._updateContent(self._label.width())

        if self._hex:
            self.show()
        else:
            self.hide()

    def minimumWidth(self) -> int:
        if self._resizeMinWidth != None:
            return self._resizeMinWidth
        return super().minimumWidth()

    def setMinimumWidth(self, minw: int) -> None:
        #return super().setMinimumWidth(minw)
        self._resizeMinWidth = minw
        self.setFixedWidth(self.width())

    def maximumWidth(self) -> int:
        if self._resizeMaxWidth != None:
            return self._resizeMaxWidth
        return super().maximumWidth()

    def setMaximumWidth(self, maxw: int) -> None:
        #return super().setMaximumWidth(maxw)
        self._resizeMaxWidth = maxw
        self.setFixedWidth(self.width())

    def minimumSize(self) -> QtCore.QSize:
        return QtCore.QSize(self.minimumWidth(), self.minimumHeight())

    def maximumSize(self) -> QtCore.QSize:
        return QtCore.QSize(self.maximumWidth(), self.maximumHeight())

    def setFixedWidth(self, width: int) -> None:
        if self._resizeMinWidth != None and width < self._resizeMinWidth:
            width = self._resizeMinWidth
        if self._resizeMaxWidth != None and width > self._resizeMaxWidth:
            width = self._resizeMaxWidth
        return super().setFixedWidth(width)

    def sizeHint(self) -> QtCore.QSize:
        scrollerHint = self._scroller.sizeHint()
        gripperHint = self._gripper.sizeHint()
        return QtCore.QSize(
            scrollerHint.width() + gripperHint.width(),
            scrollerHint.height())

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if object == self._gripper:
            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                assert(isinstance(event, QtGui.QMouseEvent))
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    self._startDragResize()
            elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
                assert(isinstance(event, QtGui.QMouseEvent))
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    self._stopDragResize()
            elif event.type() == QtCore.QEvent.Type.MouseMove:
                assert(isinstance(event, QtGui.QMouseEvent))
                if self._resizeAnchor:
                    self._updateDragResize()
        elif object == self._scroller:
            if event.type() == QtCore.QEvent.Type.Resize:
                assert(isinstance(event, QtGui.QResizeEvent))
                usableWidth = max(
                    event.size().width() - (self._scroller.verticalScrollBarWidth() + 2),
                    0)
                self._updateContent(usableWidth)

        return super().eventFilter(object, event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        # Resize the gripper so it's not quite full height (it looks nicer)
        height = max(
            event.size().height() - _InfoWidget._GrabberHeightOffset,
            0)
        self._gripper.setFixedHeight(height)

        return super().resizeEvent(event)

    def _updateContent(self, width: int) -> None:
        self._label.setFixedWidth(width)

        if self._hex:
            text = gui.createHexToolTip(
                hex=self._hex,
                milieu=self._milieu,
                rules=self._rules,
                width=width - _InfoWidget._ContentRightMargin,
                worldTagging=self._worldTagging,
                taggingColours=self._taggingColours,
                # Don't display the thumbnail as the the user is already looking at the map so no point
                includeHexImage=False,
                hexImageStyle=None,
                hexImageOptions=None)
            self._label.setText(text)
        else:
            self._label.setText('')

        self.adjustSize()

    def _startDragResize(self) -> None:
        self._resizeAnchor = QtGui.QCursor.pos()
        self._resizeBaseWidth = self.width()

    def _stopDragResize(self) -> None:
        self._resizeAnchor = None
        self._resizeBaseWidth = None

    def _updateDragResize(self) -> None:
        delta = QtGui.QCursor.pos().x() - self._resizeAnchor.x()
        newWidth = self._resizeBaseWidth + delta
        self.setFixedWidth(newWidth)

class _LegendWidget(QtWidgets.QWidget):
    def __init__(
            self,
            style: travellermap.Style,
            options: typing.Collection[travellermap.Option],
            parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._style = style
        self._options = set(options)

        self._label = MapOverlayLabel()
        self._label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self._label.setWordWrap(True)
        self._label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._label.setMinimumHeight(0)
        self._label.setMaximumHeight(100000)
        self._label.setContentsMargins(20, 10, 20, 10)

        self._scroller = _CustomScrollArea()
        self._scroller.setWidgetResizable(True)
        self._scroller.setWidget(self._label)
        self._scroller.setMinimumHeight(0)
        self._scroller.setMaximumHeight(100000)
        self._scroller.installEventFilter(self)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._scroller, 1)

        self.setMinimumHeight(0)
        self.setLayout(widgetLayout)
        self.setAutoFillBackground(True)
        self.syncContent()
        self.adjustSize()

    def setMapStyle(self, style: travellermap.Style) -> None:
        if style is self._style:
            return
        self._style = style
        self.syncContent()

    def setMapOptions(self, options: typing.Collection[travellermap.Option]) -> None:
        options = set(options)
        if options == self._options:
            return

        self._options = options
        self.syncContent()

    def sizeHint(self) -> QtCore.QSize:
        return self._scroller.sizeHint()

    # This is based on the legend definition in index.html & index.css. Along
    # with some details from Sectorsheet.cs. It's been modified heavily to
    # work around the fact QLabel only supports a limited html subset.
    def syncContent(self):
        textStyle = 'color: #FFFFFF;'
        backgroundStyle = 'background-color: #000000;'
        largeGlyphStyle = 'width: 20px; text-align: center; font-size: 19pt;'
        middleGlyphStyle = 'width: 20px; text-align: center; font-size: 14pt;'
        smallGlyphStyle = 'width: 20px; text-align: center; font-size: 13pt;'
        lowPopulationStyle = ''
        highPopulationStyle = ''
        capitalStyle = ''

        highlightColour = '#E32736'
        hasWaterFillColour = '#00BFFF'
        hasWaterOutlineColour = None
        noWaterFillColour = '#F0F0F0'
        noWaterOutlineColour = None
        greenZoneColour = '#80c676'
        amberZoneColour = '#FFCC00'
        redZoneColour = '#E32736'

        worldGlyphSize = int(12 * gui.interfaceScale())

        if self._style is travellermap.Style.Print:
            textStyle = 'color: black;'
            backgroundStyle = 'background-color: #FFFFFF;'
            noWaterFillColour = '#FFFFFF'
            noWaterOutlineColour = '#6F6F6F'
        elif self._style is travellermap.Style.Draft:
            textStyle = 'color: #B0000000;' # Note that this is alpha blended
            backgroundStyle = 'background-color: #FAEBD7;'
            highlightColour = '#B0FF0000' # Note that this is alpha blended
            hasWaterOutlineColour = '#B0000000' # Note that this is alpha blended
            hasWaterFillColour = None
            noWaterFillColour = '#B0000000' # Note that this is alpha blended
            noWaterOutlineColour = '#B0000000' # Note that this is alpha blended
            amberZoneColour = '#B0000000' # Note that this is alpha blended
            lowPopulationStyle = 'text-transform: uppercase;'
            highPopulationStyle = 'text-transform: uppercase; text-decoration: underline;'
            capitalStyle = 'text-transform: uppercase;'
        elif self._style is travellermap.Style.Atlas:
            textStyle = 'color: black;'
            backgroundStyle = 'background-color: #FFFFFF;'
            highlightColour = '#808080'
            hasWaterFillColour = '#000000'
            noWaterFillColour = '#FFFFFF'
            noWaterOutlineColour = '#000000'
            amberZoneColour = '#C0C0C0'
            redZoneColour = '#000000'
        elif self._style is travellermap.Style.Mongoose:
            textStyle = 'color: #000000;'
            backgroundStyle = 'background-color: #E6E7E8;'
            hasWaterFillColour = '#0000CD'
            noWaterFillColour = '#BDB76B'
            hasWaterOutlineColour = noWaterOutlineColour = '#A9A9A9'
            amberZoneColour = '#FBB040'
            lowPopulationStyle = 'text-transform: uppercase;'
            highPopulationStyle = 'text-transform: uppercase; font-weight: bold;'
            capitalStyle = 'text-transform: uppercase;'
        elif self._style is travellermap.Style.Fasa:
            textStyle = 'color: #5C4033;'
            backgroundStyle = 'background-color: #FFFFFF;'
            amberZoneColour = '#5C4033'
            redZoneColour = '#805C4033' # Note that this is alpha blended
        elif self._style is travellermap.Style.Terminal:
            textStyle = 'color: #00FFFF; font-family: "Courier New", "Courier", monospace;'
            hasWaterFillColour = '#000000'
            hasWaterOutlineColour = '#00FFFF'
            noWaterFillColour = '#00FFFF'

        characteristicItems = []
        if travellermap.Option.WorldColours in self._options and \
                self._style is not travellermap.Style.Atlas:
            characteristicItems.extend([
                ('Rich &amp; Agricultural', self._createWorldGlyph(size=worldGlyphSize, fill='#F1C232'), ''),
                ('Agricultural', self._createWorldGlyph(size=worldGlyphSize, fill='#6AA84F'), ''),
                ('Rich', self._createWorldGlyph(size=worldGlyphSize, fill='#800080'), ''),
                ('Industrial', self._createWorldGlyph(size=worldGlyphSize, fill='#808080'), ''),
                ('Corrosive/Insidious', self._createWorldGlyph(size=worldGlyphSize, fill='#BE5F06'), ''),
                ('Vacuum', self._createWorldGlyph(size=worldGlyphSize, fill='#000000', outline='#FFFFFF'), '')
            ])
        characteristicItems.extend([
            ('Water Present', self._createWorldGlyph(size=worldGlyphSize, fill=hasWaterFillColour, outline=hasWaterOutlineColour), ''),
            ('No Water Present', self._createWorldGlyph(size=worldGlyphSize, fill=noWaterFillColour, outline=noWaterOutlineColour), ''),
            ('Asteroid Belt', ':::', middleGlyphStyle),
            ('Unknown', '&#x2217;', middleGlyphStyle),
            ('Anomaly', '&#x2316;', f'{middleGlyphStyle} color: {highlightColour};'),
        ])

        baseItems = [
            ('Imperial Naval Base', '&#x2605;', smallGlyphStyle),
            ('Imperial Scout Base', '&#x25B2;', middleGlyphStyle),
            ('Imperial Scout Way Station', '&#x25B2;', f'{middleGlyphStyle} color: {highlightColour};'),
            ('Imperial Naval Depot', '&#x25A0;', middleGlyphStyle),
            ('Zhodani Base', '&diams;', largeGlyphStyle),
            ('Zhodani Relay Station', '&diams;', f'{largeGlyphStyle} color: {highlightColour};'),
            ('Other Naval / Tlauku Base', '&#x2605;', f'{smallGlyphStyle} color: {highlightColour};'),
            ('Other Naval Outpost / Depot', '&#x25A0;', f'{middleGlyphStyle} color: {highlightColour};'),
            ('Corsair / Clan / Embassy', '&#x2217;&#x2217;', f'{smallGlyphStyle}'),
            ('Military Base / Garrison', '&#x2726;', middleGlyphStyle),
            ('Independent Base', '&bull;', largeGlyphStyle),
            ('Research Station', '&Gamma;', f'{middleGlyphStyle} color: {highlightColour};'),
            ('Imperial Reserve', '<b>R</b>', middleGlyphStyle),
            ('Penal Colony', '<b>P</b>', f'{middleGlyphStyle} color: {highlightColour};'),
            ('Prison, Exile Camp', '<b>X</b>', middleGlyphStyle),
        ]

        zoneItems = []
        if self._style is travellermap.Style.Mongoose:
            zoneItems.append(('Green Zone', '&#x25AC;', f'{largeGlyphStyle} color: {greenZoneColour};'))
        zoneItems.extend([
            ('Amber Zone', '&#x25AC;', f'{largeGlyphStyle} color: {amberZoneColour};'),
            ('Red Zone', '&#x25AC;', f'{largeGlyphStyle} color: {redZoneColour};')
        ])

        populationItems = [
            ('Under 1 billion', 'Wef', lowPopulationStyle),
            ('Over 1 billion', 'YNAM', highPopulationStyle),
            ('Subsector capitals', 'Highlighted', f'{capitalStyle} color: {highlightColour};')
        ]

        legendContent = '<html>'
        legendContent += f'<h2 style="text-align: center; text-transform: uppercase; text-decoration: underline;">Map Legend</h2>'

        imageData = self._loadLegendImage(imageFile=f'Legend_1003_{self._style.name.lower()}.png')
        if imageData:
            legendContent += f'<center><img src=data:image/png;base64,{imageData}></center>'

        legendContent += '<br>'

        imageData = self._loadLegendImage(imageFile=f'Legend_1006_{self._style.name.lower()}.png')
        if imageData:
            legendContent += f'<center><img src=data:image/png;base64,{imageData}></center>'

        if self._style is not travellermap.Style.Candy and \
                self._style is not travellermap.Style.Fasa:
            legendContent += self._createLegendSection(
                title='World Characteristics',
                items=characteristicItems)
            legendContent += self._createLegendSection(
                title='Bases',
                items=baseItems)
        legendContent += self._createLegendSection(
            title='Travel Zones',
            items=zoneItems)

        if self._style is not travellermap.Style.Fasa:
            legendContent += self._createLegendSection(
                title='Population',
                items=populationItems)

        legendContent += '</html>'

        self._label.setStyleSheet(f'{textStyle} {backgroundStyle}')
        self._label.setText(legendContent)

        return legendContent

    def _loadLegendImage(
            self,
            imageFile: str
            ) -> typing.Optional[str]:
        installDir = app.Config.instance().installDir()
        imagePath = os.path.join(installDir, 'data', 'legend', imageFile)
        try:
            with open(imagePath, 'rb') as file:
                return base64.b64encode(file.read()).decode()
        except Exception as ex:
            logging.error(
                f'An exception occurred while loading legend image {imagePath}',
                exc_info=ex)
            return None

    def _createLegendSection(
            self,
            title: str,
            items: typing.Iterable[typing.Tuple[str, typing.Union[str, bytes], str]] # (Text, Glyph, Style)
            ) -> str:
        sectionText = f'<h2 style="text-align: center; text-transform: uppercase; text-decoration: underline;">{title}</h2>'
        sectionText += '<center><table>'

        for text, glyph, style in items:
            sectionText += '<tr>'
            sectionText += f'<td valign=middle align=center style="{style}">'
            if isinstance(glyph, str):
                sectionText += glyph
            else:
                sectionText += f'<center><img src=data:image/png;base64,{base64.b64encode(glyph).decode()}></center>'
            sectionText += '</td>'
            # The text is added with an extra leading space in order to add some
            # padding between the glyph and the text. This is pretty hacky but
            # it means interface scaling is automatically applied to the padding
            sectionText += f'<td valign=middle>&nbsp;{text}</td>'
            sectionText += '</tr>'

        sectionText += '</table></center>'

        return sectionText

    def _createWorldGlyph(
            self,
            size: int,
            fill: typing.Optional[str] = None,
            outline: typing.Optional[str] = None
            ) -> bytes:
        if fill is None:
            fill = QtCore.Qt.GlobalColor.transparent
        if outline is None:
            outline = fill

        pixelRatio = QtWidgets.QApplication.instance().devicePixelRatio()

        pixmap = QtGui.QPixmap(QtCore.QSize(size, size) * pixelRatio)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter()
        painter.begin(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        painter.setPen(QtGui.QColor(outline))
        painter.setBrush(QtGui.QColor(fill))
        painter.drawEllipse(pixmap.rect())

        painter.end()

        glyphBytes = QtCore.QByteArray()
        buffer = QtCore.QBuffer(glyphBytes)
        pixmap.save(buffer, 'PNG')
        return glyphBytes.data()

class _ActionGroupComboBox(gui.ComboBoxEx):
    def __init__(
            self,
            group: QtWidgets.QActionGroup,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._group = group

        selected = None
        for action in self._group.actions():
            self.addItem(action.text(), action)
            if action.isChecked():
                selected = action
        if selected:
            self.setCurrentByUserData(selected)

        self.currentIndexChanged.connect(
            self._selectionChanged)

        self._connections: typing.List[
            typing.Tuple[QtWidgets.QAction, functools.partial]] = []
        for action in self._group.actions():
            partial = functools.partial(self._syncFromAction, action)
            action.changed.connect(partial)
            self._connections.append((action, partial))

        _setMinFontSize(widget=self)

    def __del__(self) -> None:
        # Disconnect actions when widget is deleted to prevent C++ exception in
        # QT implementation
        for action, partial in self._connections:
            action.changed.disconnect(partial)

    def _selectionChanged(self, index: int) -> None:
        action = self.userDataByIndex(index)
        if isinstance(action, QtWidgets.QAction):
            action.trigger()

    def _syncFromAction(self, action: QtWidgets.QAction) -> None:
        if action and action.isChecked():
            self.setCurrentByUserData(action)

class _ActionToggleButton(gui.ToggleButton):
    def __init__(
            self,
            action: QtWidgets.QAction,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._action = action
        self._syncFromAction()

        self._action.changed.connect(
            self._syncFromAction)
        self.clicked.connect(
            self._action.trigger)

    def _syncFromAction(self) -> None:
        self.setEnabled(self._action.isEnabled())
        self.setChecked(self._action.isChecked())
        self.setToolTip(self._action.toolTip())

class _ConfigWidget(QtWidgets.QWidget):
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._optionsWidget = gui.SectionGroupWidget()
        self._optionsWidget.setStyleSheet(f'background-color:#00000000')
        _setMinFontSize(widget=self._optionsWidget)

        optionsLayout = QtWidgets.QVBoxLayout()
        optionsLayout.addWidget(self._optionsWidget)
        optionsLayout.addStretch()

        wrapperWidget = gui.LayoutWrapperWidget(
            layout=optionsLayout)

        self._scroller = _CustomScrollArea()
        self._scroller.setWidgetResizable(True)
        self._scroller.setWidget(wrapperWidget)
        self._scroller.setMinimumHeight(0)
        self._scroller.setMaximumHeight(100000)
        self._scroller.installEventFilter(self)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._scroller, 1)

        self.setStyleSheet(
            'color:{textColour}; background-color:{bkColour}'.format(
                textColour=_overlayTextColour(),
                bkColour=_overlayBkColour()))
        self.setMinimumHeight(0)
        self.setLayout(widgetLayout)
        self.setAutoFillBackground(True)
        self.adjustSize()

    def sizeHint(self) -> QtCore.QSize:
        return self._scroller.sizeHint()

    def addSection(
            self,
            section: str,
            content: typing.Union[QtWidgets.QLayout, QtWidgets.QWidget]
            ) -> None:
        self._optionsWidget.addSectionContent(
            label=section,
            content=content)
        self._optionsWidget.adjustSize()
        self.adjustSize()

class _ConfigSectionLayout(QtWidgets.QGridLayout):
    def addToggleAction(self, action: QtWidgets.QAction):
        row = self.rowCount()

        button = _ActionToggleButton(action=action)
        self.addWidget(button, row, 0)

        label = MapOverlayLabel(action.text())
        self.addWidget(label, row, 1)

class MapWidgetEx(QtWidgets.QWidget):
    leftClicked = QtCore.pyqtSignal([travellermap.HexPosition])
    rightClicked = QtCore.pyqtSignal([travellermap.HexPosition])

    mapStyleChanged = QtCore.pyqtSignal([travellermap.Style])
    mapOptionsChanged = QtCore.pyqtSignal([set]) # Set of travellermap.Options
    mapRenderingChanged = QtCore.pyqtSignal([app.MapRendering])
    mapAnimationChanged = QtCore.pyqtSignal([bool])

    selectionChanged = QtCore.pyqtSignal()

    class SelectionMode(enum.Enum):
        NoSelect = 0
        SingleSelect = 1
        MultiSelect = 2

    class MenuAction(enum.Enum):
        ExportImage = 0

    _StateVersion = 'MapWidgetEx_v1'

    _ControlWidgetInset = 20
    _ControlWidgetSpacing = 5

    _SelectionFillDarkStyleColour = QtGui.QColor('#7F8080FF')
    _SelectionFillLightStyleColour = QtGui.QColor('#7F8080FF')
    _SelectionOutlineDarkStyleColour = QtGui.QColor('#7F42d7f5')
    _SelectionOutlineLightStyleColour = QtGui.QColor('#7F5442f5')
    _SelectionOutlineWidth = 6

    _HomeLinearScale = 1

    def __init__(
            self,
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            style: travellermap.Style,
            options: typing.Collection[travellermap.Option],
            rendering: app.MapRendering,
            animated: bool,
            worldTagging: logic.WorldTagging,
            taggingColours: app.TaggingColours,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._milieu = milieu
        self._rules = traveller.Rules(rules)
        self._style = style
        self._options = set(options)
        self._rendering = rendering
        self._animated = animated
        self._worldTagging = logic.WorldTagging(worldTagging)
        self._taggingColours = app.TaggingColours(taggingColours)

        self._selectionMode = MapWidgetEx.SelectionMode.NoSelect
        self._enableDeadSpaceSelection = False
        self._selectedHexes: typing.Dict[
            travellermap.HexPosition,
            str # Overlay key
            ] = {}
        self._selectionOutlineHandle = None
        self._infoHex = None

        fontMetrics = QtGui.QFontMetrics(QtWidgets.QApplication.font())
        controlHeights = int(fontMetrics.lineSpacing() * 2)
        searchWidth = fontMetrics.width('_' * 40)
        buttonSize = QtCore.QSize(controlHeights, controlHeights)

        self._mapWidget = gui.MapWidget(
            milieu=self._milieu,
            style=self._style,
            options=self._options,
            rendering=rendering,
            animated=animated,
            parent=self)
        self._mapWidget.leftClicked.connect(self._handleLeftClick)
        self._mapWidget.rightClicked.connect(self._handleRightClick)

        # For reasons I don't understand this needs to be done after load has been called on the map.
        # If it's not then the search control is drawn under the map widget. Using stackUnder doesn't
        # seem to work either.
        self._searchWidget = _SearchComboBox(milieu=self._milieu, parent=self)
        self._searchWidget.setFixedSize(searchWidth, controlHeights)
        self._searchWidget.installEventFilter(self)
        self._searchWidget.editTextChanged.connect(self._searchHexTextEdited)
        self._searchWidget.hexChanged.connect(self._searchHexSelected)
        self._mapWidget.stackUnder(self._searchWidget)

        self._searchButton = _CustomIconButton(
            icon=gui.loadIcon(id=gui.Icon.Search),
            size=buttonSize,
            parent=self)
        self._searchButton.installEventFilter(self)
        self._searchButton.clicked.connect(self._searchButtonClicked)

        self._infoButton = _CustomIconButton(
            icon=gui.createOnOffIcon(source=gui.loadIcon(id=gui.Icon.Info)),
            size=buttonSize,
            parent=self)
        self._infoButton.setCheckable(True)
        self._infoButton.setChecked(True)
        self._infoButton.toggled.connect(self._showInfoToggled)

        self._infoWidget = _InfoWidget(
            milieu=self._milieu,
            rules=self._rules,
            worldTagging=worldTagging,
            taggingColours=taggingColours,
            parent=self)
        self._infoWidget.setMinimumWidth(200)
        self._infoWidget.setFixedWidth(300)
        self._infoWidget.hide()

        self._fullScreenButton = _CustomIconButton(
            icon=gui.createToggleIcon(
                onIcon=gui.loadIcon(id=gui.Icon.ArrowsMinimize),
                offIcon=gui.loadIcon(id=gui.Icon.ArrowsMaximize)),
            size=buttonSize,
            parent=self)
        self._fullScreenButton.setCheckable(True)
        self._fullScreenButton.setChecked(False)
        self._fullScreenButton.toggled.connect(self._fullScreenToggled)

        self._homeButton = _CustomIconButton(
            icon=gui.loadIcon(id=gui.Icon.Home),
            size=buttonSize,
            parent=self)
        self._homeButton.clicked.connect(self._gotoHome)

        self._legendButton = _CustomIconButton(
            icon=gui.createOnOffIcon(source=gui.loadIcon(id=gui.Icon.Key)),
            size=buttonSize,
            parent=self)
        self._legendButton.setCheckable(True)
        self._legendButton.setChecked(False)
        self._legendButton.toggled.connect(self._showLegendToggled)

        self._legendWidget = _LegendWidget(
            style=self._style,
            options=self._options,
            parent=self)
        self._legendWidget.hide()

        self._configButton = _CustomIconButton(
            icon=gui.createOnOffIcon(source=gui.loadIcon(id=gui.Icon.Settings)),
            size=buttonSize,
            parent=self)
        self._configButton.setCheckable(True)
        self._configButton.setChecked(False)
        self._configButton.toggled.connect(self._showConfigToggled)

        self._configWidget = _ConfigWidget(self)
        self._configWidget.hide()

        #
        # Style
        #
        self._styleActionGroup = _MapStyleActionGroup(current=self._style)
        self._styleActionGroup.selectionChanged.connect(
            self._mapStyleChanged)
        self._configWidget.addSection(
            section='Style',
            content=_ActionGroupComboBox(self._styleActionGroup))

        #
        # Rendering
        #
        renderingConfigLayout = _ConfigSectionLayout()

        self._renderingActionGroup = _RenderingTypeActionGroup(
            current=self._rendering)
        self._renderingActionGroup.selectionChanged.connect(
            self._renderingChanged)
        renderingConfigLayout.addWidget(
            _ActionGroupComboBox(self._renderingActionGroup),
            renderingConfigLayout.rowCount(), 0, 1, 2)

        self._animatedAction = QtWidgets.QAction('Animations', self)
        self._animatedAction.setCheckable(True)
        self._animatedAction.setChecked(self._animated)
        self._animatedAction.toggled.connect(self._animatedChanged)
        renderingConfigLayout.addToggleAction(self._animatedAction)

        self._configWidget.addSection(
            section='Rendering',
            content=renderingConfigLayout)

        #
        # Features
        #
        featuresConfigLayout = _ConfigSectionLayout()

        self._galacticDirectionsAction = _MapOptionAction(
                option=travellermap.Option.GalacticDirections)
        self._galacticDirectionsAction.setChecked(
            travellermap.Option.GalacticDirections in self._options)
        self._galacticDirectionsAction.optionChanged.connect(self._mapOptionChanged)
        featuresConfigLayout.addToggleAction(self._galacticDirectionsAction)

        self._sectorGridAction = _MapOptionAction(
            option=travellermap.Option.SectorGrid)
        self._sectorGridAction.setChecked(
            travellermap.Option.SectorGrid in self._options)
        self._sectorGridAction.optionChanged.connect(self._mapOptionChanged)
        featuresConfigLayout.addToggleAction(self._sectorGridAction)

        currentNames = None
        if travellermap.Option.SelectedSectorNames in self._options:
            currentNames = travellermap.Option.SelectedSectorNames
        elif travellermap.Option.SectorNames in self._options:
            currentNames = travellermap.Option.SectorNames
        self._sectorNamesActionGroup = _ExclusiveMapOptionsActionGroup(
            options=[
                travellermap.Option.SelectedSectorNames,
                travellermap.Option.SectorNames],
            current=currentNames)
        self._sectorNamesActionGroup.optionChanged.connect(self._mapOptionChanged)
        sectorNamesLayout = _ConfigSectionLayout()
        for action in self._sectorNamesActionGroup.actions():
            sectorNamesLayout.addToggleAction(action)
        featuresConfigLayout.addLayout(
            sectorNamesLayout,
            sectorNamesLayout.rowCount(), 0, 1, 2)

        self._bordersAction = _MapOptionAction(
            option=travellermap.Option.Borders)
        self._bordersAction.setChecked(
            travellermap.Option.Borders in self._options)
        self._bordersAction.optionChanged.connect(self._mapOptionChanged)
        featuresConfigLayout.addToggleAction(self._bordersAction)

        self._routesAction = _MapOptionAction(
            option=travellermap.Option.Routes)
        self._routesAction.setChecked(
            travellermap.Option.Routes in self._options)
        self._routesAction.optionChanged.connect(self._mapOptionChanged)
        featuresConfigLayout.addToggleAction(self._routesAction)

        self._regionNamesAction = _MapOptionAction(
            option=travellermap.Option.RegionNames)
        self._regionNamesAction.setChecked(
            travellermap.Option.RegionNames in self._options)
        self._regionNamesAction.optionChanged.connect(self._mapOptionChanged)
        featuresConfigLayout.addToggleAction(self._regionNamesAction)

        self._importantWorldsAction = _MapOptionAction(
            option=travellermap.Option.ImportantWorlds)
        self._importantWorldsAction.setChecked(
            travellermap.Option.ImportantWorlds in self._options)
        self._importantWorldsAction.optionChanged.connect(self._mapOptionChanged)
        featuresConfigLayout.addToggleAction(self._importantWorldsAction)

        self._configWidget.addSection(
            section='Features',
            content=featuresConfigLayout)

        #
        # Appearance
        #
        appearanceConfigLayout = _ConfigSectionLayout()

        self._worldColoursAction = _MapOptionAction(
            option=travellermap.Option.WorldColours)
        self._worldColoursAction.setChecked(
            travellermap.Option.WorldColours in self._options)
        self._worldColoursAction.optionChanged.connect(self._mapOptionChanged)
        appearanceConfigLayout.addToggleAction(self._worldColoursAction)

        self._filledBordersAction = _MapOptionAction(
            option=travellermap.Option.FilledBorders)
        self._filledBordersAction.setChecked(
            travellermap.Option.FilledBorders in self._options)
        self._filledBordersAction.optionChanged.connect(self._mapOptionChanged)
        appearanceConfigLayout.addToggleAction(self._filledBordersAction)

        self._dimUnofficialAction = _MapOptionAction(
            option=travellermap.Option.DimUnofficial)
        self._dimUnofficialAction.setChecked(
            travellermap.Option.DimUnofficial in self._options)
        self._dimUnofficialAction.optionChanged.connect(self._mapOptionChanged)
        appearanceConfigLayout.addToggleAction(self._dimUnofficialAction)

        self._configWidget.addSection(
            section='Appearance',
            content=appearanceConfigLayout)

        #
        # Overlays
        #
        overlayConfigLayout = _ConfigSectionLayout()

        self._mainsOverlayAction = _MapOptionAction(
            option=travellermap.Option.MainsOverlay)
        self._mainsOverlayAction.setChecked(
            travellermap.Option.MainsOverlay in self._options)
        self._mainsOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._mainsOverlayAction)

        self._importanceOverlayAction = _MapOptionAction(
            option=travellermap.Option.ImportanceOverlay)
        self._importanceOverlayAction.setChecked(
            travellermap.Option.ImportanceOverlay in self._options)
        self._importanceOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._importanceOverlayAction)

        self._populationOverlayAction = _MapOptionAction(
            option=travellermap.Option.PopulationOverlay)
        self._populationOverlayAction.setChecked(
            travellermap.Option.PopulationOverlay in self._options)
        self._populationOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._populationOverlayAction)

        self._capitalsOverlayAction = _MapOptionAction(
            option=travellermap.Option.CapitalsOverlay)
        self._capitalsOverlayAction.setChecked(
            travellermap.Option.CapitalsOverlay in self._options)
        self._capitalsOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._capitalsOverlayAction)

        self._minorRaceOverlayAction = _MapOptionAction(
            option=travellermap.Option.MinorRaceOverlay)
        self._minorRaceOverlayAction.setChecked(
            travellermap.Option.MinorRaceOverlay in self._options)
        self._minorRaceOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._minorRaceOverlayAction)

        self._droyneWorldOverlayAction = _MapOptionAction(
            option=travellermap.Option.DroyneWorldOverlay)
        self._droyneWorldOverlayAction.setChecked(
            travellermap.Option.DroyneWorldOverlay in self._options)
        self._droyneWorldOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._droyneWorldOverlayAction)

        self._ancientSitesOverlayAction = _MapOptionAction(
            option=travellermap.Option.AncientSitesOverlay)
        self._ancientSitesOverlayAction.setChecked(
            travellermap.Option.AncientSitesOverlay in self._options)
        self._ancientSitesOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._ancientSitesOverlayAction)

        self._stellarOverlayAction = _MapOptionAction(
            option=travellermap.Option.StellarOverlay)
        self._stellarOverlayAction.setChecked(
            travellermap.Option.StellarOverlay in self._options)
        self._stellarOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._stellarOverlayAction)

        self._empressWaveOverlayAction = _MapOptionAction(
            option=travellermap.Option.EmpressWaveOverlay)
        self._empressWaveOverlayAction.setChecked(
            travellermap.Option.EmpressWaveOverlay in self._options)
        self._empressWaveOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._empressWaveOverlayAction)

        self._qrekrshaZoneOverlayAction = _MapOptionAction(
            option=travellermap.Option.QrekrshaZoneOverlay)
        self._qrekrshaZoneOverlayAction.setChecked(
            travellermap.Option.QrekrshaZoneOverlay in self._options)
        self._qrekrshaZoneOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._qrekrshaZoneOverlayAction)

        self._antaresSupernovaOverlayAction = _MapOptionAction(
            option=travellermap.Option.AntaresSupernovaOverlay)
        self._antaresSupernovaOverlayAction.setChecked(
            travellermap.Option.AntaresSupernovaOverlay in self._options)
        self._antaresSupernovaOverlayAction.optionChanged.connect(self._mapOptionChanged)
        overlayConfigLayout.addToggleAction(self._antaresSupernovaOverlayAction)

        self._configWidget.addSection(
            section='Overlays',
            content=overlayConfigLayout)

        self._configureOverlayControls()

        self._menuActions: typing.Dict[typing.Tuple[enum.Enum, QtWidgets.QAction]] = {}

        action = QtWidgets.QAction(
            'Export Image...',
            self)
        action.triggered.connect(self.promptExportImage)
        self.setMenuAction(MapWidgetEx.MenuAction.ExportImage, action)

    def milieu(self) -> travellermap.Milieu:
        return self._milieu

    def setMilieu(self, milieu: travellermap.Milieu) -> None:
        if milieu is self._milieu:
            return

        self._milieu = milieu
        self._mapWidget.setMilieu(milieu=self._milieu)
        self._searchWidget.setMilieu(milieu=self._milieu)
        self._infoWidget.setMilieu(milieu=self._milieu)

    def rules(self) -> traveller.Rules:
        return traveller.Rules(self._rules)

    def setRules(self, rules: traveller.Rules) -> None:
        if rules == self._rules:
            return

        self._rules = traveller.Rules(rules)
        self._infoWidget.setRules(rules=self._rules)

    def mapStyle(self) -> travellermap.Style:
        return self._style

    def setMapStyle(self, style: travellermap.Style) -> None:
        if style is self._style:
            return

        self._style = style
        self._mapWidget.setMapStyle(style=self._style)
        self._legendWidget.setMapStyle(style=self._style)
        self._styleActionGroup.setCurrent(current=self._style)

        self.mapStyleChanged.emit(self._style)

    def mapOptions(self) -> typing.List[travellermap.Option]:
        return list(self._options)

    def setMapOptions(self, options: typing.Collection[travellermap.Option]) -> None:
        options = set(options)
        if options == self._options:
            return

        self._options = options
        self._mapWidget.setMapOptions(options=self._options)
        self._legendWidget.setMapOptions(options=self._options)
        self._galacticDirectionsAction.setChecked(
            travellermap.Option.GalacticDirections in self._options)
        self._sectorGridAction.setChecked(
            travellermap.Option.SectorGrid in self._options)
        if travellermap.Option.SelectedSectorNames in self._options:
            self._sectorNamesActionGroup.setSelection(travellermap.Option.SelectedSectorNames)
        elif travellermap.Option.SectorNames in self._options:
            self._sectorNamesActionGroup.setSelection(travellermap.Option.SectorNames)
        else:
            self._sectorNamesActionGroup.setSelection(None)
        self._bordersAction.setChecked(
            travellermap.Option.Borders in self._options)
        self._routesAction.setChecked(
            travellermap.Option.Routes in self._options)
        self._regionNamesAction.setChecked(
            travellermap.Option.RegionNames in self._options)
        self._importantWorldsAction.setChecked(
            travellermap.Option.ImportantWorlds in self._options)
        self._worldColoursAction.setChecked(
            travellermap.Option.WorldColours in self._options)
        self._filledBordersAction.setChecked(
            travellermap.Option.FilledBorders in self._options)
        self._dimUnofficialAction.setChecked(
            travellermap.Option.DimUnofficial in self._options)
        self._mainsOverlayAction.setChecked(
            travellermap.Option.MainsOverlay in self._options)
        self._importanceOverlayAction.setChecked(
            travellermap.Option.ImportanceOverlay in self._options)
        self._populationOverlayAction.setChecked(
            travellermap.Option.PopulationOverlay in self._options)
        self._capitalsOverlayAction.setChecked(
            travellermap.Option.CapitalsOverlay in self._options)
        self._minorRaceOverlayAction.setChecked(
            travellermap.Option.MinorRaceOverlay in self._options)
        self._droyneWorldOverlayAction.setChecked(
            travellermap.Option.DroyneWorldOverlay in self._options)
        self._ancientSitesOverlayAction.setChecked(
            travellermap.Option.AncientSitesOverlay in self._options)
        self._stellarOverlayAction.setChecked(
            travellermap.Option.StellarOverlay in self._options)
        self._empressWaveOverlayAction.setChecked(
            travellermap.Option.EmpressWaveOverlay in self._options)
        self._qrekrshaZoneOverlayAction.setChecked(
            travellermap.Option.QrekrshaZoneOverlay in self._options)
        self._antaresSupernovaOverlayAction.setChecked(
            travellermap.Option.AntaresSupernovaOverlay in self._options)

        self.mapOptionsChanged.emit(self._options)

    def rendering(self) -> app.MapRendering:
        return self._rendering

    def setRendering(self, rendering: app.MapRendering) -> None:
        if rendering is self._rendering:
            return False

        self._rendering = rendering
        if isinstance(self._mapWidget, gui.MapWidget):
            self._mapWidget.setRendering(
                rendering=self._rendering)
        if self._renderingActionGroup:
            self._renderingActionGroup.setCurrent(
                current=self._rendering)

        self.mapRenderingChanged.emit(self._rendering)

    def isAnimated(self) -> bool:
        return self._animated

    def setAnimated(self, animated: bool) -> None:
        if animated == self._animated:
            return

        self._animated = animated
        if isinstance(self._mapWidget, gui.MapWidget):
            self._mapWidget.setAnimated(animated=self._animated)
        if self._animatedAction:
            self._animatedAction.setChecked(self._animated)

        self.mapAnimationChanged.emit(self._animated)

    def setWorldTagging(
            self,
            tagging: typing.Optional[logic.WorldTagging],
            ) -> None:
        if tagging == self._worldTagging:
            return

        self._worldTagging = logic.WorldTagging(tagging) if tagging else None
        self._infoWidget.setWorldTagging(tagging=self._worldTagging)

    def setTaggingColours(
            self,
            colours: typing.Optional[app.TaggingColours]
            ) -> None:
        if colours == self._taggingColours:
            return

        self._taggingColours = app.TaggingColours(colours) if colours else None
        self._infoWidget.setTaggingColours(colours=self._taggingColours)

    def hexAt(
            self,
            pos: typing.Union[QtCore.QPoint, QtCore.QPointF]
            ) -> travellermap.HexPosition:
        pos = self._mapWidget.mapFrom(self, pos)
        return self._mapWidget.hexAt(pos=pos)

    def worldAt(
            self,
            pos: typing.Union[QtCore.QPoint, QtCore.QPointF]
            ) -> typing.Optional[traveller.World]:
        pos = self._mapWidget.mapFrom(self, pos)
        return self._mapWidget.worldAt(pos=pos)

    def centerOnHex(
            self,
            hex: travellermap.HexPosition,
            scale: typing.Optional[travellermap.Scale] = travellermap.Scale(linear=64), # None keeps current scale
            immediate: bool = False
            ) -> None:
        self._mapWidget.centerOnHex(
            hex=hex,
            scale=scale,
            immediate=immediate)

    def centerOnHexes(
            self,
            hexes: typing.Collection[travellermap.HexPosition],
            immediate: bool = False
            ) -> None:
        self._mapWidget.centerOnHexes(
            hexes=hexes,
            immediate=immediate)

    def hasJumpRoute(self) -> bool:
        return self._mapWidget.hasJumpRoute()

    def setJumpRoute(
            self,
            jumpRoute: typing.Optional[logic.JumpRoute],
            refuellingPlan: typing.Optional[typing.Iterable[logic.PitStop]] = None
            ) -> None:
        self._mapWidget.setJumpRoute(
            jumpRoute=jumpRoute,
            refuellingPlan=refuellingPlan)

    def clearJumpRoute(self) -> None:
        self._mapWidget.clearJumpRoute()

    def centerOnJumpRoute(
            self,
            immediate: bool = False
            ) -> None:
        self._mapWidget.centerOnJumpRoute(immediate=immediate)

    def highlightHex(
            self,
            hex: travellermap.HexPosition,
            radius: float = 0.5,
            colour: QtGui.QColor = QtGui.QColor('#7F8080FF')
            ) -> None:
        self._mapWidget.highlightHex(
            hex=hex,
            radius=radius,
            colour=colour)

    def highlightHexes(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            radius: float = 0.5,
            colour: QtGui.QColor = QtGui.QColor('#7F8080FF')
            ) -> None:
        self._mapWidget.highlightHexes(
            hexes=hexes,
            radius=radius,
            colour=colour)

    def clearHexHighlight(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        self._mapWidget.clearHexHighlight(hex=hex)

    def clearHexHighlights(self) -> None:
        self._mapWidget.clearHexHighlights()

    # Create an overlay with a primitive at each hex
    def createHexOverlay(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            primitive: gui.MapPrimitiveType,
            fillColour: typing.Optional[QtGui.QColor] = None,
            fillMap: typing.Optional[typing.Mapping[
                travellermap.HexPosition,
                QtGui.QColor
            ]] = None,
            radius: float = 0.5 # Only used for circle primitive
            ) -> str:
        return self._mapWidget.createHexOverlay(
            hexes=hexes,
            primitive=primitive,
            fillColour=fillColour,
            fillMap=fillMap,
            radius=radius)

    def createHexBordersOverlay(
            self,
            hexes: typing.Iterable[travellermap.HexPosition],
            lineColour: typing.Optional[QtGui.QColor] = None,
            lineWidth: typing.Optional[int] = None, # In pixels
            fillColour: typing.Optional[QtGui.QColor] = None,
            includeInterior: bool = True
            ) -> str:
        return self._mapWidget.createHexBordersOverlay(
            hexes=hexes,
            lineColour=lineColour,
            lineWidth=lineWidth,
            fillColour=fillColour,
            includeInterior=includeInterior)

    def createRadiusOverlay(
            self,
            center: travellermap.HexPosition,
            radius: int,
            lineColour: typing.Optional[QtGui.QColor] = None,
            lineWidth: typing.Optional[int] = None, # In pixels
            fillColour: typing.Optional[QtGui.QColor] = None,
            ) -> str:
        radiusHexes = list(center.yieldRadiusHexes(
            radius=radius,
            includeInterior=False))
        return self._mapWidget.createHexBordersOverlay(
            hexes=radiusHexes,
            fillColour=fillColour,
            lineColour=lineColour,
            lineWidth=lineWidth,
            includeInterior=False)

    def removeOverlay(
            self,
            handle: str
            ) -> None:
        self._mapWidget.removeOverlay(handle=handle)

    def setToolTipCallback(
            self,
            callback: typing.Optional[typing.Callable[[typing.Optional[travellermap.HexPosition]], typing.Optional[str]]],
            ) -> None:
        self._mapWidget.setToolTipCallback(callback=callback)

    def createPixmap(self) -> QtGui.QPixmap:
        return self._mapWidget.createPixmap()

    def hasSelection(self) -> bool:
        return len(self._selectedHexes) > 0

    def selectedHexes(self) -> typing.Iterable[travellermap.HexPosition]:
        return list(self._selectedHexes.keys())

    def selectHex(
            self,
            hex: travellermap.HexPosition,
            setInfoHex: bool = True
            ) -> None:
        if self._selectionMode == MapWidgetEx.SelectionMode.NoSelect:
            return

        if hex in self._selectedHexes:
            if setInfoHex:
                self.setInfoHex(hex=hex)
            return

        world = traveller.WorldManager.instance().worldByPosition(
            milieu=self._milieu,
            hex=hex)
        if not world and not self._enableDeadSpaceSelection:
            return

        if self._selectionMode == MapWidgetEx.SelectionMode.SingleSelect and \
                self._selectedHexes:
            with gui.SignalBlocker(widget=self):
                self.clearSelectedHexes()

        with gui.SignalBlocker(widget=self._searchWidget):
            self._searchWidget.setCurrentHex(hex=hex)

        self._createSelectionHexOverlay(hex=hex)
        self._updateSelectionOutline()

        if setInfoHex:
            self.setInfoHex(hex=hex)

        self.selectionChanged.emit()

    def selectHexes(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        if self._selectionMode == MapWidgetEx.SelectionMode.NoSelect:
            return

        if not self._enableDeadSpaceSelection:
            filtered = []
            for hex in hexes:
                world = traveller.WorldManager.instance().worldByPosition(
                    milieu=self._milieu,
                    hex=hex)
                if world:
                    filtered.append(hex)
            hexes = filtered

        if not hexes:
            return

        if self._selectionMode == MapWidgetEx.SelectionMode.SingleSelect:
            # In single select mode just select the first item
            self.selectHex(
                hex=hexes[0],
                setInfoHex=False)
            return

        with gui.SignalBlocker(widget=self._searchWidget):
            self._searchWidget.setCurrentHex(hex=hexes[0])

        selectionChanged = False
        for hex in hexes:
            if hex not in self._selectedHexes:
                self._createSelectionHexOverlay(hex=hex)
                selectionChanged = True

        if selectionChanged:
            self._updateSelectionOutline()
            self.selectionChanged.emit()

    def deselectHex(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        if not self._removeSelectionHexOverlay(hex=hex):
            return # Hex wasn't selected
        self._updateSelectionOutline()

        if self._selectionMode != MapWidgetEx.SelectionMode.NoSelect:
            self.selectionChanged.emit()

    def clearSelectedHexes(self) -> None:
        if not self._selectedHexes:
            return # Nothing to do

        for overlayHandle in self._selectedHexes.values():
            self.removeOverlay(handle=overlayHandle)
        self._selectedHexes.clear()
        self._updateSelectionOutline()

        self.selectionChanged.emit()

    def selectionMode(self) -> 'MapWidgetEx.SelectionMode':
        return self._selectionMode

    def setSelectionMode(
            self,
            mode: 'MapWidgetEx.SelectionMode'
            ) -> None:
        self._selectionMode = mode

        if self._selectionMode == MapWidgetEx.SelectionMode.NoSelect:
            if self._selectedHexes:
                for overlayHandle in self._selectedHexes.values():
                    self.removeOverlay(handle=overlayHandle)
                self._selectedHexes.clear()
                self._updateSelectionOutline()
                # NOTE: The selection changed signal is intentionally not generated
                # as we're now in no select mode
        elif self._selectionMode == MapWidgetEx.SelectionMode.SingleSelect:
            # When single selection is enabled make sure there's one world at most selected
            selectionChanged = False
            while len(self._selectedHexes) > 1:
                hex = next(iter(self._selectedHexes))
                overlayHandle = self._selectedHexes[hex]
                self.removeOverlay(handle=overlayHandle)
                del self._selectedHexes[hex]
                selectionChanged = True
            if selectionChanged:
                self._updateSelectionOutline()
                self.selectionChanged.emit()

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        self._enableDeadSpaceSelection = enable
        self._searchWidget.enableDeadSpaceSelection(enable=enable)

        if not self._enableDeadSpaceSelection:
            # Deselect any dead space
            selectionChanged = False
            for hex in list(self._selectedHexes.keys()):
                world = traveller.WorldManager.instance().worldByPosition(
                    milieu=self._milieu,
                    hex=hex)
                if not world:
                    self._removeSelectionHexOverlay(hex=hex)
                    selectionChanged = True

            if selectionChanged:
                self._updateSelectionOutline()
                self.selectionChanged.emit()

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._enableDeadSpaceSelection

    def setInfoHex(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._infoWidget.setHex(hex if self._infoButton.isChecked() else None)
        # Update the stored info hex even if the info widget isn't being shown. This is done so
        # the info for this hex would be shown if the user enabled the info widget
        self._infoHex = hex

    def setInfoEnabled(self, enabled: bool) -> None:
        self._infoButton.setChecked(enabled)

    def addConfigSection(
            self,
            section: str,
            content: QtWidgets.QLayout
            ) -> None:
        self._configWidget.addSection(section=section, content=content)

    def promptExportImage(self) -> None:
        try:
            snapshot = self._mapWidget.createPixmap()
        except Exception as ex:
            message = 'An exception occurred while generating image to export'
            logging.error(msg=message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        # https://doc.qt.io/qt-5/qpixmap.html#reading-and-writing-image-files
        _SupportedFormats = {
            'Bitmap (*.bmp)': 'bmp',
            'JPEG (*.jpg *.jpeg)': 'jpg',
            'PNG (*.png)': 'png',
            'Portable Pixmap (*.ppm)': 'ppm',
            'X11 Bitmap (*.xbm)': 'xbm',
            'X11 Pixmap (*.xpm)': 'xpm'}

        path, filter = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Export Snapshot',
            filter=';;'.join(_SupportedFormats.keys()))
        if not path:
            return # User cancelled

        format = _SupportedFormats.get(filter)
        if format is None:
            message = f'Unable to export image with unknown format "{filter}"'
            logging.error(msg=message)
            gui.MessageBoxEx.critical(message)
            return

        try:
            if not snapshot.save(path, format):
                gui.MessageBoxEx.critical(f'Failed to export image to "{path}"')
        except Exception as ex:
            message = f'An exception occurred while exporting the image to "{path}"'
            logging.error(msg=message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def menuAction(
            self,
            id: enum.Enum
            ) -> typing.Optional[QtWidgets.QAction]:
        return self._menuActions.get(id)

    def setMenuAction(
            self,
            id: enum.Enum,
            action: typing.Optional[QtWidgets.QAction]
            ) -> None:
        self._menuActions[id] = action

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        action = self.menuAction(MapWidgetEx.MenuAction.ExportImage)
        if action:
            menu.addAction(action)

    def displayContextMenu(self, pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        self.fillContextMenu(menu=menu)

        if menu.isEmpty():
            return

        globalPos = self.mapToGlobal(pos)
        menu.exec(globalPos)

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if object == self._searchWidget or object == self._searchButton:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Return:
                    self._searchButtonClicked()

        return super().eventFilter(object, event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.modifiers() == QtCore.Qt.KeyboardModifier.NoModifier:
            if event.key() == QtCore.Qt.Key.Key_Escape:
                if self._fullScreenButton.isChecked():
                    self._fullScreenButton.setChecked(False)
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key.Key_C:
                hex = self._searchWidget.currentHex()
                if hex:
                    self.centerOnHex(hex=hex)
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key.Key_H: # Copied from Traveller Map
                self._gotoHome()
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key.Key_F: # Copied from Traveller Map
                self._fullScreenButton.toggle()
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key.Key_M: # Copied from Traveller Map
                self._legendButton.toggle()
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key.Key_Slash: # Copied from Traveller Map
                self._searchWidget.setFocus()
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key.Key_F5:
                self._mapWidget.fullRedraw()
                event.accept()
                return
        elif event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            if event.key() == QtCore.Qt.Key.Key_F:
                self._searchWidget.setFocus()
                event.accept()
                return
            elif event.key() == QtCore.Qt.Key.Key_W:
                self._infoButton.toggle()
                return

        super().keyPressEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._mapWidget.resize(event.size())
        self._configureOverlayControls()

    def contextMenuEvent(self, event: typing.Optional[QtGui.QContextMenuEvent]) -> None:
        if self.contextMenuPolicy() != QtCore.Qt.ContextMenuPolicy.DefaultContextMenu:
            super().contextMenuEvent(event)
            return

        if event:
            self.displayContextMenu(pos=event.pos())
            event.accept()
        #super().contextMenuEvent(event)

    def minimumSizeHint(self) -> QtCore.QSize:
        searchWidgetSize = self._searchWidget.size()
        searchButtonSize = self._searchButton.size()
        infoButtonSize = self._infoButton.size()
        fullScreenButtonSize = self._configButton.size()
        homeButtonSize = self._homeButton.size()
        keyButtonSize = self._legendButton.size()
        configButtonSize = self._configButton.size()
        infoWidgetMinSize = self._infoWidget.minimumSize()
        legendWidgetMinSize = self._legendWidget.minimumSize()
        configWidgetMinSize = self._configWidget.minimumSize()

        toolbarWidth = searchWidgetSize.width() + \
            MapWidgetEx._ControlWidgetSpacing + \
            searchButtonSize.width() + \
            MapWidgetEx._ControlWidgetSpacing + \
            infoButtonSize.width() + \
            MapWidgetEx._ControlWidgetSpacing + \
            fullScreenButtonSize.width() + \
            MapWidgetEx._ControlWidgetSpacing + \
            homeButtonSize.width() + \
            MapWidgetEx._ControlWidgetSpacing + \
            keyButtonSize.width() + \
            MapWidgetEx._ControlWidgetSpacing + \
            configButtonSize.width()
        toolbarHeight = max(
            searchWidgetSize.height(),
            searchButtonSize.height(),
            infoButtonSize.height(),
            fullScreenButtonSize.height(),
            homeButtonSize.height(),
            keyButtonSize.height(),
            configButtonSize.height())

        paneWidth = infoWidgetMinSize.width() + \
            MapWidgetEx._ControlWidgetSpacing + \
            max(legendWidgetMinSize.width(), configWidgetMinSize.width())
        paneHeight = max(
            infoWidgetMinSize.height(),
            legendWidgetMinSize.height(),
            configWidgetMinSize.height())

        minWidth = max(toolbarWidth, paneWidth) + \
            (MapWidgetEx._ControlWidgetInset * 2)
        minHeight = toolbarHeight + \
            MapWidgetEx._ControlWidgetSpacing + \
            paneHeight + \
            (MapWidgetEx._ControlWidgetInset * 2)

        return QtCore.QSize(minWidth, minHeight)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        childState = self._mapWidget.saveState()
        stream.writeUInt32(childState.count() if childState else 0)
        if childState:
            stream.writeRawData(childState.data())

        stream.writeBool(self._infoButton.isChecked())
        stream.writeUInt32(self._infoWidget.width())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != self._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug('Failed to restore MapWidgetEx state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count:
            self._mapWidget.restoreState(
                QtCore.QByteArray(stream.readRawData(count)))

        self._infoButton.setChecked(stream.readBool())
        self._infoWidget.setFixedWidth(stream.readUInt32())

        return True

    def selectionFillColour(self) -> QtGui.QColor:
        return MapWidgetEx._SelectionFillDarkStyleColour \
            if travellermap.isDarkStyle(style=self._style) else \
            MapWidgetEx._SelectionFillLightStyleColour

    def selectionOutlineColour(self) -> QtGui.QColor:
        return MapWidgetEx._SelectionOutlineDarkStyleColour \
            if travellermap.isDarkStyle(style=self._style) else \
            MapWidgetEx._SelectionOutlineLightStyleColour

    def selectionOutlineWidth(self) -> int:
        return MapWidgetEx._SelectionOutlineWidth

    def _handleLeftClick(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        shouldSelect = False
        if self._enableDeadSpaceSelection:
            shouldSelect = hex != None
        elif hex:
            shouldSelect = traveller.WorldManager.instance().worldByPosition(
                milieu=self._milieu,
                hex=hex) != None

        if shouldSelect:
            # Show info for the world the user clicked on or hide any current world info if there
            # is no world in the hex the user clicked
            if self._infoButton.isChecked():
                self.setInfoHex(hex=hex)

            # Update selection if enabled
            if self._selectionMode != MapWidgetEx.SelectionMode.NoSelect:
                if self._selectionMode == MapWidgetEx.SelectionMode.MultiSelect and \
                        gui.isShiftKeyDown():
                    worlds = traveller.WorldManager.instance().worldsInFlood(
                        milieu=self._milieu,
                        hex=hex)
                    self.selectHexes(hexes=[world.hex() for world in worlds])
                elif hex not in self._selectedHexes:
                    self.selectHex(
                        hex=hex,
                        setInfoHex=False) # Updating info world has already been handled
                else:
                    # Clicking a selected worlds deselects it
                    self.deselectHex(hex=hex)

        self.leftClicked.emit(hex)

    def _handleRightClick(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self.rightClicked.emit(hex)

    def _gotoHome(self) -> None:
        self.centerOnHex(
            hex=travellermap.HexPosition(
                sectorX=travellermap.ReferenceSectorX,
                sectorY=travellermap.ReferenceSectorY,
                offsetX=travellermap.ReferenceHexX,
                offsetY=travellermap.ReferenceHexY),
            scale=travellermap.Scale(
                linear=MapWidgetEx._HomeLinearScale))

    def _mapStyleChanged(self, style: travellermap.Style) -> None:
        self.setMapStyle(style=style)

    def _mapOptionChanged(self, option: travellermap.Option, enabled: bool) -> None:
        if (enabled and option in self._options) or (not enabled and option not in self._options):
            return

        newOptions = set(self._options)
        if enabled:
            newOptions.add(option)
        else:
            newOptions.remove(option)

        self.setMapOptions(options=newOptions)

    def _renderingChanged(self, rendering: app.MapRendering) -> None:
        self.setRendering(rendering=rendering)

    def _animatedChanged(self, animate: bool) -> None:
        self.setAnimated(animated=animate)

    def _configureOverlayControls(self) -> None:
        self._resizeOverlayWidgets()
        self._positionOverlayWidgets()

    def _resizeOverlayWidgets(self) -> None:
        usedHeight = self._searchWidget.height() + \
            MapWidgetEx._ControlWidgetSpacing + \
            (MapWidgetEx._ControlWidgetInset * 2)
        remainingHeight = self.height() - usedHeight
        remainingHeight = max(remainingHeight, 0)

        usedWidth = MapWidgetEx._ControlWidgetInset * 2
        if self._legendButton.isChecked() or self._configButton.isChecked():
            if self._legendButton.isChecked():
                usedWidth += self._legendWidget.width()
            else:
                usedWidth += self._configWidget.width()

            usedWidth += MapWidgetEx._ControlWidgetSpacing
        remainingWidth = self.width() - usedWidth
        remainingWidth = max(remainingWidth, 0)

        self._infoWidget.setMaximumHeight(remainingHeight)
        self._infoWidget.setMaximumWidth(remainingWidth)
        self._infoWidget.adjustSize()

        self._legendWidget.setMaximumHeight(remainingHeight)
        self._legendWidget.adjustSize()

        self._configWidget.setMaximumHeight(remainingHeight)
        self._configWidget.adjustSize()

    def _positionOverlayWidgets(self) -> None:
        self._searchWidget.move(
            MapWidgetEx._ControlWidgetInset,
            MapWidgetEx._ControlWidgetInset)
        self._mapWidget.stackUnder(self._searchWidget)

        self._searchButton.move(
            MapWidgetEx._ControlWidgetInset + \
            self._searchWidget.width(),
            MapWidgetEx._ControlWidgetInset)

        self._infoButton.move(
            MapWidgetEx._ControlWidgetInset + \
            self._searchWidget.width() + \
            self._searchButton.width() + \
            MapWidgetEx._ControlWidgetSpacing,
            MapWidgetEx._ControlWidgetInset)

        self._fullScreenButton.move(
            self.width() - \
            (self._fullScreenButton.width() + \
             MapWidgetEx._ControlWidgetSpacing + \
             self._homeButton.width() + \
             MapWidgetEx._ControlWidgetSpacing + \
             self._legendButton.width() + \
             MapWidgetEx._ControlWidgetSpacing + \
             self._configButton.width() + \
             MapWidgetEx._ControlWidgetInset),
            MapWidgetEx._ControlWidgetInset)

        self._homeButton.move(
            self.width() - \
            (self._homeButton.width() + \
             MapWidgetEx._ControlWidgetSpacing + \
             self._legendButton.width() + \
             MapWidgetEx._ControlWidgetSpacing + \
             self._configButton.width() + \
             MapWidgetEx._ControlWidgetInset),
            MapWidgetEx._ControlWidgetInset)

        self._legendButton.move(
            self.width() - \
            (self._legendButton.width() + \
             MapWidgetEx._ControlWidgetSpacing + \
             self._configButton.width() + \
             MapWidgetEx._ControlWidgetInset),
            MapWidgetEx._ControlWidgetInset)

        self._configButton.move(
            self.width() - \
            (self._configButton.width() +
             MapWidgetEx._ControlWidgetInset),
            MapWidgetEx._ControlWidgetInset)

        vertOffset = MapWidgetEx._ControlWidgetInset + \
            self._searchWidget.height() + \
            MapWidgetEx._ControlWidgetSpacing

        self._infoWidget.move(
            MapWidgetEx._ControlWidgetInset,
            vertOffset)

        legendSize = self._legendWidget.size()
        self._legendWidget.move(
            self.width() - (MapWidgetEx._ControlWidgetInset +
                            legendSize.width()),
            vertOffset)

        configSize = self._configWidget.size()
        self._configWidget.move(
            self.width() - (MapWidgetEx._ControlWidgetInset +
                            configSize.width()),
            vertOffset)

    def _createSelectionHexOverlay(
            self,
            hex: travellermap.HexPosition,
            ) -> None:
        self._selectedHexes[hex] = self.createHexOverlay(
            hexes=[hex],
            primitive=gui.MapPrimitiveType.Hex,
            fillColour=self.selectionFillColour())

    def _removeSelectionHexOverlay(
            self,
            hex: travellermap.HexPosition
            ) -> bool:
        overlayHandle = self._selectedHexes.get(hex)
        if not overlayHandle:
            return False

        self.removeOverlay(handle=overlayHandle)
        del self._selectedHexes[hex]
        return True

    def _updateSelectionOutline(self) -> None:
        if self._selectionOutlineHandle:
            self.removeOverlay(handle=self._selectionOutlineHandle)
            self._selectionOutlineHandle = None
        if self._selectedHexes:
            self._selectionOutlineHandle = self.createHexBordersOverlay(
                hexes=self._selectedHexes.keys(),
                lineColour=self.selectionOutlineColour(),
                lineWidth=self.selectionOutlineWidth())

    def _recreateSelectionOverlays(self):
        for overlayHandle in self._selectedHexes.values():
            self.removeOverlay(handle=overlayHandle)
        for hex in self._selectedHexes.keys():
            self._createSelectionHexOverlay(hex=hex)
        self._updateSelectionOutline()

    def _searchHexTextEdited(self) -> None:
        # Clear the current info hex (and hide the widget) as soon as the user starts editing the
        # search hex text. This is done to prevent the selection drop down from being hard to read
        # due to it overlapping the info widget. This behaviour is consistent with Traveller Map
        self.setInfoHex(hex=None)

    def _searchHexSelected(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if self._infoButton.isChecked():
            self.setInfoHex(hex=hex)

        if hex:
            self.centerOnHex(hex=hex)

            # Add the selected world to the recently used list
            app.HexHistory.instance().addHex(hex=hex)

            if self._selectionMode == MapWidgetEx.SelectionMode.SingleSelect:
                self.selectHex(
                    hex=hex,
                    setInfoHex=False) # Updating info world has already been handled

        self._searchButton.setEnabled(hex != None)

    def _searchButtonClicked(self) -> None:
        self._searchHexSelected(hex=self._searchWidget.currentHex())

    def _showInfoToggled(self) -> None:
        # Update info widget directly rather than calling setInfoWorld. This is done as we don't
        # want to clear the info world. If the user was to re-enable the info widget straight away
        # they would expect to see the same world as it was previously showing
        self._infoWidget.setHex(self._infoHex if self._infoButton.isChecked() else None)

    def _showLegendToggled(self) -> None:
        if self._legendButton.isChecked():
            self._configButton.setChecked(False)
            self._legendWidget.show()
        else:
            self._legendWidget.hide()
        self._configureOverlayControls()

    def _showConfigToggled(self) -> None:
        if self._configButton.isChecked():
            self._legendButton.setChecked(False)
            self._configWidget.show()
        else:
            self._configWidget.hide()
        self._configureOverlayControls()

    def _fullScreenToggled(self) -> None:
        if self._fullScreenButton.isChecked():
            # Fullscreen and borderless
            self.setWindowFlags(
                QtCore.Qt.WindowType.Window | QtCore.Qt.WindowType.FramelessWindowHint)
            self.showFullScreen()
        else:
            self.showNormal()
            self.setWindowFlags(QtCore.Qt.WindowType.Widget)
            self.show()
            self.setFocus()
