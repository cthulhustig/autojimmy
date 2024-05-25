import construction
import gui
import typing
from PyQt5 import QtWidgets, QtCore

class ConstructableSelectDialog(gui.DialogEx):
    def __init__(
            self,
            title: str,
            constructables: typing.Collection[construction.ConstructableInterface],
            text: typing.Optional[str] = None,
            defaultState: QtCore.Qt.CheckState = QtCore.Qt.CheckState.Unchecked,
            showYesNoCancel: bool = False,
            configSection: typing.Optional[str] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title=title,
            configSection=configSection,
            parent=parent)

        self._noClicked = False

        label = QtWidgets.QLabel(text) if text else None

        self._list = gui.ListWidgetEx()
        for constructable in constructables:
            item = gui.NaturalSortListWidgetItem()
            item.setData(QtCore.Qt.ItemDataRole.DisplayRole, constructable.name())
            item.setData(QtCore.Qt.ItemDataRole.UserRole, constructable)
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

    def selected(self) -> typing.Collection[construction.ConstructableInterface]:
        if self._noClicked:
            return []

        constructables = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            if not item or item.checkState() != QtCore.Qt.CheckState.Checked:
                continue
            constructable = item.data(QtCore.Qt.ItemDataRole.UserRole)
            constructables.append(constructable)
        return constructables

    def _yesButtonClicked(self) -> None:
        self._noClicked = False
        self.accept()

    def _noButtonClicked(self) -> None:
        self._noClicked = True
        self.accept()
