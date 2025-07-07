import gui
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

class ColourButton(QtWidgets.QPushButton):
    colourChanged = QtCore.pyqtSignal(QtGui.QColor)

    _ColourBoxMargin = 4
    _ColourBoxOutlineWidth = 1

    def __init__(
            self,
            colour: QtGui.QColor
            ) -> None:
        super().__init__()
        self._colour = QtGui.QColor(colour)
        self.clicked.connect(self._showColourSelect)

    def colour(self) -> QtGui.QColor:
        return QtGui.QColor(self._colour)

    def setColour(self, colour: QtGui.QColor) -> None:
        if colour == self._colour:
            return

        self._colour = QtGui.QColor(colour)
        self.colourChanged.emit(QtGui.QColor(self._colour))
        self.update() # Force redraw

    def paintEvent(
            self,
            event: typing.Optional[QtGui.QPaintEvent]
            ) -> None:
        super().paintEvent(event)

        palette = self.palette()
        outlineColour = palette.color(QtGui.QPalette.ColorRole.Shadow)

        margin = int(ColourButton._ColourBoxMargin * gui.interfaceScale())
        rect = self.rect()
        rect = rect.adjusted(margin, margin, -margin, -margin)

        outlineWidth = int(ColourButton._ColourBoxOutlineWidth * gui.interfaceScale())
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(outlineColour, outlineWidth, QtCore.Qt.PenStyle.SolidLine))
        painter.setBrush(QtGui.QBrush(self._colour, QtCore.Qt.BrushStyle.SolidPattern))
        painter.drawRect(rect)

    def _showColourSelect(self) -> None:
        colour = gui.ColourDialogEx.getColor(
            initial=self._colour,
            parent=self,
            options=QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel | QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if not colour.isValid():
            return # Dialog cancelled

        self.setColour(colour=colour)
