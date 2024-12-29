import app
import gui
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

class WorldSearchDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='World Search',
            configSection='WorldSearchDialog',
            parent=parent)

        self._selectWorldWidget = gui.WorldSearchWidget()
        self._selectWorldWidget.selectionChanged.connect(self._selectionChanged)

        self._selectButton = QtWidgets.QPushButton('Select')
        self._selectButton.setDisabled(not self._selectWorldWidget.world())
        self._selectButton.setDefault(True)
        self._selectButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._selectButton)
        buttonLayout.addWidget(self._cancelButton)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._selectWorldWidget)
        windowLayout.addLayout(buttonLayout)

        self.setLayout(windowLayout)

    def world(self) -> typing.Optional[traveller.World]:
        return self._selectWorldWidget.world()

    def setWorld(self, world: typing.Optional[traveller.World]) -> None:
        self._selectWorldWidget.setWorld(world)

    # There is intentionally no saveSettings implementation as saving is only done if the user clicks ok
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)
        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SelectWorldState',
            type=QtCore.QByteArray)
        if storedValue:
            self._selectWorldWidget.restoreState(storedValue)
        self._settings.endGroup()

    def accept(self) -> None:
        world = self.world()
        if not world:
            return # A valid world must be selected to accept

        # Add the selected world to the recently used list
        app.HexHistory.instance().addHex(pos=world.hexPosition()) # TODO: This is temporary until this widget is updated to uses hexes

        self._settings.beginGroup(self._configSection)
        self._settings.setValue('SelectWorldState', self._selectWorldWidget.saveState())
        self._settings.endGroup()

        super().accept()

    def _selectionChanged(self) -> None:
        self._selectButton.setDisabled(not self._selectWorldWidget.world())
