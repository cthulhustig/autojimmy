import app
import gui
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

class HexRadiusSelectDialog(gui.DialogEx):
    _RadiusOverlayDarkStyleColour = '#0000FF'
    _RadiusOverlayLightStyleColour = '#0000FF'
    _SelectionOverlayDarkStyleColour = '#9D03FC'
    _SelectionOverlayLightStyleColour = '#4A03FC'
    _OverlayLineWidth = 6

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
        self._enableDeadSpaceSelection = False

        self._radiusSpinBox = gui.SpinBoxEx()
        self._radiusSpinBox.setRange(app.MinPossibleJumpRating, app.MaxSearchRadius)
        self._radiusSpinBox.setValue(2)
        self._radiusSpinBox.valueChanged.connect(self._handleConfigChange)

        selectionRadiusLayout = QtWidgets.QHBoxLayout()
        selectionRadiusLayout.setContentsMargins(0, 0, 0, 0)
        selectionRadiusLayout.addWidget(QtWidgets.QLabel('Selection Radius (Parsecs): '))
        selectionRadiusLayout.addWidget(self._radiusSpinBox)
        selectionRadiusLayout.addStretch()

        self._travellerMapWidget = gui.TravellerMapWidget()
        self._travellerMapWidget.setSelectionMode(
            mode=gui.TravellerMapWidget.SelectionMode.SingleSelect)
        # Always enable dead space selection on the map as, even if dead space selection
        # is disabled at the dialog level, the user should be able to select a dead space
        # hex and have the worlds around it selected
        self._travellerMapWidget.enableDeadSpaceSelection(enable=True)
        self._travellerMapWidget.selectionChanged.connect(self._handleConfigChange)

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
        windowLayout.addWidget(self._travellerMapWidget)
        windowLayout.addLayout(buttonLayout)

        self.setLayout(windowLayout)

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
            self._travellerMapWidget.restoreState(storedValue)
        self._settings.endGroup()

        self._settings.beginGroup(self._configSection)
        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SelectRadiusState',
            type=QtCore.QByteArray)
        if storedValue:
            self._radiusSpinBox.restoreState(storedValue)
        self._settings.endGroup()

    def selectedHexes(self) -> typing.Collection[travellermap.HexPosition]:
        return list(self._selectedHexes)

    def centerHex(self) -> typing.Optional[travellermap.HexPosition]:
        selection = self._travellerMapWidget.selectedHexes()
        return selection[0] if selection else None

    def setCenterHex(self, hex: typing.Optional[travellermap.HexPosition]) -> None:
        if hex == self.centerHex():
            return # Nothing to do

        with gui.SignalBlocker(self._travellerMapWidget):
            if hex:
                self._travellerMapWidget.selectHex(
                    hex=hex,
                    centerOnHex=True)
            else:
                self._travellerMapWidget.clearSelectedHexes()

        self._handleConfigChange()

    def searchRadius(self) -> int:
        return self._radiusSpinBox.value()

    def setSearchRadius(self, radius: int) -> None:
        if radius == self.searchRadius():
            return # Nothing to do

        with gui.SignalBlocker(self._travellerMapWidget):
            self._radiusSpinBox.setValue(radius)

        self._handleConfigChange()

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        if enable == self._enableDeadSpaceSelection:
            return # Nothing to do

        self._enableDeadSpaceSelection = enable
        self._handleConfigChange()

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._enableDeadSpaceSelection

    def accept(self) -> None:
        hex = self.centerHex()
        if not hex:
            return # A valid hex must be selected to accept

        # Add the selected hex to the selection history
        app.HexHistory.instance().addHex(hex=hex)

        self._settings.beginGroup(self._configSection)
        self._settings.setValue('SelectHexState', self._travellerMapWidget.saveState())
        self._settings.setValue('SelectRadiusState', self._radiusSpinBox.saveState())
        self._settings.endGroup()

        super().accept()

    def _handleConfigChange(self) -> None:
        self._selectedHexes.clear()
        for handle in self._overlays:
            self._travellerMapWidget.removeOverlayGroup(handle)
        self._overlays.clear()

        centerHex = self.centerHex()
        if centerHex:
            searchRadius = self.searchRadius()

            isDarkMapStyle = travellermap.isDarkStyle(
                style=app.Config.instance().mapStyle())
            if isDarkMapStyle:
                radiusColour = HexRadiusSelectDialog._RadiusOverlayDarkStyleColour
                selectionColour = HexRadiusSelectDialog._SelectionOverlayDarkStyleColour
            else:
                radiusColour = HexRadiusSelectDialog._RadiusOverlayLightStyleColour
                selectionColour = HexRadiusSelectDialog._SelectionOverlayLightStyleColour

            if self._enableDeadSpaceSelection:
                for hex in centerHex.yieldRadiusHexes(radius=searchRadius):
                    self._selectedHexes.append(hex)

                handle = self._travellerMapWidget.createHexRadiusOverlayGroup(
                    center=centerHex,
                    radius=searchRadius,
                    fillColour=selectionColour)
                self._overlays.append(handle)
            else:
                try:
                    worlds = traveller.WorldManager.instance().worldsInArea(
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
                    handle = self._travellerMapWidget.createHexBorderOverlayGroup(
                        hexes=self._selectedHexes,
                        fillColour=selectionColour)
                    self._overlays.append(handle)

            handle = self._travellerMapWidget.createHexRadiusOverlayGroup(
                center=centerHex,
                radius=searchRadius,
                lineColour=radiusColour,
                lineWidth=HexRadiusSelectDialog._OverlayLineWidth)
            self._overlays.append(handle)

        self._okButton.setDisabled(not self._selectedHexes)
