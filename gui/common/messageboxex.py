import gui
import typing
from PyQt5 import QtWidgets, QtCore

class MessageBoxEx(QtWidgets.QMessageBox):
    def __init__(
            self,
            icon: QtWidgets.QMessageBox.Icon,
            title: str,
            text: str,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton],
            parent: typing.Optional[QtWidgets.QWidget] = None,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType.Dialog | QtCore.Qt.WindowType.MSWindowsFixedSizeDialogHint
            ) -> None:
        super().__init__(icon, title, text, buttons, parent, flags)
        gui.configureWindowTitleBar(widget=self)

    @staticmethod
    def information(
            text: str,
            title: str = 'Information',
            parent: typing.Optional[QtWidgets.QWidget] = None,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.Ok,
            defaultButton: typing.Optional[QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            checkBox: typing.Optional[QtWidgets.QCheckBox] = None
            ) -> QtWidgets.QMessageBox.StandardButton:
        return MessageBoxEx.showMessageBox(
            parent,
            MessageBoxEx.Icon.Information,
            title,
            text,
            buttons,
            defaultButton,
            checkBox)

    @staticmethod
    def critical(
            text: str,
            title: str = 'Error',
            parent: typing.Optional[QtWidgets.QWidget] = None,
            exception: typing.Optional[Exception] = None,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.Ok,
            defaultButton: typing.Optional[QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            checkBox: typing.Optional[QtWidgets.QCheckBox] = None
            ) -> QtWidgets.QMessageBox.StandardButton:
        if exception:
            if text:
                text += '\n\n' + str(exception)
            else:
                text = str(exception)
        return MessageBoxEx.showMessageBox(
            parent,
            MessageBoxEx.Icon.Critical,
            title,
            text,
            buttons,
            defaultButton,
            checkBox)

    @staticmethod
    def warning(
            text: str,
            title: str = 'Warning',
            parent: typing.Optional[QtWidgets.QWidget] = None,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.Ok,
            defaultButton: typing.Optional[QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            checkBox: typing.Optional[QtWidgets.QCheckBox] = None
            ) -> QtWidgets.QMessageBox.StandardButton:
        return MessageBoxEx.showMessageBox(
            parent,
            MessageBoxEx.Icon.Warning,
            title,
            text,
            buttons,
            defaultButton,
            checkBox)

    @staticmethod
    def question(
            text: str,
            title: str = 'Prompt',
            parent: typing.Optional[QtWidgets.QWidget] = None,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            defaultButton: typing.Optional[QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            checkBox: typing.Optional[QtWidgets.QCheckBox] = None
            ) -> QtWidgets.QMessageBox.StandardButton:
        return MessageBoxEx.showMessageBox(
            parent,
            MessageBoxEx.Icon.Question,
            title,
            text,
            buttons,
            defaultButton,
            checkBox)

    # Reimplementation of the the underlying C++ QMessageBox but using my MessageBoxEx class instead
    # of QtWidgets.QMessageBox
    # https://codebrowser.dev/qt5/qtbase/src/widgets/dialogs/qmessagebox.cpp.html
    @staticmethod
    def showMessageBox(
            parent: QtWidgets.QWidget,
            icon: QtWidgets.QMessageBox.Icon,
            title: str,
            text: str,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton],
            defaultButton: QtWidgets.QMessageBox.StandardButton,
            checkBox: typing.Optional[QtWidgets.QCheckBox]
            ) -> QtWidgets.QMessageBox.StandardButton:
        msgBox = MessageBoxEx(icon, title, text, QtWidgets.QMessageBox.StandardButton.NoButton, parent)
        buttonBox: QtWidgets.QDialogButtonBox = msgBox.findChild(QtWidgets.QDialogButtonBox)
        mask = QtWidgets.QMessageBox.StandardButton.FirstButton
        while mask <= QtWidgets.QMessageBox.StandardButton.LastButton:
            standardButton = QtWidgets.QMessageBox.StandardButton(buttons & mask)
            mask <<= 1
            if not standardButton:
                continue

            button = msgBox.addButton(standardButton)
            if msgBox.defaultButton():
                continue
            if (defaultButton == QtWidgets.QMessageBox.StandardButton.NoButton and \
                buttonBox.buttonRole(button) == QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole) \
                or \
                (defaultButton != QtWidgets.QMessageBox.StandardButton.NoButton and \
                 standardButton == defaultButton):
                msgBox.setDefaultButton(button)

        if checkBox:
            msgBox.setCheckBox(checkBox)

        if msgBox.exec() == -1:
            return QtWidgets.QMessageBox.StandardButton.Cancel
        return msgBox.standardButton(msgBox.clickedButton())
