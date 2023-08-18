import app
import app
import gui
import traveller
import typing
from PyQt5 import QtWidgets

class LocalBrokerWidget(gui.TogglableSpinBox):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        rules = app.Config.instance().rules()
        minLocalBrokerDm = traveller.minLocalBrokerDm(rules=rules)
        maxLocalBrokerDm = traveller.maxLocalBrokerDm(rules=rules)

        self.setRange(minLocalBrokerDm, maxLocalBrokerDm)
        self.setValue(minLocalBrokerDm)
        self.setChecked(False)

        if rules == traveller.Rules.MGT:
            self.setToolTip(gui.MgtLocalBrokerToolTip)
        elif rules == traveller.Rules.MGT2:
            self.setToolTip(gui.Mgt2LocalBrokerToolTip)
        elif rules == traveller.Rules.MGT2022:
            self.setToolTip(gui.Mgt2022LocalBrokerToolTip)
            self.hideSpinBox()

    def value(self, rawValue: bool = False) -> int | None:
        if app.Config.instance().rules() == traveller.Rules.MGT2022:
            # HACK: For 2022 rules return a raw value of 0 to stop consumers barfing
            return 0 if rawValue else None
        return super().value(rawValue)
