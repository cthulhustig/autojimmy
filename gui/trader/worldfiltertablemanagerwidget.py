import app
import gui
import logging
import logic
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

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
        self._filterTable.installEventFilter(self)
        self._filterTable.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        self._filterTable.doubleClicked.connect(self.promptEditSelected)
        self._filterTable.itemSelectionChanged.connect(self._tableSelectionChanged)

        self._promptAddNewAction = QtWidgets.QAction('Add...', self)
        self._promptAddNewAction.triggered.connect(self.promptAddNew)

        self._promptEditSelectedAction = QtWidgets.QAction('Edit...', self)
        self._promptEditSelectedAction.setEnabled(False) # No selection
        self._promptEditSelectedAction.triggered.connect(self.promptEditSelected)

        self._removeSelectedAction = QtWidgets.QAction('Remove Selected', self)
        self._removeSelectedAction.setEnabled(False) # No selection
        self._removeSelectedAction.triggered.connect(self.removeSelectedFilters)

        self._removeAllAction = QtWidgets.QAction('Remove All', self)
        self._removeAllAction.setEnabled(False) # No content
        self._removeAllAction.triggered.connect(self.removeAllFilters)

        self._addNewButton = gui.ActionButton(
            action=self._promptAddNewAction)
        self._addNewButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._editSelectionButton = gui.ActionButton(
            action=self._promptEditSelectedAction)
        self._editSelectionButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._removeSelectedButton = gui.ActionButton(
            action=self._removeSelectedAction,
            text='Remove')
        self._removeSelectedButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._removeAllButton = gui.ActionButton(
            action=self._removeAllAction)
        self._removeAllButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._addNewButton)
        buttonLayout.addWidget(self._editSelectionButton)
        buttonLayout.addWidget(self._removeSelectedButton)
        buttonLayout.addWidget(self._removeAllButton)
        buttonWidget = QtWidgets.QWidget()
        buttonWidget.setLayout(buttonLayout)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addLayout(gui.createLabelledWidgetLayout('Filter Logic: ', self._logicComboBox))
        widgetLayout.addWidget(self._filterTable)
        widgetLayout.addWidget(buttonWidget)

        self.setLayout(widgetLayout)
        self.installEventFilter(self)

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
        if self._addNewButton:
            self._addNewButton.setAction(action=self._promptAddNewAction)

    def promptEditSelectedAction(self) -> QtWidgets.QAction:
        return self._promptEditSelectedAction

    def setPromptEditSelectedAction(self, action: QtWidgets.QAction) -> None:
        self._promptEditSelectedAction = action
        if self._editSelectionButton:
            self._editSelectionButton.setAction(action=self._promptEditSelectedAction)

    def removeSelectedAction(self) -> QtWidgets.QAction:
        return self._removeSelectedAction

    def setRemoveSelectedAction(self, action: QtWidgets.QAction) -> None:
        self._removeSelectedAction = action
        if self._removeSelectedButton:
            self._removeSelectedButton.setAction(action=self._removeSelectedAction)

    def removeAllAction(self) -> QtWidgets.QAction:
        return self._removeAllAction

    def setRemoveAllAction(self, action: QtWidgets.QAction) -> None:
        self._removeAllAction = action
        if self._removeAllButton:
            self._removeAllButton.setAction(action=self._removeAllAction)

    def copyToClipboardAsCSvAction(self) -> QtWidgets.QAction:
        return self._filterTable.copyToClipboardAsCSvAction()

    def setCopyToClipboardAsCsvAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setCopyToClipboardAsCsvAction(action)

    def promptExportAsCsvAction(self) -> QtWidgets.QAction:
        return self._filterTable.promptExportAsCsvAction()

    def setPromptExportAsCsvAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setPromptExportAsCsvAction(action)

    def copyToClipboardAsHtmlAction(self) -> QtWidgets.QAction:
        return self._filterTable.copyToClipboardAsHtmlAction()

    def setCopyToClipboardAsHtmlAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setCopyToClipboardAsHtmlAction(action)

    def copyToClipboardAsImageAction(self) -> QtWidgets.QAction:
        self._filterTable.copyToClipboardAsImageAction()

    def setCopyToClipboardAsImageAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setCopyToClipboardAsImageAction(action)

    def promptExportAsHtmlAction(self) -> QtWidgets.QAction:
        return self._filterTable.promptExportAsHtmlAction()

    def setPromptExportAsHtmlAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setPromptExportAsHtmlAction(action)

    def promptExportAsImageAction(self) -> QtWidgets.QAction:
        return self._filterTable.promptExportAsImageAction()

    def setPromptExportAsImageAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._filterTable.setPromptExportAsImageAction(action)

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        menu.addAction(self.promptAddNewAction())
        menu.addAction(self.promptEditSelectedAction())
        menu.addSeparator()
        menu.addAction(self.removeSelectedAction())
        menu.addAction(self.removeAllAction())
        menu.addSeparator()

        # Add table menu options
        self._filterTable.fillContextMenu(menu)

    def contextMenuEvent(self, event: typing.Optional[QtGui.QContextMenuEvent]) -> None:
        if self.contextMenuPolicy() != QtCore.Qt.ContextMenuPolicy.DefaultContextMenu:
            super().contextMenuEvent(event)
            return

        if not event or not self._filterTable:
            return

        globalPos = event.globalPos()
        tablePos = self._filterTable.mapFromGlobal(globalPos)
        viewport = self._filterTable.viewport()
        tableGeometry = viewport.geometry() if viewport else self._filterTable.geometry()
        if tableGeometry.contains(tablePos):
            menu = QtWidgets.QMenu(self)
            self.fillContextMenu(menu=menu)
            menu.exec(globalPos)

        #super().contextMenuEvent(event)

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if object == self:
            if event.type() == QtCore.QEvent.Type.ContextMenu:
                if self.contextMenuPolicy() == QtCore.Qt.ContextMenuPolicy.CustomContextMenu:
                    assert(isinstance(event, QtGui.QContextMenuEvent))
                    if self._filterTable:
                        globalPos = event.globalPos()
                        tablePos = self._filterTable.mapFromGlobal(globalPos)

                        # Only allow context menu if mouse is over the table viewport
                        viewport = self._filterTable.viewport()
                        tableGeometry = viewport.geometry() if viewport else self._filterTable.geometry()
                        if tableGeometry.contains(tablePos):
                            self.customContextMenuRequested.emit(event.pos())

                    event.accept()
                    return True
        elif object == self._filterTable:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Delete:
                    self.removeSelectedFilters()
                    event.accept()
                    return True

        return super().eventFilter(object, event)

    def _syncActions(self) -> None:
        hasContent = not self.isEmpty()
        hasSelection = self.hasSelection()
        if self._promptEditSelectedAction:
            self._promptEditSelectedAction.setEnabled(hasSelection)
        if self._removeSelectedAction:
            self._removeSelectedAction.setEnabled(hasSelection)
        if self._removeAllAction:
            self._removeAllAction.setEnabled(hasContent)

    def _notifyContentChangeObservers(self) -> None:
        self._syncActions()
        self.contentChanged.emit()

    def _tableSelectionChanged(self) -> None:
        hasSelection = self._filterTable.hasSelection()
        self._editSelectionButton.setEnabled(hasSelection)
        self._removeSelectedButton.setEnabled(hasSelection)
        self._syncActions()