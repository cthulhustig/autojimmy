import common
import math
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
        self._configureFont()

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text
        self._configureFont()
        self.repaint()

    def resizeEvent(self, a0: QtGui.QResizeEvent | None) -> None:
        super().resizeEvent(a0)
        self._configureFont()

    def paintEvent(self, a0: QtGui.QPaintEvent | None) -> None:
        painter = QtGui.QPainter(self)

        usableArea = self.rect()
        painter.drawText(
            usableArea,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter,
            self._text)
        painter.end()

    def _configureFont(self) -> None:
        text = self.text()
        font = self.font()
        usableArea = self.rect()

        low = 1
        high = usableArea.height()
        best = None

        while low <= high:
            mid = low + ((high - low) // 2)
            font.setPixelSize(mid)
            fontMetrics = QtGui.QFontMetrics(font)
            contentRect = fontMetrics.boundingRect(text)
            contentRect.moveTo(0, 0)

            contained = usableArea.contains(contentRect)
            if (best == None or mid > best) and contained:
                best = mid

            if contained:
                low = mid + 1
            else:
                high = mid - 1

        if best != None:
            font.setPixelSize(best)
            self.setFont(font)