import app
import gui
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

# TODO: The tooltips of widgets should update to say world/hex depending on if dead
# space selection is enabled
class WorldSelectToolWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()
    showHex = QtCore.pyqtSignal(travellermap.HexPosition)

    # TODO: I suspect this class will be renamed to HexSelectWidget but I might need
    # to keep this state so users don't loose the last selected world
    _StateVersion = 'WorldSelectWidget_v1'

    # The hex select combo box has a minimum width applied to stop it becoming
    # stupidly small. This min size isn't expected to be big enough for all
    # world names
    _MinWoldSelectWidth = 150

    def __init__(
            self,
            text: typing.Optional[str] = 'Select World:',
            world: typing.Optional[traveller.World] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._enableMapSelectButton = False
        self._enableShowHexButton = False
        self._enableShowInfoButton = False
        self._mapSelectDialog = None

        self._searchComboBox = gui.HexSelectComboBox()
        if world:
            self._searchComboBox.setCurrentHex(pos=world.hexPosition()) # TODO: This is a hack until this widget supports hexes
        self._searchComboBox.enableAutoComplete(True)
        self._searchComboBox.setMinimumWidth(int(
            WorldSelectToolWidget._MinWoldSelectWidth *
            app.Config.instance().interfaceScale()))
        self._searchComboBox.hexChanged.connect(self._selectionChanged)

        self._mapSelectButton = gui.IconButton(
            icon=gui.loadIcon(id=gui.Icon.Map),
            parent=self)
        self._mapSelectButton.setToolTip(gui.createStringToolTip(
            'Select a world using Traveller Map.'))
        self._mapSelectButton.setHidden(True)
        self._mapSelectButton.clicked.connect(self._mapSelectClicked)

        self._showHexButton = gui.IconButton(
            icon=gui.loadIcon(id=gui.Icon.Search),
            parent=self)
        self._showHexButton.setToolTip(gui.createStringToolTip(
            'Show world in Traveller Map.'))
        self._showHexButton.setHidden(True)
        self._showHexButton.clicked.connect(self._showHexClicked)

        self._showInfoButton = gui.IconButton(
            icon=gui.loadIcon(id=gui.Icon.Info),
            parent=self)
        self._showInfoButton.setToolTip(gui.createStringToolTip(
            'Show world info.'))
        self._showInfoButton.setHidden(True)
        self._showInfoButton.clicked.connect(self._showInfoClicked)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        if text:
            layout.addWidget(QtWidgets.QLabel(text))
        layout.addWidget(self._searchComboBox, 1)
        layout.addWidget(self._mapSelectButton)
        layout.addWidget(self._showHexButton)
        layout.addWidget(self._showInfoButton)

        self.setLayout(layout)

        # I'm not sure why I need to explicitly set tab order here but I don't
        # elsewhere. If it's not done then the default tab order has the buttons
        # before the combo box
        QtWidgets.QWidget.setTabOrder(self._searchComboBox, self._mapSelectButton)
        QtWidgets.QWidget.setTabOrder(self._mapSelectButton, self._showHexButton)
        QtWidgets.QWidget.setTabOrder(self._showHexButton, self._showInfoButton)

    def selectedHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._searchComboBox.currentHex()

    def setSelectedHex(
            self,
            pos: typing.Optional[travellermap.HexPosition],
            updateHistory: bool = True
            ) -> None:
        self._searchComboBox.setCurrentHex(
            pos=pos,
            updateHistory=updateHistory)

    # Helper to get the selected world if a world is selected. Useful for code
    # that never enables dead space selection
    def selectedWorld(self) -> typing.Optional[traveller.World]:
        pos = self.selectedHex()
        if not pos:
            return None
        return traveller.WorldManager.instance().worldByPosition(pos=pos) if pos else None

    def enableMapSelectButton(self, enable: bool) -> None:
        self._enableMapSelectButton = enable
        self._mapSelectButton.setHidden(not self._enableMapSelectButton)

    def isMapSelectButtonEnabled(self) -> bool:
        return self._enableMapSelectButton

    def enableShowHexButton(self, enable: bool) -> None:
        self._enableShowHexButton = enable
        self._showHexButton.setHidden(not self._enableShowHexButton)

    def isShowHexButtonEnabled(self) -> bool:
        return self._enableShowHexButton

    def enableShowInfoButton(self, enable: bool) -> None:
        self._enableShowInfoButton = enable
        self._showInfoButton.setHidden(not self._enableShowInfoButton)

    def isShowInfoButtonEnabled(self) -> bool:
        return self._enableShowInfoButton

    def enableDeadSpaceSelection(self, enable: bool) -> None:
        self._searchComboBox.enableDeadSpaceSelection(enable=enable)
        if self._mapSelectDialog:
            self._mapSelectDialog.configureSelection(
                singleSelect=True,
                includeDeadSpace=enable)

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._searchComboBox.isDeadSpaceSelectionEnabled()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(WorldSelectToolWidget._StateVersion)

        pos = self.selectedHex()
        sectorHex = ''
        if pos:
            try:
                sectorHex = traveller.WorldManager.instance().positionToSectorHex(pos=pos)
            except Exception as ex:
                logging.error(
                    f'Failed to resolve hex {pos} to sector hex when saving HexSelectToolWidget state',
                    exc_info=ex)
        stream.writeQString(sectorHex)

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WorldSelectToolWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore HexSelectToolWidget state (Incorrect version)')
            return False

        sectorHex = stream.readQString()
        pos = None
        if sectorHex:
            try:
                pos = traveller.WorldManager.instance().sectorHexToPosition(
                    sectorHex=sectorHex)
            except Exception as ex:
                logging.error(f'Failed to restore HexSelectToolWidget state', exc_info=ex)
                return False

        self.setSelectedHex(pos=pos, updateHistory=False)
        return True

    def _selectionChanged(
            self,
            pos: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._showHexButton.setEnabled(pos != None)
        self._showInfoButton.setEnabled(pos != None)
        self.selectionChanged.emit()

    def _mapSelectClicked(self) -> None:
        if not self._mapSelectDialog:
            self._mapSelectDialog = gui.TravellerMapSelectDialog(parent=self)
            self._mapSelectDialog.configureSelection(
                singleSelect=True,
                includeDeadSpace=self._searchComboBox.isDeadSpaceSelectionEnabled())

        pos = self.selectedHex()
        if pos:
            self._mapSelectDialog.selectHex(pos=pos)
        else:
            self._mapSelectDialog.clearSelectedHexes()
        if self._mapSelectDialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        newSelection = self._mapSelectDialog.selectedHexes()
        if len(newSelection) != 1:
            return

        self._searchComboBox.setCurrentHex(pos=newSelection[0])

    def _showHexClicked(self) -> None:
        pos = self.selectedHex()
        if pos:
            self.showHex.emit(pos)

    def _showInfoClicked(self) -> None:
        # TODO: This is a hack needed until the world details widget is updated to
        # show details of dead space
        pos = self.selectedHex()
        if not pos:
            return
        world = traveller.WorldManager.instance().worldByPosition(pos=pos)
        if not world:
            return
        infoWindow = gui.WindowManager.instance().showWorldDetailsWindow()
        infoWindow.addWorld(world=world)
