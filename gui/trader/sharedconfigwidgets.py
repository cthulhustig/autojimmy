import app
import enum
import gui
import logic
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

class _SpinBoxUpdater(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__(None)

        self._widgets: typing.Set[typing.Union[gui.SpinBoxEx, gui.DoubleSpinBoxEx]] = set()
        self._ignoreNotifications = False

    def attach(self, widget: typing.Union[gui.SpinBoxEx, gui.DoubleSpinBoxEx]) -> None:
        widget.setValue(self.loadValue())
        widget.valueChanged.connect(lambda value: self._valueChanged(widget, value))
        widget.destroyed.connect(self.detach)
        self._widgets.add(widget)

    def detach(self, widget: typing.Union[gui.SpinBoxEx, gui.DoubleSpinBoxEx]) -> None:
        if widget in self._widgets:
            self._widgets.remove(widget)
        widget.destroyed.disconnect(self.detach)

    def loadValue(self) -> int:
        raise RuntimeError('The loadValue method should be overridden by derived _SpinBoxUpdater')

    def saveValue(self, value: int) -> None:
        raise RuntimeError('The saveValue method should be overridden by derived _SpinBoxUpdater')

    def _valueChanged(
            self,
            widget: typing.Union[gui.SpinBoxEx, gui.DoubleSpinBoxEx],
            value: typing.Union[int, float]
            ) -> None:
        if self._ignoreNotifications:
            return # Events are currently being ignored so nothing to do

        # Save the setting
        self.saveValue(value=value)

        # Push new value to other attached widgets. Blocking signals can't be used as we want
        # the widget being updated to still notify other observers
        self._ignoreNotifications = True

        try:
            for other in self._widgets:
                if other != widget:
                    other.setValue(value)
        finally:
            self._ignoreNotifications = False

class _TogglableSpinBoxUpdater(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__(None)

        self._widgets: typing.Set[typing.Union[gui.TogglableSpinBox, gui.TogglableDoubleSpinBox]] = set()
        self._ignoreNotifications = False

    def attach(self, widget: typing.Union[gui.TogglableSpinBox, gui.TogglableDoubleSpinBox]) -> None:
        enabled, value = self.loadValue()
        widget.setConfig(enabled, value)
        widget.valueChanged.connect(lambda value: self._valueChanged(widget, value))
        widget.destroyed.connect(self.detach)
        self._widgets.add(widget)

    def detach(self, widget: typing.Union[gui.TogglableSpinBox, gui.TogglableDoubleSpinBox]) -> None:
        if widget in self._widgets:
            self._widgets.remove(widget)
        widget.destroyed.disconnect(self.detach)

    def loadValue(self) -> typing.Tuple[bool, int]:
        raise RuntimeError('The loadValue method should be overridden by derived _TogglableSpinBoxUpdater')

    def saveValue(self, enabled: bool, value: int) -> None:
        raise RuntimeError('The saveValue method should be overridden by derived _TogglableSpinBoxUpdater')

    def _valueChanged(
            self,
            widget: typing.Union[gui.TogglableSpinBox, gui.TogglableDoubleSpinBox],
            value: typing.Optional[typing.Union[int, float]]
            ) -> None:
        if self._ignoreNotifications:
            return # Events are currently being ignored so nothing to do

        # Retrieve the raw config from the widget. This gets that set value even if the widget
        # is disabled
        enabled, value = widget.config()
        self.saveValue(enabled, value)

        # Push new value to other attached widgets. Blocking signals can't be used as we want
        # the widget being updated to still notify other observers
        self._ignoreNotifications = True

        try:
            for other in self._widgets:
                if other != widget:
                    other.setConfig(enabled, value)
        finally:
            self._ignoreNotifications = False

class _EnumComboBoxUpdater(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__(None)

        self._widgets: typing.Set[gui.EnumComboBox] = set()
        self._ignoreNotifications = False

    def attach(self, widget: gui.EnumComboBox) -> None:
        widget.setCurrentEnum(self.loadValue())
        widget.currentIndexChanged.connect(lambda: self._indexChanged(widget))
        widget.destroyed.connect(self.detach)
        self._widgets.add(widget)

    def detach(self, widget: gui.EnumComboBox) -> None:
        if widget in self._widgets:
            self._widgets.remove(widget)
        widget.destroyed.disconnect(self.detach)

    def loadValue(self) -> enum.Enum:
        raise RuntimeError('The loadValue method should be overridden by derived _EnumComboBoxUpdater')

    def saveValue(self, value: enum.Enum) -> None:
        raise RuntimeError('The saveValue method should be overridden by derived _EnumComboBoxUpdater')

    def _indexChanged(
            self,
            widget: gui.EnumComboBox
            ) -> None:
        if self._ignoreNotifications:
            return # Events are currently being ignored so nothing to do

        value = widget.currentEnum()

        # Save the setting
        self.saveValue(value=value)

        # Push new value to other attached widgets. Blocking signals can't be used as we want
        # the widget being updated to still notify other observers
        self._ignoreNotifications = True

        try:
            for other in self._widgets:
                if other != widget:
                    other.setCurrentEnum(value)
        finally:
            self._ignoreNotifications = False

class _CheckBoxUpdater(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__(None)

        self._widgets: typing.Set[gui.CheckBoxEx] = set()
        self._ignoreNotifications = False

    def attach(self, widget: gui.CheckBoxEx) -> None:
        widget.setChecked(self.loadValue())
        widget.stateChanged.connect(lambda: self._valueChanged(widget))
        widget.destroyed.connect(self.detach)
        self._widgets.add(widget)

    def detach(self, widget: gui.CheckBoxEx) -> None:
        if widget in self._widgets:
            self._widgets.remove(widget)
        widget.destroyed.disconnect(self.detach)

    def loadValue(self) -> int:
        raise RuntimeError('The loadValue method should be overridden by derived _CheckBoxUpdater')

    def saveValue(self, value: int) -> None:
        raise RuntimeError('The saveValue method should be overridden by derived _CheckBoxUpdater')

    def _valueChanged(
            self,
            widget: gui.CheckBoxEx
            ) -> None:
        if self._ignoreNotifications:
            return # Events are currently being ignored so nothing to do

        value = widget.isChecked()

        # Save the setting
        self.saveValue(value=value)

        # Push new value to other attached widgets. Blocking signals can't be used as we want
        # the widget being updated to still notify other observers
        self._ignoreNotifications = True

        try:
            for other in self._widgets:
                if other != widget:
                    other.setChecked(value)
        finally:
            self._ignoreNotifications = False

class _RangeUpdater(QtCore.QObject):
    def __init__(self) -> None:
        super().__init__(None)

        self._widgets: typing.Set[gui.RangeSpinBoxWidget] = set()
        self._ignoreNotifications = False

    def attach(self, widget: gui.RangeSpinBoxWidget) -> None:
        minValue, maxValue = self.loadValue()
        widget.setValues(lowerValue=minValue, upperValue=maxValue)
        widget.rangeChanged.connect(lambda: self._rangeChanged(widget))
        widget.destroyed.connect(self.detach)
        self._widgets.add(widget)

    def detach(self, widget: gui.RangeSpinBoxWidget) -> None:
        if widget in self._widgets:
            self._widgets.remove(widget)
        widget.destroyed.disconnect(self.detach)

    def loadValue(self) -> typing.Tuple[int, int]:
        raise RuntimeError('The loadValue method should be overridden by derived _RangeUpdater')

    def saveValue(self, lowerValue: int, upperValue: int) -> None:
        raise RuntimeError('The saveValue method should be overridden by derived _RangeUpdater')

    def _rangeChanged(
            self,
            widget: gui.RangeSpinBoxWidget
            ) -> None:
        if self._ignoreNotifications:
            return # Events are currently being ignored so nothing to do

        lowerValue = widget.lowerValue()
        upperValue = widget.upperValue()

        # Save the setting
        self.saveValue(lowerValue=lowerValue, upperValue=upperValue)

        # Push new value to other attached widgets. Blocking signals can't be used as we want
        # the widget being updated to still notify other observers
        self._ignoreNotifications = True

        try:
            for other in self._widgets:
                if other != widget:
                    other.setValues(lowerValue=lowerValue, upperValue=upperValue)
        finally:
            self._ignoreNotifications = False

class _SharedSpinBox(gui.SpinBoxEx):
    _updaterMap: typing.Dict[typing.Type[gui.SpinBoxEx], _SpinBoxUpdater] = {}

    def __init__(
            self,
            updaterType: typing.Type[_SpinBoxUpdater],
            minValue: int,
            maxValue: int,
            toolTip: str,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self.setRange(minValue, maxValue)
        self.setToolTip(toolTip)

        # Create shared setting updater if it doesn't exist and attach this widget to it
        updater = self._updaterMap.get(type(self))
        if not updater:
            updater = updaterType()
            self._updaterMap[type(self)] = updater
        updater.attach(self)

class _SharedDoubleSpinBox(gui.DoubleSpinBoxEx):
    _updaterMap: typing.Dict[typing.Type[gui.DoubleSpinBoxEx], _SpinBoxUpdater] = {}

    def __init__(
            self,
            updaterType: typing.Type[_SpinBoxUpdater],
            minValue: float,
            maxValue: float,
            toolTip: str,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self.setRange(minValue, maxValue)
        self.setToolTip(toolTip)

        # Create shared setting updater if it doesn't exist and attach this widget to it
        updater = self._updaterMap.get(type(self))
        if not updater:
            updater = updaterType()
            self._updaterMap[type(self)] = updater
        updater.attach(self)

class _SharedTogglableSpinBox(gui.TogglableSpinBox):
    _updaterMap: typing.Dict[typing.Type[gui.TogglableSpinBox], _TogglableSpinBoxUpdater] = {}

    def __init__(
            self,
            updaterType: typing.Type[_TogglableSpinBoxUpdater],
            minValue: int,
            maxValue: int,
            toolTip: str,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self.setRange(minValue, maxValue)
        self.setToolTip(toolTip)

        # Create shared setting updater if it doesn't exist and attach this widget to it
        updater = self._updaterMap.get(type(self))
        if not updater:
            updater = updaterType()
            self._updaterMap[type(self)] = updater
        updater.attach(self)

class _SharedTogglableDoubleSpinBox(gui.TogglableDoubleSpinBox):
    _updaterMap: typing.Dict[typing.Type[gui.TogglableDoubleSpinBox], _TogglableSpinBoxUpdater] = {}

    def __init__(
            self,
            updaterType: typing.Type[_TogglableSpinBoxUpdater],
            minValue: float,
            maxValue: float,
            toolTip: str,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self.setRange(minValue, maxValue)
        self.setToolTip(toolTip)

        # Create shared setting updater if it doesn't exist and attach this widget to it
        updater = self._updaterMap.get(type(self))
        if not updater:
            updater = updaterType()
            self._updaterMap[type(self)] = updater
        updater.attach(self)

class _SharedEnumComboBox(gui.EnumComboBox):
    _updaterMap: typing.Dict[typing.Type[gui.EnumComboBox], _EnumComboBoxUpdater] = {}

    def __init__(
            self,
            updaterType: typing.Type[_SpinBoxUpdater],
            enumType: typing.Type[enum.Enum],
            toolTip: str,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            type=enumType,
            parent=parent)

        self.setToolTip(toolTip)

        # Create shared setting updater if it doesn't exist and attach this widget to it
        updater = self._updaterMap.get(type(self))
        if not updater:
            updater = updaterType()
            self._updaterMap[type(self)] = updater
        updater.attach(self)

class _SharedCheckBox(gui.CheckBoxEx):
    _updaterMap: typing.Dict[typing.Type[gui.CheckBoxEx], _CheckBoxUpdater] = {}

    def __init__(
            self,
            updaterType: typing.Type[_CheckBoxUpdater],
            toolTip: str,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self.setToolTip(toolTip)

        # Create shared setting updater if it doesn't exist and attach this widget to it
        updater = self._updaterMap.get(type(self))
        if not updater:
            updater = updaterType()
            self._updaterMap[type(self)] = updater
        updater.attach(self)

class _SharedRangeWidget(gui.RangeSpinBoxWidget):
    _updaterMap: typing.Dict[typing.Type[gui.RangeSpinBoxWidget], _RangeUpdater] = {}

    def __init__(
            self,
            updaterType: typing.Type[_RangeUpdater],
            minValue: int,
            maxValue: int,
            toolTip: str,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self.setLimits(minValue, maxValue)
        self.setToolTip(toolTip)

        # Create shared setting updater if it doesn't exist and attach this widget to it
        updater = self._updaterMap.get(type(self))
        if not updater:
            updater = updaterType()
            self._updaterMap[type(self)] = updater
        updater.attach(self)

class SharedPlayerBrokerDMSpinBox(_SharedSpinBox):
    class _SettingUpdater(_SpinBoxUpdater):
        def loadValue(self) -> int:
            return app.Config.instance().playerBrokerDm()

        def saveValue(self, value: int) -> None:
            return app.Config.instance().setPlayerBrokerDm(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedPlayerBrokerDMSpinBox._SettingUpdater,
            minValue=app.MinPossibleDm,
            maxValue=app.MaxPossibleDm,
            toolTip=gui.PlayerBrokerDmToolTip,
            parent=parent)

class SharedShipTonnageSpinBox(_SharedSpinBox):
    class _SettingUpdater(_SpinBoxUpdater):
        def loadValue(self) -> int:
            return app.Config.instance().shipTonnage()

        def saveValue(self, value: int) -> None:
            return app.Config.instance().setShipTonnage(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedShipTonnageSpinBox._SettingUpdater,
            minValue=app.MinPossibleShipTonnage,
            maxValue=app.MaxPossibleShipTonnage,
            toolTip=gui.ShipTonnageToolTip,
            parent=parent)

class SharedJumpRatingSpinBox(_SharedSpinBox):
    class _SettingUpdater(_SpinBoxUpdater):
        def loadValue(self) -> int:
            return app.Config.instance().shipJumpRating()

        def saveValue(self, value: int) -> None:
            return app.Config.instance().setShipJumpRating(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedJumpRatingSpinBox._SettingUpdater,
            minValue=app.MinPossibleJumpRating,
            maxValue=app.MaxPossibleJumpRating,
            toolTip=gui.ShipJumpRatingToolTip,
            parent=parent)

class SharedFuelCapacitySpinBox(_SharedSpinBox):
    class _SettingUpdater(_SpinBoxUpdater):
        def loadValue(self) -> int:
            return app.Config.instance().shipFuelCapacity()

        def saveValue(self, value: int) -> None:
            return app.Config.instance().setShipFuelCapacity(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedFuelCapacitySpinBox._SettingUpdater,
            minValue=0,
            maxValue=app.MaxPossibleShipTonnage,
            toolTip=gui.ShipFuelCapacityToolTip,
            parent=parent)

class SharedCurrentFuelSpinBox(_SharedDoubleSpinBox):
    class _SettingUpdater(_SpinBoxUpdater):
        def loadValue(self) -> float:
            return app.Config.instance().shipCurrentFuel()

        def saveValue(self, value: float) -> None:
            return app.Config.instance().setShipCurrentFuel(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedCurrentFuelSpinBox._SettingUpdater,
            minValue=0,
            maxValue=app.MaxPossibleShipTonnage,
            toolTip=gui.ShipCurrentFuelToolTip,
            parent=parent)

class SharedFuelPerParsecSpinBox(_SharedTogglableDoubleSpinBox):
    class _SettingUpdater(_TogglableSpinBoxUpdater):
        def loadValue(self) -> typing.Tuple[bool, float]:
            return (app.Config.instance().useShipFuelPerParsec(),
                    app.Config.instance().shipFuelPerParsec())

        def saveValue(self, enabled: bool, value: float) -> None:
            app.Config.instance().setUseShipFuelPerParsec(enabled)
            app.Config.instance().setShipFuelPerParsec(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedFuelPerParsecSpinBox._SettingUpdater,
            minValue=0.1,
            maxValue=app.MaxPossibleShipTonnage,
            toolTip=gui.ShipFuelPerParsecToolTip,
            parent=parent)

class SharedFreeCargoSpaceSpinBox(_SharedSpinBox):
    class _SettingUpdater(_SpinBoxUpdater):
        def loadValue(self) -> int:
            return app.Config.instance().shipCargoCapacity()

        def saveValue(self, value: int) -> None:
            return app.Config.instance().setShipCargoCapacity(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedFreeCargoSpaceSpinBox._SettingUpdater,
            minValue=0,
            maxValue=app.MaxPossibleShipTonnage,
            toolTip=gui.FreeCargoSpaceToolTip,
            parent=parent)

class SharedJumpOverheadSpinBox(_SharedSpinBox):
    class _SettingUpdater(_SpinBoxUpdater):
        def loadValue(self) -> int:
            return app.Config.instance().perJumpOverheads()

        def saveValue(self, value: int) -> None:
            return app.Config.instance().setPerJumpOverheads(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedJumpOverheadSpinBox._SettingUpdater,
            minValue=0,
            maxValue=app.MaxPossibleCredits,
            toolTip=gui.PerJumpOverheadsToolTip,
            parent=parent)

class SharedAvailableFundsSpinBox(_SharedSpinBox):
    class _SettingUpdater(_SpinBoxUpdater):
        def loadValue(self) -> int:
            return app.Config.instance().availableFunds()

        def saveValue(self, value: int) -> None:
            return app.Config.instance().setAvailableFunds(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedAvailableFundsSpinBox._SettingUpdater,
            minValue=0,
            maxValue=app.MaxPossibleCredits,
            toolTip=gui.AvailableFundsToolTip,
            parent=parent)

class SharedRefuellingStrategyComboBox(_SharedEnumComboBox):
    class _SettingUpdater(_EnumComboBoxUpdater):
        def loadValue(self) -> logic.RefuellingStrategy:
            return app.Config.instance().refuellingStrategy()

        def saveValue(self, value: logic.RefuellingStrategy) -> None:
            return app.Config.instance().setRefuellingStrategy(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedRefuellingStrategyComboBox._SettingUpdater,
            enumType=logic.RefuellingStrategy,
            toolTip=gui.RefuellingStrategyToolTip,
            parent=parent)

class SharedUseFuelCachesCheckBox(_SharedCheckBox):
    class _SettingUpdater(_CheckBoxUpdater):
        def loadValue(self) -> bool:
            return app.Config.instance().useFuelCaches()

        def saveValue(self, value: bool) -> None:
            return app.Config.instance().setUseFuelCaches(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedUseFuelCachesCheckBox._SettingUpdater,
            toolTip=gui.UseFuelCachesToolTip,
            parent=parent)

class SharedUseAnomalyRefuellingCheckBox(_SharedCheckBox):
    class _SettingUpdater(_CheckBoxUpdater):
        def loadValue(self) -> bool:
            return app.Config.instance().useAnomalyRefuelling()

        def saveValue(self, value: bool) -> None:
            return app.Config.instance().setUseAnomalyRefuelling(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedUseAnomalyRefuellingCheckBox._SettingUpdater,
            toolTip=gui.AnomalyRefuellingToolTip,
            parent=parent)

class SharedAnomalyFuelCostSpinBox(_SharedSpinBox):
    class _SettingUpdater(_SpinBoxUpdater):
        def loadValue(self) -> int:
            return app.Config.instance().anomalyFuelCost()

        def saveValue(self, value: int) -> None:
            app.Config.instance().setAnomalyFuelCost(value)

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            updaterType=SharedAnomalyFuelCostSpinBox._SettingUpdater,
            minValue=0,
            maxValue=app.MaxPossibleCredits,
            toolTip=gui.AnomalyFuelCostToolTip,
            parent=parent)

class SharedAnomalyBerthingCostSpinBox(_SharedSpinBox):
    class _SettingUpdater(_SpinBoxUpdater):
        def loadValue(self) -> int:
            return app.Config.instance().anomalyBerthingCost()

        def saveValue(self, value: int) -> None:
            app.Config.instance().setAnomalyBerthingCost(value)

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            updaterType=SharedAnomalyBerthingCostSpinBox._SettingUpdater,
            minValue=0,
            maxValue=app.MaxPossibleCredits,
            toolTip=gui.AnomalyBerthingCostToolTip,
            parent=parent)

class SharedRoutingTypeComboBox(_SharedEnumComboBox):
    class _SettingUpdater(_EnumComboBoxUpdater):
        def loadValue(self) -> logic.RoutingType:
            return app.Config.instance().routingType()

        def saveValue(self, value: logic.RoutingType) -> None:
            return app.Config.instance().setRoutingType(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedRoutingTypeComboBox._SettingUpdater,
            enumType=logic.RoutingType,
            toolTip=gui.RoutingTypeToolTip,
            parent=parent)

class SharedRouteOptimisationComboBox(_SharedEnumComboBox):
    class _SettingUpdater(_EnumComboBoxUpdater):
        def loadValue(self) -> logic.RouteOptimisation:
            return app.Config.instance().routeOptimisation()

        def saveValue(self, value: logic.RouteOptimisation) -> None:
            return app.Config.instance().setRouteOptimisation(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedRouteOptimisationComboBox._SettingUpdater,
            enumType=logic.RouteOptimisation,
            toolTip=gui.RouteOptimisationToolTip,
            parent=parent)

class SharedIncludeStartBerthingCheckBox(_SharedCheckBox):
    class _SettingUpdater(_CheckBoxUpdater):
        def loadValue(self) -> bool:
            return app.Config.instance().includeStartBerthing()

        def saveValue(self, value: bool) -> None:
            return app.Config.instance().setIncludeStartBerthing(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedIncludeStartBerthingCheckBox._SettingUpdater,
            toolTip=gui.IncludeStartBerthingToolTip,
            parent=parent)

class SharedIncludeFinishBerthingCheckBox(_SharedCheckBox):
    class _SettingUpdater(_CheckBoxUpdater):
        def loadValue(self) -> bool:
            return app.Config.instance().includeFinishBerthing()

        def saveValue(self, value: bool) -> None:
            return app.Config.instance().setIncludeFinishBerthing(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedIncludeFinishBerthingCheckBox._SettingUpdater,
            toolTip=gui.IncludeFinishBerthingToolTip,
            parent=parent)

class SharedIncludeLogisticsCostsCheckBox(_SharedCheckBox):
    class _SettingUpdater(_CheckBoxUpdater):
        def loadValue(self) -> bool:
            return app.Config.instance().includeLogisticsCosts()

        def saveValue(self, value: bool) -> None:
            return app.Config.instance().setIncludeLogisticsCosts(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedIncludeLogisticsCostsCheckBox._SettingUpdater,
            toolTip=gui.IncludeLogisticsCostsToolTip,
            parent=parent)

class SharedIncludeUnprofitableCheckBox(_SharedCheckBox):
    class _SettingUpdater(_CheckBoxUpdater):
        def loadValue(self) -> bool:
            return app.Config.instance().includeUnprofitableTrades()

        def saveValue(self, value: bool) -> None:
            return app.Config.instance().setIncludeUnprofitableTrades(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedIncludeUnprofitableCheckBox._SettingUpdater,
            toolTip=gui.IncludeUnprofitableTradesToolTip,
            parent=parent)

class SharedSellerDMRangeWidget(_SharedRangeWidget):
    class _SettingUpdater(_RangeUpdater):
        def loadValue(self) -> typing.Tuple[int, int]:
            return app.Config.instance().sellerDmRange()

        def saveValue(self, lowerValue: int, upperValue: int) -> None:
            return app.Config.instance().setSellerDmRange(lowerValue=lowerValue, upperValue=upperValue)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedSellerDMRangeWidget._SettingUpdater,
            minValue=app.MinPossibleDm,
            maxValue=app.MaxPossibleDm,
            toolTip=gui.SellerDmToolTip,
            parent=parent)

class SharedBuyerDMRangeWidget(_SharedRangeWidget):
    class _SettingUpdater(_RangeUpdater):
        def loadValue(self) -> typing.Tuple[int, int]:
            return app.Config.instance().buyerDmRange()

        def saveValue(self, lowerValue: int, upperValue: int) -> None:
            return app.Config.instance().setBuyerDmRange(minValue=lowerValue, maxValue=upperValue)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedBuyerDMRangeWidget._SettingUpdater,
            minValue=app.MinPossibleDm,
            maxValue=app.MaxPossibleDm,
            toolTip=gui.BuyerDmToolTip,
            parent=parent)

class _SharedLocalBrokerSpinBoxBase(_SharedTogglableSpinBox):
    def __init__(
            self,
            updaterType: _TogglableSpinBoxUpdater,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        rules = app.Config.instance().rules()
        super().__init__(
            updaterType=updaterType,
            minValue=traveller.minLocalBrokerDm(rules=rules),
            maxValue=traveller.maxLocalBrokerDm(rules=rules),
            toolTip=self._ruleSpecificToolTip(rules=rules),
            parent=parent)

        if rules.system() == traveller.RuleSystem.MGT2022:
            self.hideSpinBox()

    def value(self, rawValue: bool = False) -> typing.Optional[int]:
        rules = app.Config.instance().rules()
        if rules.system() == traveller.RuleSystem.MGT2022:
            # HACK: For 2022 rules return a raw value of 0 to stop consumers barfing
            return 0 if rawValue else None
        return super().value(rawValue)

    @staticmethod
    def _ruleSpecificToolTip(rules: traveller.Rules):
        ruleSystem = rules.system()
        if ruleSystem == traveller.RuleSystem.MGT:
            return gui.MgtLocalBrokerToolTip
        elif ruleSystem == traveller.RuleSystem.MGT2:
            return gui.Mgt2LocalBrokerToolTip
        elif ruleSystem == traveller.RuleSystem.MGT2022:
            return gui.Mgt2022LocalBrokerToolTip
        return None

class SharedLocalPurchaseBrokerSpinBox(_SharedLocalBrokerSpinBoxBase):
    class _SettingUpdater(_TogglableSpinBoxUpdater):
        def loadValue(self) -> typing.Tuple[bool, int]:
            return (app.Config.instance().usePurchaseBroker(),
                    app.Config.instance().purchaseBrokerDmBonus())

        def saveValue(self, enabled: bool, value: int) -> None:
            app.Config.instance().setUsePurchaseBroker(enabled)
            app.Config.instance().setPurchaseBrokerDmBonus(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedLocalPurchaseBrokerSpinBox._SettingUpdater,
            parent=parent)

class SharedLocalSaleBrokerSpinBox(_SharedLocalBrokerSpinBoxBase):
    class _SettingUpdater(_TogglableSpinBoxUpdater):
        def loadValue(self) -> typing.Tuple[bool, int]:
            return (app.Config.instance().useSaleBroker(),
                    app.Config.instance().saleBrokerDmBonus())

        def saveValue(self, enabled: bool, value: int) -> None:
            app.Config.instance().setUseSaleBroker(enabled)
            app.Config.instance().setSaleBrokerDmBonus(value)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            updaterType=SharedLocalSaleBrokerSpinBox._SettingUpdater,
            parent=parent)
