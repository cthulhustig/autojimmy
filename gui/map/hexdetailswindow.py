import app
import cartographer
import gui
import logic
import multiverse
import traveller
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

class _CustomLabel(QtWidgets.QLabel):
    def __init__(
            self,
            milieu: multiverse.Milieu,
            rules: traveller.Rules,
            mapStyle: cartographer.MapStyle,
            mapOptions: typing.Collection[app.MapOption],
            worldTagging: typing.Optional[logic.WorldTagging] = None,
            taggingColours: typing.Optional[app.TaggingColours] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._milieu = milieu
        self._rules = traveller.Rules(rules)
        self._mapStyle = mapStyle
        self._mapOptions = set(mapOptions)
        self._worldTagging = logic.WorldTagging(worldTagging)
        self._taggingColours = app.TaggingColours(taggingColours)
        self._hex = None

        self.setBackgroundRole(QtGui.QPalette.ColorRole.Base)
        self.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse | QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setOpenExternalLinks(True)
        self.setWordWrap(True)
        self.linkHovered.connect(self._linkHovered)

    def setMilieu(self, milieu: multiverse.Milieu) -> None:
        if milieu is self._milieu:
            return

        self._milieu = milieu
        self._updateContent()

    def setRules(self, rules: traveller.Rules) -> None:
        if rules == self._rules:
            return

        self._rules = traveller.Rules(rules)
        self._updateContent()

    def setMapStyle(self, style: cartographer.MapStyle) -> None:
        if style is self._mapStyle:
            return

        self._mapStyle = style
        self._updateContent()

    def setMapOptions(self, options: typing.Collection[app.MapOption]) -> None:
        options = set(options) # Force use of set so options can be compared
        if options == self._mapOptions:
            return

        self._mapOptions = options
        self._updateContent()

    def setWorldTagging(
            self,
            tagging: typing.Optional[logic.WorldTagging],
            ) -> None:
        if tagging == self._worldTagging:
            return
        self._worldTagging = logic.WorldTagging(tagging) if tagging else None
        self._updateContent()

    def setTaggingColours(
            self,
            colours: typing.Optional[app.TaggingColours]
            ) -> None:
        if colours == self._taggingColours:
            return
        self._taggingColours = app.TaggingColours(colours) if colours else None
        self._updateContent()

    def setHex(
            self,
            hex: typing.Optional[multiverse.HexPosition]
            ) -> None:
        if hex == self._hex:
            return

        self._hex = hex
        self._updateContent()

    def _updateContent(self) -> None:
        if self._hex:
            self.setText(gui.createHexToolTip(
                universe=multiverse.WorldManager.instance().universe(),
                milieu=self._milieu,
                hex=self._hex,
                rules=self._rules,
                worldTagging=self._worldTagging,
                taggingColours=self._taggingColours,
                width=0,
                includeHexImage=True, # Always show image of the hex in hex detail window
                hexImageStyle=self._mapStyle,
                hexImageOptions=self._mapOptions))
        else:
            self.clear()

    def _linkHovered(self, link: str) -> None:
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), link)

class HexDetailsWindow(gui.WindowWidget):
    def __init__(
            self,
            ) -> None:
        super().__init__(
            title='Hex Details',
            configSection='HexDetailsWindow')

        self._hexes: typing.List[multiverse.HexPosition] = []

        self._tabBar = gui.VerticalTabBar()
        self._tabBar.setTabsClosable(True)
        self._tabBar.tabCloseRequested.connect(self._tabCloseRequested)
        self._tabBar.selectionChanged.connect(self._tabChanged)

        self._hexLabel = _CustomLabel(
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            mapStyle=app.Config.instance().value(option=app.ConfigOption.MapStyle),
            mapOptions=app.Config.instance().value(option=app.ConfigOption.MapOptions),
            worldTagging=app.Config.instance().value(option=app.ConfigOption.WorldTagging),
            taggingColours=app.Config.instance().value(option=app.ConfigOption.TaggingColours))

        scrollArea = gui.ScrollAreaEx()
        scrollArea.setWidget(self._hexLabel)
        scrollArea.setWidgetResizable(True)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._tabBar, 0)
        layout.addWidget(scrollArea, 1)

        self.setLayout(layout)
        self.resize(800, 600)

        app.Config.instance().configChanged.connect(self._appConfigChanged)

    def addHex(
            self,
            hex: multiverse.HexPosition
            ) -> None:
        for index, existingHex in enumerate(self._hexes):
            if hex == existingHex:
                self._tabBar.setCurrentIndex(index)
                self._hexLabel.setHex(hex)
                return

        tabName = multiverse.WorldManager.instance().canonicalHexName(
            milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
            hex=hex)
        self._hexes.append(hex)
        index = self._tabBar.addTab(tabName)
        self._tabBar.setCurrentIndex(index)
        self._hexLabel.setHex(hex)

    def addHexes(
            self,
            hexes: typing.Iterable[multiverse.HexPosition]
            ) -> None:
        if not hexes:
            return

        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        currentHexes = set(self._hexes)
        for hex in hexes:
            if hex not in currentHexes:
                tabName = multiverse.WorldManager.instance().canonicalHexName(
                    milieu=milieu,
                    hex=hex)
                self._hexes.append(hex)
                self._tabBar.addTab(tabName)

        firstHex = hexes[0]
        index = self._hexes.index(firstHex)
        if index >= 0:
            self._tabBar.setCurrentIndex(index)
            self._hexLabel.setHex(firstHex)

    def _tabChanged(self) -> None:
        index = self._tabBar.currentIndex()
        if index < 0:
            return

        assert(index < len(self._hexes))
        self._hexLabel.setHex(self._hexes[index])

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
            self._hexLabel.setHex(self._hexes[currentIndex])
        else:
            # No more worlds to display so clear the current world info and close the window.
            # The world info is cleared in case the window is re-shown
            self._hexLabel.clear()
            self.close()

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Milieu:
            for index, hex in enumerate(self._hexes):
                tabName = multiverse.WorldManager.instance().canonicalHexName(
                    milieu=newValue,
                    hex=hex)
                self._tabBar.setTabText(index, tabName)
            self._hexLabel.setMilieu(milieu=newValue)
        elif option is app.ConfigOption.Rules:
            self._hexLabel.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._hexLabel.setMapStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._hexLabel.setMapOptions(options=newValue)
        elif option is app.ConfigOption.WorldTagging:
            self._hexLabel.setWorldTagging(tagging=newValue)
        elif option is app.ConfigOption.TaggingColours:
            self._hexLabel.setTaggingColours(colours=newValue)
