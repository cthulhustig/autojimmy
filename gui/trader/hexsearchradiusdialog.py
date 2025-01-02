import app
import gui
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

# TODO: Rename this to HexRadiusSelectDialog
# - Do this after I've renamed what is currently HexSelectComboBox & HexSelectToolWidget
# TODO: This dialog should work differently
# - When you select a hex in traveller map it should show you the world in the current radius
#   - This would mean logically the radius should be above the map widget
#   - When you click ok it should be possible to pull back the selected hexes from the dialog
# - I'm not sure if the offline mode actually makes sense
class HexSearchRadiusDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Search Radius',
            configSection='HexSearchRadiusDialog',
            parent=parent)

        self._hexWidget = gui.HexSearchWidget()
        self._hexWidget.enableDeadSpaceSelection(enable=True)
        self._hexWidget.selectionChanged.connect(self._selectionChanged)

        self._radiusSpinBox = gui.SpinBoxEx()
        self._radiusSpinBox.setRange(app.MinPossibleJumpRating, app.MaxSearchRadius)
        self._radiusSpinBox.setValue(2)

        selectionRadiusLayout = QtWidgets.QHBoxLayout()
        selectionRadiusLayout.setContentsMargins(0, 0, 0, 0)
        selectionRadiusLayout.addWidget(QtWidgets.QLabel('Selection Radius (Parsecs): '))
        selectionRadiusLayout.addWidget(self._radiusSpinBox)

        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDisabled(not self._hexWidget.selectedHex())
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
        windowLayout.addWidget(self._hexWidget)
        windowLayout.addLayout(selectionRadiusLayout)
        windowLayout.addLayout(buttonLayout)

        self.setLayout(windowLayout)

    # There is intentionally no saveSettings implementation as saving is only done if the user clicks ok
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)
        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SelectHexState',
            type=QtCore.QByteArray)
        if storedValue:
            self._hexWidget.restoreState(storedValue)
        self._settings.endGroup()

        self._settings.beginGroup(self._configSection)
        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SelectRadiusState',
            type=QtCore.QByteArray)
        if storedValue:
            self._radiusSpinBox.restoreState(storedValue)
        self._settings.endGroup()

    def centerHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._hexWidget.selectedHex()

    def setCenterHex(self, hex: typing.Optional[travellermap.HexPosition]) -> None:
        self._hexWidget.setSelectedHex(hex=hex)

    def searchRadius(self) -> int:
        return self._radiusSpinBox.value()

    def setSearchRadius(self, radius: int) -> None:
        self._radiusSpinBox.setValue(radius)

    def accept(self) -> None:
        hex = self.centerHex()
        if not hex:
            return # A valid hex must be selected to accept

        # Add the selected hex to the selection history
        app.HexHistory.instance().addHex(hex=hex)

        self._settings.beginGroup(self._configSection)
        self._settings.setValue('SelectHexState', self._hexWidget.saveState())
        self._settings.setValue('SelectRadiusState', self._radiusSpinBox.saveState())
        self._settings.endGroup()

        super().accept()

    def _selectionChanged(self) -> None:
        self._okButton.setDisabled(not self._hexWidget.selectedHex())
