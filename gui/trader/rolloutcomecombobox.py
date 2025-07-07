import logic
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class RollOutcomeComboBox(QtWidgets.QComboBox):
    _OptionTextMap = {
        logic.RollOutcome.AverageCase: 'Average Case',
        logic.RollOutcome.WorstCase: 'Worst Case',
        logic.RollOutcome.BestCase: 'Best Case'
    }

    _StateVersion = 'RollOutcomeComboBox_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            value: typing.Optional[logic.RollOutcome] = None
            ) -> None:
        super().__init__(parent=parent)
        for option in logic.RollOutcome:
            self.addItem(RollOutcomeComboBox._OptionTextMap[option], option)

        if value:
            self.setCurrentCase(value)

    def currentCase(self) -> logic.RollOutcome:
        return self.currentData(QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentCase(self, rollOutcome: logic.RollOutcome) -> None:
        for index in range(self.count()):
            itemRollOutcome = self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)
            if rollOutcome == itemRollOutcome:
                self.setCurrentIndex(index)
                return

    def saveState(self) -> QtCore.QByteArray:
        case = self.currentCase()
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(RollOutcomeComboBox._StateVersion)
        stream.writeQString(case.name)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != RollOutcomeComboBox._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore RollOutcomeComboBox state (Incorrect version)')
            return False

        name = stream.readQString()
        if name not in logic.RollOutcome.__members__:
            logging.warning(f'Failed to restore RollOutcomeComboBox state (Unknown case "{name}")')
            return False
        self.setCurrentCase(logic.RollOutcome.__members__[name])
        return True
