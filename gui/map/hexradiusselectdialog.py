import app
import gui
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class HexRadiusSelectDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Radius Select',
            configSection='HexRadiusSelectDialog',
            parent=parent)

        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(app.ConfigOption.MapStyle)
        mapOptions = set(app.Config.instance().value(option=app.ConfigOption.MapOptions)) # Convert to set for speed
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        app.Config.instance().configChanged.connect(self._appConfigChanged)

        self._overlays: typing.List[str] = []
        self._selectedHexes: typing.List[travellermap.HexPosition] = []

        self._radiusSpinBox = gui.SpinBoxEx()
        self._radiusSpinBox.setRange(app.MinPossibleJumpRating, app.MaxSearchRadius)
        self._radiusSpinBox.setValue(2)
        self._radiusSpinBox.valueChanged.connect(self._updateOverlay)

        self._includeDeadSpaceCheckBox = gui.CheckBoxEx('Include Dead Space: ')
        self._includeDeadSpaceCheckBox.setTextOnLeft(True)
        self._includeDeadSpaceCheckBox.setHidden(True)
        self._includeDeadSpaceCheckBox.stateChanged.connect(self._updateOverlay)

        selectionRadiusLayout = QtWidgets.QHBoxLayout()
        selectionRadiusLayout.setContentsMargins(0, 0, 0, 0)
        selectionRadiusLayout.addWidget(QtWidgets.QLabel('Selection Radius (Parsecs): '))
        selectionRadiusLayout.addWidget(self._radiusSpinBox)
        selectionRadiusLayout.addWidget(self._includeDeadSpaceCheckBox)
        selectionRadiusLayout.addStretch()

        self._mapWidget = gui.MapWidgetEx(
            milieu=milieu,
            rules=rules,
            style=mapStyle,
            options=mapOptions,
            rendering=mapRendering,
            animated=mapAnimations)
        self._mapWidget.setSelectionMode(
            mode=gui.MapWidgetEx.SelectionMode.SingleSelect)
        # Always enable dead space selection on the map as, even if dead space selection
        # is disabled at the dialog level, the user should be able to select a dead space
        # hex and have the worlds around it selected
        self._mapWidget.enableDeadSpaceSelection(enable=True)
        self._mapWidget.selectionChanged.connect(self._updateOverlay)
        self._mapWidget.mapStyleChanged.connect(self._mapStyleChanged)
        self._mapWidget.mapOptionsChanged.connect(self._mapOptionsChanged)
        self._mapWidget.mapRenderingChanged.connect(self._mapRenderingChanged)
        self._mapWidget.mapAnimationChanged.connect(self._mapAnimationChanged)

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

        self._updateOverlay()

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

        self._updateOverlay()

    def searchRadius(self) -> int:
        return self._radiusSpinBox.value()

    def setSearchRadius(self, radius: int) -> None:
        if radius == self.searchRadius():
            return # Nothing to do

        with gui.SignalBlocker(self._mapWidget):
            self._radiusSpinBox.setValue(radius)

        self._updateOverlay()

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        self._includeDeadSpaceCheckBox.setHidden(not enable)
        self._updateOverlay()

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

    # TODO: Is this actually getting hit.
    def closeEvent(self, event: QtGui.QCloseEvent):
        self._mapWidget.selectionChanged.disconnect(self._updateOverlay)
        self._mapWidget.mapStyleChanged.disconnect(self._mapStyleChanged)
        self._mapWidget.mapOptionsChanged.disconnect(self._mapOptionsChanged)
        self._mapWidget.mapRenderingChanged.disconnect(self._mapRenderingChanged)
        self._mapWidget.mapAnimationChanged.disconnect(self._mapAnimationChanged)

        app.Config.instance().configChanged.disconnect(self._appConfigChanged)

        return super().closeEvent(event)

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.Milieu:
            self._mapWidget.setMilieu(milieu=newValue)
            self._updateOverlay()
        if option is app.ConfigOption.Rules:
            self._mapWidget.setRules(rules=newValue)
        elif option is app.ConfigOption.MapStyle:
            self._mapWidget.setStyle(style=newValue)
        elif option is app.ConfigOption.MapOptions:
            self._mapWidget.setOptions(options=newValue)
        elif option is app.ConfigOption.MapRendering:
            self._mapWidget.setRendering(rendering=newValue)
        elif option is app.ConfigOption.MapAnimations:
            self._mapWidget.setAnimation(enabled=newValue)

    def _mapStyleChanged(
            self,
            style: travellermap.Style
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapStyle,
            value=style)

    def _mapOptionsChanged(
            self,
            options: typing.Iterable[travellermap.Option]
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapOptions,
            value=options)

    def _mapRenderingChanged(
            self,
            renderingType: app.MapRendering,
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapRendering,
            value=renderingType)

    def _mapAnimationChanged(
            self,
            animations: bool
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapAnimations,
            value=animations)

    def _updateOverlay(self) -> None:
        self._selectedHexes.clear()
        for handle in self._overlays:
            self._mapWidget.removeOverlay(handle)
        self._overlays.clear()

        centerHex = self.centerHex()
        if centerHex:
            searchRadius = self.searchRadius()
            selectionColour = self._mapWidget.selectionFillColour()
            radiusColour = self._mapWidget.selectionOutlineColour()

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
                        milieu=app.Config.instance().value(option=app.ConfigOption.Milieu),
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
                lineWidth=gui.MapWidgetEx._SelectionOutlineWidth)
            self._overlays.append(handle)

        self._okButton.setDisabled(not self._selectedHexes)
