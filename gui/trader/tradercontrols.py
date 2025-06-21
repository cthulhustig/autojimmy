import app
import gui
import logic
import traveller
import typing
from PyQt5 import QtWidgets

# TODO: Need to check tooltips are correct for all these controls (and ones I added in other files)

class AvailableFundsSpinBox(gui.SpinBoxEx):
    def __init__(
            self,
            value: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setRange(0, app.MaxPossibleCredits)
        self.setValue(int(value))
        self.setToolTip(gui.AvailableFundsToolTip)

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

class SellerDMRangeWidget(gui.RangeSpinBoxWidget):
    def __init__(
            self,
            lowerValue: int,
            upperValue: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setLimits(app.MinPossibleDm, app.MaxPossibleDm)
        self.setValues(lowerValue, upperValue)
        self.setToolTip(gui.SellerDmToolTip)

class BuyerDMRangeWidget(gui.RangeSpinBoxWidget):
    def __init__(
            self,
            lowerValue: int,
            upperValue: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setLimits(app.MinPossibleDm, app.MaxPossibleDm)
        self.setValues(lowerValue, upperValue)
        self.setToolTip(gui.BuyerDmToolTip)

class LocalBrokerSpinBox(gui.TogglableSpinBox):
    def __init__(
            self,
            enabled: bool,
            value: int,
            rules: traveller.Rules,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self._rules = traveller.Rules(rules)

        self.setChecked(enabled)
        self.setValue(int(value))
        self._syncToRules()

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
        ruleSystem = self._rules.system()
        self.setRange(
            minValue=traveller.minLocalBrokerDm(ruleSystem=ruleSystem),
            maxValue=traveller.maxLocalBrokerDm(ruleSystem=ruleSystem))
        self.setToolTip(self._generateToolTip())

        if ruleSystem == traveller.RuleSystem.MGT2022:
            self.hideSpinBox()
        else:
            self.showSpinBox()

    def _generateToolTip(self) -> typing.Optional[str]:
        ruleSystem = self._rules.system()
        if ruleSystem == traveller.RuleSystem.MGT:
            return gui.MgtLocalBrokerToolTip
        elif ruleSystem == traveller.RuleSystem.MGT2:
            return gui.Mgt2LocalBrokerToolTip
        elif ruleSystem == traveller.RuleSystem.MGT2022:
            return gui.Mgt2022LocalBrokerToolTip
        return None


class RoutingTypeComboBox(gui.EnumComboBox):
    def __init__(
            self,
            value: logic.RoutingType,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(
            type=logic.RoutingType,
            value=value,
            isOptional=False,
            parent=parent)
        self.setToolTip(gui.RoutingTypeToolTip)

class RouteOptimisationComboBox(gui.EnumComboBox):
    def __init__(
            self,
            value: logic.RouteOptimisation,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(
            type=logic.RouteOptimisation,
            value=value,
            isOptional=False,
            parent=parent)
        self.setToolTip(gui.RouteOptimisationToolTip)

class JumpOverheadsSpinBox(gui.SpinBoxEx):
    def __init__(
            self,
            value: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setRange(0, app.MaxPossibleCredits)
        self.setValue(int(value))
        self.setToolTip(gui.PerJumpOverheadsToolTip)

class IncludeStartBerthingCheckBox(gui.CheckBoxEx):
    def __init__(
            self,
            value: bool,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setChecked(bool(value))
        self.setToolTip(gui.IncludeStartBerthingToolTip)

class IncludeFinishBerthingCheckBox(gui.CheckBoxEx):
    def __init__(
            self,
            value: bool,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setChecked(bool(value))
        self.setToolTip(gui.IncludeFinishBerthingToolTip)

class UseFuelCachesCheckBox(gui.CheckBoxEx):
    def __init__(
            self,
            value: bool,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setChecked(bool(value))
        self.setToolTip(gui.UseFuelCachesToolTip)

class UseAnomalyRefuellingCheckBox(gui.CheckBoxEx):
    def __init__(
            self,
            value: bool,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setChecked(bool(value))
        self.setToolTip(gui.AnomalyRefuellingToolTip)

class AnomalyFuelCostSpinBox(gui.SpinBoxEx):
    def __init__(
            self,
            value: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setRange(0, app.MaxPossibleCredits)
        self.setValue(int(value))
        self.setToolTip(gui.AnomalyFuelCostToolTip)

class AnomalyBerthingCostSpinBox(gui.SpinBoxEx):
    def __init__(
            self,
            value: int,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setRange(0, app.MaxPossibleCredits)
        self.setValue(int(value))
        self.setToolTip(gui.AnomalyBerthingCostToolTip)

class RefuellingStrategyComboBox(gui.EnumComboBox):
    def __init__(
            self,
            value: logic.RefuellingStrategy,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(
            type=logic.RefuellingStrategy,
            value=value,
            isOptional=False,
            parent=parent)
        self.setToolTip(gui.RefuellingStrategyToolTip)

class IncludeLogisticsCostsCheckBox(gui.CheckBoxEx):
    def __init__(
            self,
            value: bool,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setChecked(bool(value))
        self.setToolTip(gui.IncludeLogisticsCostsToolTip)

class ShowUnprofitableTradesCheckBox(gui.CheckBoxEx):
    def __init__(
            self,
            value: bool,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ):
        super().__init__(parent)
        self.setChecked(bool(value))
        self.setToolTip(gui.ShowUnprofitableTradesToolTip)
