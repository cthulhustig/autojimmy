import gui
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

class TravellerMapSelectDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Traveller Map World Select',
            configSection='TravellerMapSelectDialog',
            parent=parent)

        self._mapWidget = gui.TravellerMapWidget()
        self._mapWidget.setInfoEnabled(False) # Disable by default
        self._mapWidget.setSelectionMode(gui.TravellerMapWidget.SelectionMode.MultiSelect)

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
        windowLayout.addWidget(QtWidgets.QLabel('Click on the worlds you want to select or deselect.'), 0)
        windowLayout.addWidget(self._mapWidget, 1)
        windowLayout.addLayout(buttonLayout, 0)

        self.setLayout(windowLayout)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint, True)

    def selectedWorlds(self) -> typing.Iterable[traveller.World]:
        return self._mapWidget.selectedWorlds()

    def selectWorld(
            self,
            world: traveller.World,
            centerOnWorld: bool = True,
            setInfoWorld: bool = True
            ) -> None:
        self._mapWidget.selectWorld(
            world=world,
            centerOnWorld=centerOnWorld,
            setInfoWorld=setInfoWorld)

    def deselectWorld(
            self,
            world: traveller.World
            ) -> None:
        self._mapWidget.deselectWorld(world=world)

    def setSelectedWorlds(
            self,
            worlds: typing.Iterable[traveller.World],
            centerOnWorlds: bool = True
            ) -> None:
        self._mapWidget.clearSelectedWorlds()
        for world in worlds:
            self._mapWidget.selectWorld(
                world=world,
                centerOnWorld=False)
        if centerOnWorlds:
            self._mapWidget.centerOnWorlds(worlds=worlds)

    def setSingleSelect(
            self,
            singleSelect: bool
            ) -> None:
        self._mapWidget.setSelectionMode(
            gui.TravellerMapWidget.SelectionMode.SingleSelect \
            if singleSelect else \
            gui.TravellerMapWidget.SelectionMode.MultiSelect)

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
