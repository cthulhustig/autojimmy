import gui
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

class _CustomTextEdit(gui.TextEditEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self.setReadOnly(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)

        # Call adjustSize on the document to force an update of it's size after the content has been
        # set. This is required so the sizeHint is generated correctly
        self.document().adjustSize()

    def setHex(
            self,
            hex: typing.Optional[typing.Union[travellermap.HexPosition, traveller.World]]
            ) -> None:
        if hex:
            self.setHtml(gui.createHexToolTip(hex=hex))
        else:
            self.clear()

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

        self._hexDetails = _CustomTextEdit()

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._tabBar, 0)
        layout.addWidget(self._hexDetails, 1)

        self.setLayout(layout)
        self.resize(800, 600)

    def addHex(
            self,
            hex: typing.Union[
                travellermap.HexPosition,
                traveller.World]
                ) -> None:
        if isinstance(hex, traveller.World):
            hex = hex.hex()

        for index, existingHex in enumerate(self._hexes):
            if hex == existingHex:
                self._tabBar.setCurrentIndex(index)
                self._hexDetails.setHex(hex)
                return

        tabName = traveller.WorldManager.instance().canonicalHexName(hex)
        self._hexes.append(hex)
        index = self._tabBar.addTab(tabName)
        self._tabBar.setCurrentIndex(index)
        self._hexDetails.setHex(hex)

    def addHexes(
            self,
            hexes: typing.Iterable[typing.Union[
                travellermap.HexPosition,
                traveller.World]]
            ) -> None:
        for hex in hexes:
            self.addHex(hex=hex)

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
