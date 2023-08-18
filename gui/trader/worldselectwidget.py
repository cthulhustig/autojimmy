import gui
import logging
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

class WorldSelectWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()

    _StateVersion = 'WorldSelectWidget_v1'

    def __init__(
            self,
            labelText: str = 'World',
            noSelectionText: str = 'Select a world to continue',
            world: typing.Optional[traveller.World] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._selectButton = QtWidgets.QPushButton('Select...')
        self._selectButton.clicked.connect(self._selectClicked)

        self._worldLabel = gui.WorldLabel(
            world=world,
            prefixText=f'{labelText}: ',
            noWorldText=noSelectionText)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._selectButton)
        layout.addWidget(self._worldLabel)
        layout.addStretch()
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def world(self) -> typing.Optional[traveller.World]:
        return self._worldLabel.world()

    def setWorld(self, world: typing.Optional[traveller.World]) -> None:
        if world != self.world():
            self._worldLabel.setWorld(world)
            self.selectionChanged.emit()

    def hasSelection(self) -> bool:
        return self._worldLabel.world() != None

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

    def _selectClicked(self) -> None:
        dlg = gui.WorldSearchDialog()
        dlg.setWorld(self.world()) # Set initial selection to current world
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None
        world = dlg.world()
        if not world:
            return
        self.setWorld(world=world)
