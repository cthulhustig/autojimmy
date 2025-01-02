import app
import gui
import traveller
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

        self._hexSelectWidget = gui.HexSearchWidget()
        self._hexSelectWidget.selectionChanged.connect(self._selectionChanged)

        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDisabled(not self._hexSelectWidget.selectedHex())
        self._okButton.setDefault(True)
        self._okButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._okButton)
        buttonLayout.addWidget(self._cancelButton)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._hexSelectWidget)
        windowLayout.addLayout(buttonLayout)

        self.setLayout(windowLayout)

    def selectedHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._hexSelectWidget.selectedHex()

    def setSelectedHex(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._hexSelectWidget.setSelectedHex(hex=hex)

    # Helper to get the selected world if a world is selected. Useful for code
    # that never enables dead space selection
    def selectedWorld(self) -> typing.Optional[traveller.World]:
        return self._hexSelectWidget.selectedWorld()

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        self._hexSelectWidget.enableDeadSpaceSelection(enable=enable)

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._hexSelectWidget.isDeadSpaceSelectionEnabled()

    # There is intentionally no saveSettings implementation as saving is only done if the user clicks ok
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)
        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SelectWorldState',
            type=QtCore.QByteArray)
        if storedValue:
            self._hexSelectWidget.restoreState(storedValue)
        self._settings.endGroup()

    def accept(self) -> None:
        hex = self.selectedHex()
        if not hex:
            return # A valid hex must be selected to accept

        # Add the selected hex to the selection history
        app.HexHistory.instance().addHex(hex=hex)

        self._settings.beginGroup(self._configSection)
        self._settings.setValue('SelectWorldState', self._hexSelectWidget.saveState())
        self._settings.endGroup()

        super().accept()

    def _selectionChanged(self) -> None:
        self._okButton.setDisabled(not self._hexSelectWidget.selectedHex())
