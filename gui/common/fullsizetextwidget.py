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

    # Based on some code from here
    # https://stackoverflow.com/questions/42652738/how-to-automatically-increase-decrease-text-size-in-label-in-qt
    def _configureFont(self) -> None:
        text = self.text()
        font = self.font()
        size = font.pointSize()
        fontMetrics = QtGui.QFontMetrics(font)
        usableArea = self.rect()
        contentRect = fontMetrics.boundingRect(
            usableArea,
            0,
            text)

        # decide whether to increase or decrease
        if (contentRect.height() > usableArea.height()) or \
            (contentRect.width() > usableArea.width()):
            step = -1
        else:
            step = 1

        # iterate until text fits best into rectangle of label
        while(True):
            font.setPointSize(size + step)
            fontMetrics = QtGui.QFontMetrics(font)
            contentRect = fontMetrics.boundingRect(
                usableArea,
                0,
                text)
            if (step < 0):
                if (size <= 1):
                    break
                size += step
                if (contentRect.height() < usableArea.height()) and \
                    (contentRect.width() < usableArea.width()):
                    # Stop as soon as the new size would mean both the
                    # content dimensions are within the usable area
                    break
            else:
                if (contentRect.height() > usableArea.height()) or \
                    (contentRect.width() > usableArea.width()):
                    # Stop as soon as the new size would mean either of
                    # the content dimensions were larger than the usable
                    # area
                    break
                size += step

        font.setPointSize(size)
        self.setFont(font)