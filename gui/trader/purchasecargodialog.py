import app
import common
import gui
import logic
import traveller
import typing
from PyQt5 import QtCore, QtWidgets

# TODO: Rather than registering for config updates the dialog should
# have the values passed to it by its creator
# TODO: This probably needs updated to handle the rules changing as it
# invalidates an current cargo records. I'm not sure what the correct
# thing to do is
class PurchaseCargoDialog(gui.DialogEx):
    _CargoRecordColumns = [
        gui.CargoRecordTable.ColumnType.TradeGood,
        gui.CargoRecordTable.ColumnType.SetPricePerTon,
        gui.CargoRecordTable.ColumnType.SetQuantity]

    def __init__(
            self,
            world: traveller.World,
            availableCargo: typing.Iterable[logic.CargoRecord],
            availableFunds: typing.Union[int, float, common.ScalarCalculation],
            freeCargoCapacity: typing.Union[int, common.ScalarCalculation],
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Purchase Cargo Dialog',
            configSection='PurchaseCargoDialog',
            parent=parent)

        self._world = world

        self._availableFunds = availableFunds
        if not isinstance(self._availableFunds, common.ScalarCalculation):
            assert(isinstance(self._availableFunds, int) or isinstance(self._availableFunds, float))
            self._availableFunds = common.ScalarCalculation(
                value=self._availableFunds,
                name='Available Funds')
        self._freeCargoCapacity = freeCargoCapacity
        if not isinstance(self._freeCargoCapacity, common.ScalarCalculation):
            assert(isinstance(self._freeCargoCapacity, int))
            self._freeCargoCapacity = common.ScalarCalculation(
                value=self._freeCargoCapacity,
                name='Cargo Capacity')

        self._totalCost = common.ScalarCalculation(value=0, name='Total Cost')

        self._availableFundsLabel = gui.PrefixLabel(
            prefix='Funds: ',
            text=common.formatNumber(
                number=self._availableFunds.value(),
                infix='Cr'))

        outcomeColours = app.Config.instance().value(
            option=app.ConfigOption.OutcomeColours)

        self._availableCargoTable = gui.CargoRecordTable(
            outcomeColours=outcomeColours,
            columns=PurchaseCargoDialog._CargoRecordColumns)
        self._availableCargoTable.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._availableCargoTable.selectionModel().selectionChanged.connect(
            self._availableSelectionChanged)
        if availableCargo:
            self._availableCargoTable.addCargoRecords(cargoRecords=availableCargo)

        availableLayout = QtWidgets.QVBoxLayout()
        availableLayout.addWidget(self._availableFundsLabel)
        availableLayout.addWidget(self._availableCargoTable)
        availableGroupBox = QtWidgets.QGroupBox('Available')
        availableGroupBox.setLayout(availableLayout)

        self._totalCostLabel = gui.PrefixLabel(
            prefix='Total: ',
            text=common.formatNumber(
                number=self._totalCost.value(),
                infix='Cr'))

        self._purchaseCargoTable = gui.CargoRecordTable(
            outcomeColours=outcomeColours,
            columns=PurchaseCargoDialog._CargoRecordColumns)
        self._purchaseCargoTable.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._purchaseCargoTable.selectionModel().selectionChanged.connect(
            self._purchaseSelectionChanged)

        purchaseLayout = QtWidgets.QVBoxLayout()
        purchaseLayout.addWidget(self._totalCostLabel)
        purchaseLayout.addWidget(self._purchaseCargoTable)
        purchaseGroupBox = QtWidgets.QGroupBox('Purchase')
        purchaseGroupBox.setLayout(purchaseLayout)

        self._purchaseCargoButton = QtWidgets.QToolButton()
        self._purchaseCargoButton.setText('Purchase >')
        self._purchaseCargoButton.clicked.connect(self._promptPurchaseGoods)
        self._purchaseCargoButton.setDisabled(True)

        self._returnCargoButton = QtWidgets.QToolButton()
        self._returnCargoButton.setText('< Return')
        self._returnCargoButton.clicked.connect(self._promptReturnGoods)
        self._returnCargoButton.setDisabled(True)

        moveLayout = QtWidgets.QVBoxLayout()
        moveLayout.addStretch()
        moveLayout.addWidget(
            self._purchaseCargoButton,
            alignment=QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        moveLayout.addWidget(
            self._returnCargoButton,
            alignment=QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        moveLayout.addStretch()

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

        tableLayout = QtWidgets.QHBoxLayout()
        tableLayout.setContentsMargins(0, 0, 0, 0)
        tableLayout.addWidget(availableGroupBox)
        tableLayout.addLayout(moveLayout)
        tableLayout.addWidget(purchaseGroupBox)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(tableLayout)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

        app.Config.instance().configChanged.connect(self._appConfigChanged)

    def purchasedCargo(self) -> typing.Iterable[logic.CargoRecord]:
        return self._purchaseCargoTable.cargoRecords()

    def remainingCargo(self) -> typing.Iterable[logic.CargoRecord]:
        return self._availableCargoTable.cargoRecords()

    def _appConfigChanged(
            self,
            option: app.ConfigOption,
            oldValue: typing.Any,
            newValue: typing.Any
            ) -> None:
        if option is app.ConfigOption.OutcomeColours:
            self._availableCargoTable.setOutcomeColours(colours=newValue)
            self._purchaseCargoTable.setOutcomeColours(colours=newValue)

    def _availableSelectionChanged(self) -> None:
        enable = self._availableFunds.value() > 0 and \
            self._freeCargoCapacity.value() > 0 and \
            self._availableCargoTable.hasSelection()
        self._purchaseCargoButton.setEnabled(enable)

    def _purchaseSelectionChanged(self) -> None:
        enable = self._purchaseCargoTable.hasSelection()
        self._returnCargoButton.setEnabled(enable)

    def _promptPurchaseGoods(self) -> None:
        self._moveCargoBetweenTables(isPurchase=True)

    def _promptReturnGoods(self) -> None:
        self._moveCargoBetweenTables(isPurchase=False)

    def _moveCargoBetweenTables(
            self,
            isPurchase
            ) -> None:
        if isPurchase:
            fromTable = self._availableCargoTable
            toTable = self._purchaseCargoTable
        else:
            fromTable = self._purchaseCargoTable
            toTable = self._availableCargoTable

        fromRow = fromTable.currentRow()
        if fromRow < 0:
            return # No selection, nothing to do

        originalCargoRecord = fromTable.cargoRecord(row=fromRow)
        originalQuantity = originalCargoRecord.quantity()
        originalPricePerTon = originalCargoRecord.pricePerTon()

        # This shouldn't happen but do something vaguely sensible just in case
        if isinstance(originalQuantity, common.RangeCalculation):
            originalQuantity = originalPricePerTon.averageCaseCalculation()
        if isinstance(originalPricePerTon, common.RangeCalculation):
            originalPricePerTon = originalPricePerTon.averageCaseCalculation()

        if isPurchase and originalPricePerTon.value() > 0:
            maxQuantity = common.Calculator.divideFloor(
                lhs=self._availableFunds,
                rhs=originalPricePerTon)
            maxQuantity = common.Calculator.min(
                lhs=maxQuantity,
                rhs=originalQuantity,
                name='Affordable Quantity')
        else:
            maxQuantity = originalCargoRecord.quantity()

        if isPurchase:
            maxQuantity = common.Calculator.min(
                lhs=maxQuantity,
                rhs=self._freeCargoCapacity)

        dlg = gui.ScalarCargoDetailsDialog(
            parent=self,
            title='Cargo Quantity',
            world=self._world,
            editTradeGood=originalCargoRecord.tradeGood(),
            editPricePerTon=originalPricePerTon,
            lockPrice=True,
            editQuantity=maxQuantity,
            limitQuantity=maxQuantity)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        selectedQuantity = dlg.quantity()
        if selectedQuantity.value() == originalQuantity.value():
            toCargoRecord = originalCargoRecord
            fromCargoRecord = None
        else:
            toCargoRecord = logic.CargoRecord(
                tradeGood=originalCargoRecord.tradeGood(),
                pricePerTon=originalPricePerTon,
                quantity=selectedQuantity)
            fromCargoRecord = logic.CargoRecord(
                tradeGood=originalCargoRecord.tradeGood(),
                pricePerTon=originalPricePerTon,
                quantity=common.Calculator.subtract(
                    lhs=originalQuantity,
                    rhs=toCargoRecord.quantity(),
                    name=originalQuantity.name()))

        if fromCargoRecord:
            fromTable.setCargoRecord(row=fromRow, cargoRecord=fromCargoRecord)
        else:
            fromTable.removeRow(fromRow)
        toTable.addCargoRecord(cargoRecord=toCargoRecord)

        cargoCost = common.Calculator.multiply(
            lhs=selectedQuantity,
            rhs=originalPricePerTon)

        if isPurchase:
            self._availableFunds = common.Calculator.subtract(
                lhs=self._availableFunds,
                rhs=cargoCost,
                name=self._availableFunds.name())
            self._totalCost = common.Calculator.add(
                lhs=self._totalCost,
                rhs=cargoCost,
                name=self._totalCost.name())
            self._freeCargoCapacity = common.Calculator.subtract(
                lhs=self._freeCargoCapacity,
                rhs=selectedQuantity,
                name=self._freeCargoCapacity.name())
        else:
            self._availableFunds = common.Calculator.add(
                lhs=self._availableFunds,
                rhs=cargoCost,
                name=self._availableFunds.name())
            self._totalCost = common.Calculator.subtract(
                lhs=self._totalCost,
                rhs=cargoCost,
                name=self._totalCost.name())
            self._freeCargoCapacity = common.Calculator.add(
                lhs=self._freeCargoCapacity,
                rhs=selectedQuantity,
                name=self._freeCargoCapacity.name())

        self._availableFundsLabel.setText(common.formatNumber(
            number=self._availableFunds.value(),
            infix='Cr'))
        self._totalCostLabel.setText(common.formatNumber(
            number=self._totalCost.value(),
            infix='Cr'))
