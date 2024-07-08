import app
import base64
import enum
import functools
import gui
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

def _createOnOffIcon(source: QtGui.QIcon) -> QtGui.QIcon:
    icon = QtGui.QIcon()
    for availableSize in source.availableSizes():
        icon.addPixmap(
            source.pixmap(availableSize, QtGui.QIcon.Mode.Normal),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.On)
        icon.addPixmap(
            source.pixmap(availableSize, QtGui.QIcon.Mode.Disabled),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.Off)
    return icon

# Force a min font size of 10pt. That was the default before I added font
# scaling and the change to a user not using scaling is quite jarring
def _setMinFontSize(widget: QtWidgets.QWidget):
    font = widget.font()
    if font.pointSize() < 10:
        font.setPointSize(10)
        widget.setFont(font)

class _OverlayLabel(QtWidgets.QLabel):
    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ..., flags: typing.Union[QtCore.Qt.WindowFlags, QtCore.Qt.WindowType] = ...) -> None: ...
    @typing.overload
    def __init__(self, text: str, parent: typing.Optional[QtWidgets.QWidget] = ..., flags: typing.Union[QtCore.Qt.WindowFlags, QtCore.Qt.WindowType] = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setStyleSheet(f'background-color:#00000000')
        _setMinFontSize(widget=self)

class _MapStyleToggleAction(QtWidgets.QAction):
    def __init__(
            self,
            style: travellermap.Style,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(style.value, parent)

        self._style = style

        self.setCheckable(True)
        self.setChecked(app.Config.instance().mapStyle() == style)

        # It's important that this is connected to the trigger signal before any instances
        # of TravellerMapWidget. This call needs to made first as it will write the updated
        # setting to the config so the instances of TravellerMapWidget can read it back when
        # updating their URL.
        self.triggered.connect(self._optionToggled)

    def _optionToggled(self) -> None:
        if self.isChecked():
            app.Config.instance().setMapStyle(style=self._style)

class _MapOptionToggleAction(QtWidgets.QAction):
    def __init__(
            self,
            option: travellermap.Option,
            parent: typing.Optional[QtCore.QObject] = None
            ) -> None:
        super().__init__(option.value, parent)

        self._option = option

        self.setCheckable(True)
        self.setChecked(app.Config.instance().mapOption(option=option))

        # It's important that this is connected to the trigger signal before any instances
        # of TravellerMapWidget. This call needs to made first as it will write the updated
        # setting to the config so the instances of TravellerMapWidget can read it back when
        # updating their URL.
        self.triggered.connect(self._optionToggled)

    def _optionToggled(self) -> None:
        app.Config.instance().setMapOption(
            option=self._option,
            enabled=self.isChecked())

class _SearchComboBox(gui.WorldSearchComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

class _IconButton(QtWidgets.QPushButton):
    def __init__(
            self,
            icon: QtGui.QIcon,
            size: QtCore.QSize,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self.setIcon(icon)
        self.setFixedSize(size)
        self.setIconSize(QtCore.QSize(size.width() - 6, size.height() - 6))

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
            expandWidth = verticalScrollbar.sizeHint().width()

        horizontalScrollbar = self.horizontalScrollBar()
        if horizontalScrollbar.isVisible():
            expandHeight = horizontalScrollbar.sizeHint().height()

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

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._resizeAnchor = None
        self._resizeBaseWidth = None
        self._resizeMinWidth = None
        self._resizeMaxWidth = None

        self._world = None

        self._label = _OverlayLabel()
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

    def setWorld(
            self,
            world: typing.Optional[traveller.World]
            ) -> None:
        self._world = world

        self._updateContent(self._label.width())

        if self._world:
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

        if self._world:
            text = gui.createWorldToolTip(
                world=self._world,
                # Don't display the thumbnail as the the user is already looking at the map so no point
                noThumbnail=True,
                width=width - _InfoWidget._ContentRightMargin)
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
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._label = _OverlayLabel()
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

    def sizeHint(self) -> QtCore.QSize:
        return self._scroller.sizeHint()

    # This is based on the legend definition in index.html & index.css. Along
    # with some details from Sectorsheet.cs. It's been modified heavily to
    # work around the fact QLabel only supports a limited html subset.
    def syncContent(self):
        style = app.Config.instance().mapStyle()

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

        worldGlyphSize = int(12 * app.Config.instance().interfaceScale())

        if style is travellermap.Style.Print:
            textStyle = 'color: black;'
            backgroundStyle = 'background-color: #FFFFFF;'
            noWaterFillColour = '#FFFFFF'
            noWaterOutlineColour = '#6F6F6F'
        elif style is travellermap.Style.Draft:
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
        elif style is travellermap.Style.Atlas:
            textStyle = 'color: black;'
            backgroundStyle = 'background-color: #FFFFFF;'
            highlightColour = '#808080'
            hasWaterFillColour = '#000000'
            noWaterFillColour = '#FFFFFF'
            noWaterOutlineColour = '#000000'
            amberZoneColour = '#C0C0C0'
            redZoneColour = '#000000'
        elif style is travellermap.Style.Mongoose:
            textStyle = 'color: #000000;'
            backgroundStyle = 'background-color: #E6E7E8;'
            hasWaterFillColour = '#0000CD'
            noWaterFillColour = '#BDB76B'
            hasWaterOutlineColour = noWaterOutlineColour = '#A9A9A9'
            amberZoneColour = '#FBB040'
            lowPopulationStyle = 'text-transform: uppercase;'
            highPopulationStyle = 'text-transform: uppercase; font-weight: bold;'
            capitalStyle = 'text-transform: uppercase;'
        elif style is travellermap.Style.Fasa:
            textStyle = 'color: #5C4033;'
            backgroundStyle = 'background-color: #FFFFFF;'
            amberZoneColour = '#5C4033'
            redZoneColour = '#805C4033' # Note that this is alpha blended
        elif style is travellermap.Style.Terminal:
            textStyle = 'color: #00FFFF; font-family: "Courier New", "Courier", monospace;'
            hasWaterFillColour = '#000000'
            hasWaterOutlineColour = '#00FFFF'
            noWaterFillColour = '#00FFFF'

        characteristicItems = []
        if app.Config.instance().mapOption(travellermap.Option.WorldColours) and \
                style is not travellermap.Style.Atlas:
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
        if style is travellermap.Style.Mongoose:
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

        imageData = self._loadLegendImage(imageFile=f'Legend_1003_{style.name.lower()}.png')
        if imageData:
            legendContent += f'<center><img src=data:image/png;base64,{imageData}></center>'

        legendContent += '<br>'

        imageData = self._loadLegendImage(imageFile=f'Legend_1006_{style.name.lower()}.png')
        if imageData:
            legendContent += f'<center><img src=data:image/png;base64,{imageData}></center>'

        if style is not travellermap.Style.Candy and \
                style is not travellermap.Style.Fasa:
            legendContent += self._createLegendSection(
                title='World Characteristics',
                items=characteristicItems)
            legendContent += self._createLegendSection(
                title='Bases',
                items=baseItems)
        legendContent += self._createLegendSection(
            title='Travel Zones',
            items=zoneItems)

        if style is not travellermap.Style.Fasa:
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

class _MapOptionSelector(gui.ComboBoxEx):
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

class _MapOptionToggle(gui.ToggleButton):
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

    def addOptions(
            self,
            section: str,
            actions: typing.Union[QtWidgets.QActionGroup, typing.Iterable[QtWidgets.QAction]]
            ) -> None:
        if isinstance(actions, QtWidgets.QActionGroup):
            if actions.isExclusive():
                # Group is exclusive so add a combo box to allow one of the
                # actions to be selected
                selector = _MapOptionSelector(group=actions)
                self._optionsWidget.addSectionContent(
                    label=section,
                    content=selector)
                return

            # The group is not exclusive so add each action individually
            actions = actions.actions()

        layout = QtWidgets.QGridLayout()
        for action in actions:
            row = layout.rowCount()

            button = _MapOptionToggle(action=action)
            layout.addWidget(button, row, 0)

            label = _OverlayLabel(action.text())
            layout.addWidget(label, row, 1)
        self._optionsWidget.addSectionContent(
            label=section,
            content=layout)

        self._optionsWidget.adjustSize()
        self.adjustSize()

class TravellerMapWidget(gui.TravellerMapWidgetBase):
    class SelectionMode(enum.Enum):
        NoSelect = 0
        SingleSelect = 1
        MultiSelect = 2

    selectionChanged = QtCore.pyqtSignal()

    _StateVersion = 'TravellerMapWidget_v1'

    _ControlWidgetInset = 20
    _ControlWidgetSpacing = 5

    # Actions shared with all instances of this widget
    _sharedStyleGroup = None
    _sharedFeatureGroup = None
    _sharedAppearanceGroup = None
    _sharedOverlayGroup = None

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._initOptionActions()

        self._selectionMode = TravellerMapWidget.SelectionMode.NoSelect
        self._selectedWorlds: typing.List[traveller.World] = []

        self._infoWorld = None

        fontMetrics = QtGui.QFontMetrics(QtWidgets.QApplication.font())
        controlHeights = int(fontMetrics.lineSpacing() * 2)
        searchWidth = fontMetrics.width('_' * 40)
        buttonSize = QtCore.QSize(controlHeights, controlHeights)

        # For reasons I don't understand this needs to be done after load has been called on the map.
        # If it's not then the search control is drawn under the map widget. Using stackUnder doesn't
        # seem to work either.
        self._searchWidget = _SearchComboBox(self)
        self._searchWidget.setFixedSize(searchWidth, controlHeights)
        self._searchWidget.installEventFilter(self)
        self._searchWidget.editTextChanged.connect(self._searchWorldTextEdited)
        self._searchWidget.worldChanged.connect(self._searchWorldSelected)

        self._searchButton = _IconButton(
            icon=gui.loadIcon(id=gui.Icon.Search),
            size=buttonSize,
            parent=self)
        self._searchButton.installEventFilter(self)
        self._searchButton.clicked.connect(self._searchButtonClicked)

        self._infoButton = _IconButton(
            icon=_createOnOffIcon(source=gui.loadIcon(id=gui.Icon.Info)),
            size=buttonSize,
            parent=self)
        self._infoButton.setCheckable(True)
        self._infoButton.setChecked(True)
        self._infoButton.toggled.connect(self._showInfoToggled)

        self._infoWidget = _InfoWidget(self)
        self._infoWidget.setMinimumWidth(200)
        self._infoWidget.setFixedWidth(300)
        self._infoWidget.hide()

        self._reloadButton = _IconButton(
            icon=gui.loadIcon(id=gui.Icon.Reload),
            size=buttonSize,
            parent=self)
        self._reloadButton.clicked.connect(self.reload)

        self._legendButton = _IconButton(
            icon=_createOnOffIcon(source=gui.loadIcon(id=gui.Icon.Key)),
            size=buttonSize,
            parent=self)
        self._legendButton.setCheckable(True)
        self._legendButton.setChecked(False)
        self._legendButton.toggled.connect(self._showLegendToggled)

        self._legendWidget = _LegendWidget(self)
        self._legendWidget.hide()

        self._configButton = _IconButton(
            icon=_createOnOffIcon(source=gui.loadIcon(id=gui.Icon.Settings)),
            size=buttonSize,
            parent=self)
        self._configButton.setCheckable(True)
        self._configButton.setChecked(False)
        self._configButton.toggled.connect(self._showConfigToggled)

        self._configWidget = _ConfigWidget(self)
        self._configWidget.addOptions(
            section='Style',
            actions=self._sharedStyleGroup)
        self._configWidget.addOptions(
            section='Features',
            actions=self._sharedFeatureGroup)
        self._configWidget.addOptions(
            section='Appearance',
            actions=self._sharedAppearanceGroup)
        self._configWidget.addOptions(
            section='Overlays',
            actions=self._sharedOverlayGroup)
        self._configWidget.hide()

        self._configureOverlayControls()

    def __del__(self) -> None:
        if TravellerMapWidget._sharedStyleGroup:
            for action in TravellerMapWidget._sharedStyleGroup.actions():
                action.triggered.disconnect(self._displayOptionChanged)

        if TravellerMapWidget._sharedFeatureGroup:
            for action in TravellerMapWidget._sharedFeatureGroup.actions():
                action.triggered.disconnect(self._displayOptionChanged)

        if TravellerMapWidget._sharedAppearanceGroup:
            for action in TravellerMapWidget._sharedAppearanceGroup.actions():
                action.triggered.disconnect(self._displayOptionChanged)

        if TravellerMapWidget._sharedOverlayGroup:
            for action in TravellerMapWidget._sharedOverlayGroup.actions():
                action.triggered.disconnect(self._displayOptionChanged)

    def selectedWorlds(self) -> typing.Iterable[traveller.World]:
        return self._selectedWorlds

    def selectWorld(
            self,
            world: traveller.World,
            centerOnWorld: bool = True,
            setInfoWorld: bool = True
            ) -> None:
        if self._selectionMode == TravellerMapWidget.SelectionMode.NoSelect or \
                world in self._selectedWorlds:
            return

        if self._selectionMode == TravellerMapWidget.SelectionMode.SingleSelect and \
                self._selectedWorlds:
            with gui.SignalBlocker(widget=self):
                self.clearSelectedWorlds()

        self._selectedWorlds.append(world)

        with gui.SignalBlocker(widget=self._searchWidget):
            self._searchWidget.setSelectedWorld(world=world)

        self.highlightWorld(world=world)

        if centerOnWorld:
            self.centerOnWorld(world=world)

        if setInfoWorld:
            self.setInfoWorld(world=world)

        self.selectionChanged.emit()

    def deselectWorld(
            self,
            world: traveller.World
            ) -> None:
        if world not in self._selectedWorlds:
            return

        self.clearWorldHighlight(world=world)
        self._selectedWorlds.remove(world)

        if self._selectionMode != TravellerMapWidget.SelectionMode.NoSelect:
            self.selectionChanged.emit()

    def clearSelectedWorlds(self) -> None:
        if not self._selectedWorlds:
            return # Nothing to do

        for world in self._selectedWorlds:
            self.clearWorldHighlight(world=world)
        self._selectedWorlds.clear()

        self.selectionChanged.emit()

    def setSelectionMode(
            self,
            mode: 'TravellerMapWidget.SelectionMode'
            ) -> None:
        self._selectionMode = mode

        if self._selectionMode == TravellerMapWidget.SelectionMode.SingleSelect:
            if self._selectedWorlds:
                for index in range(len(self._selectedWorlds)):
                    self.clearWorldHighlight(world=self._selectedWorlds[index])
                self._selectedWorlds.clear()
                self.selectionChanged.emit()
        elif self._selectionMode == TravellerMapWidget.SelectionMode.SingleSelect:
            # When single selection is enabled make sure there's one world at most selected
            if len(self._selectedWorlds) > 1:
                for index in range(len(self._selectedWorlds) - 1):
                    self.clearWorldHighlight(world=self._selectedWorlds[index])
                self._selectedWorlds = [self._selectedWorlds[-1]]
                self.selectionChanged.emit()

    def setInfoWorld(
            self,
            world: typing.Optional[traveller.World]
            ) -> None:
        self._infoWidget.setWorld(world if self._infoButton.isChecked() else None)
        # Update the stored info world even if the world info isn't being shown. This is done so
        # the info for this world would be shown if the user enabled the info box
        self._infoWorld = world

    def setInfoEnabled(self, enabled: bool) -> None:
        self._infoButton.setChecked(enabled)

    def addConfigActions(
            self,
            section: str,
            actions: typing.Union[QtWidgets.QActionGroup, typing.Iterable[QtWidgets.QAction]]
            ) -> None:
        self._configWidget.addOptions(
            section=section,
            actions=actions)

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if object == self._searchWidget or object == self._searchButton:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Return:
                    self._searchButtonClicked()

        return super().eventFilter(object, event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier:
            if event.key() == QtCore.Qt.Key.Key_F:
                self._searchWidget.setFocus()
                return # Swallow event
            elif event.key() == QtCore.Qt.Key.Key_W:
                self._infoButton.toggle()
                return # Swallow event

        super().keyPressEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._configureOverlayControls()
        return super().resizeEvent(event)

    def minimumSizeHint(self) -> QtCore.QSize:
        searchWidgetSize = self._searchWidget.size()
        searchButtonSize = self._searchButton.size()
        infoButtonSize = self._infoButton.size()
        reloadButtonSize = self._reloadButton.size()
        keyButtonSize = self._legendButton.size()
        configButtonSize = self._configButton.size()
        infoWidgetMinSize = self._infoWidget.minimumSize()
        legendWidgetMinSize = self._legendWidget.minimumSize()
        configWidgetMinSize = self._configWidget.minimumSize()

        toolbarWidth = searchWidgetSize.width() + \
            TravellerMapWidget._ControlWidgetSpacing + \
            searchButtonSize.width() + \
            TravellerMapWidget._ControlWidgetSpacing + \
            infoButtonSize.width() + \
            TravellerMapWidget._ControlWidgetSpacing + \
            reloadButtonSize.width() + \
            TravellerMapWidget._ControlWidgetSpacing + \
            keyButtonSize.width() + \
            TravellerMapWidget._ControlWidgetSpacing + \
            configButtonSize.width()
        toolbarHeight = max(
            searchWidgetSize.height(),
            searchButtonSize.height(),
            infoButtonSize.height(),
            reloadButtonSize.height(),
            keyButtonSize.height(),
            configButtonSize.height())

        paneWidth = infoWidgetMinSize.width() + \
            TravellerMapWidget._ControlWidgetSpacing + \
            max(legendWidgetMinSize.width(), configWidgetMinSize.width())
        paneHeight = max(
            infoWidgetMinSize.height(),
            legendWidgetMinSize.height(),
            configWidgetMinSize.height())

        minWidth = max(toolbarWidth, paneWidth) + \
            (TravellerMapWidget._ControlWidgetInset * 2)
        minHeight = toolbarHeight + \
            TravellerMapWidget._ControlWidgetSpacing + \
            paneHeight + \
            (TravellerMapWidget._ControlWidgetInset * 2)

        return QtCore.QSize(minWidth, minHeight)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

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
            logging.debug('Failed to restore TravellerMapWidget state (Incorrect version)')
            return False

        self._infoButton.setChecked(stream.readBool())
        self._infoWidget.setFixedWidth(stream.readUInt32())

        return True

    def _initOptionActions(self) -> None:
        if not TravellerMapWidget._sharedStyleGroup:
            TravellerMapWidget._sharedStyleGroup = \
                QtWidgets.QActionGroup(None)
            TravellerMapWidget._sharedStyleGroup.setExclusive(True)

            for style in travellermap.Style:
                action = _MapStyleToggleAction(style=style)
                TravellerMapWidget._sharedStyleGroup.addAction(action)

        if not TravellerMapWidget._sharedFeatureGroup:
            TravellerMapWidget._sharedFeatureGroup = \
                QtWidgets.QActionGroup(None)
            TravellerMapWidget._sharedFeatureGroup.setExclusive(False)

            TravellerMapWidget._sharedFeatureGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.GalacticDirections))
            TravellerMapWidget._sharedFeatureGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.SectorGrid))
            TravellerMapWidget._sharedFeatureGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.SectorNames))
            TravellerMapWidget._sharedFeatureGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.Borders))
            TravellerMapWidget._sharedFeatureGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.Routes))
            TravellerMapWidget._sharedFeatureGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.RegionNames))
            TravellerMapWidget._sharedFeatureGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.ImportantWorlds))

        if not TravellerMapWidget._sharedAppearanceGroup:
            TravellerMapWidget._sharedAppearanceGroup = \
                QtWidgets.QActionGroup(None)
            TravellerMapWidget._sharedAppearanceGroup.setExclusive(False)

            TravellerMapWidget._sharedAppearanceGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.WorldColours))
            TravellerMapWidget._sharedAppearanceGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.FilledBorders))
            TravellerMapWidget._sharedAppearanceGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.DimUnofficial))

        if not TravellerMapWidget._sharedOverlayGroup:
            TravellerMapWidget._sharedOverlayGroup = \
                QtWidgets.QActionGroup(None)
            TravellerMapWidget._sharedOverlayGroup.setExclusive(False)

            TravellerMapWidget._sharedOverlayGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.ImportanceOverlay))
            TravellerMapWidget._sharedOverlayGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.PopulationOverlay))
            TravellerMapWidget._sharedOverlayGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.CapitalsOverlay))
            TravellerMapWidget._sharedOverlayGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.MinorRaceOverlay))
            TravellerMapWidget._sharedOverlayGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.DroyneWorldOverlay))
            TravellerMapWidget._sharedOverlayGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.AncientSitesOverlay))
            TravellerMapWidget._sharedOverlayGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.StellarOverlay))
            TravellerMapWidget._sharedOverlayGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.EmpressWaveOverlay))
            TravellerMapWidget._sharedOverlayGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.QrekrshaZoneOverlay))
            TravellerMapWidget._sharedOverlayGroup.addAction(
                _MapOptionToggleAction(
                    option=travellermap.Option.MainsOverlay))

        for action in TravellerMapWidget._sharedStyleGroup.actions():
            action.triggered.connect(self._displayOptionChanged)

        for action in TravellerMapWidget._sharedFeatureGroup.actions():
            action.triggered.connect(self._displayOptionChanged)

        for action in TravellerMapWidget._sharedAppearanceGroup.actions():
            action.triggered.connect(self._displayOptionChanged)

        for action in TravellerMapWidget._sharedOverlayGroup.actions():
            action.triggered.connect(self._displayOptionChanged)

    def _handleLeftClickEvent(
            self,
            sectorHex: typing.Optional[str]
            ) -> None:
        world = None
        if sectorHex:
            try:
                world = traveller.WorldManager.instance().world(sectorHex=sectorHex)
            except Exception:
                pass

        # Show info for the world the user clicked on or hide any current world info if there
        # is no world in the hex the user clicked
        if self._infoButton.isChecked():
            self.setInfoWorld(world=world)

        # Update selection if enabled
        if world and (self._selectionMode != TravellerMapWidget.SelectionMode.NoSelect):
            if world not in self._selectedWorlds:
                self.selectWorld(
                    world=world,
                    centerOnWorld=False, # Don't center as user is interacting with map
                    setInfoWorld=False) # Updating info world has already been handled
            else:
                # Clicking a selected worlds deselects it
                self.deselectWorld(world=world)

        # Call base implementation to generate left click event
        super()._handleLeftClickEvent(sectorHex=sectorHex)

    def _displayOptionChanged(self) -> None:
        self._legendWidget.syncContent()
        self._configureOverlayControls()
        self.reload()

    def _configureOverlayControls(self) -> None:
        self._resizeOverlayWidgets()
        self._positionOverlayWidgets()

    def _resizeOverlayWidgets(self) -> None:
        usedHeight = self._searchWidget.height() + \
            TravellerMapWidget._ControlWidgetSpacing + \
            (TravellerMapWidget._ControlWidgetInset * 2)
        remainingHeight = self.height() - usedHeight
        remainingHeight = max(remainingHeight, 0)

        usedWidth = TravellerMapWidget._ControlWidgetInset * 2
        if self._legendButton.isChecked() or self._configButton.isChecked():
            if self._legendButton.isChecked():
                usedWidth += self._legendWidget.width()
            else:
                usedWidth += self._configWidget.width()

            usedWidth += TravellerMapWidget._ControlWidgetSpacing
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
            TravellerMapWidget._ControlWidgetInset,
            TravellerMapWidget._ControlWidgetInset)

        self._searchButton.move(
            TravellerMapWidget._ControlWidgetInset + \
            self._searchWidget.width(),
            TravellerMapWidget._ControlWidgetInset)

        self._infoButton.move(
            TravellerMapWidget._ControlWidgetInset + \
            self._searchWidget.width() + \
            self._searchButton.width() + \
            TravellerMapWidget._ControlWidgetSpacing,
            TravellerMapWidget._ControlWidgetInset)

        self._reloadButton.move(
            self.width() - \
            (self._reloadButton.width() + \
             TravellerMapWidget._ControlWidgetSpacing + \
             self._legendButton.width() + \
             TravellerMapWidget._ControlWidgetSpacing + \
             self._configButton.width() + \
             TravellerMapWidget._ControlWidgetInset),
            TravellerMapWidget._ControlWidgetInset)

        self._legendButton.move(
            self.width() - \
            (self._legendButton.width() + \
             TravellerMapWidget._ControlWidgetSpacing + \
             self._configButton.width() + \
             TravellerMapWidget._ControlWidgetInset),
            TravellerMapWidget._ControlWidgetInset)

        self._configButton.move(
            self.width() - \
            (self._configButton.width() +
             TravellerMapWidget._ControlWidgetInset),
            TravellerMapWidget._ControlWidgetInset)

        vertOffset = TravellerMapWidget._ControlWidgetInset + \
            self._searchWidget.height() + \
            TravellerMapWidget._ControlWidgetSpacing

        self._infoWidget.move(
            TravellerMapWidget._ControlWidgetInset,
            vertOffset)

        legendSize = self._legendWidget.size()
        self._legendWidget.move(
            self.width() - (TravellerMapWidget._ControlWidgetInset +
                            legendSize.width()),
            vertOffset)

        configSize = self._configWidget.size()
        self._configWidget.move(
            self.width() - (TravellerMapWidget._ControlWidgetInset +
                            configSize.width()),
            vertOffset)

    def _searchWorldTextEdited(self) -> None:
        # Clear the current info world (and hide the widget) as soon as the user starts editing the
        # search world text. This is done to prevent the selection drop down from being hard to read
        # due to it overlapping the info widget. This behaviour is consistent with Traveller Map
        self.setInfoWorld(world=None)

    def _searchWorldSelected(
            self,
            world: typing.Optional[traveller.World]
            ) -> None:
        if self._infoButton.isChecked():
            self.setInfoWorld(world)

        if not world:
            return # Nothing more to do

        self.centerOnWorld(world=world)

        # Add the selected world to the recently used list
        app.RecentWorlds.instance().addWorld(world)

        if self._selectionMode == TravellerMapWidget.SelectionMode.SingleSelect:
            self.selectWorld(
                world=world,
                centerOnWorld=False, # Centring on the world has already been handled
                setInfoWorld=False) # Updating info world has already been handled

    def _searchButtonClicked(self) -> None:
        world = self._searchWidget.selectedWorld()
        if not world:
            worlds = traveller.WorldManager.instance().searchForWorlds(
                searchString=self._searchWidget.currentText())
            if worlds:
                worlds.sort(key=lambda x: x.name(includeSubsector=True))
                world = worlds[0]
        self._searchWorldSelected(world=world)

    def _showInfoToggled(self) -> None:
        # Update info widget directly rather than calling setInfoWorld. This is done as we don't
        # want to clear the info world. If the user was to re-enable the info widget straight away
        # they would expect to see the same world as it was previously showing
        self._infoWidget.setWorld(self._infoWorld if self._infoButton.isChecked() else None)

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
