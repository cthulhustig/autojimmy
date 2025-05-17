import app
import gui
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

class HexRadiusSelectDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Radius Select',
            configSection='HexRadiusSelectDialog',
            parent=parent)

        self._overlays: typing.List[str] = []
        self._selectedHexes: typing.List[travellermap.HexPosition] = []

        self._radiusSpinBox = gui.SpinBoxEx()
        self._radiusSpinBox.setRange(app.MinPossibleJumpRating, app.MaxSearchRadius)
        self._radiusSpinBox.setValue(2)
        self._radiusSpinBox.valueChanged.connect(self._handleConfigChange)

        self._includeDeadSpaceCheckBox = gui.CheckBoxEx('Include Dead Space: ')
        self._includeDeadSpaceCheckBox.setTextOnLeft(True)
        self._includeDeadSpaceCheckBox.setHidden(True)
        self._includeDeadSpaceCheckBox.stateChanged.connect(self._handleConfigChange)

        selectionRadiusLayout = QtWidgets.QHBoxLayout()
        selectionRadiusLayout.setContentsMargins(0, 0, 0, 0)
        selectionRadiusLayout.addWidget(QtWidgets.QLabel('Selection Radius (Parsecs): '))
        selectionRadiusLayout.addWidget(self._radiusSpinBox)
        selectionRadiusLayout.addWidget(self._includeDeadSpaceCheckBox)
        selectionRadiusLayout.addStretch()

        self._mapWidget = gui.MapWidgetEx()
        self._mapWidget.setSelectionMode(
            mode=gui.MapWidgetEx.SelectionMode.SingleSelect)
        # Always enable dead space selection on the map as, even if dead space selection
        # is disabled at the dialog level, the user should be able to select a dead space
        # hex and have the worlds around it selected
        self._mapWidget.enableDeadSpaceSelection(enable=True)
        self._mapWidget.selectionChanged.connect(self._handleConfigChange)
        self._mapWidget.displayOptionsChanged.connect(self._handleConfigChange)

        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDisabled(False)
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
        windowLayout.addLayout(selectionRadiusLayout)
        windowLayout.addWidget(self._mapWidget)
        windowLayout.addLayout(buttonLayout)

        self.setLayout(windowLayout)
        self.resize(640, 480)
        self.showMaximizeButton()

        self._handleConfigChange()

    # There is intentionally no saveSettings implementation as saving is only done if the user clicks ok
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SelectHexState',
            type=QtCore.QByteArray)
        if storedValue:
            self._mapWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SelectRadiusState',
            type=QtCore.QByteArray)
        if storedValue:
            self._radiusSpinBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='IncludeDeadSpaceState',
            type=QtCore.QByteArray)
        if storedValue:
            self._includeDeadSpaceCheckBox.restoreState(storedValue)

        self._settings.endGroup()

    def selectedHexes(self) -> typing.Collection[travellermap.HexPosition]:
        return list(self._selectedHexes)

    def centerHex(self) -> typing.Optional[travellermap.HexPosition]:
        selection = self._mapWidget.selectedHexes()
        return selection[0] if selection else None

    def setCenterHex(self, hex: typing.Optional[travellermap.HexPosition]) -> None:
        if hex == self.centerHex():
            return # Nothing to do

        with gui.SignalBlocker(self._mapWidget):
            if hex:
                self._mapWidget.selectHex(hex=hex)
                self._mapWidget.centerOnHex(
                    hex=hex,
                    immediate=self.isHidden())
            else:
                self._mapWidget.clearSelectedHexes()

        self._handleConfigChange()

    def searchRadius(self) -> int:
        return self._radiusSpinBox.value()

    def setSearchRadius(self, radius: int) -> None:
        if radius == self.searchRadius():
            return # Nothing to do

        with gui.SignalBlocker(self._mapWidget):
            self._radiusSpinBox.setValue(radius)

        self._handleConfigChange()

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        self._includeDeadSpaceCheckBox.setHidden(not enable)
        self._handleConfigChange()

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return not self._includeDeadSpaceCheckBox.isHidden()

    def accept(self) -> None:
        hex = self.centerHex()
        if not hex:
            return # A valid hex must be selected to accept

        # Add the selected hex to the selection history
        app.HexHistory.instance().addHex(hex=hex)

        self._settings.beginGroup(self._configSection)
        self._settings.setValue('SelectHexState', self._mapWidget.saveState())
        self._settings.setValue('SelectRadiusState', self._radiusSpinBox.saveState())
        self._settings.setValue('IncludeDeadSpaceState', self._includeDeadSpaceCheckBox.saveState())
        self._settings.endGroup()

        super().accept()

    def _handleConfigChange(self) -> None:
        self._selectedHexes.clear()
        for handle in self._overlays:
            self._mapWidget.removeOverlay(handle)
        self._overlays.clear()

        centerHex = self.centerHex()
        if centerHex:
            searchRadius = self.searchRadius()
            selectionColour = gui.MapWidgetEx.selectionFillColour()
            radiusColour = gui.MapWidgetEx.selectionOutlineColour()
            radiusWidth = gui.MapWidgetEx.selectionOutlineWidth()

            includeDeadSpace = not self._includeDeadSpaceCheckBox.isHidden() and \
                self._includeDeadSpaceCheckBox.isChecked()

            if includeDeadSpace:
                for hex in centerHex.yieldRadiusHexes(radius=searchRadius):
                    self._selectedHexes.append(hex)

                handle = self._mapWidget.createRadiusOverlay(
                    center=centerHex,
                    radius=searchRadius,
                    fillColour=selectionColour)
                self._overlays.append(handle)
            else:
                try:
                    worlds = traveller.WorldManager.instance().worldsInRadius(
                        milieu=app.Config.instance().asEnum(
                            option=app.ConfigOption.Milieu,
                            enumType=travellermap.Milieu),
                        center=centerHex,
                        searchRadius=searchRadius)
                    for world in worlds:
                        self._selectedHexes.append(world.hex())
                except Exception as ex:
                    message = 'Failed to find worlds in area'
                    logging.error(message, exc_info=ex)
                    gui.MessageBoxEx.critical(
                        parent=self,
                        text=message,
                        exception=ex)

                if self._selectedHexes:
                    handle = self._mapWidget.createHexOverlay(
                        hexes=self._selectedHexes,
                        primitive=gui.MapPrimitiveType.Hex,
                        fillColour=selectionColour)
                    self._overlays.append(handle)

            handle = self._mapWidget.createRadiusOverlay(
                center=centerHex,
                radius=searchRadius,
                lineColour=radiusColour,
                lineWidth=radiusWidth)
            self._overlays.append(handle)

        self._okButton.setDisabled(not self._selectedHexes)
