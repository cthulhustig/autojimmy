import app
import gui
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

class _CustomTextEdit(gui.TextEditEx):
    def __init__(
            self,
            milieu: travellermap.Milieu,
            rules: traveller.Rules,
            mapStyle: travellermap.Style,
            mapOptions: typing.Collection[travellermap.Option],
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._milieu = milieu
        self._rules = traveller.Rules(rules)
        self._mapStyle = mapStyle
        self._mapOptions = set(mapOptions)
        self._hex = None

        self.setReadOnly(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)

        # Call adjustSize on the document to force an update of it's size after the content has been
        # set. This is required so the sizeHint is generated correctly
        self.document().adjustSize()

    def setMilieu(self, milieu: travellermap.Milieu) -> None:
        if milieu is self._milieu:
            return

        self._milieu = milieu
        self._updateContent()

    def setRules(self, rules: traveller.Rules) -> None:
        if rules == self._rules:
            return

        self._rules = traveller.Rules(rules)
        self._updateContent()

    def setMapStyle(self, style: travellermap.Style) -> None:
        if style is self._mapStyle:
            return

        self._mapStyle = style
        self._updateContent()

    def setMapOptions(self, options: typing.Collection[travellermap.Option]) -> None:
        options = set(options)
        if options == self._mapOptions:
            return

        self._mapOptions = options
        self._updateContent()

    def setHex(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        if hex == self._hex:
            return

        self._hex = hex
        self._updateContent()

    def clear(self) -> None:
        super().clear()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        key = event.key()
        # Accept + or = for zoom in so user doesn't have to press shift
        if key == QtCore.Qt.Key.Key_Plus:
            self.zoomIn(1)
            return # Swallow event
        elif key == QtCore.Qt.Key.Key_Minus:
            self.zoomOut(1)
            return # Swallow event

        return super().keyPressEvent(event)

    def _updateContent(self) -> None:
        if self._hex:
            self.setHtml(gui.createHexToolTip(
                hex=self._hex,
                milieu=self._milieu,
                rules=self._rules,
                hexImage=True, # Always show image of the hex in hex detail window
                hexImageStyle=self._mapStyle,
                hexImageOptions=self._mapOptions))
        else:
            self.clear()

class HexDetailsWindow(gui.WindowWidget):
    def __init__(
            self,
            ) -> None:
        super().__init__(
            title='Hex Details',
            configSection='HexDetailsWindow')

        self._hexes: typing.List[travellermap.HexPosition] = []

        self._tabBar = gui.VerticalTabBar()
        self._tabBar.setTabsClosable(True)
        self._tabBar.tabCloseRequested.connect(self._tabCloseRequested)
        self._tabBar.selectionChanged.connect(self._tabChanged)

        self._hexDetails = _CustomTextEdit(
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            mapStyle=app.Config.instance().value(option=app.ConfigOption.MapStyle),
            mapOptions=app.Config.instance().value(option=app.ConfigOption.MapOptions))

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._tabBar, 0)
        layout.addWidget(self._hexDetails, 1)

        self.setLayout(layout)
        self.resize(800, 600)

        app.Config.instance().configChanged.connect(self._appConfigChanged)

    def addHex(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        for index, existingHex in enumerate(self._hexes):
            if hex == existingHex:
                self._tabBar.setCurrentIndex(index)
                self._hexDetails.setHex(hex)
                return

        tabName = traveller.WorldManager.instance().canonicalHexName(
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            hex=hex)
        self._hexes.append(hex)
        index = self._tabBar.addTab(tabName)
        self._tabBar.setCurrentIndex(index)
        self._hexDetails.setHex(hex)

    def addHexes(
            self,
            hexes: typing.Iterable[travellermap.HexPosition]
            ) -> None:
        for hex in hexes:
            self.addHex(hex)

    def _tabChanged(self) -> None:
        index = self._tabBar.currentIndex()
        if index < 0:
            return

        assert(index < len(self._hexes))
        self._hexDetails.setHex(self._hexes[index])

    def _tabCloseRequested(
            self,
            index: int
            ) -> None:
        assert(index < len(self._hexes))

        del self._hexes[index]

        # Block signals while removing the tab to prevent the tabChanged handler being called
        self._tabBar.blockSignals(True)
        try:
            self._tabBar.removeTab(index)
        finally:
            self._tabBar.blockSignals(False)

        if len(self._hexes) > 0:
            currentIndex = self._tabBar.currentIndex()
            assert(currentIndex < len(self._hexes))
            self._hexDetails.setHex(self._hexes[currentIndex])
        else:
            # No more worlds to display so clear the current world info and close the window.
            # The world info is cleared in case the window is re-shown
            self._hexDetails.clear()
            self.close()

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Milieu:
            for index, hex in enumerate(self._hexes):
                tabName = traveller.WorldManager.instance().canonicalHexName(
                    milieu=newValue,
                    hex=hex)
                self._tabBar.setTabText(index, tabName)
            self._hexDetails.setMilieu(milieu=newValue)
        elif option is app.ConfigOption.Rules:
            self._hexDetails.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._hexDetails.setMapStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._hexDetails.setMapOptions(options=newValue)
