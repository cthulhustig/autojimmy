import gui
import gunsmith
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class WeaponInfoTabWidget(QtWidgets.QWidget):
    _StateVersion = 'WeaponInfoTabWidget_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._weapon = None

        self._tabBar = gui.TabBarEx()
        self._tabBar.currentChanged.connect(self._selectedTabChanged)

        self._infoWidget = gui.WeaponInfoWidget()

        self._scrollArea = QtWidgets.QScrollArea()
        self._scrollArea.setWidgetResizable(True)
        self._scrollArea.setWidget(self._infoWidget)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0) # No spacing between tabs and scroll area
        layout.addWidget(self._tabBar)
        layout.addWidget(self._scrollArea)
        layout.addStretch(1)

        self.setLayout(layout)

    def currentSequence(self) -> typing.Optional[str]:
        currentIndex = self._tabBar.currentIndex()
        if currentIndex < 0:
            return None
        return self._tabBar.tabData(currentIndex)

    def setWeapon(
            self,
            weapon: typing.Optional[gunsmith.Weapon]
            ) -> None:
        self._weapon = weapon

        self._updateTabs()

        self._infoWidget.setWeapon(
            weapon=weapon,
            sequence=self.currentSequence())

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        subState = self._tabBar.saveState()
        stream.writeUInt32(subState.count() if subState else 0)
        if subState:
            stream.writeRawData(subState.data())

        subState = self._infoWidget.saveState()
        stream.writeUInt32(subState.count() if subState else 0)
        if subState:
            stream.writeRawData(subState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != self._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug('Failed to restore WeaponInfoTabWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count > 0:
            subState = QtCore.QByteArray(stream.readRawData(count))
            if not self._tabBar.restoreState(subState):
                return False

        count = stream.readUInt32()
        if count > 0:
            subState = QtCore.QByteArray(stream.readRawData(count))
            if not self._infoWidget.restoreState(subState):
                return False

        return True

    def _updateTabs(self) -> None:
        with gui.SignalBlocker(widget=self._tabBar):
            sequences = self._weapon.sequences()
            while self._tabBar.count() > max(len(sequences), 1):
                self._tabBar.removeTab(self._tabBar.count() - 1)

            while self._tabBar.count() < len(sequences):
                index = self._tabBar.count()
                if index == 0:
                    self._tabBar.addTab('Primary Weapon')
                elif len(sequences) == 2:
                    self._tabBar.addTab('Secondary Weapon')
                else:
                    self._tabBar.addTab(f'Secondary Weapon {index}')

            if sequences:
                for index, sequence in enumerate(sequences):
                    self._tabBar.setTabData(index, sequence)
            else:
                # The Primary Weapon tab isn't removed when there is no weapon set but the
                # tab data is set to None
                self._tabBar.setTabData(0, None)

    def _selectedTabChanged(
            self,
            index: int
            ) -> None:
        sequence = self._tabBar.tabData(index)
        self._infoWidget.setWeapon(
            weapon=self._weapon,
            sequence=sequence)
