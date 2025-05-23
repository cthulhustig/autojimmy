import app
import common
import gui
import traveller
import typing
from PyQt5 import QtWidgets, QtCore

# TODO: This needs update to handle rules changing
class TradeGoodQuantityDialog(gui.DialogEx):
    def __init__(
            self,
            title: str,
            selectableTradeGoods: typing.Optional[typing.List[traveller.TradeGood]] = None,
            editTradeGood: typing.Optional[traveller.TradeGood] = None,
            editQuantity: typing.Optional[common.ScalarCalculation] = None,
            limitQuantity: typing.Optional[common.ScalarCalculation] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title=title,
            configSection='TradeGoodQuantityDialog',
            parent=parent)

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

        self._quantitySpinBox = gui.SpinBoxEx()
        self._quantitySpinBox.setRange(
            1,
            int(limitQuantity.value()) if limitQuantity != None else app.MaxPossibleShipTonnage)
        self._quantitySpinBox.setValue(int(self._quantity.value()))
        self._quantitySpinBox.valueChanged.connect(self._quantityChanged)

        columnLayout = gui.FormLayoutEx()
        columnLayout.setContentsMargins(0, 0, 0, 0)
        columnLayout.addRow('Quantity (Tons):', self._quantitySpinBox)

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
        windowLayout.addLayout(columnLayout)
        windowLayout.addSpacing(10) # Put a small gap between labels and edit controls
        windowLayout.addLayout(buttonLayout)
        self.setLayout(windowLayout)

        # Prevent the dialog being resized as there is no need to and it looks stupid if you do
        windowLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        self.setSizeGripEnabled(False)

    def tradeGood(self) -> traveller.TradeGood:
        return self._tradeGoodCombo.currentData(QtCore.Qt.ItemDataRole.UserRole)

    def quantity(self) -> common.ScalarCalculation:
        return self._quantity

    def _quantityChanged(self, value: int) -> None:
        self._quantity = self._createCustomQuantity(value=value)

    @staticmethod
    def _createCustomQuantity(value: int) -> common.ScalarCalculation:
        return common.ScalarCalculation(
            value=value,
            name='Custom Quantity')
