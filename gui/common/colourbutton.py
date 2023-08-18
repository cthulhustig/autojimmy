import gui
from PyQt5 import QtWidgets, QtGui

class ColourButton(QtWidgets.QPushButton):
    def __init__(
            self,
            colour: str
            ) -> None:
        super().__init__()
        self.setColour(colour)
        self.clicked.connect(self._showColourSelect)

    def colour(self) -> str:
        return self._colour

    def setColour(self, colour: str) -> None:
        self._colour = colour
        self.setStyleSheet(f'QPushButton {{border:1px solid; border-color=#000000; background-color: {colour}}}')

    def _showColourSelect(self) -> None:
        dlg = gui.ColourDialogEx()
        dlg.setOptions(QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel | QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog)
        dlg.setCurrentColor(QtGui.QColor(self._colour))
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return # Cancelled

        colour = dlg.currentColor()
        colour = f'#{colour.alpha():02X}{colour.red():02X}{colour.green():02X}{colour.blue():02X}'
        self.setColour(colour)
