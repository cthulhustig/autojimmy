import gui
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

class ColourDialogEx(QtWidgets.QColorDialog):
    def __init__(
            self,
            initial: typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor] = QtCore.Qt.GlobalColor.white,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        if initial:
            super().__init__(initial, parent)
        else:
            super().__init__(parent)

    # This is a reimplementation of the QColorDialog static getColor
    # helper that displays the dialog and returns a colour. You can
    # check if the dialog was cancelled by checking if the colour is
    # valid (i.e. QColour.isValid())
    @staticmethod
    def getColor(
            initial: QtGui.QColor = QtCore.Qt.GlobalColor.white,
            parent: typing.Optional[QtWidgets.QWidget] = None,
            title: str = '',
            options: QtWidgets.QColorDialog.ColorDialogOptions = 0
            ) -> QtGui.QColor:
        dlg = ColourDialogEx(initial=initial, parent=parent)
        if title:
            dlg.setWindowTitle(title)
        dlg.setOptions(options)

        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return QtGui.QColor()

        return dlg.selectedColor()

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            # Setting up the title bar needs to be done before the window is show to take effect. It
            # needs to be done every time the window is shown as the setting is lost if the window is
            # closed then reshown
            gui.configureWindowTitleBar(widget=self)

        return super().showEvent(e)
