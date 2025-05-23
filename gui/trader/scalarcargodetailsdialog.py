import app
import common
import gui
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

# TODO: This needs update to handle rules changing
class ScalarCargoDetailsDialog(gui.DialogEx):
    def __init__(
            self,
            title: str,
            world: traveller.World,
            selectableTradeGoods: typing.Optional[typing.List[traveller.TradeGood]] = None,
            editTradeGood: typing.Optional[traveller.TradeGood] = None,
            editPricePerTon: typing.Optional[common.ScalarCalculation] = None,
            editQuantity: typing.Optional[common.ScalarCalculation] = None,
            lockPrice: bool = False,
            lockQuantity: bool = False,
            limitQuantity: typing.Optional[common.ScalarCalculation] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title=title,
            configSection='ScalarCargoDetailsDialog',
            parent=parent)

        self._world = world
        self._price = editPricePerTon if editPricePerTon != None else self._createCustomPricePerTon(0)
        self._quantity = editQuantity if editQuantity != None else self._createCustomQuantity(1)

        self._tradeGoodCombo = QtWidgets.QComboBox()
        if not editTradeGood:
            if not selectableTradeGoods:
                selectableTradeGoods = traveller.tradeGoodList(
                    rules=app.Config.instance().value(option=app.ConfigOption.Rules))
            for tradeGood in selectableTradeGoods:
                insertIndex = self._tradeGoodCombo.count()
                self._tradeGoodCombo.addItem(f'{tradeGood.id()}: {tradeGood.name()}')
                self._tradeGoodCombo.setItemData(insertIndex, tradeGood, QtCore.Qt.ItemDataRole.UserRole)
        else:
            self._tradeGoodCombo.addItem(f'{editTradeGood.id()}: {editTradeGood.name()}')
            self._tradeGoodCombo.setItemData(0, editTradeGood, QtCore.Qt.ItemDataRole.UserRole)
            self._tradeGoodCombo.setDisabled(True)
        self._tradeGoodCombo.currentIndexChanged.connect(self._syncControls)

        self._basePricePerTonLabel = QtWidgets.QLabel()
        self._baseAvailabilityRangeLabel = QtWidgets.QLabel()

        self._perTonPriceSpinBox = QtWidgets.QDoubleSpinBox()
        self._perTonPriceSpinBox.setRange(0, app.MaxPossibleCredits)
        self._perTonPriceSpinBox.setValue(self._price.value())
        self._perTonPriceSpinBox.valueChanged.connect(self._perTonPriceChanged)
        self._perTonPriceSpinBox.setDisabled(lockPrice)

        self._totalPriceSpinBox = QtWidgets.QDoubleSpinBox()
        self._totalPriceSpinBox.setRange(0, app.MaxPossibleCredits)
        self._totalPriceSpinBox.setValue(self._price.value() * self._quantity.value())
        self._totalPriceSpinBox.valueChanged.connect(self._totalPriceChanged)
        self._totalPriceSpinBox.setDisabled(lockPrice)

        self._quantitySpinBox = gui.SpinBoxEx()
        self._quantitySpinBox.setRange(
            1,
            int(limitQuantity.value()) if limitQuantity != None else app.MaxPossibleShipTonnage)
        self._quantitySpinBox.setValue(int(self._quantity.value()))
        self._quantitySpinBox.valueChanged.connect(self._quantityChanged)
        self._quantitySpinBox.setDisabled(lockQuantity)

        self._perTonPriceRadioButton = gui.RadioButtonEx('Price per ton (Cr):')
        self._perTonPriceRadioButton.setChecked(True)
        self._perTonPriceRadioButton.toggled.connect(self._syncControls)
        self._perTonPriceRadioButton.setDisabled(lockPrice)

        self._totalPriceRadioButton = gui.RadioButtonEx('Total price (Cr):')
        self._totalPriceRadioButton.toggled.connect(self._syncControls)
        self._totalPriceRadioButton.setDisabled(lockPrice)

        columnLayout = gui.FormLayoutEx()
        columnLayout.setContentsMargins(0, 0, 0, 0)
        columnLayout.addRow('Quantity (Tons):', self._quantitySpinBox)
        columnLayout.addRow(self._perTonPriceRadioButton, self._perTonPriceSpinBox)
        columnLayout.addRow(self._totalPriceRadioButton, self._totalPriceSpinBox)

        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDefault(True)
        self._okButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._okButton)
        buttonLayout.addWidget(self._cancelButton)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._tradeGoodCombo)
        windowLayout.addWidget(self._basePricePerTonLabel)
        windowLayout.addWidget(self._baseAvailabilityRangeLabel)
        windowLayout.addSpacing(10) # Put a small gap between labels and edit controls
        windowLayout.addLayout(columnLayout)
        windowLayout.addLayout(buttonLayout)
        self.setLayout(windowLayout)

        # Prevent the dialog being resized as there is no need to and it looks stupid if you do
        windowLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        self.setSizeGripEnabled(False)

        self._syncControls()

    def tradeGood(self) -> traveller.TradeGood:
        return self._tradeGoodCombo.currentData(QtCore.Qt.ItemDataRole.UserRole)

    def pricePerTon(self) -> common.ScalarCalculation:
        return self._price

    def quantity(self) -> common.ScalarCalculation:
        return self._quantity

    def _syncControls(self) -> None:
        tradeGood: traveller.TradeGood = self._tradeGoodCombo.currentData(QtCore.Qt.ItemDataRole.UserRole)
        baseAvailability = traveller.calculateWorldTradeGoodQuantity(
            rules=app.Config.instance().value(option=app.ConfigOption.Rules),
            world=self._world,
            tradeGood=tradeGood)
        basePrice = tradeGood.basePrice()
        self._baseAvailabilityRangeLabel.setText(
            f'Base availability (Tons): {baseAvailability.worstCaseValue()} - {baseAvailability.bestCaseValue()}')
        self._basePricePerTonLabel.setText(
            f'Base price per ton (Cr): {basePrice.value()}')

        if self._totalPriceRadioButton.isEnabled():
            self._totalPriceSpinBox.setDisabled(not self._totalPriceRadioButton.isChecked())
        if self._perTonPriceRadioButton.isEnabled():
            self._perTonPriceSpinBox.setDisabled(not self._perTonPriceRadioButton.isChecked())

    def _totalPriceChanged(self, value: float) -> None:
        if self._totalPriceRadioButton.isChecked():
            pricePerTon = value / self._quantitySpinBox.value()
            self._perTonPriceSpinBox.setValue(pricePerTon)
            self._price = self._createCustomPricePerTon(value=pricePerTon)

    def _perTonPriceChanged(self, value: float) -> None:
        if self._perTonPriceRadioButton.isChecked():
            self._totalPriceSpinBox.setValue(value * self._quantitySpinBox.value())
            self._price = self._createCustomPricePerTon(value=value)

    def _quantityChanged(self, value: int) -> None:
        assert(value > 0)
        if self._totalPriceRadioButton.isChecked():
            self._perTonPriceSpinBox.setValue(self._totalPriceSpinBox.value() / value)
        else:
            self._totalPriceSpinBox.setValue(self._perTonPriceSpinBox.value() * value)
        self._quantity = self._createCustomQuantity(value=value)

    @staticmethod
    def _createCustomPricePerTon(value: int) -> common.ScalarCalculation:
        return common.ScalarCalculation(
            value=value,
            name='Custom Purchase Price Per Ton')

    @staticmethod
    def _createCustomQuantity(value: int) -> common.ScalarCalculation:
        return common.ScalarCalculation(
            value=value,
            name='Custom Quantity')
