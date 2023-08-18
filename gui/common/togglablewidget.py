import gui
import logging
import typing
from PyQt5 import QtCore, QtWidgets

class TogglableWidget(QtWidgets.QWidget):
    checkToggled = QtCore.pyqtSignal([bool])

    def __init__(
            self,
            widget: QtWidgets.QWidget,
            text: typing.Optional[str] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._widget = widget

        self._enabledCheckBox = gui.CheckBoxEx()
        self._enabledCheckBox.setChecked(self._widget.isEnabled())
        self._enabledCheckBox.stateChanged.connect(self._enabledChanged)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._enabledCheckBox)
        if text:
            layout.addWidget(QtWidgets.QLabel(text))
        layout.addWidget(self._widget)

        self.setLayout(layout)

    def widget(self) -> QtWidgets.QWidget:
        return self._widget

    def isChecked(self) -> bool:
        return self._enabledCheckBox.isChecked()

    def setChecked(self, enabled: bool) -> None:
        self._enabledCheckBox.setChecked(enabled)

    def _enabledChanged(self, value: int) -> None:
        enabled = not not value
        self._widget.setEnabled(enabled)
        self.checkToggled.emit(enabled)

class TogglableSpinBox(TogglableWidget):
    valueChanged = QtCore.pyqtSignal([int], [type(None)])

    _StateVersion = 'TogglableSpinBox_v1'

    def __init__(
            self,
            text: typing.Optional[str] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            spinBox: typing.Optional[QtWidgets.QSpinBox] = None
            ) -> None:
        super().__init__(
            widget=spinBox if spinBox else gui.SpinBoxEx(),
            text=text,
            parent=parent)

        self.widget().valueChanged.connect(self._valueChanged)

    # This is only really here to sort code completion/highlighting in VSCode
    def widget(self) -> gui.SpinBoxEx:
        return self._widget

    def value(
            self,
            rawValue: bool = False
            ) -> typing.Optional[int]:
        if not rawValue and not self.isChecked():
            return None
        return self.widget().value()

    def setValue(self, value: int) -> None:
        self.widget().setValue(value)

    def config(self) -> typing.Tuple[bool, int]:
        return (self.isChecked(), self.value(rawValue=True))

    def setConfig(
            self,
            enabled: bool,
            value: int
            ) -> None:
        enabledChanged = enabled != self.isChecked()
        oldValue = self.value(rawValue=True)

        with gui.SignalBlocker(self):
            if enabledChanged:
                self.setChecked(enabled)
            self.setValue(value)

        # Get the _actual_ new value after any min/max clamping
        newValue = self.value(rawValue=True)

        if enabledChanged:
            # The enabled state has changed so emit the check and value events
            self.checkToggled.emit(enabled)
            self.valueChanged.emit(newValue if enabled else None)
        elif enabled and oldValue != newValue:
            # The spin box is enabled and the value has changed so emit the value event
            self.valueChanged.emit(newValue)

    def setRange(self, minValue: int, maxValue: int) -> None:
        self.widget().setRange(minValue, maxValue)

    def showSpinBox(self) -> None:
        self._widget.show()

    def hideSpinBox(self) -> None:
        self._widget.hide()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(TogglableSpinBox._StateVersion)
        stream.writeBool(self._enabledCheckBox.isChecked())
        stream.writeInt32(self.widget().value())
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> None:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != TogglableSpinBox._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore UserEnableSpinBox state (Incorrect version')
            return False

        self._enabledCheckBox.setChecked(stream.readBool())
        self.widget().setValue(stream.readInt32())
        return True

    def _enabledChanged(self, value: int) -> None:
        super()._enabledChanged(value)
        # The value has "changed" as it's switched to/from None
        self.valueChanged.emit(self.value())

    def _valueChanged(
            self,
            value: int
            ) -> None:
        # Emit None if the widget is disabled
        self.valueChanged.emit(self.value())
