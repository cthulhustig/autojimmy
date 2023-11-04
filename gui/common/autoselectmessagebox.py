import gui
import typing
from PyQt5 import QtWidgets

class AutoSelectMessageBox(object):
    _SettingSection = 'AutoSelectMessageBox'
    _CheckBoxText = 'Don\'t show again'

    class _NoShowAgainStateCapture(object):
        def __init__(self) -> None:
            self._checked = False

        def isChecked(self) -> bool:
            return self._checked

        def setChecked(self, state: bool) -> None:
            self._checked = state

    @staticmethod
    def information(
            text: str,
            stateKey: str,
            title: str = 'Information',
            parent: typing.Optional[QtWidgets.QWidget] = None,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.Ok,
            defaultButton: typing.Optional[QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            rememberState: typing.Optional[QtWidgets.QMessageBox.StandardButton] = None
            ) -> QtWidgets.QMessageBox.StandardButton:
        return AutoSelectMessageBox.showMessageBox(
            parent=parent,
            icon=gui.MessageBoxEx.Icon.Information,
            title=title,
            text=text,
            buttons=buttons,
            defaultButton=defaultButton,
            stateKey=stateKey,
            rememberState=rememberState)

    @staticmethod
    def critical(
            text: str,
            stateKey: str,
            title: str = 'Error',
            parent: typing.Optional[QtWidgets.QWidget] = None,
            exception: typing.Optional[Exception] = None,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.Ok,
            defaultButton: typing.Optional[QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            rememberState: typing.Optional[QtWidgets.QMessageBox.StandardButton] = None
            ) -> QtWidgets.QMessageBox.StandardButton:
        if exception:
            if text:
                text += '\n\n' + str(exception)
            else:
                text = str(exception)
        return AutoSelectMessageBox.showMessageBox(
            parent=parent,
            icon=gui.MessageBoxEx.Icon.Critical,
            title=title,
            text=text,
            buttons=buttons,
            defaultButton=defaultButton,
            stateKey=stateKey,
            rememberState=rememberState)

    @staticmethod
    def warning(
            text: str,
            stateKey: str,
            title: str = 'Warning',
            parent: typing.Optional[QtWidgets.QWidget] = None,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.Ok,
            defaultButton: typing.Optional[QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            rememberState: typing.Optional[QtWidgets.QMessageBox.StandardButton] = None
            ) -> QtWidgets.QMessageBox.StandardButton:
        return AutoSelectMessageBox.showMessageBox(
            parent=parent,
            icon=gui.MessageBoxEx.Icon.Warning,
            title=title,
            text=text,
            buttons=buttons,
            defaultButton=defaultButton,
            stateKey=stateKey,
            rememberState=rememberState)

    @staticmethod
    def question(
            text: str,
            stateKey: str,
            title: str = 'Prompt',
            parent: typing.Optional[QtWidgets.QWidget] = None,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            defaultButton: typing.Optional[QtWidgets.QMessageBox.StandardButton] = QtWidgets.QMessageBox.StandardButton.NoButton,
            rememberState: typing.Optional[QtWidgets.QMessageBox.StandardButton] = None
            ) -> QtWidgets.QMessageBox.StandardButton:
        return AutoSelectMessageBox.showMessageBox(
            parent=parent,
            icon=gui.MessageBoxEx.Icon.Question,
            title=title,
            text=text,
            buttons=buttons,
            defaultButton=defaultButton,
            stateKey=stateKey,
            rememberState=rememberState)

    @staticmethod
    def showMessageBox(
            icon: QtWidgets.QMessageBox.Icon,
            title: str,
            text: str,
            buttons: typing.Union[QtWidgets.QMessageBox.StandardButtons, QtWidgets.QMessageBox.StandardButton],
            defaultButton: QtWidgets.QMessageBox.StandardButton,
            stateKey: str,
            rememberState: typing.Optional[QtWidgets.QMessageBox.StandardButton],
            parent: QtWidgets.QWidget = None
            ) -> QtWidgets.QMessageBox.StandardButton:
        buttonEnumMap = gui.pyQtEnumMapping(QtWidgets.QMessageBox, QtWidgets.QMessageBox.StandardButton)

        settings = gui.globalWindowSettings()
        settings.beginGroup(AutoSelectMessageBox._SettingSection)
        autoSelect = gui.safeLoadSetting(
            settings=settings,
            key=stateKey,
            type=str,
            default=None)
        settings.endGroup()

        if autoSelect != None:
            # Map the name of the button enum to its int value
            autoSelect = buttonEnumMap.get(autoSelect)
            if (autoSelect != None) and ((not rememberState) or (autoSelect == rememberState)):
                return autoSelect

        # Set up the 'No show again' check box. A bit of a hack is needed as it looks like the check
        # box will be destroyed when the dialog closed meaning it's state can't be read back after
        noShowAgainState = AutoSelectMessageBox._NoShowAgainStateCapture()
        checkBox = gui.CheckBoxEx(AutoSelectMessageBox._CheckBoxText)
        checkBox.setChecked(False)
        checkBox.stateChanged.connect(lambda state, stateCapture=noShowAgainState: stateCapture.setChecked(state != 0))

        result = gui.MessageBoxEx.showMessageBox(
            parent=parent,
            icon=icon,
            title=title,
            text=text,
            buttons=buttons,
            defaultButton=defaultButton,
            checkBox=checkBox)

        if noShowAgainState.isChecked() and ((not rememberState) or (rememberState == result)):
            # Map button enums int value to its name
            autoSelect = buttonEnumMap.get(result)
            if autoSelect != None:
                settings.beginGroup(AutoSelectMessageBox._SettingSection)
                settings.setValue(stateKey, autoSelect)
                settings.endGroup()

        return result
