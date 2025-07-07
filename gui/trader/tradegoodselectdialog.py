import gui
import traveller
import typing
from PyQt5 import QtWidgets

class TradeGoodSelectDialog(gui.DialogEx):
    def __init__(
            self,
            rules: traveller.Rules,
            filterCallback: typing.Optional[typing.Callable[[traveller.TradeGood], bool]] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Select Trade Goods',
            # NOTE: The config section name differs from the class name for
            # backwards compatibility
            configSection='TradeGoodMultiSelectDialog',
            parent=parent)

        self._table = gui.TradeGoodTable(
            rules=rules,
            filterCallback=filterCallback)
        self._table.setCheckable(enable=True)

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
