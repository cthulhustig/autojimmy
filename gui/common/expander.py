import app
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore

# Based on solution from this post
# https://stackoverflow.com/questions/32476006/how-to-make-an-expandable-collapsable-section-widget-in-qt

class ExpanderWidget(QtWidgets.QWidget):
    expansionChanged = QtCore.pyqtSignal([bool, bool])

    _LeftContentMargin = 20
    _RightContentMargin = 5
    _TopContentMargin = 5
    _BottomContentMargin = 5

    def __init__(
            self,
            label: str,
            animationDuration: int = 300,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._content = None
        self._animationDuration = animationDuration
        self._collapsedHeight = None
        self._contentHeight = None

        self._toggleButton = QtWidgets.QToolButton()
        self._toggleButton.setStyleSheet('QToolButton { border: none; }')
        self._toggleButton.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggleButton.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self._toggleButton.setText(label)
        self._toggleButton.setCheckable(True)
        self._toggleButton.setChecked(False)

        self._headerLine = QtWidgets.QFrame()
        self._headerLine.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self._headerLine.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self._headerLine.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum)

        self._contentArea = QtWidgets.QScrollArea()
        #self._contentArea.setStyleSheet('QScrollArea { background-color: #00000000; border: none; }')
        self._contentArea.setStyleSheet('QScrollArea { border: none; }')
        self._contentArea.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed)
        # start out collapsed
        self._contentArea.setMaximumHeight(0)
        self._contentArea.setMinimumHeight(0)
        # let the entire widget grow and shrink with its content
        self._toggleAnimation = QtCore.QParallelAnimationGroup()
        self._toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, b'minimumHeight'))
        self._toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, b'maximumHeight'))
        self._toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self._contentArea, b'maximumHeight'))
        self._toggleAnimation.finished.connect(self._animationFinished)

        # don't waste space
        self._mainLayout = QtWidgets.QGridLayout()
        self._mainLayout.setSpacing(0)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)
        row = 0
        self._mainLayout.addWidget(self._toggleButton, row, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignLeft)
        self._mainLayout.addWidget(self._headerLine, row, 2, 1, 1)
        row += 1
        self._mainLayout.addWidget(self._contentArea, row, 0, 1, 3)
        self.setLayout(self._mainLayout)

        # Take note of collapsed height after setting up basic layout without widget to be expanded
        self._collapsedHeight = self._toggleButton.sizeHint().height()

        self._contentArea.installEventFilter(self)
        self._toggleButton.clicked.connect(self._toggleClicked)

    def label(self) -> str:
        return self._toggleButton.text()

    def setLabel(self, label: str) -> None:
        self._toggleButton.setText(label)

    def content(self) -> typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]]:
        return self._content

    def setContent(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> None:
        if isinstance(content, QtWidgets.QWidget):
            # This layout intentionally keeps the default padding to indent the widget a little
            layout = QtWidgets.QVBoxLayout()
            interfaceScale = app.ConfigEx.instance().asFloat(
                option=app.ConfigOption.InterfaceScale)
            layout.setContentsMargins(
                int(ExpanderWidget._LeftContentMargin * interfaceScale),
                int(ExpanderWidget._TopContentMargin * interfaceScale),
                int(ExpanderWidget._RightContentMargin * interfaceScale),
                int(ExpanderWidget._BottomContentMargin * interfaceScale))
            layout.addWidget(content)
        elif isinstance(content, QtWidgets.QLayout):
            layout = content
        else:
            raise TypeError('Layout object must be a widget or layout')
        self._content = content
        self._contentArea.setLayout(layout)

    def isExpanded(self) -> bool:
        return self._toggleButton.isChecked()

    def setExpanded(
            self,
            expanded: bool,
            animated: bool = True
            ) -> None:
        oldExpanded = self.isExpanded()
        if animated and (expanded == oldExpanded):
            # Animated expanding/collapsing was requested but the widget is either in
            # the required state or the animation to get it into that state has already
            # been started so nothing to do. We don't take an early out if no animation
            # is requested as in the case that an animation is underway we want to stop
            # the animation and perform an immediate expand/collapse
            return

        self._updateState(expanded=expanded, animated=animated)

        if expanded != oldExpanded:
            self.expansionChanged.emit(expanded, animated)

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if object == self._contentArea and event.type() == QtCore.QEvent.Type.LayoutRequest:
            self._updateContentHeight()
        return super().eventFilter(object, event)

    def sizeHint(self) -> QtCore.QSize:
        hint = super().sizeHint()

        contentLayout = self._contentArea.layout()
        contentHint = contentLayout.sizeHint()
        if contentHint.width() > hint.width():
            hint.setWidth(contentHint.width())
        return hint

    def _updateState(
            self,
            expanded: bool,
            animated: bool
            ) -> None:
        self._toggleButton.setChecked(expanded)
        self._toggleButton.setArrowType(
            QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow)

        if animated:
            self._startAnimation(expanding=expanded)
        else:
            self._toggleAnimation.stop()
            requiredHeight = self._collapsedHeight
            contentHeight = 0
            if expanded:
                contentLayout = self._contentArea.layout()
                contentHeight = contentLayout.sizeHint().height() if contentLayout else 0
                requiredHeight += contentHeight
            self.setMaximumHeight(requiredHeight)
            self.setMinimumHeight(requiredHeight)
            self._contentArea.setMaximumHeight(contentHeight)
            # Hide the content area (and therefore the content) if the widget is
            # being collapsed. This is important as it makes tab order
            # automatically skip any widgets that have been collapsed.
            self._contentArea.setHidden(not expanded)

    def _startAnimation(
            self,
            expanding: bool
            ) -> None:
        contentLayout = self._contentArea.layout()
        self._contentHeight = contentLayout.sizeHint().height()
        for i in range(self._toggleAnimation.animationCount() - 1):
            expanderAnimation: QtCore.QPropertyAnimation = self._toggleAnimation.animationAt(i)
            expanderAnimation.setDuration(self._animationDuration)
            expanderAnimation.setStartValue(self._collapsedHeight)
            expanderAnimation.setEndValue(self._collapsedHeight + self._contentHeight)

        contentAnimation: QtCore.QPropertyAnimation = self._toggleAnimation.animationAt(self._toggleAnimation.animationCount() - 1)
        contentAnimation.setDuration(self._animationDuration)
        contentAnimation.setStartValue(0)
        contentAnimation.setEndValue(self._contentHeight)

        self._toggleAnimation.setDirection(
            QtCore.QAbstractAnimation.Direction.Forward if expanding else QtCore.QAbstractAnimation.Direction.Backward)
        self._toggleAnimation.start()

        # Show the content area if the widget is being expanded. See the note in
        # _updateState for why this is important
        if expanding:
            self._contentArea.setHidden(False)

    def _animationFinished(self) -> None:
        # Hide the content area if the widget has been collapsed. See the note in
        # _updateState for why this is important
        if not self.isExpanded():
            self._contentArea.setHidden(True)

    def _updateContentHeight(self) -> None:
        # The content height has changed. If the expander is expanded then update its height to
        # match the widget. This is done as an instant update rather than being animated.
        if self.isExpanded():
            self._updateState(expanded=True, animated=False)

    def _toggleClicked(
            self,
            checked: bool
            ) -> None:
        self._updateState(expanded=checked, animated=True)
        self.expansionChanged.emit(checked, True)

class ExpanderGroupWidget(QtWidgets.QWidget):
    expansionChanged = QtCore.pyqtSignal([QtCore.QObject, bool, bool])

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._expanders: typing.List[ExpanderWidget] = []

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.setLayout(self._layout)

    def expanders(self) -> typing.Iterable[ExpanderWidget]:
        return self._expanders

    def addExpander(
            self,
            expander: ExpanderWidget,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        self._insertExpander(
            index=-1, # Insert at end
            expander=expander,
            stretch=stretch,
            alignment=alignment)

    def insertExpander(
            self,
            index: int,
            expander: ExpanderWidget,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        self._insertExpander(
            index=index,
            expander=expander,
            stretch=stretch,
            alignment=alignment)

    def addExpandingContent(
            self,
            label: str,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            expanded: bool = True,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> ExpanderWidget:
        return self._insertExpandingContent(
            index=-1, # Insert at end
            label=label,
            content=content,
            expanded=expanded,
            stretch=stretch,
            alignment=alignment)

    def insertExpandingContent(
            self,
            index: int,
            label: str,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            expanded: bool = True,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> ExpanderWidget:
        return self._insertExpandingContent(
            index=index,
            label=label,
            content=content,
            expanded=expanded,
            stretch=stretch,
            alignment=alignment)

    def addStaticContent(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        self._insertStaticContent(
            index=-1, # Insert at end
            content=content,
            stretch=stretch,
            alignment=alignment)

    def insertStaticContent(
            self,
            index: int,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        self._insertStaticContent(
            index=index,
            content=content,
            stretch=stretch,
            alignment=alignment)

    def addStretch(
            self,
            stretch: int
            ) -> None:
        self._layout.addStretch(stretch=stretch)

    def insertStretch(
            self,
            index: int,
            stretch: int
            ) -> None:
        self._layout.insertStretch(index, stretch)

    def expanderFromContent(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> typing.Optional[ExpanderWidget]:
        for expander in self._expanders:
            if content == expander.content():
                return expander
        return None

    def isContentExpanded(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> bool:
        expander = self.expanderFromContent(content)
        if not expander:
            return False
        return expander.isExpanded()

    def labelFromContent(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> typing.Optional[str]:
        expander = self.expanderFromContent(content)
        if not expander:
            return None
        return expander.label()

    def contentFromLabel(
            self,
            label: str
            ) -> typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]]:
        for expander in self._expanders:
            if expander.label() == label:
                return expander.content()
        return None

    def expandByContent(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            expand: bool = True,
            animate: bool = True
            ) -> None:
        expander = self.expanderFromContent(content)
        if not expander:
            return
        expander.setExpanded(expanded=expand, animated=animate)

    def expandByLabel(
            self,
            label: str,
            expand: bool = True,
            animate: bool = True
            ) -> None:
        for expander in self._expanders:
            if expander.label() == label:
                expander.setExpanded(expanded=expand, animated=animate)

    # This is named removeWidget but QVBoxLayout also (as far as I can tell) uses it to remove
    # layouts so I've gone with the same approach
    def removeContent(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout]
            ) -> None:
        expander = self.expanderFromContent(content)
        if expander:
            # If an expander is used then it's the expander that needs to be removed
            self._expanders.remove(expander)
            content = expander

        self._layout.removeWidget(content)

        if expander:
            expander.expansionChanged.disconnect(self._expansionChanged)

            # Destroy the expander after removing it. Reset the parent on the widget to detach it
            # from the parent the widget that the layout would have set for it (i.e. the widget the
            # layout is attached to). I'm not sure why removeWidget doesn't do this as it would seem
            # logical when addWidget sets the parent. I found that in most cases this was enough to
            # stop the removed widget from being displayed. However if adding/removing widgets is
            # done rapidly (e.g. by the user scrolling up and down through the weapon list with the
            # cursor keys) then sometimes the removed widgets would be left displayed in separate
            # floating windows (I've no idea why this is happening but ut doesn't appear to be my
            # code). The explicit deleteLater fixes this. Hiding the widget is done to prevent it
            # temporarily being displayed in a floating window before deleteLater kicks in.
            expander.setParent(None)
            expander.setHidden(True)
            expander.deleteLater()

    def contentFromIndex(
            self,
            index: int
            ) -> typing.Optional[typing.Union[QtWidgets.QWidget, QtWidgets.QLabel]]:
        layoutItem = self._layout.itemAt(index)
        if not layoutItem:
            return None
        widget = layoutItem.widget()
        if not widget:
            return layoutItem.layout()
        if widget in self._expanders:
            assert(isinstance(widget, ExpanderWidget))
            return widget.content()
        return widget

    def setExpanderLabel(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            label: str
            ) -> None:
        expander = self.expanderFromContent(content)
        if not expander:
            return # Nothing to do
        expander.setLabel(label=label)

    def isWidgetHidden(
            self,
            widget: QtWidgets.QWidget
            ) -> bool:
        expander = self.expanderFromContent(widget)
        if expander:
            widget = expander
        return widget.isHidden()

    def setContentHidden(
            self,
            content: QtWidgets.QWidget,
            hidden: bool
            ) -> None:
        expander = self.expanderFromContent(content)
        if expander:
            expander.setHidden(hidden)
        else:
            content.setHidden(hidden)

    def _insertExpander(
            self,
            index: int,
            expander: ExpanderWidget,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        assert(isinstance(expander, ExpanderWidget))
        expander.expansionChanged.connect(self._expansionChanged)
        self._expanders.append(expander)
        self._layout.insertWidget(index, expander, stretch, alignment)

    def _insertExpandingContent(
            self,
            index: int,
            label: str,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            expanded: bool,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> ExpanderWidget:
        expander = ExpanderWidget(label=label)
        expander.setContent(content)
        expander.setExpanded(expanded=expanded, animated=False)
        self._insertExpander(
            index=index,
            expander=expander,
            stretch=stretch,
            alignment=alignment)
        return expander

    def _insertStaticContent(
            self,
            index: int,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> None:
        if isinstance(content, QtWidgets.QLayout):
            # Note that alignment doesn't apply for layouts
            self._layout.insertLayout(index, content, stretch)
        else:
            self._layout.insertWidget(index, content, stretch, alignment)

    def _expansionChanged(
            self,
            expanded: bool,
            animated: bool
            ) -> None:
        expander = self.sender()
        assert(isinstance(expander, ExpanderWidget))

        # Generate event to let external observers know of expansion change
        self.expansionChanged.emit(expander.content(), expanded, animated)

        updateAll = gui.isShiftKeyDown()
        updateBefore = gui.isCtrlKeyDown()
        updateAfter = gui.isAltKeyDown()
        if not (updateAll or updateBefore or updateAfter):
            return

        foundObject = False
        for other in self._expanders:
            if expander == other:
                foundObject = True
                continue

            if not foundObject and updateAfter:
                # We're only updating rows before the expanded object but we've not hit
                # it yet so nothing to do
                continue
            if foundObject and updateBefore:
                # We're only updating rows before the expanded object and we've already
                # hit it so no need ot process further rows. This could be done at the
                # point the object is hit but I've done it hear for clarity
                break

            if expanded != other.isExpanded():
                # Silently update the expander to prevent it generating expansion events and
                # calling this function recursively
                self._silentlyUpdateExpander(
                    expander=other,
                    expanded=expanded,
                    animated=animated)

                # Generate event to let external observers know of expansion change
                self.expansionChanged.emit(other.content(), expanded, animated)

    def _silentlyUpdateExpander(
            self,
            expander: ExpanderWidget,
            expanded: bool,
            animated: bool
            ) -> None:
        with gui.SignalBlocker(widget=expander):
            expander.setExpanded(expanded=expanded, animated=animated)

class ExpanderGroupWidgetEx(ExpanderGroupWidget):
    _StateVersion = 'ExpanderWidgetEx_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)
        self._storedExpansionStates: typing.Optional[typing.Dict[str, bool]] = None

    def setPersistExpanderStates(self, enable: bool):
        if enable and (self._storedExpansionStates == None):
            self._storedExpansionStates = {}
        elif (not enable) and (self._storedExpansionStates != None):
            self._storedExpansionStates = None

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(ExpanderGroupWidgetEx._StateVersion)

        stream.writeUInt32(len(self._storedExpansionStates) if self._storedExpansionStates else 0)
        if self._storedExpansionStates:
            for label, expanded in self._storedExpansionStates.items():
                stream.writeQString(label)
                stream.writeBool(expanded)

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != ExpanderGroupWidgetEx._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore ExpanderGroupWidgetEx state (Incorrect version)')
            return False

        if self._storedExpansionStates != None:
            count = stream.readUInt32()
            for _ in range(count):
                label = stream.readQString()
                expanded = stream.readBool()
                self.expandByLabel(label=label, expand=expanded, animate=False)

        return True

    # Override _insertExpandingContent in order to override expanded setting with the cached value
    def _insertExpandingContent(
            self,
            index: int,
            label: str,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            expanded: bool,
            stretch: int = 0,
            alignment: QtCore.Qt.AlignmentFlag = QtCore.Qt.AlignmentFlag(0)
            ) -> ExpanderWidget:
        if self._storedExpansionStates != None:
            storedState = self._storedExpansionStates.get(label)
            if storedState != None:
                expanded = storedState

        return super()._insertExpandingContent(index, label, content, expanded, stretch, alignment)

    def _expansionChanged(
            self,
            expanded: bool,
            animated: bool
            ) -> None:
        super()._expansionChanged(expanded, animated)

        expander = self.sender()
        assert(isinstance(expander, ExpanderWidget))
        self._updateExpansionState(
            content=expander.content(),
            expanded=expanded)

    def _silentlyUpdateExpander(
            self,
            expander: ExpanderWidget,
            expanded: bool,
            animated: bool
            ) -> None:
        super()._silentlyUpdateExpander(expander, expanded, animated)

        self._updateExpansionState(
            content=expander.content(),
            expanded=expanded)

    def _updateExpansionState(
            self,
            content: typing.Union[QtWidgets.QWidget, QtWidgets.QLayout],
            expanded: bool
            ) -> ExpanderWidget:
        if self._storedExpansionStates != None:
            label = self.labelFromContent(content=content)
            if label:
                self._storedExpansionStates[label] = expanded
