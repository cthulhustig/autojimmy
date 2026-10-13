import gui
import typing
from PyQt5 import QtWidgets, QtCore

class MessageBoxEx(QtWidgets.QMessageBox):
    # Use a separate config section for the no show again flag as it makes it easier to
    # reset it if needed
    _NoShowAgainConfigSection = 'NoShowAgain'

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
            parent=parent,
            icon=MessageBoxEx.Icon.Critical,
            title=title,
            text=text,
            buttons=buttons,
            defaultButton=defaultButton,
            checkBox=checkBox)

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
            parent=parent,
            icon=MessageBoxEx.Icon.Warning,
            title=title,
            text=text,
            buttons=buttons,
            defaultButton=defaultButton,
            checkBox=checkBox)

    @staticmethod
    def information(
            text: str,
            title: str = 'Information',
            parent: typing.Optional[QtWidgets.QWidget] = None,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.Ok,
            defaultButton: typing.Optional[QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            checkBox: typing.Optional[QtWidgets.QCheckBox] = None,
            noShowAgainKey: typing.Optional[str] = None,
            noShowAgainButtons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            ) -> QtWidgets.QMessageBox.StandardButton:
        return MessageBoxEx.showMessageBox(
            parent=parent,
            icon=MessageBoxEx.Icon.Information,
            title=title,
            text=text,
            buttons=buttons,
            defaultButton=defaultButton,
            checkBox=checkBox,
            noShowAgainKey=noShowAgainKey,
            noShowAgainButtons=noShowAgainButtons)

    @staticmethod
    def question(
            text: str,
            title: str = 'Prompt',
            parent: typing.Optional[QtWidgets.QWidget] = None,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            defaultButton: typing.Optional[QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            checkBox: typing.Optional[QtWidgets.QCheckBox] = None,
            noShowAgainKey: typing.Optional[str] = None,
            noShowAgainButtons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            ) -> QtWidgets.QMessageBox.StandardButton:
        return MessageBoxEx.showMessageBox(
            parent=parent,
            icon=MessageBoxEx.Icon.Question,
            title=title,
            text=text,
            buttons=buttons,
            defaultButton=defaultButton,
            checkBox=checkBox,
            noShowAgainKey=noShowAgainKey,
            noShowAgainButtons=noShowAgainButtons)

    # Reimplementation of the the underlying C++ QMessageBox but using my MessageBoxEx class instead
    # of QtWidgets.QMessageBox
    # https://codebrowser.dev/qt5/qtbase/src/widgets/dialogs/qmessagebox.cpp.html
    @staticmethod
    def showMessageBox(
            icon: QtWidgets.QMessageBox.Icon,
            title: str,
            text: str,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton],
            defaultButton: QtWidgets.QMessageBox.StandardButton,
            checkBox: typing.Optional[QtWidgets.QCheckBox] = None, # Ignored if no show again key is set
            noShowAgainKey: typing.Optional[str] = None,
            noShowAgainButtons: typing.Optional[typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton]] = None,
            parent: QtWidgets.QWidget = None,
            ) -> QtWidgets.QMessageBox.StandardButton:
        if noShowAgainKey:
            settings = gui.globalWindowSettings()
            settings.beginGroup(MessageBoxEx._NoShowAgainConfigSection)
            savedResult = gui.safeLoadSetting(
                settings=settings,
                key=noShowAgainKey,
                type=int)
            settings.endGroup()
            # NOTE: If no show again buttons are specified, the saved result is only used
            # if it's one of the specified buttons.
            if (savedResult is not None) and ((noShowAgainButtons is None) or (savedResult & noShowAgainButtons)):
                return savedResult

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

        if noShowAgainKey:
            checkBox = gui.CheckBoxEx('Don\'t show again')

            # This is a bit of a hack to force some spacing between the main message
            # and the check box that allows the user to say the message shouldn't
            # be shown again.
            text += '\n'

        if checkBox:
            msgBox.setCheckBox(checkBox)

        if msgBox.exec() == -1:
            return QtWidgets.QMessageBox.StandardButton.Cancel

        result = msgBox.standardButton(msgBox.clickedButton())

        # NOTE: If no show again buttons are specified the result is only saved if it's
        # one of the valid buttons. This is mainly done to make the interfaces of different
        # messages boxes a bit easier to deal with
        # - Single button messages boxes (such as info boxes) can just specify the key and
        # the result will always be saved when the check box is checked
        # - Multi button messages boxes (such as questions) can specify only the affirmative
        # action button(s) are saved
        if noShowAgainKey and checkBox.isChecked() and ((noShowAgainButtons is None) or (result & noShowAgainButtons)):
            settings = gui.globalWindowSettings()
            settings.beginGroup(MessageBoxEx._NoShowAgainConfigSection)
            settings.setValue(noShowAgainKey, result)
            settings.endGroup()

        return result
