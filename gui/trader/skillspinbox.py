import app
import gui
import typing
from PyQt5 import QtWidgets

class SkillSpinBox(gui.SpinBoxEx):
    def __init__(
            self,
            value: int,
            toolTip: typing.Optional[str] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self.setRange(app.MinPossibleDm, app.MaxPossibleDm)
        self.setValue(value)
        if toolTip:
            self.setToolTip(toolTip)
