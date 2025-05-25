import app
import app
import gui
import traveller
import typing
from PyQt5 import QtWidgets

class LocalBrokerWidget(gui.TogglableSpinBox):
    def __init__(
            self,
            rules: traveller.Rules,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._rules = traveller.Rules(rules)
        self._syncToRules()

    def rules(self) -> traveller.Rules:
        return traveller.Rules(self._rules)

    def setRules(self, rules: traveller.Rules) -> None:
        if rules == self._rules:
            return
        self._rules = traveller.Rules(rules)
        self._syncToRules()

    def value(self, rawValue: bool = False) -> typing.Optional[int]:
        if self._rules.system() == traveller.RuleSystem.MGT2022:
            # HACK: For 2022 rules return a raw value of 0 to stop consumers barfing
            return 0 if rawValue else None
        return super().value(rawValue)

    def _syncToRules(self) -> None:
        minLocalBrokerDm = traveller.minLocalBrokerDm(ruleSystem=self._rules.system())
        maxLocalBrokerDm = traveller.maxLocalBrokerDm(ruleSystem=self._rules.system())

        self.setRange(minLocalBrokerDm, maxLocalBrokerDm)
        self.setValue(minLocalBrokerDm)
        self.setChecked(False)

        ruleSystem = self._rules.system()
        if ruleSystem == traveller.RuleSystem.MGT:
            self.setToolTip(gui.MgtLocalBrokerToolTip)
        elif ruleSystem == traveller.RuleSystem.MGT2:
            self.setToolTip(gui.Mgt2LocalBrokerToolTip)
        elif ruleSystem == traveller.RuleSystem.MGT2022:
            self.setToolTip(gui.Mgt2022LocalBrokerToolTip)
            self.hideSpinBox()
