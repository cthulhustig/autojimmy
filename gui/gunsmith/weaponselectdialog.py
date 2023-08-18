import gui
import gunsmith
import typing
from PyQt5 import QtWidgets, QtCore

class WeaponSelectDialog(gui.DialogEx):
    def __init__(
            self,
            title: str,
            weapons: typing.Collection[gunsmith.Weapon],
            text: typing.Optional[str] = None,
            defaultState: QtCore.Qt.CheckState = QtCore.Qt.CheckState.Unchecked,
            showYesNoCancel: bool = False,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title=title,
            configSection='WeaponSelectDialog',
            parent=parent)

        self._noClicked = False

        label = QtWidgets.QLabel(text) if text else None

        self._list = gui.ListWidgetEx()
        for weapon in weapons:
            item = gui.NaturalSortListWidgetItem()
            item.setData(QtCore.Qt.ItemDataRole.DisplayRole, weapon.weaponName())
            item.setData(QtCore.Qt.ItemDataRole.UserRole, weapon)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(defaultState)
            self._list.addItem(item)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()

        if showYesNoCancel:
            yesButton = QtWidgets.QPushButton('Yes')
            yesButton.setDefault(True)
            yesButton.clicked.connect(self._yesButtonClicked)
            buttonLayout.addWidget(yesButton)

            noButton = QtWidgets.QPushButton('No')
            noButton.clicked.connect(self._noButtonClicked)
            buttonLayout.addWidget(noButton)
        else:
            okButton = QtWidgets.QPushButton('OK')
            okButton.setDefault(True)
            okButton.clicked.connect(self.accept)
            buttonLayout.addWidget(okButton)

        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(cancelButton)

        dialogLayout = QtWidgets.QVBoxLayout()
        if label:
            dialogLayout.addWidget(label)
        dialogLayout.addWidget(self._list)
        dialogLayout.addLayout(buttonLayout)

        self.setLayout(dialogLayout)

    def selectedWeapons(self) -> typing.Collection[gunsmith.Weapon]:
        if self._noClicked:
            return []

        weapons = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            if not item or item.checkState() != QtCore.Qt.CheckState.Checked:
                continue
            weapon = item.data(QtCore.Qt.ItemDataRole.UserRole)
            weapons.append(weapon)
        return weapons

    def _yesButtonClicked(self) -> None:
        self._noClicked = False
        self.accept()

    def _noButtonClicked(self) -> None:
        self._noClicked = True
        self.accept()
