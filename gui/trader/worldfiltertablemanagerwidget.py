import app
import gui
import logging
import logic
import typing
from PyQt5 import QtWidgets, QtCore

class _FilterLogicComboBox(gui.EnumComboBox):
    _TextMap = {
        logic.FilterLogic.MatchesAny: 'Worlds Matching Any Filter',
        logic.FilterLogic.MatchesAll: 'Worlds Matching All Filters',
        logic.FilterLogic.MatchesNone: 'Worlds Matching No Filters'
    }

    _StateVersion = '_FilterLogicComboBox_v1'

    def __init__(
            self,
            value: typing.Optional[logic.FilterLogic] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            type=logic.FilterLogic,
            textMap=_FilterLogicComboBox._TextMap,
            value=value,
            parent=parent)

    def saveState(self) -> QtCore.QByteArray:
        logic = self.currentEnum()
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_FilterLogicComboBox._StateVersion)
        stream.writeQString(logic.name)
        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != _FilterLogicComboBox._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore _FilterLogicComboBox state (Incorrect version)')
            return False

        name = stream.readQString()
        if name not in logic.FilterLogic.__members__:
            logging.warning(f'Failed to restore _FilterLogicComboBox state (Unknown filter logic "{name}")')
            return False
        self.setCurrentEnum(logic.FilterLogic.__members__[name])
        return True

class WorldFilterTableManagerWidget(QtWidgets.QWidget):
    contentChanged = QtCore.pyqtSignal()

    _StateVersion = 'WorldFilterTableManagerWidget_v1'

    def __init__(
            self,
            taggingColours: app.TaggingColours,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._taggingColours = app.TaggingColours(taggingColours)

        self._logicComboBox = _FilterLogicComboBox(
            value=logic.FilterLogic.MatchesAll)

        self._filterTable = gui.WorldFilterTable()
        self._filterTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._filterTable.customContextMenuRequested.connect(self._showTableContextMenu)
        self._filterTable.keyPressed.connect(self._tableKeyPressed)
        self._filterTable.doubleClicked.connect(self.promptEditSelected)
        self._filterTable.itemSelectionChanged.connect(self._tableSelectionChanged)

        self._promptAddNewAction = QtWidgets.QAction('Add...', self)
        self._promptAddNewAction.setEnabled(True)
        self._promptAddNewAction.triggered.connect(self.promptAddNew)

        self._promptEditSelectedAction = QtWidgets.QAction('Edit...', self)
        self._promptEditSelectedAction.setEnabled(False) # No selection
        self._promptEditSelectedAction.triggered.connect(self.promptEditSelected)

        self._removeSelectedAction = QtWidgets.QAction('Remove Selected', self)
        self._removeSelectedAction.setEnabled(False) # No selection
        self._removeSelectedAction.triggered.connect(self.removeSelectedFilters)

        self._removeContentAction = QtWidgets.QAction('Remove All', self)
        self._removeContentAction.setEnabled(False) # No content
        self._removeContentAction.triggered.connect(self.removeAllFilters)

        # TODO: These buttons should probably trigger the actions
        self._addButton = QtWidgets.QPushButton('Add...')
        self._addButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addButton.clicked.connect(self.promptAddNew)

        self._editButton = QtWidgets.QPushButton('Edit...')
        self._editButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._editButton.clicked.connect(self.promptEditSelected)

        self._removeButton = QtWidgets.QPushButton('Remove')
        self._removeButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeButton.clicked.connect(self.removeSelectedFilters)

        self._removeAllButton = QtWidgets.QPushButton('Remove All')
        self._removeAllButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._removeAllButton.clicked.connect(self.removeAllFilters)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addButton)
        buttonLayout.addWidget(self._editButton)
        buttonLayout.addWidget(self._removeButton)
        buttonLayout.addWidget(self._removeAllButton)
        buttonWidget = QtWidgets.QWidget()
        buttonWidget.setLayout(buttonLayout)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addLayout(gui.createLabelledWidgetLayout('Filter Logic: ', self._logicComboBox))
        widgetLayout.addWidget(self._filterTable)
        widgetLayout.addWidget(buttonWidget)

        self.setLayout(widgetLayout)

    def setTaggingColours(self, colours: app.TaggingColours) -> None:
        if colours == self._taggingColours:
            return
        self._taggingColours = app.TaggingColours(colours)

    def filterLogic(self) -> logic.FilterLogic:
        return self._logicComboBox.currentEnum()

    def setFilterLogic(self, filterLogic: logic.FilterLogic) -> None:
        self._logicComboBox.setCurrentEnum(filterLogic)

    def addFilter(self, filter: logic.WorldFilter) -> None:
        self._filterTable.addFilter(filter=filter)
        self._notifyContentChangeObservers()

    def addFilters(self, filters: typing.Iterable[logic.WorldFilter]) -> None:
        self._filterTable.addFilters(filters=filters)
        self._notifyContentChangeObservers()

    def removeFilters(self, filter: logic.WorldFilter) -> bool:
        removed = self._filterTable.removeFilter(filter=filter)
        if removed:
            self._notifyContentChangeObservers()
        return removed

    def removeAllFilters(self) -> None:
        if not self._filterTable.isEmpty():
            self._filterTable.removeAllRows()
            self._notifyContentChangeObservers()

    def isEmpty(self) -> bool:
        return self._filterTable.isEmpty()

    def filterCount(self) -> int:
        return self._filterTable.rowCount()

    def filters(self) -> typing.Iterable[logic.WorldFilter]:
        return self._filterTable.filters()

    def rowAt(self, y: int) -> int:
        translated = self.mapToGlobal(QtCore.QPoint(self.x(), y))
        translated = self._filterTable.viewport().mapFromGlobal(translated)
        return self._filterTable.rowAt(translated.y())

    def filterAt(self, y: int) -> typing.Optional[logic.WorldFilter]:
        row = self.rowAt(y)
        return self._filterTable.row(row) if row >= 0 else None

    def hasSelection(self) -> bool:
        return self._filterTable.hasSelection()

    def selectedFilters(self) -> typing.Iterable[logic.WorldFilter]:
        return self._filterTable.selectedFilters()

    def removeSelectedFilters(self) -> None:
        if self._filterTable.hasSelection():
            self._filterTable.removeSelectedRows()
            self._notifyContentChangeObservers()

    def setActiveColumns(
            self,
            columns: typing.Iterable[gui.WorldFilterTable.ColumnType]
            ) -> None:
        self._filterTable.setActiveColumns(columns=columns)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(WorldFilterTableManagerWidget._StateVersion)

        bytes = self._logicComboBox.saveState()
        stream.writeUInt32(bytes.count() if bytes else 0)
        if bytes:
            stream.writeRawData(bytes.data())

        bytes = self._filterTable.saveState()
        stream.writeUInt32(bytes.count() if bytes else 0)
        if bytes:
            stream.writeRawData(bytes.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> None:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != WorldFilterTableManagerWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore WorldFilterTableManagerWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count:
            if not self._logicComboBox.restoreState(
                    QtCore.QByteArray(stream.readRawData(count))):
                return False

        count = stream.readUInt32()
        if count:
            if not self._filterTable.restoreState(
                    QtCore.QByteArray(stream.readRawData(count))):
                return False

        return True

    def saveContent(self) -> QtCore.QByteArray:
        return self._filterTable.saveContent()

    def restoreContent(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        result = self._filterTable.restoreContent(state=state)
        if not self._filterTable.isEmpty():
            self._notifyContentChangeObservers()
        return result

    def promptAddNew(self) -> None:
        dlg = gui.WorldFilterDialog(
            title='Add Filter',
            taggingColours=self._taggingColours,
            parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        self.addFilter(dlg.filter())

    def promptEditSelected(self) -> None:
        filter = self._filterTable.currentFilter()
        if not filter:
            gui.MessageBoxEx.information(
                parent=self,
                text='Select a filter to edit')
            return

        dlg = gui.WorldFilterDialog(
            title='Edit Filter',
            editFilter=filter,
            taggingColours=self._taggingColours,
            parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        index = self._filterTable.currentIndex()
        self._filterTable.setFilter(index.row(), dlg.filter())
        self._notifyContentChangeObservers()

    def promptAddNewAction(self) -> QtWidgets.QAction:
        return self._promptAddNewAction

    def setPromptAddNewAction(self, action: QtWidgets.QAction) -> None:
        self._promptAddNewAction = action

    def promptEditSelectedAction(self) -> QtWidgets.QAction:
        return self._promptEditSelectedAction

    def setPromptEditSelectedAction(self, action: QtWidgets.QAction) -> None:
        self._promptEditSelectedAction = action

    def removeSelectedAction(self) -> QtWidgets.QAction:
        return self._removeSelectedAction

    def setRemoveSelectedAction(self, action: QtWidgets.QAction) -> None:
        self._removeSelectedAction = action

    def removeContentAction(self) -> QtWidgets.QAction:
        return self._removeContentAction

    def setRemoveContentAction(self, action: QtWidgets.QAction) -> None:
        self._removeContentAction = action

    def copyContentToClipboardAsCSvAction(self) -> QtWidgets.QAction:
        return self._filterTable.copyContentToClipboardAsCSvAction()

    def setCopyContentToClipboardAsCsvAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setCopyContentToClipboardAsCsvAction(action)

    def promptExportContentToCsvAction(self) -> QtWidgets.QAction:
        return self._filterTable.promptExportContentToCsvAction()

    def setPromptExportContentToCsvAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setPromptExportContentToCsvAction(action)

    def copyContentToClipboardAsHtmlAction(self) -> QtWidgets.QAction:
        return self._filterTable.copyContentToClipboardAsHtmlAction()

    def setCopyContentToClipboardAsHtmlAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setCopyContentToClipboardAsHtmlAction(action)

    def copyViewToClipboardAction(self) -> QtWidgets.QAction:
        self._filterTable.copyViewToClipboardAction()

    def setCopyViewToClipboardAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setCopyViewToClipboardAction(action)

    def promptExportContentToHtmlAction(self) -> QtWidgets.QAction:
        return self._filterTable.promptExportContentToHtmlAction()

    def setPromptExportContentToHtmlAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setPromptExportContentToHtmlAction(action)

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        menu.addAction(self.promptAddNewAction())
        menu.addAction(self.promptEditSelectedAction())
        menu.addSeparator()
        menu.addAction(self.removeSelectedAction())
        menu.addAction(self.removeContentAction())
        menu.addSeparator()

        # Add table menu options
        self._filterTable.fillContextMenu(menu)

    def _syncActions(self) -> None:
        hasContent = not self.isEmpty()
        hasSelection = self.hasSelection()
        if self._promptEditSelectedAction:
            self._promptEditSelectedAction.setEnabled(hasSelection)
        if self._removeSelectedAction:
            self._removeSelectedAction.setEnabled(hasSelection)
        if self._removeContentAction:
            self._removeContentAction.setEnabled(hasContent)

    def _notifyContentChangeObservers(self) -> None:
        self._syncActions()
        self.contentChanged.emit()

    def _tableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self.removeSelectedFilters()

    def _showTableContextMenu(self, point: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        self.fillContextMenu(menu=menu)
        menu.exec(self.mapToGlobal(point))

    def _tableSelectionChanged(self) -> None:
        hasSelection = self._filterTable.hasSelection()
        self._editButton.setEnabled(hasSelection)
        self._removeButton.setEnabled(hasSelection)
        self._syncActions()