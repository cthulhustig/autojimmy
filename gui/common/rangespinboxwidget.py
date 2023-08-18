import gui
import logging
import typing
from PyQt5 import QtCore, QtWidgets

class RangeSpinBoxWidget(QtWidgets.QWidget):
    rangeChanged = QtCore.pyqtSignal(int, int)

    _StateVersion = 'RangeSpinBoxWidget_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._lowerValueSpinBox = gui.SpinBoxEx()
        self._lowerValueSpinBox.valueChanged.connect(self._lowerValueChanged)

        self._upperValueSpinBox = gui.SpinBoxEx()
        self._upperValueSpinBox.valueChanged.connect(self._upperValueChanged)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._lowerValueSpinBox)
        layout.addWidget(QtWidgets.QLabel(' to '))
        layout.addWidget(self._upperValueSpinBox)

        self.setLayout(layout)

    def lowerValue(self) -> int:
        return self._lowerValueSpinBox.value()

    def setLowerValue(self, value: int) -> None:
        self._lowerValueSpinBox.setValue(value)

    def upperValue(self) -> int:
        return self._upperValueSpinBox.value()

    def setUpperValue(self, value: int) -> None:
        self._upperValueSpinBox.setValue(value)

    def setValues(self, lowerValue: int, upperValue: int) -> None:
        with gui.SignalBlocker(widget=self):
            self.setLowerValue(lowerValue)
            self.setUpperValue(upperValue)

        self.rangeChanged.emit(self.lowerValue(), self.upperValue())

    def setLimits(
            self,
            minValue: int,
            maxValue: int
            ) -> None:
        self._lowerValueSpinBox.setRange(minValue, maxValue)
        self._upperValueSpinBox.setRange(minValue, maxValue)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(RangeSpinBoxWidget._StateVersion)
        stream.writeInt32(self.lowerValue())
        stream.writeInt32(self.upperValue())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> None:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != RangeSpinBoxWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore RangeSpinBoxWidget state (Incorrect version')
            return False

        self.setValues(
            lowerValue=stream.readInt32(),
            upperValue=stream.readInt32())
        return True

    def _lowerValueChanged(self, value: int) -> None:
        if value > self._upperValueSpinBox.value():
            with gui.SignalBlocker(widget=self):
                self._upperValueSpinBox.setValue(value)
        self.rangeChanged.emit(value, self.upperValue())

    def _upperValueChanged(self, value: int) -> None:
        if value < self._lowerValueSpinBox.value():
            with gui.SignalBlocker(widget=self):
                self._lowerValueSpinBox.setValue(value)
        self.rangeChanged.emit(self.lowerValue(), value)
