import common
import construction
import enum
import gui
import gunsmith
import logging
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class WeaponManifestTable(gui.ListTable):
    class ColumnType(enum.Enum):
        Component = 'Component'
        Cost = 'Cost'
        Weight = 'Weight'
        Factors = 'Other Factors'

    AllColumns = [
        ColumnType.Component,
        ColumnType.Cost,
        ColumnType.Weight,
        ColumnType.Factors
    ]

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self.setColumnHeaders(self.AllColumns)
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

    def setWeapon(
            self,
            weapon: typing.Optional[gunsmith.Weapon]
            ) -> None:
        self._weapon = weapon
        self.update()

    def update(self) -> None:
        self.removeAllRows()
        if not self._weapon:
            self.resizeRowsToContents()
            return

        manifest = self._weapon.manifest()
        for section in manifest.sections():
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
            self._fillManifestTotalRow(row=row, manifest=manifest)

        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)

    def _fillManifestEntryRow(
            self,
            row: int,
            entry: construction.ManifestEntry
            ) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == self.ColumnType.Component:
                tableItem = QtWidgets.QTableWidgetItem(entry.component())
            elif columnType == self.ColumnType.Cost:
                cost = entry.cost(costId=gunsmith.WeaponCost.Credits)
                if cost:
                    text = cost.displayString(
                        decimalPlaces=gunsmith.ConstructionDecimalPlaces)
                    if isinstance(cost, construction.ConstantModifier):
                        text = text.strip('+')
                        text = 'Cr' + text
                else:
                    text = '-'
                tableItem = QtWidgets.QTableWidgetItem(text)
            elif columnType == self.ColumnType.Weight:
                weight = entry.cost(costId=gunsmith.WeaponCost.Weight)
                if weight:
                    text = weight.displayString(
                        decimalPlaces=gunsmith.ConstructionDecimalPlaces)
                    if isinstance(weight, construction.ConstantModifier):
                        text = text.strip('+')
                        text += 'kg'
                else:
                    text = '-'
                tableItem = QtWidgets.QTableWidgetItem(text)
            elif columnType == self.ColumnType.Factors:
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
            if columnType == self.ColumnType.Component:
                tableItem = QtWidgets.QTableWidgetItem(f'{section.name()} Total')
            elif columnType == self.ColumnType.Cost:
                cost = section.totalCost(costId=gunsmith.WeaponCost.Credits)
                if cost.value():
                    itemText = f'Cr{common.formatNumber(cost.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)}'
                else:
                    itemText = '-'
                tableItem = QtWidgets.QTableWidgetItem(itemText)
            elif columnType == self.ColumnType.Weight:
                weight = section.totalCost(costId=gunsmith.WeaponCost.Weight)
                if weight.value():
                    itemText = f'{common.formatNumber(weight.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)}kg'
                else:
                    itemText = '-'
                tableItem = QtWidgets.QTableWidgetItem(itemText)
            elif columnType == self.ColumnType.Factors:
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
            row: int,
            manifest: construction.Manifest
            ) -> None:
        for column in range(self.columnCount()):
            columnType = self.columnHeader(column)
            tableItem = None
            if columnType == self.ColumnType.Component:
                tableItem = QtWidgets.QTableWidgetItem(f'Total')
            elif columnType == self.ColumnType.Cost:
                cost = manifest.totalCost(costId=gunsmith.WeaponCost.Credits)
                tableItem = QtWidgets.QTableWidgetItem(
                    f'Cr{common.formatNumber(cost.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)}')
            elif columnType == self.ColumnType.Weight:
                weight = manifest.totalCost(costId=gunsmith.WeaponCost.Weight)
                tableItem = QtWidgets.QTableWidgetItem(
                    f'{common.formatNumber(weight.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)}kg')
            elif columnType == self.ColumnType.Factors:
                tableItem = QtWidgets.QTableWidgetItem('-')

            if tableItem:
                font = tableItem.font()
                font.setBold(True)
                tableItem.setFont(font)

                self.setItem(row, column, tableItem)
                tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, manifest)

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

        if column == WeaponManifestTable.ColumnType.Cost or \
                column == WeaponManifestTable.ColumnType.Component:
            if isinstance(rowObject, construction.ManifestEntry):
                costModifier = rowObject.cost(costId=gunsmith.WeaponCost.Credits)
                if costModifier:
                    calculations.append(costModifier.numericModifier())
            elif isinstance(rowObject, construction.ManifestSection):
                calculations.append(rowObject.totalCost(costId=gunsmith.WeaponCost.Credits))
            elif isinstance(rowObject, construction.Manifest):
                calculations.append(rowObject.totalCost(costId=gunsmith.WeaponCost.Credits))

        if column == WeaponManifestTable.ColumnType.Weight or \
                column == WeaponManifestTable.ColumnType.Component:
            if isinstance(rowObject, construction.ManifestEntry):
                weightModifier = rowObject.cost(costId=gunsmith.WeaponCost.Weight)
                if weightModifier:
                    calculations.append(weightModifier.numericModifier())
            elif isinstance(rowObject, construction.ManifestSection):
                calculations.append(rowObject.totalCost(costId=gunsmith.WeaponCost.Weight))
            elif isinstance(rowObject, construction.Manifest):
                calculations.append(rowObject.totalCost(costId=gunsmith.WeaponCost.Weight))

        if column == WeaponManifestTable.ColumnType.Factors or \
                column == WeaponManifestTable.ColumnType.Component:
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
                decimalPlaces=gunsmith.ConstructionDecimalPlaces)
        except Exception as ex:
            message = 'Failed to show calculations'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
