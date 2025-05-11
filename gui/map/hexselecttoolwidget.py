import app
import gui
import logging
import traveller
import travellermap
import typing
from PyQt5 import QtWidgets, QtCore

class HexSelectToolWidget(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()
    showHex = QtCore.pyqtSignal(travellermap.HexPosition)

    # This state version intentionally doesn't match the class name. This
    # was done for backwards compatibility when the class was renamed as
    # part of the work for dead space routing
    # v2 - Switched to storing absolute hex rather than sector hex as part
    # of making the milieu dynamically changeable
    _StateVersion = 'WorldSelectWidget_v2'

    # The hex select combo box has a minimum width applied to stop it becoming
    # stupidly small. This min size isn't expected to be big enough for all
    # world names
    _MinWoldSelectWidth = 150

    def __init__(
            self,
            labelText: typing.Optional[str] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._enableMapSelectButton = False
        self._enableShowHexButton = False
        self._enableShowInfoButton = False
        self._hexSelectDialog = None

        self._searchComboBox = gui.HexSelectComboBox()
        self._searchComboBox.enableAutoComplete(True)
        self._searchComboBox.setMinimumWidth(int(
            HexSelectToolWidget._MinWoldSelectWidth *
            app.Config.instance().interfaceScale()))
        self._searchComboBox.hexChanged.connect(self._selectionChanged)

        self._mapSelectButton = gui.IconButton(
            icon=gui.loadIcon(id=gui.Icon.Map),
            parent=self)
        self._mapSelectButton.setToolTip(gui.createStringToolTip(
            'Select Using Traveller Map.'))
        self._mapSelectButton.setHidden(True)
        self._mapSelectButton.clicked.connect(self._mapSelectClicked)

        self._showHexButton = gui.IconButton(
            icon=gui.loadIcon(id=gui.Icon.Search),
            parent=self)
        self._showHexButton.setToolTip(gui.createStringToolTip(
            'Show in Traveller Map.'))
        self._showHexButton.setHidden(True)
        self._showHexButton.clicked.connect(self._showHexClicked)

        self._showInfoButton = gui.IconButton(
            icon=gui.loadIcon(id=gui.Icon.Info),
            parent=self)
        self._showInfoButton.setToolTip(gui.createStringToolTip(
            'Show Location Details.'))
        self._showInfoButton.setHidden(True)
        self._showInfoButton.clicked.connect(self._showInfoClicked)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        if labelText:
            layout.addWidget(QtWidgets.QLabel(labelText))
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
            hex: typing.Optional[travellermap.HexPosition],
            updateHistory: bool = True
            ) -> None:
        self._searchComboBox.setCurrentHex(
            hex=hex,
            updateHistory=updateHistory)

    # Helper to get the selected world if a world is selected. Useful for code
    # that never enables dead space selection
    def selectedWorld(self) -> typing.Optional[traveller.World]:
        hex = self.selectedHex()
        if not hex:
            return None
        return traveller.WorldManager.instance().worldByPosition(
            milieu=app.Config.instance().milieu(),
            hex=hex)

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
        if self._hexSelectDialog:
            self._hexSelectDialog.configureSelection(
                singleSelect=True,
                includeDeadSpace=enable)

    def isDeadSpaceSelectionEnabled(self) -> bool:
        return self._searchComboBox.isDeadSpaceSelectionEnabled()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(HexSelectToolWidget._StateVersion)

        hex = self.selectedHex()
        stream.writeQString(f'{hex.absoluteX()}:{hex.absoluteY()}' if hex else '')

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != HexSelectToolWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore HexSelectToolWidget state (Incorrect version)')
            return False

        value = stream.readQString()
        hex = None
        if value:
            tokens = value.split(':')
            if len(tokens) < 0:
                logging.warning(f'Failed to restore HexSelectToolWidget state (Invalid hex string "{value}")')
                return False
            try:
                hex = travellermap.HexPosition(
                    absoluteX=int(tokens[0]),
                    absoluteY=int(tokens[1]))
            except Exception as ex:
                # This can happen if sector data has changed for whatever reason
                # (e.g. map updates or custom sectors)
                logging.warning(f'Failed to restore HexSelectToolWidget state (Invalid hex string "{value}"', exc_info=ex)
                return False

        self.setSelectedHex(hex=hex, updateHistory=False)
        return True

    def _selectionChanged(
            self,
            hex: typing.Optional[travellermap.HexPosition]
            ) -> None:
        self._showHexButton.setEnabled(hex != None)
        self._showInfoButton.setEnabled(hex != None)
        self.selectionChanged.emit()

    def _mapSelectClicked(self) -> None:
        if not self._hexSelectDialog:
            self._hexSelectDialog = gui.HexSelectDialog(parent=self)
            self._hexSelectDialog.configureSelection(
                singleSelect=True,
                includeDeadSpace=self._searchComboBox.isDeadSpaceSelectionEnabled())

        hex = self.selectedHex()
        if hex:
            self._hexSelectDialog.selectHex(hex=hex)
        else:
            self._hexSelectDialog.clearSelectedHexes()
        if self._hexSelectDialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        newSelection = self._hexSelectDialog.selectedHexes()
        if len(newSelection) != 1:
            return

        self._searchComboBox.setCurrentHex(hex=newSelection[0])

    def _showHexClicked(self) -> None:
        hex = self.selectedHex()
        if hex:
            self.showHex.emit(hex)

    def _showInfoClicked(self) -> None:
        hex = self.selectedHex()
        if not hex:
            return
        infoWindow = gui.WindowManager.instance().showWorldDetailsWindow()
        infoWindow.addHex(hex=hex)
