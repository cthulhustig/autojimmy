import gui
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

class HexSelectDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Hex Select',
            configSection='HexSelectDialog',
            parent=parent)

        self._mapWidget = gui.MapWidgetEx()
        self._mapWidget.setInfoEnabled(False) # Disable by default
        self._mapWidget.setSelectionMode(gui.MapWidgetEx.SelectionMode.MultiSelect)

        self._label = QtWidgets.QLabel()

        self._okButton = QtWidgets.QPushButton('OK')
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
        windowLayout.addWidget(self._label, 0)
        windowLayout.addWidget(self._mapWidget, 1)
        windowLayout.addLayout(buttonLayout, 0)

        self.setLayout(windowLayout)
        self.resize(640, 480)
        self.showMaximizeButton()

        self._updateLabel()

    def selectedHexes(self) -> typing.Iterable[traveller.World]:
        return self._mapWidget.selectedHexes()

    def selectHex(
            self,
            hex: travellermap.HexPosition,
            centerOnHex: bool = True,
            setInfoHex: bool = True
            ) -> None:
        self._mapWidget.selectHex(
            hex=hex,
            setInfoHex=setInfoHex)
        if centerOnHex:
            self._mapWidget.centerOnHex(
                hex=hex,
                immediate=self.isHidden())

    def deselectHex(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        self._mapWidget.deselectHex(hex=hex)

    def clearSelectedHexes(self) -> None:
        self._mapWidget.clearSelectedHexes()

    def configureSelection(
            self,
            singleSelect: bool,
            includeDeadSpace: bool = False
            ) -> None:
        self._mapWidget.setSelectionMode(
            gui.MapWidgetEx.SelectionMode.SingleSelect \
            if singleSelect else \
            gui.MapWidgetEx.SelectionMode.MultiSelect)
        self._mapWidget.enableDeadSpaceSelection(enable=includeDeadSpace)
        self._updateLabel()

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='MapWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mapWidget.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('MapWidgetState', self._mapWidget.saveState())
        self._settings.endGroup()

        super().saveSettings()

    def _updateLabel(self) -> None:
        isWorld = not self._mapWidget.isDeadSpaceSelectionEnabled()
        isSingular = self._mapWidget.selectionMode() == gui.MapWidgetEx.SelectionMode.SingleSelect
        if isWorld:
            wording = 'world' if isSingular else 'worlds'
        else:
            wording = 'hex' if isSingular else 'hexes'

        self._label.setText(
            'Click on the {wording} you want to select or deselect.'.format(
                wording=wording))
