import app
import gui
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

class NearbyWorldsDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Nearby World Search',
            configSection='NearbyWorldDialog',
            parent=parent)

        self._selectWorldWidget = gui.WorldSearchWidget()
        self._selectWorldWidget.selectionChanged.connect(self._selectionChanged)

        self._selectRadiusSpinBox = gui.SpinBoxEx()
        self._selectRadiusSpinBox.setRange(app.MinPossibleJumpRating, app.MaxSearchRadius)
        self._selectRadiusSpinBox.setValue(2)

        selectionRadiusLayout = QtWidgets.QHBoxLayout()
        selectionRadiusLayout.setContentsMargins(0, 0, 0, 0)
        selectionRadiusLayout.addWidget(QtWidgets.QLabel('Selection Radius (Parsecs): '))
        selectionRadiusLayout.addWidget(self._selectRadiusSpinBox)

        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDisabled(not self._selectWorldWidget.world())
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
        windowLayout.addWidget(self._selectWorldWidget)
        windowLayout.addLayout(selectionRadiusLayout)
        windowLayout.addLayout(buttonLayout)

        self.setLayout(windowLayout)

    # There is intentionally no saveSettings implementation as saving is only done if the user clicks ok
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)
        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SelectWorldState',
            type=QtCore.QByteArray)
        if storedValue:
            self._selectWorldWidget.restoreState(storedValue)
        self._settings.endGroup()

        self._settings.beginGroup(self._configSection)
        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SelectRadiusState',
            type=QtCore.QByteArray)
        if storedValue:
            self._selectRadiusSpinBox.restoreState(storedValue)
        self._settings.endGroup()

    def world(self) -> typing.Optional[traveller.World]:
        return self._selectWorldWidget.world()

    def setWorld(self, world: typing.Optional[traveller.World]) -> None:
        self._selectWorldWidget.setWorld(world)

    def searchRadius(self) -> int:
        return self._selectRadiusSpinBox.value()

    def accept(self) -> None:
        world = self.world()
        if not world:
            return # A valid world must be selected to accept

        # Add the selected world to the recently used list
        app.RecentWorlds.instance().addWorld(world)

        self._settings.beginGroup(self._configSection)
        self._settings.setValue('SelectWorldState', self._selectWorldWidget.saveState())
        self._settings.setValue('SelectRadiusState', self._selectRadiusSpinBox.saveState())
        self._settings.endGroup()

        super().accept()

    def _selectionChanged(self) -> None:
        self._okButton.setDisabled(not self._selectWorldWidget.world())
