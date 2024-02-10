import common
import gui
import gunsmith
import typing
from PyQt5 import QtWidgets

class WeaponManifestTable(gui.ManifestTable):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            costsType=gunsmith.WeaponCost,
            parent=parent)
        self._weapon = None

    def formatCost(
            self,
            costId: gunsmith.WeaponCost,
            cost: common.ScalarCalculation
            ) -> str:
        text = common.formatNumber(
            number=cost.value(),
            decimalPlaces=self.decimalPlaces())
        if costId == gunsmith.WeaponCost.Credits:
            return 'Cr' + text
        elif costId == gunsmith.WeaponCost.Weight:
            return text + 'kg'

        return '????' # Should never happen

    def decimalPlaces(self) -> int:
        return gunsmith.ConstructionDecimalPlaces
