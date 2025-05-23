import app
import gui
import traveller
import typing
from PyQt5 import QtWidgets

class TradeGoodMultiSelectDialog(gui.DialogEx):
    def __init__(
            self,
            selectableTradeGoods: typing.Iterable[traveller.TradeGood] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Select Trade Goods',
            configSection='TradeGoodMultiSelectDialog',
            parent=parent)

        self._table = gui.TradeGoodTable()
        self._table.setCheckable(enable=True)
        if not selectableTradeGoods:
            selectableTradeGoods = traveller.tradeGoodList(
                rules=app.Config.instance().value(option=app.ConfigOption.Rules))
        for tradeGood in selectableTradeGoods:
            self._table.addTradeGood(tradeGood)

        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDefault(True)
        self._okButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        self._selectAllButton = QtWidgets.QPushButton('All')
        self._selectAllButton.clicked.connect(lambda: self._table.setAllRowCheckState(checkState=True))

        self._clearButton = QtWidgets.QPushButton('Clear')
        self._clearButton.clicked.connect(lambda: self._table.setAllRowCheckState(checkState=False))

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self._selectAllButton)
        buttonLayout.addWidget(self._clearButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._okButton)
        buttonLayout.addWidget(self._cancelButton)

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._table)
        dialogLayout.addLayout(buttonLayout)

        self.setLayout(dialogLayout)

    def selectedTradeGoods(self) -> None:
        return self._table.checkedTradeGoods()
