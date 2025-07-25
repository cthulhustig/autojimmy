import app
import common
import gui
import logging
import os
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class CalculationWindow(gui.WindowWidget):
    def __init__(
            self
            ) -> None:
        super().__init__(
            title='Calculations',
            configSection='CalculationWindow')

        self._calculationTree = gui.CalculationTree()

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._calculationTree)
        self.setLayout(windowLayout)

    def showCalculation(
            self,
            calculation: common.Calculation,
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        self._calculationTree.showCalculation(
            calculation=calculation,
            expand=expand,
            decimalPlaces=decimalPlaces)

    def showCalculations(
            self,
            calculations: typing.Iterable[common.Calculation],
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        self._calculationTree.showCalculations(
            calculations=calculations,
            expand=expand,
            decimalPlaces=decimalPlaces)

    def setCalculation(
            self,
            calculation: common.Calculation,
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        self._calculationTree.setCalculation(
            calculation=calculation,
            expand=expand,
            decimalPlaces=decimalPlaces)

    def setCalculations(
            self,
            calculations: typing.Iterable[common.Calculation],
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        self._calculationTree.setCalculations(
            calculations=calculations,
            expand=expand,
            decimalPlaces=decimalPlaces)

    def addCalculation(
            self,
            calculation: common.Calculation,
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        self._calculationTree.addCalculation(
            calculation=calculation,
            expand=expand,
            decimalPlaces=decimalPlaces)

    def addCalculations(
            self,
            calculations: typing.Iterable[common.Calculation],
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        self._calculationTree.addCalculations(
            calculations=calculations,
            expand=expand,
            decimalPlaces=decimalPlaces)

    def clear(self) -> None:
        self._calculationTree.clear()

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)
        storedState = gui.safeLoadSetting(
            settings=self._settings,
            key='CalculationColumnState',
            type=QtCore.QByteArray)
        if storedState:
            header = self._calculationTree.header()
            if header:
                header.restoreState(storedState)
        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)
        header = self._calculationTree.header()
        if header:
            self._settings.setValue('CalculationColumnState', header.saveState())
        self._settings.endGroup()

        super().saveSettings()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        shiftCtrlModifiers = QtCore.Qt.KeyboardModifier.ShiftModifier | QtCore.Qt.KeyboardModifier.ControlModifier
        if event.key() == QtCore.Qt.Key.Key_S and event.modifiers() == shiftCtrlModifiers:
            self._saveCalculations()
            return # Swallow event
        elif event.key() == QtCore.Qt.Key.Key_L and event.modifiers() == shiftCtrlModifiers:
            self._loadCalculations()
            return # Swallow event

        super().keyPressEvent(event)

    def _saveCalculations(self) -> None:
        path, filter = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Save Calculations',
            directory=os.path.join(QtCore.QDir.homePath(), 'calculations.json'),
            filter=f'{gui.JSONFileFilter}')
        if not path:
            return # User cancelled

        try:
            common.writeCalculationList(
                calculations=self._calculationTree.calculations(),
                path=path)
        except Exception as ex:
            message = 'Failed to save calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _loadCalculations(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            directory=QtCore.QDir.homePath(),
            filter=gui.JSONFileFilter)
        if not path:
            return # User cancelled

        try:
            self.setCalculations(
                calculations=common.readCalculationList(path=path))
        except Exception as ex:
            message = 'Failed to save calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
