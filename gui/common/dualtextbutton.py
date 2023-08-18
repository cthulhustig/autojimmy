import typing
from PyQt5 import QtWidgets

class DualTextPushButton(QtWidgets.QPushButton):
    def __init__(
        self,
        primaryText: str,
        secondaryText: str,
        parent: typing.Optional[QtWidgets.QWidget] = None
    ):
        super().__init__(primaryText, parent)
        self._primaryText = primaryText
        self._secondaryText = secondaryText

    def setPrimaryText(self, text: str, show: False) -> None:
        self._primaryText = text
        if show:
            self.showPrimaryText()

    def showPrimaryText(self) -> None:
        self.setText(self._primaryText)

    def setSecondaryText(self, text: str, show: False) -> None:
        self._secondaryText = text
        if show:
            self.showSecondaryText()

    def showSecondaryText(self) -> None:
        self.setText(self._secondaryText)
