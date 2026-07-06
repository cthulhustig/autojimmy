import app
import astronomer
import common
import gui
import jobs
import multiverse
import typing
from PyQt5 import QtWidgets, QtCore

class UniverseManagerDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Universe Manager',
            configSection='UniverseManagerDialog',
            parent=parent)

        self._setupUniverseList()
        self._setupDialogButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._universeListGroupBox)
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)

        self._syncUniverseList()

    def _setupUniverseList(self) -> None:
        self._universeList = gui.ListWidgetEx()
        self._universeList.currentRowChanged.connect(self._selectedUniverseChanged)

        self._makeActiveButton = QtWidgets.QPushButton('Make Active')
        self._makeActiveButton.clicked.connect(self._makeActiveClicked)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._universeList)
        layout.addWidget(self._makeActiveButton)

        self._universeListGroupBox = QtWidgets.QGroupBox('Universe')
        self._universeListGroupBox.setLayout(layout)

    def _setupDialogButtons(self) -> None:
        self._closeButton = QtWidgets.QPushButton('Close')
        self._closeButton.clicked.connect(self.accept)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._closeButton)

    def _syncUniverseList(self) -> None:
        activeUniverseId = app.Config.instance().value(option=app.ConfigOption.Universe)

        selectedUniverse: typing.Optional[multiverse.UniverseInfo] = self._universeList.currentData(
            QtCore.Qt.ItemDataRole.UserRole)

        with gui.SignalBlocker(self._universeList):
            self._universeList.clear()

            universes = multiverse.UniverseManager.instance().universeInfos()
            for universe in universes:
                name = universe.name()
                if activeUniverseId and universe.id() == activeUniverseId:
                    # TODO: Do this better, maybe an icon and separate column
                    name += ' (Active)'

                item = QtWidgets.QListWidgetItem(name)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, universe)
                if selectedUniverse and selectedUniverse.id() == universe.id():
                    item.setSelected(True)
                self._universeList.addItem(item)

        self._syncButtonStates()

    def _selectedUniverseChanged(self) -> None:
        self._syncButtonStates()

    def _makeActiveClicked(self) -> None:
        selectedUniverse: typing.Optional[multiverse.UniverseInfo] = self._universeList.currentData(
            QtCore.Qt.ItemDataRole.UserRole)
        if not selectedUniverse:
            return

        app.Config.instance().setValue(
            option=app.ConfigOption.Universe,
            value=selectedUniverse.id())

        self._syncUniverseList()

    def _syncButtonStates(self) -> None:
        activeUniverseId = app.Config.instance().value(option=app.ConfigOption.Universe)
        selectedUniverse: typing.Optional[multiverse.UniverseInfo] = self._universeList.currentData(
            QtCore.Qt.ItemDataRole.UserRole)
        selectedUniverseId = selectedUniverse.id() if selectedUniverse else None
        selectedIsActive = selectedUniverseId and activeUniverseId and selectedUniverseId == activeUniverseId

        self._makeActiveButton.setEnabled(not not activeUniverseId or not selectedIsActive)