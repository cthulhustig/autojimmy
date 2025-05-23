import app
import gui
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class HexSelectDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Hex Select',
            configSection='HexSelectDialog',
            parent=parent)

        milieu = app.Config.instance().value(option=app.ConfigOption.Milieu)
        rules = app.Config.instance().value(option=app.ConfigOption.Rules)
        mapStyle = app.Config.instance().value(option=app.ConfigOption.MapStyle)
        mapOptions = app.Config.instance().value(option=app.ConfigOption.MapOptions)
        mapRendering = app.Config.instance().value(option=app.ConfigOption.MapRendering)
        mapAnimations = app.Config.instance().value(option=app.ConfigOption.MapAnimations)
        app.Config.instance().configChanged.connect(self._appConfigChanged)

        self._mapWidget = gui.MapWidgetEx(
            milieu=milieu,
            rules=rules,
            style=mapStyle,
            options=mapOptions,
            rendering=mapRendering,
            animated=mapAnimations)
        self._mapWidget.setInfoEnabled(False) # Disable by default
        self._mapWidget.setSelectionMode(gui.MapWidgetEx.SelectionMode.MultiSelect)
        self._mapWidget.mapStyleChanged.connect(self._mapStyleChanged)
        self._mapWidget.mapOptionsChanged.connect(self._mapOptionsChanged)
        self._mapWidget.mapRenderingChanged.connect(self._mapRenderingChanged)
        self._mapWidget.mapAnimationChanged.connect(self._mapAnimationChanged)

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

    def selectedHexes(self) -> typing.Iterable[travellermap.HexPosition]:
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

    # TODO: Is this actually getting hit.
    def closeEvent(self, event: QtGui.QCloseEvent):
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
            # TODO: If dead space selection is NOT enabled, some of the selection
            # may now be invalid
        elif option is app.ConfigOption.Rules:
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
