import gui
import typing
from PyQt5 import QtWidgets, QtGui, QtCore

class ColourDialogEx(QtWidgets.QColorDialog):
    def __init__(
            self,
            initial: typing.Optional[typing.Union[QtGui.QColor, QtCore.Qt.GlobalColor]] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        if initial:
            super().__init__(initial, parent)
        else:
            super().__init__(parent)

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            # Setting up the title bar needs to be done before the window is show to take effect. It
            # needs to be done every time the window is shown as the setting is lost if the window is
            # closed then reshown
            gui.configureWindowTitleBar(widget=self)

        return super().showEvent(e)
