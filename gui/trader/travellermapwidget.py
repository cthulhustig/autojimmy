import app
import enum
import gui
import logging
import traveller
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
            width: int,
            height: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self.setIcon(icon)
        self.setFixedSize(QtCore.QSize(width, height))
        self.setIconSize(QtCore.QSize(width - 6, height - 6))

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

        self._label = QtWidgets.QLabel()
        self._label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self._label.setWordWrap(True)
        self._label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._label.setMinimumHeight(0)
        self._label.setMaximumHeight(100000)
        self._label.setStyleSheet(f'background-color:#00000000')

        # Force a min font size of 10pt. That was the default before I added font
        # scaling and the change to a user not using scaling is quite jarring
        font = self._label.font()
        if font.pointSize() < 10:
            font.setPointSize(10)
            self._label.setFont(font)

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

class TravellerMapWidget(gui.TravellerMapWidgetBase):
    class SelectionMode(enum.Enum):
        NoSelect = 0
        SingleSelect = 1
        MultiSelect = 2

    selectionChanged = QtCore.pyqtSignal()

    _StateVersion = 'TravellerMapWidget_v1'

    _ControlWidgetInset = 20
    _ControlWidgetSpacing = 10

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._selectionMode = TravellerMapWidget.SelectionMode.NoSelect
        self._selectedWorlds: typing.List[traveller.World] = []

        self._infoWorld = None

        fontMetrics = QtGui.QFontMetrics(QtWidgets.QApplication.font())
        controlHeights = int(fontMetrics.lineSpacing() * 2)
        searchWidth = fontMetrics.width('_' * 40)

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
            width=controlHeights,
            height=controlHeights,
            parent=self)
        self._searchButton.installEventFilter(self)
        self._searchButton.clicked.connect(self._searchButtonClicked)

        searchIcon = gui.loadIcon(id=gui.Icon.Info)
        infoButtonIcon = QtGui.QIcon()
        infoButtonIcon.addPixmap(
            searchIcon.pixmap(QtCore.QSize(32, 32), QtGui.QIcon.Mode.Normal),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.On)
        infoButtonIcon.addPixmap(
            searchIcon.pixmap(QtCore.QSize(32, 32), QtGui.QIcon.Mode.Disabled),
            QtGui.QIcon.Mode.Normal,
            QtGui.QIcon.State.Off)
        self._infoButton = _IconButton(
            icon=infoButtonIcon,
            width=controlHeights,
            height=controlHeights,
            parent=self)
        self._infoButton.setCheckable(True)
        self._infoButton.setChecked(True)
        self._infoButton.toggled.connect(self._showInfoToggled)

        self._infoWidget = _InfoWidget(self)
        self._infoWidget.setMinimumWidth(200)
        self._infoWidget.setFixedWidth(300)
        self._infoWidget.hide()

        self._layoutOverlayControls()

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
        usedHeight = self._searchWidget.height() + \
            TravellerMapWidget._ControlWidgetSpacing
        usableHeight = event.size().height() - \
            (usedHeight + (TravellerMapWidget._ControlWidgetInset * 2))
        usableHeight = max(usableHeight, 0)

        usableWidth = event.size().width() - \
            (TravellerMapWidget._ControlWidgetInset * 2)

        self._infoWidget.setMaximumHeight(usableHeight)
        self._infoWidget.setMaximumWidth(usableWidth)
        self._infoWidget.adjustSize()
        return super().resizeEvent(event)

    def minimumSizeHint(self) -> QtCore.QSize:
        # Search widget and buttons have a fixed size so just use their current position and size to
        # calculate their min bounding rect
        fixedSearchWidgetRect = QtCore.QRect(
            self._searchWidget.pos(),
            self._searchWidget.size())
        fixedSearchButtonRect = QtCore.QRect(
            self._searchButton.pos(),
            self._searchButton.size())
        fixedInfoButtonRect = QtCore.QRect(
            self._infoButton.pos(),
            self._infoButton.size())

        # The info widget can be resized so use its current position and min sizes to calculate its
        # min bounding rect
        minInfoWidgetRect = QtCore.QRect(
            self._infoWidget.pos(),
            self._infoWidget.minimumSize())

        # Calculate the bounding rect for all the
        overlayRect = QtCore.QRect(fixedSearchWidgetRect)
        overlayRect = overlayRect.united(fixedSearchButtonRect)
        overlayRect = overlayRect.united(fixedInfoButtonRect)
        overlayRect = overlayRect.united(minInfoWidgetRect)

        # Expand bounding rect by the control widget inset
        overlayRect = overlayRect.marginsAdded(QtCore.QMargins(
            TravellerMapWidget._ControlWidgetInset,
            TravellerMapWidget._ControlWidgetInset,
            TravellerMapWidget._ControlWidgetInset,
            TravellerMapWidget._ControlWidgetInset))

        return overlayRect.size()

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

    def _layoutOverlayControls(self) -> None:
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

        self._infoWidget.move(
            TravellerMapWidget._ControlWidgetInset,
            TravellerMapWidget._ControlWidgetInset + \
            self._searchWidget.height() + \
            TravellerMapWidget._ControlWidgetSpacing)

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
