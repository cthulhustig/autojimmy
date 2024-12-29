import app
import gui
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

class HexSearchDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='World/Hex Search',
            # TODO: I probably want to leave this config item as it is to save backward
            # comparability
            configSection='WorldSearchDialog',
            parent=parent)

        self._searchWidget = gui.HexSearchWidget()
        self._searchWidget.selectionChanged.connect(self._selectionChanged)

        self._selectButton = QtWidgets.QPushButton('Select')
        self._selectButton.setDisabled(not self._searchWidget.selectedHex())
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
        windowLayout.addWidget(self._searchWidget)
        windowLayout.addLayout(buttonLayout)

        self.setLayout(windowLayout)

    def selectedHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._searchWidget.selectedHex()

    def setSelectedHex(
            self,
            pos: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._searchWidget.setSelectedHex(pos=pos)

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        self._searchWidget.enableDeadSpaceSelection(enable=enable)

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._searchWidget.isDeadSpaceSelectionEnabled()

    # There is intentionally no saveSettings implementation as saving is only done if the user clicks ok
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)
        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SelectWorldState',
            type=QtCore.QByteArray)
        if storedValue:
            self._searchWidget.restoreState(storedValue)
        self._settings.endGroup()

    def accept(self) -> None:
        pos = self.selectedHex()
        if not pos:
            return # A valid hex must be selected to accept

        # Add the selected hex to the selection history
        app.HexHistory.instance().addHex(pos=pos)

        self._settings.beginGroup(self._configSection)
        self._settings.setValue('SelectWorldState', self._searchWidget.saveState())
        self._settings.endGroup()

        super().accept()

    def _selectionChanged(self) -> None:
        self._selectButton.setDisabled(not self._searchWidget.hackSelectedWorld())
