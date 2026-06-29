import app
import astronomer
import azathoth
import common
import gui
import logging
import multiverse
import os
import survey
import traveller
import typing
from PyQt5 import QtCore, QtWidgets, QtGui

class CreateUniverseDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Create Universe',
            configSection='CreateUniverseDialog',
            parent=parent)

        self._setupDialogButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)

    def _setupDialogButtons(self) -> None:
        self._createButton = QtWidgets.QPushButton('Create')
        self._createButton.setDefault(True)
        self._createButton.clicked.connect(self._createClicked)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._createButton)
        self._buttonLayout.addWidget(self._cancelButton)

    def _createClicked(self) -> None:
        pass