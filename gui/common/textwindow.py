import gui
import typing
from PyQt5 import QtWidgets

class TextWindow(gui.WindowWidget):
    def __init__(
            self,
            title: str,
            configSection: str,
            text: typing.Optional[str] = None,
            html: typing.Optional[str] = None,
            readOnly: typing.Optional[bool] = False
            ) -> None:
        super().__init__(
            title=title,
            configSection=configSection)

        self._textEdit = QtWidgets.QTextEdit()
        if text != None:
            self._textEdit.setText(text)
        elif html != None:
            self._textEdit.setHtml(html)
        self._textEdit.setReadOnly(readOnly)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._textEdit)
        self.setLayout(windowLayout)

    def text(self) -> str:
        return self._textEdit.toPlainText()

    def setText(
            self,
            text: str
            ) -> None:
        self._textEdit.setText(text)

    def html(self) -> str:
        return self._textEdit.toHtml()

    def setHtml(
            self,
            html: str
            ) -> None:
        self._textEdit.setHtml(html)

    def setReadOnly(self, readOnly: bool) -> None:
        self._textEdit.setReadOnly(readOnly)

    def isReadOnly(self) -> bool:
        return self._textEdit.isReadOnly()
