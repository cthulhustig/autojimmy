import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class FullSizeTextWidget(QtWidgets.QWidget):
    def __init__(
            self,
            text: str = '',
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._text = text
        self._alignment = QtCore.Qt.AlignmentFlag.AlignCenter
        self._configureFont()

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text
        self._configureFont()
        self.repaint()

    def alignment(self) -> QtCore.Qt.AlignmentFlag:
        return self._alignment

    def setAlignment(self, align: QtCore.Qt.AlignmentFlag) -> None:
        self._alignment = align

    def resizeEvent(self, a0: typing.Optional[QtGui.QResizeEvent]) -> None:
        super().resizeEvent(a0)
        self._configureFont()

    def paintEvent(self, a0: typing.Optional[QtGui.QPaintEvent]) -> None:
        painter = QtGui.QPainter(self)
        painter.drawText(
            self.rect(),
            self.alignment(),
            self.text())
        painter.end()

    def _configureFont(self) -> None:
        font = gui.sizeFontToFit(
            orig=self.font(),
            text=self.text(),
            rect=self.rect(),
            align=self.alignment())
        if font:
            self.setFont(font)
