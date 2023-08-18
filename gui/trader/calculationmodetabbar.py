import enum
import gui
import logging
from PyQt5 import QtCore

class CalculationModeTabBar(gui.TabBarEx):
    class CalculationMode(enum.Enum):
        AverageCase = 0
        WorstCase = 1
        BestCase = 2

    _StateVersion = 'CalculationModeTabBar_v1'

    def __init__(self) -> None:
        tabs = [
            (
                CalculationModeTabBar.CalculationMode.AverageCase,
                'Average Case',
                gui.createStringToolTip('Display values calculated using average dice rolls')),
            (
                CalculationModeTabBar.CalculationMode.WorstCase,
                'Worst Case',
                gui.createStringToolTip('Display values calculated using worst case dice rolls')),
            (
                CalculationModeTabBar.CalculationMode.BestCase,
                'Best Case',
                gui.createStringToolTip('Display values calculated using best case dice rolls'))
        ]
        super().__init__()
        for index, (mode, text, toolTip) in enumerate(tabs):
            self.addTab(text)
            self.setTabData(index, mode)
            self.setTabToolTip(index, toolTip)

    def currentCalculationMode(self) -> CalculationMode:
        return self.tabData(self.currentIndex())

    def setCurrentCalculationMode(
            self,
            calculationMode: CalculationMode
            ) -> None:
        for index in range(self.count()):
            if calculationMode == self.tabData(index):
                self.setCurrentIndex(index)
                return

    def saveState(self) -> QtCore.QByteArray:
        calculationMode = self.currentCalculationMode()
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(CalculationModeTabBar._StateVersion)
        stream.writeQString(calculationMode.name)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> None:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != CalculationModeTabBar._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore CalculationModeTabBar state (Incorrect version')
            return False

        name = stream.readQString()
        if name not in self.CalculationMode.__members__:
            logging.warning(f'Failed to restore CalculationModeTabBar state (Unknown mode "{name}")')
            return False
        self.setCurrentCalculationMode(self.CalculationMode.__members__[name])
        return True
