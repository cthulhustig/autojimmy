import common
import construction
import gui
import logging
import typing
from PyQt5 import QtCore, QtWidgets, QtGui

class NotesWidget(QtWidgets.QWidget):
    _ColumnNames = ['Source', 'Note']

    _StateVersion = 'NotesWidget_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._cachedFilterBkColour = None

        self._filterLineEdit = gui.LineEditEx()
        self._filterLineEdit.textEdited.connect(self._updateFilter)

        self._clearFilterButton = QtWidgets.QPushButton()
        self._clearFilterButton.setIcon(gui.loadIcon(gui.Icon.CloseTab))
        self._clearFilterButton.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._clearFilterButton.setToolTip('Clear filter')
        self._clearFilterButton.clicked.connect(self._clearFilter)

        self._filterTypeComboBox = gui.EnumComboBox(
            type=common.StringFilterType,
            value=common.StringFilterType.ContainsString,
            options=[
                common.StringFilterType.ContainsString,
                common.StringFilterType.Regex,
                common.StringFilterType.Wildcard])
        self._filterTypeComboBox.activated.connect(self._updateFilter)

        self._filterIgnoreCaseCheckBox = gui.CheckBoxEx("Ignore Case:")
        self._filterIgnoreCaseCheckBox.setTextOnLeft(True)
        self._filterIgnoreCaseCheckBox.setChecked(True)
        self._filterIgnoreCaseCheckBox.stateChanged.connect(self._updateFilter)

        controlsLayout = QtWidgets.QHBoxLayout()
        controlsLayout.setContentsMargins(0, 0, 0, 0)
        controlsLayout.addWidget(QtWidgets.QLabel('Filter:'))
        controlsLayout.addWidget(self._filterLineEdit)
        controlsLayout.addWidget(self._clearFilterButton)
        controlsLayout.addWidget(self._filterTypeComboBox)
        controlsLayout.addWidget(self._filterIgnoreCaseCheckBox)
        controlsLayout.addStretch()

        self._table = gui.ListTable()
        self._table.setColumnHeaders(NotesWidget._ColumnNames)
        self._table.setColumnsMoveable(False)
        self._table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        # Having the table automatically adjust to the content size can cause
        # odd draw issues if the NotesWidget is inside another widget such as a
        # group box or expander. If you type a sequence of the same character
        # into the filter edit so that no notes are mated, then hold delete
        # to delete the string quickly character by character, occasionally
        # the notes widget will briefly jump upwards. When used in the
        # robot/weapon it cause it to temporarily appear over the top of the
        # stats widget above it. Rather than have it happen automatically,
        # instead the widget is resized as the displayed content changes
        #self._table.setSizeAdjustPolicy(
        #    QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self._table.setWordWrap(True)
        self._table.setAlternatingRowColors(False)
        self._table.setSortingEnabled(False)
        self._table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().sectionResized.connect(
            self._table.resizeRowsToContents)
        self._table.installEventFilter(self)
        self._table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed)
        self._table.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self._table.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._tableContextMenu)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controlsLayout)
        layout.addWidget(self._table)
        layout.addStretch(1)

        self.setLayout(layout)

    def isEmpty(self) -> bool:
        return self._table.isEmpty()

    def setSteps(
            self,
            steps: typing.Iterable[construction.ConstructionStep]
            ) -> None:
        self._table.removeAllRows()
        seenNotes = set()
        for step in steps:
            for note in step.notes():
                source = f'{step.type()}: {step.name()}'
                key = (source, note)
                if key not in seenNotes:
                    row = self._table.rowCount()
                    self._table.insertRow(row)

                    item = QtWidgets.QTableWidgetItem(source)
                    item.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop))
                    self._table.setItem(row, 0, item)

                    item = QtWidgets.QTableWidgetItem(note)
                    item.setTextAlignment(int(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop))
                    self._table.setItem(row, 1, item)

                    seenNotes.add(key)
        self._resizeTableToContents()

    def clear(self) -> None:
        self._table.removeAllRows()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._resizeTableToContents()
        return super().resizeEvent(event)

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if object == self._table:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.matches(QtGui.QKeySequence.StandardKey.Copy):
                    self._copyToClipboard()
                    event.accept()
                    return True

        return super().eventFilter(object, event)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        filterState = self._filterLineEdit.saveState()
        stream.writeUInt32(filterState.count() if filterState else 0)
        if filterState:
            stream.writeRawData(filterState.data())

        typeState = self._filterTypeComboBox.saveState()
        stream.writeUInt32(typeState.count() if typeState else 0)
        if typeState:
            stream.writeRawData(typeState.data())

        caseState = self._filterIgnoreCaseCheckBox.saveState()
        stream.writeUInt32(caseState.count() if caseState else 0)
        if caseState:
            stream.writeRawData(caseState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != self._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug('Failed to restore NotesWidget state (Incorrect version)')
            return False

        try:
            count = stream.readUInt32()
            if count <= 0:
                return True
            filterState = QtCore.QByteArray(stream.readRawData(count))
            with gui.SignalBlocker(widget=self._filterLineEdit):
                if not self._filterLineEdit.restoreState(filterState):
                    return False

            count = stream.readUInt32()
            if count <= 0:
                return True
            typeState = QtCore.QByteArray(stream.readRawData(count))
            with gui.SignalBlocker(widget=self._filterTypeComboBox):
                if not self._filterTypeComboBox.restoreState(typeState):
                    return False

            count = stream.readUInt32()
            if count <= 0:
                return True
            caseState = QtCore.QByteArray(stream.readRawData(count))
            with gui.SignalBlocker(widget=self._filterIgnoreCaseCheckBox):
                if not self._filterIgnoreCaseCheckBox.restoreState(caseState):
                    return False
        finally:
            # Call update filter so the table is in sync with the filter config,
            # or whatever part of the filter config we managed to load.
            self._updateFilter()

        return True

    def _updateFilter(self) -> None:
        filterString = self._filterLineEdit.text()
        filterType = common.StringFilterType.NoFilter
        ignoreCase = True
        if filterString:
            filterType = self._filterTypeComboBox.currentEnum()
            ignoreCase = self._filterIgnoreCaseCheckBox.isChecked()

        isValidFilter = False
        try:
            self._table.setRowFilter(
                filterType=filterType,
                filterString=filterString,
                ignoreCase=ignoreCase)
            isValidFilter = True
        except:
            # Something wen't wrong setting the filter, most likely an error in
            # a regex. Just disable filtering until the user corrects it
            self._table.setRowFilter(
                filterType=common.StringFilterType.NoFilter)

        self._resizeTableToContents()

        palette = self._filterLineEdit.palette()
        if not self._cachedFilterBkColour:
            self._cachedFilterBkColour = palette.color(
                QtGui.QPalette.ColorRole.Base)
        palette.setColor(
            QtGui.QPalette.ColorRole.Base,
            self._cachedFilterBkColour
            if isValidFilter else
            palette.color(QtGui.QPalette.ColorRole.BrightText))
        self._filterLineEdit.setPalette(palette)

    def _tableContextMenu(
            self,
            point: QtCore.QPoint
            ) -> None:
        menuItems = [
            gui.MenuItem(
                text='Copy as HTML',
                callback=self._copyToClipboard)
        ]

        gui.displayMenu(
            self,
            menuItems,
            self._table.viewport().mapToGlobal(point))

    def _copyToClipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        if not clipboard:
            return

        content = self._table.contentToHtml()
        if content:
            clipboard.setText(content)

    def _clearFilter(self) -> None:
        self._filterLineEdit.clear()
        self._updateFilter()

    def _resizeTableToContents(self) -> None:
        maxWidth = int(self._table.width() * 0.3)
        self._table.horizontalHeader().setMaximumSectionSize(maxWidth)
        hintWidth = self._table.sizeHintForColumn(0)
        self._table.setColumnWidth(0, min(hintWidth, maxWidth))

        self._table.resizeRowsToContents()
        totalHeight = self._table.horizontalHeader().sizeHint().height() + 2
        for row in range(self._table.rowCount()):
            if self._table.isRowHidden(row):
                continue
            height = self._table.sizeHintForRow(row)
            if height > 0:
                totalHeight += height + 3
        self._table.setMinimumHeight(totalHeight)
