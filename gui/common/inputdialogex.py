import gui
import typing
from PyQt5 import QtWidgets, QtCore

# Implementation based on https://codebrowser.dev/qt5/qtbase/src/widgets/dialogs/qinputdialog.cpp.html
class InputDialogEx(QtWidgets.QInputDialog):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0)
            ) -> None:
        if flags != None:
            super().__init__(parent, flags)
        else:
            super().__init__(parent)
        gui.configureWindowTitleBar(widget=self)

    @staticmethod
    def getText(
            parent: QtWidgets.QWidget,
            title: str,
            label: str,
            echo: QtWidgets.QLineEdit.EchoMode = QtWidgets.QLineEdit.EchoMode.Normal,
            text: str = '',
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0),
            inputMethodHints: QtCore.Qt.InputMethodHint = QtCore.Qt.InputMethodHint.ImhNone
            ) -> typing.Tuple[str, bool]:
        dialog = InputDialogEx(parent, flags)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setTextValue(text)
        dialog.setTextEchoMode(echo)
        dialog.setInputMethodHints(inputMethodHints)
        result = not not dialog.exec()
        return (dialog.textValue() if result else '', result)

    @staticmethod
    def getMultiLineText(
            parent: QtWidgets.QWidget,
            title: str,
            label: str,
            text: str = '',
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0),
            inputMethodHints: QtCore.Qt.InputMethodHint = QtCore.Qt.InputMethodHint.ImhNone
            ) -> typing.Tuple[str, bool]:
        dialog = InputDialogEx(parent, flags)
        dialog.setOptions(QtWidgets.QInputDialog.InputDialogOption.UsePlainTextEditForTextInput)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setTextValue(text)
        dialog.setInputMethodHints(inputMethodHints)
        result = not not dialog.exec()
        return (dialog.textValue() if result else '', result)

    @staticmethod
    def getItem(
            parent: QtWidgets.QWidget,
            title: str,
            label: str,
            items: typing.Iterable[str],
            current: int = 0,
            editable: bool = True,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0),
            inputMethodHints: QtCore.Qt.InputMethodHint = QtCore.Qt.InputMethodHint.ImhNone
            ) -> typing.Tuple[str, bool]:
        text = items[current]
        dialog = InputDialogEx(parent, flags)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setComboBoxItems(items)
        dialog.setTextValue(text)
        dialog.setComboBoxEditable(editable)
        dialog.setInputMethodHints(inputMethodHints)
        result = not not dialog.exec()
        return (dialog.textValue() if result else text, result)

    @staticmethod
    def getDouble(
            parent: QtWidgets.QWidget,
            title: str,
            label: str,
            value: float = 0,
            minValue: float = -2147483647,
            maxValue: float = 2147483647,
            decimals: int = 1,
            step: float = 1.0,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0),
            ) -> typing.Tuple[float, bool]:
        dialog = InputDialogEx(parent, flags)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setDoubleDecimals(decimals)
        dialog.setDoubleRange(minValue, maxValue)
        dialog.setDoubleValue(value)
        dialog.setDoubleStep(step)
        result = not not dialog.exec()
        return (dialog.doubleValue() if result else value, result)

    @staticmethod
    def getInt(
            parent: QtWidgets.QWidget,
            title: str,
            label: str,
            value: int = 0,
            minValue: int = -2147483647,
            maxValue: int = 2147483647,
            step: int = 1,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0)
            ) -> typing.Tuple[int, bool]:
        dialog = InputDialogEx(parent, flags)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setIntRange(minValue, maxValue)
        dialog.setIntValue(value)
        dialog.setIntStep(step)
        result = not not dialog.exec()
        return (dialog.intValue() if result else value, result)
