import app
import gui
import logic
import traveller
import multiverse
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class HexSelectDialog(gui.DialogEx):
    def __init__(
            self,
            milieu: multiverse.Milieu,
            rules: traveller.Rules,
            mapStyle: multiverse.MapStyle,
            mapOptions: typing.Iterable[multiverse.MapOption],
            mapRendering: app.MapRendering,
            mapAnimations: bool,
            worldTagging: logic.WorldTagging,
            taggingColours: app.TaggingColours,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Hex Select',
            configSection='HexSelectDialog',
            parent=parent)

        self._mapWidget = gui.MapWidgetEx(
            milieu=milieu,
            rules=rules,
            style=mapStyle,
            options=mapOptions,
            rendering=mapRendering,
            animated=mapAnimations,
            worldTagging=worldTagging,
            taggingColours=taggingColours)
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

        # Load settings at initialisation rather than in loadSettings so the code
        # that created the dialog can specify it's own settings rather than using
        # the stored ones without having to create a derived class. If it was done
        # in loadSettings any settings the user applied after constructing the
        # dialog would be overwritten when exec was called and the dialog was shown.
        self._settings.beginGroup(self._configSection)
        storedValue = gui.safeLoadSetting(settings=self._settings, key='MapWidgetState', type=QtCore.QByteArray)
        if storedValue:
            self._mapWidget.restoreState(storedValue)
        self._settings.endGroup()

        self._updateLabel()

    def selectedHexes(self) -> typing.Iterable[multiverse.HexPosition]:
        return self._mapWidget.selectedHexes()

    def selectHex(
            self,
            hex: multiverse.HexPosition,
            setInfoHex: bool = True
            ) -> None:
        self._mapWidget.selectHex(
            hex=hex,
            setInfoHex=setInfoHex)

    def deselectHex(
            self,
            hex: multiverse.HexPosition
            ) -> None:
        self._mapWidget.deselectHex(hex=hex)

    def selectHexes(
            self,
            hexes: typing.Iterable[multiverse.HexPosition]
            ) -> None:
        self._mapWidget.selectHexes(hexes=hexes)

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

    def accept(self) -> None:
        # Only8 update saved state if ok is clicked
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('MapWidgetState', self._mapWidget.saveState())
        self._settings.endGroup()

        super().accept()

    def firstShowEvent(self, e):
        super().firstShowEvent(e)

        # Center the map on the current selection. This is done here as the
        # zoom is calculated based on the current size of the map widget so
        # it needs to be done after the initial size has been calculated.
        selection = self.selectedHexes()
        if selection:
            if self._mapWidget.selectionMode() is gui.MapWidgetEx.SelectionMode.SingleSelect:
                self._mapWidget.centerOnHex(
                    hex=selection[0],
                    immediate=True)
            else:
                self._mapWidget.centerOnHexes(
                    hexes=selection,
                    immediate=True)

    def _mapStyleChanged(
            self,
            style: multiverse.MapStyle
            ) -> None:
        app.Config.instance().setValue(
            option=app.ConfigOption.MapStyle,
            value=style)

    def _mapOptionsChanged(
            self,
            options: typing.Iterable[multiverse.MapOption]
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
