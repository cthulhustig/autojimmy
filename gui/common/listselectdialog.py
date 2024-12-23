import gui
import typing
from PyQt5 import QtWidgets, QtCore

class ListSelectDialog(gui.DialogEx):
    def __init__(
            self,
            title: str,
            selectable: typing.Collection[str],
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
        for name in selectable:
            item = gui.NaturalSortListWidgetItem()
            item.setData(QtCore.Qt.ItemDataRole.DisplayRole, name)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(defaultState)
            self._list.addItem(item)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()

        confirmButton = QtWidgets.QPushButton('Yes' if showYesNoCancel else 'OK')
        confirmButton.setDefault(True)
        confirmButton.clicked.connect(self.accept)
        buttonLayout.addWidget(confirmButton)

        if showYesNoCancel:
            noButton = QtWidgets.QPushButton('No')
            noButton.clicked.connect(self._noButtonClicked)
            buttonLayout.addWidget(noButton)

        cancelButton = QtWidgets.QPushButton('Cancel')
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(cancelButton)

        dialogLayout = QtWidgets.QVBoxLayout()
        if label:
            dialogLayout.addWidget(label)
        dialogLayout.addWidget(self._list)
        dialogLayout.addLayout(buttonLayout)

        self.setLayout(dialogLayout)

    def selected(self) -> typing.Collection[str]:
        if self._noClicked:
            return []

        selected = []
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item and item.checkState() == QtCore.Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

    def _noButtonClicked(self) -> None:
        self._noClicked = True
        self.accept()
