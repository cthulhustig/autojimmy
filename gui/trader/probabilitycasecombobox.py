import logic
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class ProbabilityCaseComboBox(QtWidgets.QComboBox):
    _OptionTextMap = {
        logic.ProbabilityCase.AverageCase: 'Average Case',
        logic.ProbabilityCase.WorstCase: 'Worst Case',
        logic.ProbabilityCase.BestCase: 'Best Case'
    }

    _StateVersion = 'ProbabilityCaseComboBox_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            value: typing.Optional[logic.ProbabilityCase] = None
            ) -> None:
        super().__init__(parent=parent)
        for option in logic.ProbabilityCase:
            self.addItem(ProbabilityCaseComboBox._OptionTextMap[option], option)

        if value:
            self.setCurrentCase(value)

    def currentCase(self) -> logic.RefuellingStrategy:
        return self.currentData(QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentCase(self, probabilityCase: logic.RefuellingStrategy) -> None:
        for index in range(self.count()):
            itemProbabilityCase = self.itemData(index, QtCore.Qt.ItemDataRole.UserRole)
            if probabilityCase == itemProbabilityCase:
                self.setCurrentIndex(index)
                return

    def saveState(self) -> QtCore.QByteArray:
        case = self.currentCase()
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(ProbabilityCaseComboBox._StateVersion)
        stream.writeQString(case.name)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != ProbabilityCaseComboBox._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore ProbabilityCaseComboBox state (Incorrect version)')
            return False

        name = stream.readQString()
        if name not in logic.ProbabilityCase.__members__:
            logging.warning(f'Failed to restore ProbabilityCaseComboBox state (Unknown case "{name}")')
            return False
        self.setCurrentCase(logic.ProbabilityCase.__members__[name])
        return True
