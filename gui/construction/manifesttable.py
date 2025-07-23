import app
import common
import construction
import enum
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class ManifestTable(gui.ListTable):
    class StdColumnType(enum.Enum):
        Component = 'Component'
        Factors = 'Other Factors'

    # I've disabled this for now as I'm not sure I like it. I think it makes
    # the table look uglier and I'm not sure it makes it any more readable
    _AddSpaceBetweenPhases = False

    def __init__(
            self,
            costsType: typing.Type[construction.ConstructionCost],
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._costType = costsType
        self._manifest = None

        columns = [ManifestTable.StdColumnType.Component]
        columns.extend(self._costType)
        columns.append(ManifestTable.StdColumnType.Factors)

        self.setColumnHeaders(columns)
        self.setColumnsMoveable(False)
        self.resizeColumnsToContents() # Size columns to header text
        self.resizeRowsToContents()
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setMinimumSectionSize(1)
        self.setWordWrap(True)

        self.setAlternatingRowColors(False)

        # Disable sorting as manifests should be kept in the order the occurred in
        self.setSortingEnabled(False)

    def setManifest(
            self,
            manifest: typing.Optional[construction.Manifest]
            ) -> None:
        self._manifest = manifest
        self.removeAllRows()
        if not self._manifest:
            self.resizeRowsToContents()
            return

        for section in self._manifest.sections():
            entries = section.entries()
            if not entries:
                continue

            for entry in entries:
                row = self.rowCount()
                self.insertRow(row)
                self._fillManifestEntryRow(row=row, entry=entry)

            row = self.rowCount()
            self.insertRow(row)
            self._fillManifestSectionTotalRow(row=row, section=section)

            if ManifestTable._AddSpaceBetweenPhases:
                row = self.rowCount()
                self.insertRow(row)
                self._fillSpacerRow(row=row)

        row = self.rowCount()
        if row > 0: # Only add total if something has been added to the manifest
            self.insertRow(row)
            self._fillManifestTotalRow(row=row)

        self.resizeColumnsToContents()
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)

    # Derived classes should reimplement this to add units
    def formatCost(
            self,
            costId: construction.ConstructionCost,
            cost: common.ScalarCalculation
            ) -> str:
        return common.formatNumber(cost.value())

    # Derived classes should reimplement this to override the
    # number of decimal places values should be displayed to
    def decimalPlaces(self) -> int:
        return 2

    def fillMenu(
            self,
            menu: QtWidgets.QMenu,
            pos: QtCore.QPoint
            ) -> None:
        super().fillMenu(menu, pos)

        selectedRowCalculations = []
        allRowCalculations = []
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            rowObject = item.data(QtCore.Qt.ItemDataRole.UserRole)

            rowCalculations = []
            for costId in self._costType:
                if isinstance(rowObject, construction.ManifestEntry):
                    costModifier = rowObject.cost(costId=costId)
                    if costModifier:
                        rowCalculations.append(costModifier.numericModifier())
                elif isinstance(rowObject, construction.ManifestSection):
                    rowCalculations.append(rowObject.totalCost(costId=costId))
                elif isinstance(rowObject, construction.Manifest):
                    rowCalculations.append(rowObject.totalCost(costId=costId))

            if isinstance(rowObject, construction.ManifestEntry):
                for factor in rowObject.factors():
                    rowCalculations.extend(factor.calculations())

            if rowCalculations:
                allRowCalculations.extend(rowCalculations)
                if self.isRowSelected(row):
                    selectedRowCalculations.extend(rowCalculations)

        menuHelper = gui.MenuHelper(menu)

        showSelected = QtWidgets.QAction("Show Selected...", self)
        showSelected.setEnabled(len(selectedRowCalculations) > 0)
        showSelected.triggered.connect(lambda: self._showCalculations(calculations=selectedRowCalculations))
        menuHelper.addAction(
            path=['Calculations'],
            action=showSelected)

        showAll = QtWidgets.QAction("Show All...", self)
        showAll.setEnabled(len(allRowCalculations) > 0)
        showAll.triggered.connect(lambda: self._showCalculations(calculations=allRowCalculations))
        menuHelper.addAction(
            path=['Calculations'],
            action=showAll)

    def _fillManifestEntryRow(
            self,
            row: int,
            entry: construction.ManifestEntry
            ) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == ManifestTable.StdColumnType.Component:
                tableItem = QtWidgets.QTableWidgetItem(entry.component())
            elif isinstance(columnType, self._costType):
                cost = entry.cost(costId=columnType)
                if cost:
                    if isinstance(cost, construction.ConstantModifier):
                        text = self.formatCost(
                            costId=columnType,
                            cost=cost.numericModifier())
                    else:
                        text = cost.displayString(
                            decimalPlaces=self.decimalPlaces())
                else:
                    text = '-'
                tableItem = QtWidgets.QTableWidgetItem(text)
            elif columnType == ManifestTable.StdColumnType.Factors:
                factorStrings = sorted([factor.displayString() for factor in entry.factors()])
                text = ''
                for factor in factorStrings:
                    if len(text) > 0:
                        text += '\n'
                    text += factor
                if not text:
                    text = '-'
                tableItem = QtWidgets.QTableWidgetItem(text)

            if tableItem:
                tableItem.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop))
                self.setItem(row, column, tableItem)
                tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, entry)
        self.resizeRowToContents(row)

    def _fillManifestSectionTotalRow(
            self,
            row: int,
            section: construction.ManifestSection
            ) -> None:
        bkColour = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorRole.AlternateBase)
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == ManifestTable.StdColumnType.Component:
                tableItem = QtWidgets.QTableWidgetItem(f'{section.name()} Total')
            elif isinstance(columnType, self._costType):
                cost = section.totalCost(costId=columnType)
                if cost.value():
                    itemText = self.formatCost(
                        costId=columnType,
                        cost=cost)
                else:
                    itemText = '-'
                tableItem = QtWidgets.QTableWidgetItem(itemText)
            elif columnType == ManifestTable.StdColumnType.Factors:
                tableItem = QtWidgets.QTableWidgetItem('-')

            if tableItem:
                font = tableItem.font()
                font.setBold(True)
                tableItem.setFont(font)

                tableItem.setBackground(bkColour)

                self.setItem(row, column, tableItem)
                tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, section)
        self.resizeRowToContents(row)

    def _fillManifestTotalRow(
            self,
            row: int
            ) -> None:
        bkColour = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorRole.AlternateBase)
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == ManifestTable.StdColumnType.Component:
                tableItem = QtWidgets.QTableWidgetItem(f'Total')
            elif isinstance(columnType, self._costType):
                cost = self._manifest.totalCost(costId=columnType)
                if cost.value():
                    text = self.formatCost(
                        costId=columnType,
                        cost=cost)
                else:
                    text = '-'
                tableItem = QtWidgets.QTableWidgetItem(text)
            elif columnType == ManifestTable.StdColumnType.Factors:
                tableItem = QtWidgets.QTableWidgetItem('-')

            if tableItem:
                font = tableItem.font()
                font.setBold(True)
                tableItem.setFont(font)

                tableItem.setBackground(bkColour)

                self.setItem(row, column, tableItem)
                tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, self._manifest)
        self.resizeRowToContents(row)

    def _fillSpacerRow(self, row: int) -> None:
        height = int(10 * gui.interfaceScale())
        for column in range(self.columnCount()):
            tableItem = QtWidgets.QTableWidgetItem()
            tableItem.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
            self.setItem(row, column, tableItem)
        self.setRowHeight(row, height)
        self.verticalHeader().resizeSection(row, height)

    def _showCalculations(
            self,
            calculations: typing.Iterable[common.ScalarCalculation]
            ) -> None:
        try:
            calculationWindow = gui.WindowManager.instance().showCalculationWindow()
            calculationWindow.showCalculations(
                calculations=calculations,
                decimalPlaces=self.decimalPlaces())
        except Exception as ex:
            message = 'Failed to show calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
