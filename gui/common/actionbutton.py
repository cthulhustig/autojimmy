import typing
from PyQt5 import QtWidgets

class ActionButton(QtWidgets.QPushButton):
    def __init__(
            self,
            action: typing.Optional[QtWidgets.QAction] = None,
            text: typing.Optional[str] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self._action = None
        self._customText = text
        self.setAction(action)
        self.clicked.connect(self._buttonClicked)

    def action(self) -> typing.Optional[QtWidgets.QAction]:
        return self._action

    def setAction(self, action: typing.Optional[QtWidgets.QAction]) -> None:
        if action == self._action:
            return

        if self._action:
            self._unhookAction()

        self._action = action
        self._syncButton()

        if self._action:
            self._hookAction()

    def customText(self) -> typing.Optional[str]:
        return self._customText

    def setCustomText(self, text: typing.Optional[str]) -> None:
        if text == self._customText:
            return

        self._customText = text
        self._syncButton()

    def _syncButton(self) -> None:
        if self._action:
            self.setText(self._customText if self._customText else self._action.text())
            self.setEnabled(self._action.isEnabled() and self._action.isVisible())
        else:
            self.setText('')
            self.setEnabled(False)

    def _hookAction(self) -> None:
        if self._action:
            self._action.changed.connect(self._syncButton)

    def _unhookAction(self) -> None:
        if self._action:
            self._action.changed.disconnect(self._syncButton)

    def _buttonClicked(self) -> None:
        if self._action:
            self._action.trigger()
