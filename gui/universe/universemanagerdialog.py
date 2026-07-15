import app
import common
import enum
import gui
import logging
import multiverse
import os
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: Need a section to the side of the manager dialog that shows
# info about the selected universe
# - Minimum it needs to show the multiline description along with the option to edit it
# - Could also show sector count, world count etc

class _PreventSetToEmptyDelegate(gui.StyledItemDelegateEx):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.setHighlightCurrentItem(False)

    def setModelData(
            self,
            editor: typing.Optional[QtWidgets.QWidget],
            model: typing.Optional[QtCore.QAbstractItemModel],
            index: QtCore.QModelIndex
            ) -> None:
        # Get the text from the line editor widget
        if isinstance(editor, QtWidgets.QLineEdit):
            text = editor.text().strip()

            # If the user typed nothing, block the update
            if not text:
                return  # Exits without updating the model

        # Otherwise, save the data normally
        super().setModelData(editor, model, index)

class _CenteredIconItemDelegate(gui.StyledItemDelegateEx):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.setHighlightCurrentItem(False)

    def paint(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> None:
        icon = index.data(QtCore.Qt.ItemDataRole.DecorationRole)
        if not isinstance(icon, QtGui.QIcon):
            super().paint(painter, option, index)
            return

        itemOption = QtWidgets.QStyleOptionViewItem(option)
        if not self._highlightCurrentItem and option.state & QtWidgets.QStyle.StateFlag.State_HasFocus:
            itemOption.state = itemOption.state ^ QtWidgets.QStyle.StateFlag.State_HasFocus

        assert(isinstance(itemOption.widget, QtWidgets.QWidget))
        assert(isinstance(itemOption.rect, QtCore.QRect))

        painter.save()

        # Draw selection background
        if itemOption.state & QtWidgets.QStyle.StateFlag.State_Selected:
            itemOption.widget.style().drawPrimitive(
                QtWidgets.QStyle.PrimitiveElement.PE_PanelItemViewItem,
                itemOption, painter, itemOption.widget)

        size = itemOption.decorationSize
        pixmap = icon.pixmap(size)

        x = itemOption.rect.x() + (itemOption.rect.width() - pixmap.width()) // 2
        y = itemOption.rect.y() + (itemOption.rect.height() - pixmap.height()) // 2

        painter.drawPixmap(x, y, pixmap)

        painter.restore()

class _UniverseTable(gui.ListTable):
    inPlaceRename = QtCore.pyqtSignal(
        str, # Universe Id
        str) # New universe name

    class ColumnType(enum.Enum):
        Universe = 'Universe'
        Active = 'Active'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._starIcon = gui.loadIcon(gui.Icon.Star)

        self.setColumnHeaders(_UniverseTable.ColumnType)
        self.setColumnsMoveable(False)
        self.resizeColumnsToContents() # Size columns to header text
        self.resizeRowsToContents()
        self.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setMinimumSectionSize(1)
        self.setWordWrap(True)
        self.setAlternatingRowColors(False)
        self.setSortingEnabled(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self._universeColumnDelegate = _PreventSetToEmptyDelegate()
        self.setItemDelegateForColumn(0, self._universeColumnDelegate)

        self._activeColumnDelegate = _CenteredIconItemDelegate()
        self.setItemDelegateForColumn(1, self._activeColumnDelegate)

        self.itemChanged.connect(self._inPlaceRename)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)

    def universe(self, row: int) -> typing.Optional[multiverse.UniverseInfo]:
        item = self.item(row, 0)
        if item is None:
            return None
        return item.data(QtCore.Qt.ItemDataRole.UserRole)

    def setCurrentUniverse(self, id: str) -> None:
        for row in range(self.rowCount()):
            universeInfo = self.universe(row)
            if universeInfo is not None and id == universeInfo.id():
                self.setCurrentRow(row)

    def currentUniverse(self) -> typing.Optional[multiverse.UniverseInfo]:
        row = self.currentRow()
        if row < 0:
            return None
        return self.universe(row)

    def syncUniverseList(self, activeId: typing.Optional[str]) -> None:
        oldCurrentRow = self.currentRow()
        oldCurrentUniverseInfo = self.universe(oldCurrentRow)

        newCurrentRow = None
        with gui.SignalBlocker(self):
            self.removeAllRows()

            universes = multiverse.UniverseManager.instance().universeInfos()
            for row, universe in enumerate(universes):
                isActive = universe.id() == activeId

                self.insertRow(row)
                for column in range(self.columnCount()):
                    columnType = self.columnHeader(column)
                    tableItem: typing.Optional[QtWidgets.QTableWidgetItem] = None
                    if columnType == self.ColumnType.Universe:
                        tableItem = QtWidgets.QTableWidgetItem(universe.name())
                    elif columnType == self.ColumnType.Active:
                        tableItem = QtWidgets.QTableWidgetItem()
                        tableItem.setFlags(tableItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                        if isActive:
                            tableItem.setIcon(self._starIcon)

                    if tableItem:
                        self.setItem(row, column, tableItem)
                        tableItem.setData(QtCore.Qt.ItemDataRole.UserRole, universe)

                self.resizeRowToContents(row)

                if oldCurrentUniverseInfo is not None and oldCurrentUniverseInfo.id() == universe.id():
                    newCurrentRow = row

            # The entry for the previous current row was found so set the current
            # row inside the signal blocker. The whole point is to have it so the
            # current row doesn't change so from an observers perspective you
            # wouldn't expect to see an event
            if newCurrentRow is not None:
                self.setCurrentRow(newCurrentRow)

        if newCurrentRow is None and oldCurrentRow != self.currentRow():
            # The current row has changed but the old current universe wasn't
            # reselected so we need to notify observers that the current row has
            # changed
            # TODO: Need to check this actually works
            self.setCurrentRow(self.currentRow())

    def _inPlaceRename(self, item: QtWidgets.QListWidgetItem) -> None:
        universeInfo: typing.Optional[multiverse.UniverseInfo] = item.data(
            QtCore.Qt.ItemDataRole.UserRole)
        if universeInfo is None:
            return
        self.inPlaceRename.emit(universeInfo.id(), item.text())

class UniverseManagerDialog(gui.DialogEx):
    _IconSize = 24

    _ImportExportLastDirKey = 'UniverseManagerDialogImportExportDir'
    _UniverseFileFilter = 'Universe (*.db)'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Universe Manager',
            configSection='UniverseManagerDialog',
            parent=parent)

        self._setupUniverseList()
        self._setupDialogButtons()

        dialogLayout = QtWidgets.QVBoxLayout()
        dialogLayout.addWidget(self._universeListGroupBox)
        dialogLayout.addLayout(self._buttonLayout)

        self.setLayout(dialogLayout)

        self._syncUniverseList(firstSync=True)

    def _setupUniverseList(self) -> None:
        self._universeTable = _UniverseTable()
        self._universeTable.currentRowChanged.connect(self._selectedUniverseChanged)
        self._universeTable.inPlaceRename.connect(self._renameUniverseInPlace)
        self._universeTable.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)
        self._universeTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)

        iconSize = int(UniverseManagerDialog._IconSize * gui.interfaceScale())
        self._toolbar = QtWidgets.QToolBar()
        self._toolbar.setIconSize(QtCore.QSize(iconSize, iconSize))
        self._toolbar.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self._toolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._newUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseNew), 'New...', self)
        self._newUniverseAction.triggered.connect(self._newUniverse)
        self._universeTable.addAction(self._newUniverseAction)
        self._toolbar.addAction(self._newUniverseAction)

        self._deleteUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseDelete), 'Delete...', self)
        self._deleteUniverseAction.triggered.connect(self._deleteUniverse)
        self._universeTable.addAction(self._deleteUniverseAction)
        self._toolbar.addAction(self._deleteUniverseAction)

        self._renameUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseRename), 'Rename...', self)
        self._renameUniverseAction.triggered.connect(self._renameUniverse)
        self._universeTable.addAction(self._renameUniverseAction)
        self._toolbar.addAction(self._renameUniverseAction)

        self._makeActiveUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseStar), 'Make Active', self)
        self._makeActiveUniverseAction.triggered.connect(self._makeActiveUniverse)
        self._universeTable.addAction(self._makeActiveUniverseAction)
        self._toolbar.addAction(self._makeActiveUniverseAction)

        self._importUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseImport), 'Import...', self)
        self._importUniverseAction.triggered.connect(self._importUniverse)
        self._universeTable.addAction(self._importUniverseAction)
        self._toolbar.addAction(self._importUniverseAction)

        self._exportUniverseAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DatabaseExport), 'Export...', self)
        self._exportUniverseAction.triggered.connect(self._exportUniverse)
        self._universeTable.addAction(self._exportUniverseAction)
        self._toolbar.addAction(self._exportUniverseAction)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._toolbar)
        layout.addWidget(self._universeTable)

        self._universeListGroupBox = QtWidgets.QGroupBox('Universe')
        self._universeListGroupBox.setLayout(layout)

    def _setupDialogButtons(self) -> None:
        self._closeButton = QtWidgets.QPushButton('Close')
        self._closeButton.clicked.connect(self.accept)

        self._buttonLayout = QtWidgets.QHBoxLayout()
        self._buttonLayout.addStretch()
        self._buttonLayout.addWidget(self._closeButton)

    def _selectedUniverseChanged(
            self,
            currentRow: int,
            previousRow: int
            ) -> None:
        self._syncActionStates()

    def _newUniverse(self) -> None:
        dlg = gui.CreateUniverseDialog()
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        self._syncUniverseList()
        self._selectUniverse(dlg.universeId())

    def _deleteUniverse(self) -> None:
        universeInfo = self._universeTable.currentUniverse()
        if universeInfo is None:
            return

        activeId = app.Config.instance().value(option=app.ConfigOption.Universe)
        if universeInfo.id() == activeId:
            gui.MessageBoxEx.critical(parent=self, text='The active universe can\'t be deleted.')
            return

        answer = gui.MessageBoxEx.question(
            parent=self,
            text=f'Are you sure you want to delete universe {universeInfo.name()!r}?\nThis cannot be undone!')
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            multiverse.UniverseManager.instance().deleteUniverse(universeId=universeInfo.id())
        except Exception as ex:
            message = f'An error occurred while deleting universe {universeInfo.name()!r}.'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)

        self._syncUniverseList()

    def _renameUniverse(self) -> None:
        universeInfo = self._universeTable.currentUniverse()
        if universeInfo is None:
            return

        newName = universeInfo.name()
        while True:
            newName, result = gui.InputDialogEx.getText(
                parent=self,
                title='Rename Universe',
                label=f'Enter the new universe name',
                text=newName)
            if not result:
                return
            # TODO: This should check that a universe with the same name
            # doesn't already exist or I should drop that requirement
            if newName:
                break
            gui.MessageBoxEx.critical(
                parent=self,
                text='Name can\'t be empty')

        if newName == universeInfo.name():
            return

        try:
            multiverse.UniverseManager.instance().setUniverseName(
                universeId=universeInfo.id(),
                name=newName)
        except Exception as ex:
            message = f'An error occurred while renaming universe {universeInfo.name()!r}.'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)

        self._syncUniverseList()

    # TODO: This should check that a universe with the same name doesn't
    # already exist or I should drop that requirement. This is problematic
    # because the list content has already been changed. Not sure if you
    # can set up a validator for editing
    def _renameUniverseInPlace(
            self,
            id: str,
            name: str
            ) -> None:
        try:
            multiverse.UniverseManager.instance().setUniverseName(
                universeId=id,
                name=name)
        except Exception as ex:
            message = f'An error occurred while renaming universe {id!r}.'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)

    def _makeActiveUniverse(self) -> None:
        universeInfo = self._universeTable.currentUniverse()
        if universeInfo is None:
            return

        app.Config.instance().setValue(
            option=app.ConfigOption.Universe,
            value=universeInfo.id())

        self._syncUniverseList()

    def _importUniverse(self) -> None:
        path, filter = gui.FileDialogEx.getOpenFileName(
            parent=self,
            caption='Import Universe',
            filter=f'{UniverseManagerDialog._UniverseFileFilter};;{gui.AllFileFilter}',
            lastDirKey=UniverseManagerDialog._ImportExportLastDirKey)
        if not path:
            return # User cancelled

        try:
            # Use filename without extension as the universe name
            universeName = os.path.splitext(os.path.basename(path))[0]
            universeId = multiverse.UniverseManager.instance().importUniverse(
                name=universeName,
                importPath=path)
        except Exception as ex:
            message = f'An error occurred while importing the universe from {path!r}.'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)

        # Make the imported universe the active universe
        app.Config.instance().setValue(
            option=app.ConfigOption.Universe,
            value=universeId)

        self._syncUniverseList()
        self._selectUniverse(universeId)

    def _exportUniverse(self) -> None:
        universeInfo = self._universeTable.currentUniverse()
        if universeInfo is None:
            return

        path, filter = gui.FileDialogEx.getSaveFileName(
            parent=self,
            caption='Export Universe',
            filter=f'{UniverseManagerDialog._UniverseFileFilter};;{gui.AllFileFilter}',
            lastDirKey=UniverseManagerDialog._ImportExportLastDirKey,
            defaultFileName=f'{common.sanitiseFileName(universeInfo.name())}.db')
        if not path:
            return # User cancelled

        try:
            multiverse.UniverseManager.instance().exportUniverse(
                universeId=universeInfo.id(),
                exportPath=path)
        except Exception as ex:
            message = f'An error occurred while exporting the universe to {path!r}.'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(parent=self, text=message, exception=ex)

    def _selectUniverse(self, id: str) -> None:
        self._universeTable.setCurrentUniverse(id=id)

    def _syncUniverseList(
            self,
            firstSync: bool = False
            ) -> None:
        activeId = app.Config.instance().value(option=app.ConfigOption.Universe)
        self._universeTable.syncUniverseList(activeId=activeId)
        if firstSync and activeId:
            self._universeTable.setCurrentUniverse(id=activeId)
        self._syncActionStates()

    def _syncActionStates(self) -> None:
        activeId = app.Config.instance().value(option=app.ConfigOption.Universe)
        universeInfo = self._universeTable.currentUniverse()
        hasSelection = universeInfo is not None
        selectedUniverseId = universeInfo.id() if hasSelection else None
        selectedIsActive = \
            selectedUniverseId is not None and \
            activeId is not None and \
            selectedUniverseId == activeId

        self._deleteUniverseAction.setEnabled(hasSelection and not selectedIsActive)
        self._renameUniverseAction.setEnabled(hasSelection)
        self._makeActiveUniverseAction.setEnabled(hasSelection and not selectedIsActive)
        self._exportUniverseAction.setEnabled(hasSelection)