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
        self._filterTable.customContextMenuRequested.connect(self._showFilterTableContextMenu)
        self._filterTable.keyPressed.connect(self._worldTableKeyPressed)
        self._filterTable.doubleClicked.connect(self.promptEditFilter)

        self._addButton = QtWidgets.QPushButton('Add...')
        self._addButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._addButton.clicked.connect(self.promptAddFilter)

        self._editButton = QtWidgets.QPushButton('Edit...')
        self._editButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)
        self._editButton.clicked.connect(self.promptEditFilter)

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
        self.contentChanged.emit()

    def addFilters(self, filters: typing.Iterable[logic.WorldFilter]) -> None:
        self._filterTable.addFilters(filters=filters)
        self.contentChanged.emit()

    def removeFilters(self, filter: logic.WorldFilter) -> bool:
        removed = self._filterTable.removeFilter(filter=filter)
        if removed:
            self.contentChanged.emit()
        return removed

    def removeAllFilters(self) -> None:
        if not self._filterTable.isEmpty():
            self._filterTable.removeAllRows()
            self.contentChanged.emit()

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
            self.contentChanged.emit()

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
            self.contentChanged.emit()
        return result

    def promptAddFilter(self) -> None:
        dlg = gui.WorldFilterDialog(
            title='Add Filter',
            taggingColours=self._taggingColours,
            parent=self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        self.addFilter(dlg.filter())

    def promptEditFilter(self) -> None:
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
        self.contentChanged.emit()

    def _worldTableKeyPressed(self, key: int) -> None:
        if key == QtCore.Qt.Key.Key_Delete:
            self.removeSelectedFilters()

    def _showFilterTableContextMenu(self, point: QtCore.QPoint) -> None:
        filter = self._filterTable.filterAt(point.y())

        menuItems = [
            gui.MenuItem(
                text='Add Filter...',
                callback=self.promptAddFilter,
                enabled=True
            ),
            gui.MenuItem(
                text='Edit Filter...',
                callback=self.promptEditFilter,
                enabled=filter != None
            ),
            gui.MenuItem(
                text='Remove Selected Filters',
                callback=self.removeSelectedFilters,
                enabled=self._filterTable.hasSelection()
            ),
            gui.MenuItem(
                text='Remove All Filters',
                callback=self.removeAllFilters,
                enabled=not self._filterTable.isEmpty()
            )
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._filterTable.viewport().mapToGlobal(point)
        )
