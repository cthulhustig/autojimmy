import gui
import multiverse
import typing
from PyQt5 import QtWidgets, QtCore

class UniverseSelectDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Select Universe',
            configSection='UniverseSelectDialog',
            parent=parent)

        self._setupUniverseList()
        self._setupDialogButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._universeListGroupBox)
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)

        self._syncUniverseList()

    def universeId(self) -> typing.Optional[str]:
        selectedUniverse: typing.Optional[multiverse.UniverseInfo] = self._universeList.currentData(
            QtCore.Qt.ItemDataRole.UserRole)

        return selectedUniverse.id() if selectedUniverse else None

    def _setupUniverseList(self) -> None:
        self._universeList = gui.ListWidgetEx()
        self._universeList.currentRowChanged.connect(self._currentUniverseChanged)
        itemDelegate = gui.StyledItemDelegateEx()
        itemDelegate.setHighlightCurrentItem(enabled=False)
        self._universeList.setItemDelegate(itemDelegate)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._universeList)

        self._universeListGroupBox = QtWidgets.QGroupBox('Universe')
        self._universeListGroupBox.setLayout(layout)

    def _setupDialogButtons(self) -> None:
        self._newButton = QtWidgets.QPushButton('New')
        self._newButton.clicked.connect(self._newUniverseClicked)

        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDefault(True)
        self._okButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addWidget(self._newButton)
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._okButton)
        self._buttonLayout.addWidget(self._cancelButton)

    def _syncUniverseList(self) -> None:
        oldCurrentUniverseInfo: typing.Optional[multiverse.UniverseInfo] = \
            self._universeList.currentData(QtCore.Qt.ItemDataRole.UserRole)

        newCurrentItem = None
        with gui.SignalBlocker(self._universeList):
            self._universeList.clear()

            universes = multiverse.UniverseManager.instance().universeInfos()
            for universe in universes:
                item = QtWidgets.QListWidgetItem(universe.name())
                item.setData(QtCore.Qt.ItemDataRole.UserRole, universe)
                if oldCurrentUniverseInfo and oldCurrentUniverseInfo.id() == universe.id():
                    newCurrentItem = item
                self._universeList.addItem(item)

        if newCurrentItem:
            self._universeList.setCurrentItem(newCurrentItem)

        self._syncButtonStates()

    def _syncButtonStates(self) -> None:
        hasCurrent = self._universeList.hasCurrentItem()
        self._okButton.setEnabled(hasCurrent)

    def _currentUniverseChanged(self) -> None:
        item = self._universeList.currentItem()
        if item:
            item.setSelected(True)
        self._syncButtonStates()

    def _newUniverseClicked(self) -> None:
        dialog = gui.CreateUniverseDialog(self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        self._syncUniverseList()

        universeId = dialog.universeId()
        if universeId:
            item = self._findListItem(universeId=universeId)
            if item:
                self._universeList.setCurrentItem(item)

    def _findListItem(self, universeId: str) -> typing.Optional[QtWidgets.QListWidgetItem]:
        for row in range(self._universeList.count()):
            item = self._universeList.item(row)
            if not item:
                continue
            universeInfo: typing.Optional[multiverse.UniverseInfo] = \
                item.data(QtCore.Qt.ItemDataRole.UserRole)
            if universeInfo and universeInfo.id() == universeId:
                return item
        return None