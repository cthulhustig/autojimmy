import gui
import traveller
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

class _CustomTextEdit(gui.TextEditEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._world = None

        self.setReadOnly(True)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)

        # Call adjustSize on the document to force an update of it's size after the content has been
        # set. This is required so the sizeHint is generated correctly
        self.document().adjustSize()

    def world(self) -> traveller.World:
        return self._world

    def setWorld(
            self,
            world: typing.Optional[traveller.World]
            ) -> None:
        if world == self._world:
            return # Nothing to do

        self._world = world
        if self._world:
            self.setHtml(gui.createWorldToolTip(self._world))
        else:
            self.clear()

    def clear(self) -> None:
        self._world = None
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

class WorldDetailsWindow(gui.WindowWidget):
    def __init__(
            self,
            ) -> None:
        super().__init__(
            title='World Details',
            configSection='WorldDetailsWindow')

        self._worlds = []

        self._tabBar = gui.VerticalTabBar()
        self._tabBar.setTabsClosable(True)
        self._tabBar.tabCloseRequested.connect(self._tabCloseRequested)
        self._tabBar.selectionChanged.connect(self._tabChanged)

        self._worldDetails = _CustomTextEdit()

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._tabBar, 0)
        layout.addWidget(self._worldDetails, 1)

        self.setLayout(layout)
        self.resize(800, 600)

    def addWorld(
            self,
            world: traveller.World
            ) -> None:
        for index, existingWorld in enumerate(self._worlds):
            if world == existingWorld:
                self._tabBar.setCurrentIndex(index)
                self._worldDetails.setWorld(world)
                return

        self._worlds.append(world)
        index = self._tabBar.addTab(world.name(includeSubsector=True))
        self._tabBar.setCurrentIndex(index)
        self._worldDetails.setWorld(world)

    def addWorlds(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        for world in worlds:
            self.addWorld(world=world)

    def _tabChanged(self) -> None:
        index = self._tabBar.currentIndex()
        if index < 0:
            return

        assert(index < len(self._worlds))
        self._worldDetails.setWorld(self._worlds[index])

    def _tabCloseRequested(
            self,
            index: int
            ) -> None:
        assert(index < len(self._worlds))

        del self._worlds[index]

        # Block signals while removing the tab to prevent the tabChanged handler being called
        self._tabBar.blockSignals(True)
        try:
            self._tabBar.removeTab(index)
        finally:
            self._tabBar.blockSignals(False)

        if len(self._worlds) > 0:
            currentIndex = self._tabBar.currentIndex()
            assert(currentIndex < len(self._worlds))
            self._worldDetails.setWorld(self._worlds[currentIndex])
        else:
            # No more worlds to display so clear the current world info and close the window.
            # The world info is cleared in case the window is re-shown
            self._worldDetails.clear()
            self.close()
