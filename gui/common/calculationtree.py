import common
import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class CalculationTree(QtWidgets.QTreeWidget):
    Columns = [
        'Name',
        'Value',
        'Calculation'
    ]

    def __init__(self) -> None:
        super().__init__()

        self.setColumnCount(len(CalculationTree.Columns))
        self.setHeaderLabels(CalculationTree.Columns)
        self.setAlternatingRowColors(True)
        # Setup horizontal scroll bar. Setting the last column to stretch to fit it's content
        # is required to make the it appear reliably
        self.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.header().setSectionResizeMode(
            self.columnCount() - 1,
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.header().setStretchLastSection(False)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)

    def calculations(self) -> typing.Iterable[common.Calculation]:
        calculations = []
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            calculation = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if isinstance(calculation, common.Calculation):
                calculations.append(calculation)
        return calculations

    def showCalculation(
            self,
            calculation: common.Calculation,
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        if gui.isShiftKeyDown():
            self.addCalculation(
                calculation=calculation,
                expand=expand,
                decimalPlaces=decimalPlaces)
        else:
            self.setCalculation(
                calculation=calculation,
                expand=expand,
                decimalPlaces=decimalPlaces)

    def showCalculations(
            self,
            calculations: typing.Iterable[common.Calculation],
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        if gui.isShiftKeyDown():
            self.addCalculations(
                calculations=calculations,
                expand=expand,
                decimalPlaces=decimalPlaces)
        else:
            self.setCalculations(
                calculations=calculations,
                expand=expand,
                decimalPlaces=decimalPlaces)

    def setCalculation(
            self,
            calculation: common.Calculation,
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        self.clear()
        self.addCalculation(
            calculation=calculation,
            expand=expand,
            decimalPlaces=decimalPlaces)

    def setCalculations(
            self,
            calculations: typing.Iterable[common.Calculation],
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        self.clear()
        self.addCalculations(
            calculations=calculations,
            expand=expand,
            decimalPlaces=decimalPlaces)

    def addCalculation(
            self,
            calculation: common.Calculation,
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        if isinstance(calculation, common.ScalarCalculation):
            self._addTopLevelCalculation(
                calculation=calculation,
                expand=expand,
                decimalPlaces=decimalPlaces)
        else:
            assert(isinstance(calculation, common.RangeCalculation))
            self._addTopLevelCalculation(
                calculation=calculation.averageCaseCalculation(),
                expand=expand,
                decimalPlaces=decimalPlaces)
            self._addTopLevelCalculation(
                calculation=calculation.worstCaseCalculation(),
                expand=expand,
                decimalPlaces=decimalPlaces)
            self._addTopLevelCalculation(
                calculation=calculation.bestCaseCalculation(),
                expand=expand,
                decimalPlaces=decimalPlaces)

    def addCalculations(
            self,
            calculations: typing.Iterable[common.Calculation],
            expand: bool = True,
            decimalPlaces: int = 2
            ) -> None:
        for value in calculations:
            self.addCalculation(
                calculation=value,
                expand=expand,
                decimalPlaces=decimalPlaces)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        position = event.pos()
        index = self.indexAt(position)
        if not index.isValid():
            return # Nothing to do

        clickItem = self.itemFromIndex(index)
        rootItem = self.invisibleRootItem()
        itemIndex = rootItem.indexOfChild(clickItem)

        if itemIndex == -1:
            return # Only display menu on top level items

        removeSelectedAction = QtWidgets.QAction('Remove')
        removeSelectedAction.triggered.connect(lambda: self.takeTopLevelItem(itemIndex))

        removeAllAction = QtWidgets.QAction('Remove All')
        removeAllAction.triggered.connect(self.clear)

        menu = QtWidgets.QMenu()
        menu.addAction(removeSelectedAction)
        menu.addAction(removeAllAction)
        menu.exec(self.viewport().mapToGlobal(position))

        # Don't call base class as we've handled the event
        #return super().contextMenuEvent(event)

    def _addTopLevelCalculation(
            self,
            calculation: common.ScalarCalculation,
            expand: bool,
            decimalPlaces: int
            ) -> None:
        item = self._createCalculationItem(
            calculation=calculation,
            decimalPlaces=decimalPlaces)
        self.addTopLevelItem(item)
        if expand:
            self.expandRecursively(self.indexFromItem(item))

    @staticmethod
    def _createCalculationItem(
            calculation: common.ScalarCalculation,
            decimalPlaces: int
            ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([
            str(calculation.name()),
            common.formatNumber(
                number=calculation.value(),
                thousandsSeparator=False,
                infinityString='infinity',
                decimalPlaces=decimalPlaces),
            calculation.calculationString(
                outerBrackets=False,
                decimalPlaces=decimalPlaces)
        ])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, calculation)

        for subCalculation in calculation.subCalculations():
            item.addChild(CalculationTree._createCalculationItem(
                calculation=subCalculation,
                decimalPlaces=decimalPlaces))
        return item
