import common
import gui
import robots
import typing
from PyQt5 import QtWidgets

class RobotManifestTable(gui.ManifestTable):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            costsType=robots.RobotCost,
            parent=parent)

    def formatCost(
            self,
            costId: robots.RobotCost,
            cost: common.ScalarCalculation
            ) -> str:
        return common.formatNumber(
            number=cost.value(),
            decimalPlaces=self.decimalPlaces(),
            infix='Cr' if costId == robots.RobotCost.Credits else '')

    def decimalPlaces(self) -> int:
        return robots.ConstructionDecimalPlaces
