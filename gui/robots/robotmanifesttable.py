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
        self._weapon = None

    def formatCost(
            self,
            costId: robots.RobotCost,
            cost: common.ScalarCalculation
            ) -> str:
        text = common.formatNumber(
            number=cost.value(),
            decimalPlaces=self.decimalPlaces())
        if costId == robots.RobotCost.Credits:
            return 'Cr' + text
        elif costId == robots.RobotCost.Slots:
            return text
        elif costId == robots.RobotCost.Bandwidth:
            return text

        return '????' # Should never happen

    def decimalPlaces(self) -> int:
        return robots.ConstructionDecimalPlaces
