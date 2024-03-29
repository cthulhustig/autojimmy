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
        self.resizeColumnsToContents() # Size columns to header text
        self.resizeRowsToContents()
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._showContextMenu)
        self.setWordWrap(True)

        self.setAlternatingRowColors(False)

        # Disable sorting as manifests should be kept in the order the occurred in
        self.setSortingEnabled(False)

    def setManifest(
            self,
            manifest: typing.Optional[construction.Manifest]
            ) -> None:
        self._manifest = manifest
        self.update()

    def update(self) -> None:
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

        row = self.rowCount()
        if row > 0: # Only add total if something has been added to the manifest
            self.insertRow(row)
            self._fillManifestTotalRow(row=row)

        self.resizeRowsToContents()
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

    def _fillManifestTotalRow(
            self,
            row: int
            ) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == ManifestTable.StdColumnType.Component:
                tableItem = QtWidgets.QTableWidgetItem(f'Total')
            elif isinstance(columnType, self._costType):
                cost = self._manifest.totalCost(costId=columnType)
                text = self.formatCost(
                    costId=columnType,
                    cost=cost)
                tableItem = QtWidgets.QTableWidgetItem(text)
            elif columnType == ManifestTable.StdColumnType.Factors:
                tableItem = QtWidgets.QTableWidgetItem('-')

            if tableItem:
                font = tableItem.font()
                font.setBold(True)
                tableItem.setFont(font)

                self.setItem(row, column, tableItem)
                tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, self._manifest)

    def _showContextMenu(
            self,
            position: QtCore.QPoint
            ) -> None:
        item = self.itemAt(position)
        if not item:
            return # Nothing to do
        column = self.columnHeader(column=item.column())

        rowObject = item.data(QtCore.Qt.ItemDataRole.UserRole)
        calculations = []

        for costId in self._costType:
            if column != costId and column != ManifestTable.StdColumnType.Component:
                continue

            if isinstance(rowObject, construction.ManifestEntry):
                costModifier = rowObject.cost(costId=costId)
                if costModifier:
                    calculations.append(costModifier.numericModifier())
            elif isinstance(rowObject, construction.ManifestSection):
                calculations.append(rowObject.totalCost(costId=costId))
            elif isinstance(rowObject, construction.Manifest):
                calculations.append(rowObject.totalCost(costId=costId))

        if column == ManifestTable.StdColumnType.Factors or \
                column == ManifestTable.StdColumnType.Component:
            if isinstance(rowObject, construction.ManifestEntry):
                for factor in rowObject.factors():
                    calculations.extend(factor.calculations())

        menuItems = [
            gui.MenuItem(
                text='Calculation...',
                callback=lambda: self._showCalculations(calculations=calculations),
                enabled=len(calculations) > 0
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self.viewport().mapToGlobal(position))

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
