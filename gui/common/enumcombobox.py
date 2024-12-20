import enum
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class EnumComboBox(QtWidgets.QComboBox):
    _StateVersion = 'EnumComboBox_v1'

    def __init__(
            self,
            type: typing.Type[enum.Enum],
            value: typing.Optional[enum.Enum] = None,
            options: typing.Iterable[enum.Enum] = None,
            textMap: typing.Optional[typing.Mapping[enum.Enum, str]] = None,
            isOptional: bool = False,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._type = None

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
        oldSelectedIndex = self.currentIndex()
        oldSelectedText = self.currentText()
        oldSelectedEnum = self.currentEnum()

        self._type = type

        # Block signals while we update. Signal will be manually generated if the selection actually
        # changes
        with gui.SignalBlocker(widget=self):
            self.clear()

            if isOptional:
                self.addItem('None', None)

            if not options:
                options = type
            for entry in options:
                text = str(entry.value)
                if textMap:
                    text = textMap.get(entry, text)
                self.addItem(text, entry)

            self.setCurrentEnum(value=oldSelectedEnum)

        newSelectedIndex = self.currentIndex()
        if newSelectedIndex != oldSelectedIndex:
            self.currentIndexChanged.emit(newSelectedIndex)

        newSelectedText = self.currentText()
        if newSelectedText != oldSelectedText:
            self.currentTextChanged.emit(newSelectedText)

    def currentEnum(self) -> typing.Optional[enum.Enum]:
        return self.currentData(QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentEnum(self, value: typing.Optional[enum.Enum]) -> None:
        for index in range(self.count()):
            if value == self.itemData(index, QtCore.Qt.ItemDataRole.UserRole):
                self.setCurrentIndex(index)
                return

    def saveState(self) -> QtCore.QByteArray:
        value = self.currentEnum()
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(EnumComboBox._StateVersion)
        stream.writeQString(value.name)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != EnumComboBox._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore EnumComboBox state (Incorrect version)')
            return False

        name = stream.readQString()
        if name not in self._type.__members__:
            logging.warning(f'Failed to restore EnumComboBox state (Unknown enum "{name}")')
            return False
        self.setCurrentEnum(self._type.__members__[name])
        return True
