import gui
import logging
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

# TODO: Need to fix tab order, combo box is currently after icons
class WorldSelectWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()
    showWorld = QtCore.pyqtSignal(traveller.World)

    _StateVersion = 'WorldSelectWidget_v1'

    def __init__(
            self,
            text: str = 'Select World:',
            world: typing.Optional[traveller.World] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._enableMapSelectButton = False
        self._enableShowWorldButton = False
        self._enableShowInfoButton = False
        self._mapSelectDialog = None

        self._worldComboBox = gui.WorldSelectComboBox()
        if world:
            self._worldComboBox.setCurrentWorld(world=world)
        self._worldComboBox.enableAutoComplete(True)
        self._worldComboBox.worldChanged.connect(self._selectionChanged)

        self._mapSelectButton = gui.IconButton(
            icon=gui.loadIcon(id=gui.Icon.Map),
            parent=self)
        self._mapSelectButton.setToolTip(gui.createStringToolTip(
            'Select a world using Traveller Map.'))
        self._mapSelectButton.setHidden(True)
        self._mapSelectButton.clicked.connect(self._mapSelectClicked)

        self._showWorldButton = gui.IconButton(
            icon=gui.loadIcon(id=gui.Icon.Search),
            parent=self)
        self._showWorldButton.setToolTip(gui.createStringToolTip(
            'Show world in Traveller Map.'))
        self._showWorldButton.setHidden(True)
        self._showWorldButton.clicked.connect(self._showWorldClicked)

        self._showInfoButton = gui.IconButton(
            icon=gui.loadIcon(id=gui.Icon.Info),
            parent=self)
        self._showInfoButton.setToolTip(gui.createStringToolTip(
            'Show world info.'))
        self._showInfoButton.setHidden(True)
        self._showInfoButton.clicked.connect(self._showInfoClicked)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        if text:
            layout.addWidget(QtWidgets.QLabel(text))
        layout.addWidget(self._worldComboBox, 1)
        layout.addWidget(self._mapSelectButton)
        layout.addWidget(self._showWorldButton)
        layout.addWidget(self._showInfoButton)

        self.setLayout(layout)

    def world(self) -> typing.Optional[traveller.World]:
        return self._worldComboBox.currentWorld()

    def setWorld(self, world: typing.Optional[traveller.World]) -> None:
        if world != self.world():
            self._worldComboBox.setCurrentWorld(world=world)
            self.selectionChanged.emit()

    def hasSelection(self) -> bool:
        return self._worldComboBox.currentWorld() != None

    def enableMapSelectButton(self, enable: bool) -> None:
        self._enableMapSelectButton = enable
        self._mapSelectButton.setHidden(not self._enableMapSelectButton)

    def enableShowWorldButton(self, enable: bool) -> None:
        self._enableShowWorldButton = enable
        self._showWorldButton.setHidden(not self._enableShowWorldButton)

    def enableShowInfoButton(self, enable: bool) -> None:
        self._enableShowInfoButton = enable
        self._showInfoButton.setHidden(not self._enableShowInfoButton)

    def saveState(self) -> QtCore.QByteArray:
        world = self.world()
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(WorldSelectWidget._StateVersion)
        stream.writeQString(world.sectorHex() if world else '')
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WorldSelectWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WorldSelectWidget state (Incorrect version)')
            return False

        sectorHex = stream.readQString()
        world = None
        if sectorHex:
            try:
                world = traveller.WorldManager.instance().world(sectorHex=sectorHex)
            except Exception as ex:
                logging.error(f'Failed to restore WorldSelectWidget state', exc_info=ex)
                return False

        self.setWorld(world=world)
        return True

    def _selectionChanged(self) -> None:
        world = self.world()
        self._showWorldButton.setEnabled(world != None)
        self._showInfoButton.setEnabled(world != None)
        self.selectionChanged.emit()

    def _mapSelectClicked(self) -> None:
        if not self._mapSelectDialog:
            self._mapSelectDialog = gui.TravellerMapSelectDialog(parent=self)
            self._mapSelectDialog.setSingleSelect(True)

        currentSelection = [self.world()] if self.hasSelection() else []
        self._mapSelectDialog.setSelectedWorlds(currentSelection)
        if self._mapSelectDialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        newSelection = self._mapSelectDialog.selectedWorlds()
        if len(newSelection) != 1:
            return

        self._worldComboBox.setCurrentWorld(world=newSelection[0])

    def _showWorldClicked(self) -> None:
        world = self.world()
        if world:
            self.showWorld.emit(world)

    def _showInfoClicked(self) -> None:
        world = self.world()
        if world:
            infoWindow = gui.WindowManager.instance().showWorldDetailsWindow()
            infoWindow.addWorld(world=world)
