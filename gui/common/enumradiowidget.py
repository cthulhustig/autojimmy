import enum
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

class EnumRadioWidget(QtWidgets.QWidget):
    enumChanged = QtCore.pyqtSignal()

    _StateVersion = 'EnumRadioWidget_v1'

    def __init__(
            self,
            type: typing.Type[enum.Enum],
            value: typing.Optional[enum.Enum] = None,
            options: typing.Iterable[enum.Enum] = None,
            textMap: typing.Optional[typing.Mapping[enum.Enum, str]] = None,
            isOptional: bool = False,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)

        self._type = None
        self._controlMap: typing.Dict[enum.Enum, QtWidgets.QRadioButton] = {}

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self._layout)

        self.setEnumType(
            type=type,
            options=options,
            textMap=textMap,
            isOptional=isOptional)

        self.setCurrentEnum(value)

    def setEnumType(
            self,
            type: typing.Type[enum.Enum],
            options: typing.Iterable[enum.Enum] = None,
            textMap: typing.Optional[typing.Mapping[enum.Enum, str]] = None,
            isOptional: bool = False,
            ) -> None:
        self._type = type

        with gui.SignalBlocker(widget=self):
            self._removeControls()

            if isOptional:
                self._addControl(text='None', value=None)

            if not options:
                options = type
            for value in options:
                text = None
                if textMap:
                    text = textMap.get(value)
                if not text:
                    text = str(value.value)
                self._addControl(text=text, value=value)

        self.enumChanged.emit()

    def currentEnum(self) -> typing.Optional[enum.Enum]:
        for value, control in self._controlMap.items():
            if control.isChecked():
                return value
        return None

    def setCurrentEnum(self, value: typing.Optional[enum.Enum]) -> None:
        control = self._controlMap.get(value)
        if control:
            control.setChecked(True)

    def saveState(self) -> QtCore.QByteArray:
        value = self.currentEnum()
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(EnumRadioWidget._StateVersion)
        stream.writeQString(value.name)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != EnumRadioWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore EnumRadioWidget state (Incorrect version)')
            return False

        name = stream.readQString()
        if name not in self._type.__members__:
            logging.warning(f'Failed to restore EnumRadioWidget state (Unknown enum "{name}")')
            return False
        self.setCurrentEnum(self._type.__members__[name])
        return True

    def _addControl(self, text: str, value: typing.Optional[enum.Enum]) -> None:
        control = gui.RadioButtonEx(text)
        control.toggled.connect(self._controlToggled)
        self._layout.addWidget(control)
        self._controlMap[value] = control

    def _removeControls(self) -> None:
        for control in self._controlMap.values():
            self._layout.removeWidget(control)
            control.setParent(None)
            control.setHidden(True)
            control.deleteLater()
        self._controlMap.clear()

    def _controlToggled(
            self,
            checked: bool
            ) -> None:
        if checked:
            self.enumChanged.emit()
