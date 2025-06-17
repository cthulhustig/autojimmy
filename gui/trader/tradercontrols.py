import app
import gui
import typing
from PyQt5 import QtWidgets

class MaxCargoTonnageSpinBox(gui.SpinBoxEx):
    def __init__(
            self,
            value: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setRange(1, app.MaxPossibleShipTonnage)
        self.setValue(int(value))
        self.setToolTip(gui.MaxCargoTonnageToolTip)
