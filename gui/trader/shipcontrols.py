import app
import gui
import typing
from PyQt5 import QtWidgets

class ShipTonnageSpinBox(gui.SpinBoxEx):
    def __init__(
            self,
            value: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setRange(app.MinPossibleShipTonnage, app.MaxPossibleShipTonnage)
        self.setValue(int(value))
        self.setToolTip(gui.ShipTonnageToolTip)

class JumpRatingSpinBox(gui.SpinBoxEx):
    def __init__(
            self,
            value: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setRange(app.MinPossibleJumpRating, app.MaxPossibleJumpRating)
        self.setValue(int(value))
        self.setToolTip(gui.ShipJumpRatingToolTip)

class FuelCapacitySpinBox(gui.SpinBoxEx):
    def __init__(
            self,
            value: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setRange(0, app.MaxPossibleShipTonnage)
        self.setValue(int(value))
        self.setToolTip(gui.ShipFuelCapacityToolTip)

class CurrentFuelSpinBox(gui.DoubleSpinBoxEx):
    def __init__(
            self,
            value: float,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setRange(0, app.MaxPossibleShipTonnage)
        self.setValue(float(value))
        self.setToolTip(gui.ShipCurrentFuelToolTip)

class FuelPerParsecSpinBox(gui.TogglableDoubleSpinBox):
    def __init__(
            self,
            enabled: bool,
            value: float,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setChecked(enabled)
        self.setRange(0.1, app.MaxPossibleShipTonnage)
        self.setValue(float(value))
        self.setToolTip(gui.ShipFuelPerParsecToolTip)
