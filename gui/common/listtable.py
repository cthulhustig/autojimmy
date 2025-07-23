import common
import csv
import enum
import functools
import gui
import io
import logging
import math
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# This QProxyStyle is intended to work around what appears to be a bug in Qt that means the icon
# size set for the table isn't applied to the header
# https://bugreports.qt.io/browse/QTBUG-61559
class _SizeableIconHeaderStyle(QtWidgets.QProxyStyle):
    def __init__(
            self,
            iconSize: QtCore.QSize
            ) -> None:
        # Not sure why I can't pass the QStyle from the table in and use that. If I do I get a crash
        # inside Qt when closing the config dialog.
        super().__init__('fusion')
        self._iconSize = iconSize

    def setIconSize(self, size: QtCore.QSize) -> None:
        self._iconSize = size

    def iconRect(
            self,
            sectionRect: QtCore.QRect
            ) -> QtCore.QRect:
        return QtCore.QRect(
            sectionRect.left(),
            int(sectionRect.top() + (sectionRect.height() - self._iconSize.height()) / 2 ),
            self._iconSize.width(),
            self._iconSize.height())

    def drawControl(
            self,
            element: QtWidgets.QStyle.ControlElement,
            option: QtWidgets.QStyleOption,
            painter: QtGui.QPainter,
            widget: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        if element != QtWidgets.QStyle.ControlElement.CE_HeaderLabel:
            return super().drawControl(element, option, painter, widget)

        icon = None
        alignment = None

        # NOTE: On macOS the header is using QStyleOptionViewItem but on Windows
        # and Linux it's using QStyleOptionHeader. I've not looked into why, the
        # simplest thing is to just handle both.
        if isinstance(option, QtWidgets.QStyleOptionHeader):
            icon = option.icon
            alignment = option.textAlignment
        elif isinstance(option, QtWidgets.QStyleOptionViewItem):
            icon = option.icon
            alignment = option.displayAlignment

        if not icon or not alignment:
            return super().drawControl(element, option, painter, widget)

        assert(isinstance(icon, QtGui.QIcon))
        pixmap = icon.pixmap(self._iconSize, QtGui.QIcon.Mode.Normal)
        if not pixmap:
            return super().drawControl(element, option, painter, widget)

        drawRect = option.rect
        iconRect = self.iconRect(drawRect)

        textRect = QtCore.QRect(
            drawRect.left() + self._iconSize.width(),
            drawRect.top(),
            drawRect.width() - self._iconSize.width(),
            drawRect.height())

        painter.drawPixmap(iconRect, pixmap)
        painter.drawText(
            textRect,
            int(alignment), # Older versions of PyQt require explicit cast
            option.text)

class ListTable(gui.TableWidgetEx):
    keyPressed = QtCore.pyqtSignal(int)
    iconClicked = QtCore.pyqtSignal(int)

    _StateVersion = 'ListTable_v2'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._activeColumns: typing.List[typing.Union[enum.Enum, str]] = []
        self._headerIconClickIndex = None
        self._headerStyle = _SizeableIconHeaderStyle(iconSize=self.iconSize())
        self._rowFilter = None

        self._userColumnHidingEnabled = False
        self._userHiddenColumns: typing.Set[str] = set()

        self._columnWidths: typing.Dict[str, int] = {}

        header = self.horizontalHeader()
        header.setStyle(self._headerStyle)
        header.viewport().setMouseTracking(True)
        header.viewport().installEventFilter(self)
        header.setSectionsClickable(True)
        header.setSectionsMovable(True)
        header.setHighlightSections(False) # Don't bold header when cells are selected
        header.sectionResized.connect(self._columnWidthChanged)

        self.verticalHeader().hide()
        self.setSortingEnabled(True)
        self.setEditTriggers(QtWidgets.QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self.resizeRowsToContents()
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        itemDelegate = gui.StyledItemDelegateEx()
        itemDelegate.setHighlightCurrentItem(enabled=False)
        self.setItemDelegate(itemDelegate)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(ListTable._StateVersion)

        stream.writeUInt32(len(self._columnWidths))
        for key, value in self._columnWidths.items():
            stream.writeQString(key)
            stream.writeInt32(value)

        stream.writeUInt32(len(self._userHiddenColumns))
        for key in self._userHiddenColumns:
            stream.writeQString(key)

        headerState = self.horizontalHeader().saveState()
        stream.writeUInt32(headerState.count() if headerState else 0)
        if headerState:
            stream.writeRawData(headerState.data())

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != ListTable._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore ListTable state (Incorrect version)')
            return False

        count = stream.readUInt32()
        for _ in range(count):
            key = stream.readQString()
            value = stream.readInt32()
            self._columnWidths[key] = value

        count = stream.readUInt32()
        for _ in range(count):
            key = stream.readQString()
            self._userHiddenColumns.add(key)

        count = stream.readUInt32()
        if count > 0:
            headerState = QtCore.QByteArray(stream.readRawData(count))
            if not self.horizontalHeader().restoreState(headerState):
                return False

        # Restore the column widths and user hide settings after the header
        # has been restored
        for columnIndex in range(self.columnCount()):
            self._restoreColumnUserHide(columnIndex)
            self._restoreColumnWidth(columnIndex)

        return True

    def setColumnHeaders(
            self,
            columns: typing.Iterable[typing.Union[enum.Enum, str]]
            ) -> None:
        self._activeColumns = list(columns)

        self.setColumnCount(len(columns))
        for columnIndex, columnHeader in enumerate(columns):
            if isinstance(columnHeader, enum.Enum):
                item = QtWidgets.QTableWidgetItem(columnHeader.value)
            else:
                assert(isinstance(columnHeader, str))
                item = QtWidgets.QTableWidgetItem(columnHeader)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, columnHeader)
            self.setHorizontalHeaderItem(columnIndex, item)
            self.showColumn(columnIndex)
            self._restoreColumnUserHide(columnIndex)
            self._restoreColumnWidth(columnIndex)

        # Lock the height of the header to the height required with all columns
        # displayed (i.e. the current state). This just stops the header resizing
        # if the visible columns are changed and the currently visible ones don't
        # require as much height
        header = self.horizontalHeader()
        hint = header.sizeHint()
        header.setFixedHeight(hint.height())

    def columnHeader(
            self,
            column: int,
            ) -> typing.Optional[typing.Union[enum.Enum, str]]:
        item = self.horizontalHeaderItem(column)
        if not item:
            return None
        return item.data(QtCore.Qt.ItemDataRole.UserRole)

    def columnHeaderIndex(
            self,
            header: typing.Union[enum.Enum, str]
            ) -> int:
        for column in range(self.columnCount()):
            if header == self.columnHeader(column):
                return column
        return -1

    def columnHeaderText(
            self,
            index: int
            ) -> typing.Optional[str]:
        item = self.horizontalHeaderItem(index)
        if not item:
            return None
        return item.text()

    def setActiveColumns(self, columns: typing.Iterable[typing.Union[enum.Enum, str]]) -> None:
        self._activeColumns.clear()
        for columnIndex in range(self.columnCount()):
            columnHeader = self.columnHeader(columnIndex)
            if not columnHeader:
                continue

            if columnHeader in columns:
                self.showColumn(columnIndex)
                self._restoreColumnUserHide(columnIndex)
                self._restoreColumnWidth(columnIndex)
                self._activeColumns.append(columnHeader)
            else:
                self._cacheColumnWidth(columnIndex, self.columnWidth(columnIndex))
                self.hideColumn(columnIndex)

    def visibleColumnCount(self) -> None:
        count = 0
        for columnHeader in self._activeColumns:
            columnIndex = self.columnHeaderIndex(columnHeader)
            if not self.isColumnHidden(columnIndex):
                count += 1
        return count

    def setUserColumnHiding(self, enabled: bool) -> None:
        if self._userColumnHidingEnabled == enabled:
            return # Nothing to do

        self._userColumnHidingEnabled = enabled

        header = self.horizontalHeader()
        if self._userColumnHidingEnabled:
            header.setContextMenuPolicy(
                QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            header.customContextMenuRequested.connect(
                self._showHeaderContextMenu)
        else:
            header.customContextMenuRequested.disconnect(
                self._showHeaderContextMenu)

        # Update columns to match new state
        if self._activeColumns:
            for columnHeader in self._activeColumns:
                columnIndex = self.columnHeaderIndex(columnHeader)
                if columnIndex < 0:
                    continue
                key = columnHeader.name if isinstance(columnHeader, enum.Enum) else columnHeader
                shouldHide = self._userColumnHidingEnabled and (key in self._userHiddenColumns)
                self.setColumnHidden(columnIndex, shouldHide)

    def isEmpty(self) -> bool:
        return self.rowCount() <= 0

    def addRow(self) -> int:
        index = self.rowCount()
        self.insertRow(index)
        return index

    def hasSelection(self) -> bool:
        return self.selectionModel().hasSelection()

    def isRowSelected(self, row: int):
        item = self.item(row, 0)
        return item and item.isSelected()

    def setSelectedRow(self, row: int, select: bool):
        for column in range(self.columnCount()):
            item = self.item(row, column)
            if item:
                item.setSelected(select)

    def selectedRows(self) -> typing.List[int]:
        selectedRows = []
        for row in range(self.rowCount()):
            if self.isRowSelected(row):
                selectedRows.append(row)
        return selectedRows

    def removeSelectedRows(self) -> None:
        selection = self.selectedIndexes()
        if not selection:
            return
        selection.sort(key=lambda x: -1 * x.row())
        for index in selection:
            if index.column() == 0:
                self.removeRow(index.row())

    def removeAllRows(self) -> None:
        self.setRowCount(0)

    def takeRow(self, row: int) -> typing.Iterable[QtWidgets.QTableWidgetItem]:
        rowItems = []
        for column in range(self.columnCount()):
            item = self.takeItem(row, column)
            rowItems.append(item)
        return rowItems

    def setRow(self, row: int, rowItems: typing.Iterable[QtWidgets.QTableWidgetItem]) -> None:
        for column in range(self.columnCount()):
            self.setItem(row, column, rowItems[column])

    def moveSelectionUp(self) -> typing.Iterable[typing.Tuple[int, int]]:
        return self._moveSelection(moveUp=True)

    def moveSelectionDown(self) -> typing.Iterable[typing.Tuple[int, int]]:
        return self._moveSelection(moveUp=False)

    def setRowBold(self, row: int, bold: bool) -> None:
        for column in range(self.columnCount()):
            item = self.item(row, column)
            font = item.font()
            font.setBold(bold)
            item.setFont(font)

    def setColumnsMoveable(self, enable: bool) -> None:
        self.horizontalHeader().setSectionsMovable(enable)

    def columnsMoveable(self) -> bool:
        return self.horizontalHeader().sectionsMovable()

    def sortByColumnHeader(
            self,
            header: typing.Union[enum.Enum, str],
            order: QtCore.Qt.SortOrder
            ) -> None:
        columnIndex = self.columnHeaderIndex(header)
        if columnIndex >= 0:
            self.sortByColumn(columnIndex, order)

    def setIconSize(self, size: QtCore.QSize) -> None:
        self._headerStyle.setIconSize(size)
        super().setIconSize(size)

    def setStyle(self, style: QtWidgets.QStyle) -> None:
        self._headerStyle.setBaseStyle(style)
        super().setStyle(style)

    def setItem(
            self,
            row: int,
            column: int,
            item: QtWidgets.QTableWidgetItem
            ) -> None:
        super().setItem(row, column, item)
        self._checkRowFiltering(row=row)

    def takeItem(
            self,
            row: int,
            column: int
            ) -> QtWidgets.QTableWidgetItem:
        item = super().takeItem(row, column)
        self._checkRowFiltering(row=row)
        return item

    def setRowFilter(
            self,
            filterType: common.StringFilterType,
            filterString: typing.Optional[str] = None,
            ignoreCase: bool = True
            ) -> None:
        if filterType == common.StringFilterType.NoFilter:
            if self._rowFilter:
                self._rowFilter = None
                self.itemChanged.disconnect(self._filterWhenItemChanged)
        else:
            if not self._rowFilter:
                self._rowFilter = common.StringFilter()
                self.itemChanged.connect(self._filterWhenItemChanged)
            self._rowFilter.setFilter(
                filterType=filterType,
                filterString=filterString,
                ignoreCase=ignoreCase)

        for row in range(self.rowCount()):
            self._checkRowFiltering(row=row)

    # TODO: This should probably only write out visible columns (not sure what it does now)
    # TODO: This should probably write columns out in display order (not sure what it does now)
    def contentToCsv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        header = []
        for column in range(self.columnCount()):
            header.append(self.columnHeaderText(column))
        writer.writerow(header)

        for row in range(self.rowCount()):
            content = []
            for column in range(self.columnCount()):
                item = self.item(row, column)
                content.append(item.text() if item else '')
            writer.writerow(content)

        content = output.getvalue()
        # The csv writer inserts \r\n which get messed up if you try
        # to write the content to a file, resulting in blank lines
        # between every line of data
        return content.replace('\r\n', '\n')

    def fillMenu(
            self,
            menu: QtWidgets.QMenu,
            pos: QtCore.QPoint
            ) -> None:
        menuHelper = gui.MenuHelper(menu)

        hasContent = self.rowCount() > 0

        copyAsCsv = QtWidgets.QAction("CSV", self)
        copyAsCsv.setEnabled(hasContent)
        copyAsCsv.triggered.connect(self._copyContentToClipboardAsCsv)
        menuHelper.addAction(
            path=['Copy to Clipboard'],
            action=copyAsCsv)

        copyAsHtml = QtWidgets.QAction("HTML", self)
        copyAsHtml.setEnabled(hasContent)
        copyAsHtml.triggered.connect(self._copyContentToClipboardAsHtml)
        menuHelper.addAction(
            path=['Copy to Clipboard'],
            action=copyAsHtml)

        copyAsBitmap = QtWidgets.QAction('Bitmap', self)
        copyAsBitmap.setEnabled(True)
        copyAsBitmap.triggered.connect(self._copyViewToClipboardAsBitmap)
        menuHelper.addAction(
            path=['Copy to Clipboard'],
            action=copyAsBitmap)

        exportToCsv = QtWidgets.QAction("CSV...", self)
        exportToCsv.setEnabled(hasContent)
        exportToCsv.triggered.connect(self._interactiveExportContentToCsv)
        menuHelper.addAction(
            path=['Export'],
            action=exportToCsv)

        exportToHtml = QtWidgets.QAction("HTML...", self)
        exportToHtml.setEnabled(hasContent)
        exportToHtml.triggered.connect(self._interactiveExportContentToHtml)
        menuHelper.addAction(
            path=['Export'],
            action=exportToHtml)

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if object == self:
            if event.type() == QtCore.QEvent.Type.ToolTip:
                assert(isinstance(event, QtGui.QHelpEvent))
                position = event.pos()
                # Event position is in full table coordinates where as items
                # seem to have a coordinate space that covers the area minus
                # the row and column headers
                position.setY(position.y() - self.horizontalHeader().height())
                item = self.itemAt(position)

                if item:
                    # Generating the tooltip on demand like this is problematic
                    # as a tooltip set on an item at this point won't be actually
                    # displayed. Storing the tooltips would also cause additional
                    # headaches for tables where the tooltip content can change
                    # (e.g. hex tooltips change if map style changes). The solution
                    # is to just manually display the tooltip.
                    toolTip = self._createToolTip(item)
                    if toolTip:
                        QtWidgets.QToolTip.showText(event.globalPos(), toolTip)
        if object == self.horizontalHeader().viewport():
            # Process header mouse down and release events to check for icon click (if enabled).
            # Both the down and release events are tracked so that we can check that the icon that
            # was clicked is the same one that was released on to prevent issues with column drag
            # and drop
            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                assert(isinstance(event, QtGui.QMouseEvent))
                iconIndex = self._checkForHeaderIconClick(event.pos())
                if iconIndex >= 0:
                    self._headerIconClickIndex = iconIndex
            elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
                assert(isinstance(event, QtGui.QMouseEvent))
                iconIndex = self._checkForHeaderIconClick(event.pos())
                if iconIndex >= 0 and iconIndex == self._headerIconClickIndex:
                    self.iconClicked.emit(iconIndex)
                    self._headerIconClickIndex = None
                    # Return True so event isn't processed any further. This is important to prevent
                    # clicking the icon also causing the sort column to change
                    return True
                self._headerIconClickIndex = None

        return super().eventFilter(object, event)

    def keyPressEvent(self, event: typing.Optional[QtGui.QKeyEvent]) -> None:
        if event is not None and event.matches(QtGui.QKeySequence.StandardKey.Copy):
            # If there is no content, don't do anything but still accept
            # the event so the handling of the key press is consistent
            if self.rowCount() > 0:
                self._copyContentToClipboardAsCsv()
            event.accept()

        super().keyPressEvent(event)

        # TODO: I don't think this is the best way to handle this. Things that
        # are currently connecting to this event should probably be registering
        # an event filter with the list and monitoring for key presses that way
        if event:
            self.keyPressed.emit(event.key())

    def contextMenuEvent(self, event: typing.Optional[QtGui.QContextMenuEvent]) -> None:
        super().contextMenuEvent(event)

        if event:
            menu = QtWidgets.QMenu(self)
            self.fillMenu(menu, event.pos())
            menu.exec(event.globalPos())

    def _cacheColumnWidth(
            self,
            column: int,
            width: int
            ) -> None:
        if width <= 0:
            # When columns are hidden the size will be set to zero. We want to keep the pre-hidden
            # with so ignore the event. The isColumnHidden isn't used as it appears when hiding the
            # column width is set to 0 before the tables internal state is update to say the column
            # is hidden
            return

        columnType = self.columnHeader(column)
        if columnType == None:
            return

        if isinstance(columnType, enum.Enum):
            self._columnWidths[columnType.name] = width
        else:
            self._columnWidths[columnType] = width

    def _restoreColumnWidth(
            self,
            column: int
            ) -> None:
        columnType = self.columnHeader(column)
        if columnType == None:
            return

        width = None
        if isinstance(columnType, enum.Enum):
            width = self._columnWidths.get(columnType.name)
        else:
            width = self._columnWidths.get(columnType)
        if width != None:
            self.setColumnWidth(column, width)

    def _cacheColumnUserHide(
            self,
            column: int,
            hidden: bool
            ) -> None:
        columnType = self.columnHeader(column)
        if columnType == None:
            return

        key = columnType.name if isinstance(columnType, enum.Enum) else columnType
        if hidden:
            self._userHiddenColumns.add(key)
        elif key in self._userHiddenColumns:
            self._userHiddenColumns.remove(key)

    def _restoreColumnUserHide(
            self,
            column: int
            ) -> None:
        if not self._userColumnHidingEnabled:
            return

        columnType = self.columnHeader(column)
        if columnType == None:
            return

        key = columnType.name if isinstance(columnType, enum.Enum) else columnType
        if key in self._userHiddenColumns:
            if self.visibleColumnCount() <= 1:
                # Don't allow the last column to be hidden as the header will be
                # hidden, it looks weird and it might not be obvious to the user
                # how to get back to having headers.
                return

            self.hideColumn(column)

    def _createToolTip(
            self,
            item: QtWidgets.QTableWidgetItem
            ) -> typing.Optional[str]:
        return None

    def _moveSelection(
            self,
            moveUp: bool
            ) -> typing.Iterable[typing.Tuple[int, int]]:
        selectedRows = self.selectedRows()
        selectedRows.sort(key=lambda x: (1 if moveUp else -1) * x)

        swappedRows = []
        for currentRow in selectedRows:
            swapRow = currentRow + (-1 if moveUp else 1)
            if swapRow < 0 or swapRow >= self.rowCount():
                continue
            if self.isRowSelected(swapRow):
                continue

            currentItems = self.takeRow(currentRow)
            swapItems = self.takeRow(swapRow)

            self.setRow(currentRow, swapItems)
            self.setSelectedRow(currentRow, False)
            self.setRow(swapRow, currentItems)
            self.setSelectedRow(swapRow, True)

            swappedRows.append((currentRow, swapRow))

        return swappedRows

    def _checkRowFiltering(
            self,
            row: int
            ) -> None:
        hideRow = False
        if self._rowFilter:
            matches = False
            for column in range(self.columnCount()):
                item = self.item(row, column)
                if item and self._rowFilter.matches(string=item.text()):
                    matches = True
                    break
            hideRow = not matches
        self.setRowHidden(row, hideRow)

    def _filterWhenItemChanged(
            self,
            item: QtWidgets.QTableWidgetItem
            ) -> None:
        self._checkRowFiltering(row=item.row())

    def _checkForHeaderIconClick(self, point: QtCore.QPoint) -> int:
        header = self.horizontalHeader()
        for column in range(self.columnCount()):
            if self.isColumnHidden(column):
                continue

            item = self.horizontalHeaderItem(column)
            icon = item.data(QtCore.Qt.ItemDataRole.DecorationRole)
            if not icon:
                continue
            assert(isinstance(icon, QtGui.QIcon))

            sectionRect = QtCore.QRect(
                header.sectionViewportPosition(column),
                0,
                header.sectionSize(column),
                header.height())
            iconRect = self._headerStyle.iconRect(sectionRect)

            # Check if the click position is inside the icon rect. Don't include the edges of the
            # rect as I was finding i was getting false clicks when resizing columns
            if iconRect.contains(point, True):
                return column

        return -1

    def _showHeaderContextMenu(
            self,
            point: QtCore.QPoint
            ) -> None:
        if not self._activeColumns or not self._userColumnHidingEnabled:
            return

        visibleColumnCount = self.visibleColumnCount()

        menu = QtWidgets.QMenu(self)
        for columnHeader in self._activeColumns:
            columnIndex = self.columnHeaderIndex(columnHeader)
            if columnIndex < 0:
                continue

            columnText = self.columnHeaderText(columnIndex)
            if not columnText:
                continue

            action = QtWidgets.QAction(columnText, self)
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(columnIndex))
            action.setData(columnIndex)
            partial = functools.partial(self._userHideColumnAction, action)
            action.changed.connect(partial)

            if (visibleColumnCount == 1) and action.isChecked():
                # Don't allow the user to hide the last column as the header
                # will be hidden and there is no great way of getting it back
                action.setDisabled(True)

            menu.addAction(action)

        menu.exec(self.mapToGlobal(point))

    def _userHideColumnAction(self, action: QtWidgets.QAction) -> None:
        shouldHide = not action.isChecked()
        columnIndex = action.data()
        self.setColumnHidden(columnIndex, shouldHide)
        self._cacheColumnUserHide(columnIndex, shouldHide)

        if not shouldHide:
            self._restoreColumnWidth(columnIndex)

    def _columnWidthChanged(
            self,
            logicalIndex: int,
            oldSize : int,
            newSize: int
            ) -> None:
        self._cacheColumnWidth(logicalIndex, newSize)

        # Reset header icon click index to prevent the mouse button release after a resize also
        # triggering an icon click. This is necessary as the hit box for column resize gripper
        # overlaps the icon rect
        self._headerIconClickIndex = None

    def _copyContentToClipboardAsCsv(self) -> None:
        gui.setClipboardContent(content=self.contentToCsv())

    def _copyContentToClipboardAsHtml(self) -> None:
        gui.setClipboardContent(content=self.contentToHtml())

    def _copyViewToClipboardAsBitmap(self) -> None:
        gui.setClipboardContent(content=self.grab())

    def _interactiveExportContentToCsv(self) -> None:
        content = self.contentToCsv()

        path, _ = gui.FileDialogEx.getSaveFileName(
            parent=self,
            caption='Export to CSV',
            filter=f'{gui.CSVFileFilter};;{gui.AllFileFilter}',
            defaultFileName='export.csv')
        if not path:
            return # User cancelled

        try:
            with open(path, 'w', encoding='UTF8') as file:
                file.write(content)
        except Exception as ex:
            message = f'Failed to export content to "{path}"'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

    def _interactiveExportContentToHtml(self) -> None:
        content = self.contentToHtml()

        path, _ = gui.FileDialogEx.getSaveFileName(
            parent=self,
            caption='Export to HTML',
            filter=f'{gui.HTMLFileFilter};;{gui.AllFileFilter}',
            defaultFileName='export.html')
        if not path:
            return # User cancelled

        try:
            with open(path, 'w', encoding='UTF8') as file:
                file.write(content)
        except Exception as ex:
            message = f'Failed to export content to "{path}"'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

# Based on code from here
# https://github.com/baoboa/pyqt5/blob/master/examples/itemviews/frozencolumn/frozencolumn.py
class FrozenColumnListTable(ListTable):
    _StateVersion = 'FrozenColumnListTable_v1'

    # Create a de-duplicated & sorted list of the int values of all possible roles. De-duplication
    # is needed as, at least for Qt5, some role "enums" map to the same int value
    # e.g. BackgroundColorRole == BackgroundRole and ForegroundRole == TextColorRole
    _DataRoleValues = list(set(gui.pyQtEnumValues(QtCore.Qt, QtCore.Qt.ItemDataRole)))
    _DataRoleValues.sort()

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        self._frozenColumnWidget = None
        self._frozenColumnVisualIndex = None
        self._restoreColumnMovable = None
        self._signalLoopBlock = False
        super().__init__(parent=parent)

        fontMetrics = QtGui.QFontMetrics(self.font())
        lineSpacing = fontMetrics.lineSpacing()
        iconDim = max(math.ceil(lineSpacing * 0.75), 16)
        iconSize = QtCore.QSize(iconDim, iconDim)

        self.setIconSize(iconSize)
        self.iconClicked.connect(self._headerIconClicked)
        self.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)

        self._frozenColumnWidget = ListTable(parent=self)
        self._frozenColumnWidget.setColumnsMoveable(False)
        self._frozenColumnWidget.setIconSize(iconSize)
        self._frozenColumnWidget.iconClicked.connect(self._headerIconClicked)
        self._frozenColumnWidget.setEditTriggers(QtWidgets.QTableWidget.EditTrigger.NoEditTriggers)
        self._frozenColumnWidget.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._frozenColumnWidget.verticalHeader().hide()
        self._frozenColumnWidget.horizontalHeader().setFixedHeight(self.horizontalHeader().height())
        self._frozenColumnWidget.setSelectionMode(self.selectionMode())
        self._frozenColumnWidget.setSelectionBehavior(self.selectionBehavior())
        self._frozenColumnWidget.setSortingEnabled(self.isSortingEnabled())
        self._frozenColumnWidget.setAlternatingRowColors(self.alternatingRowColors())
        self._frozenColumnWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._frozenColumnWidget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._frozenColumnWidget.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._frozenColumnWidget.setItemDelegate(self.itemDelegate())
        self._frozenColumnWidget.installEventFilter(self)

        # Disable auto scroll on the frozen widget. I was seeing an odd issue where sometimes
        # clicking at the lower or left edge of the frozen table was causing to scroll by a single
        # pixel. As well as looking ugly this resulted in odd behaviour if you the changed the
        # displayed columns. As far as I can tell the frozen table would scroll all the cells one
        # place to the left meaning the left most column would be missing and there would be a blank
        # column where the right most column should be.
        self._frozenColumnWidget.setAutoScroll(False)

        # Disable user column hiding on the frozen widget and handle it locally
        self._frozenColumnWidget.setUserColumnHiding(False)
        self._frozenColumnWidget.horizontalHeader().setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._frozenColumnWidget.horizontalHeader().customContextMenuRequested.connect(
            self._showHeaderContextMenu)

        self.itemChanged.connect(self._itemChanged)

        self.itemSelectionChanged.connect(self._itemSelectionChanged)
        self._frozenColumnWidget.itemSelectionChanged.connect(self._frozenItemSelectionChanged)

        self.verticalHeader().sectionResized.connect(self._rowHeightChanged)
        self._frozenColumnWidget.horizontalHeader().sectionResized.connect(self._frozenColumnWidthChanged)

        self.verticalScrollBar().valueChanged.connect(self._frozenColumnWidget.verticalScrollBar().setValue)
        self._frozenColumnWidget.verticalScrollBar().valueChanged.connect(self.verticalScrollBar().setValue)

        self._frozenColumnWidget.customContextMenuRequested.connect(self._frozenContextMenuRequested)

        self.horizontalHeader().sectionMoved.connect(self._columnMoved)

        if self.isSortingEnabled():
            self.horizontalHeader().sortIndicatorChanged.connect(self._sortIndicatorChanged)
            self._frozenColumnWidget.horizontalHeader().sortIndicatorChanged.connect(self._frozenSortIndicatorChanged)

        self.viewport().stackUnder(self._frozenColumnWidget)

    def setActiveColumns(self, columns: typing.Iterable[typing.Union[enum.Enum, str]]) -> None:
        self._frozenColumnWidget.setActiveColumns(columns)
        return super().setActiveColumns(columns)

    def frozenColumnVisualIndex(self) -> typing.Optional[int]:
        return self._frozenColumnVisualIndex

    def setFrozenColumnVisualIndex(
            self,
            visualIndex: typing.Optional[int]
            ) -> None:
        if visualIndex == None:
            self._frozenColumnVisualIndex = None
            self._frozenColumnWidget.hide()

            if self._restoreColumnMovable != None:
                self.setColumnsMoveable(self._restoreColumnMovable)
                self._restoreColumnMovable = None
            return

        self._frozenColumnVisualIndex = min(visualIndex, self._frozenColumnWidget.columnCount() - 1)
        self._updateFrozenWidgetColumns()
        self._updateFrozenWidgetGeometry()
        self._frozenColumnWidget.show()

        # Disable moving columns while showing frozen columns. It doesn't work properly and fixing it
        # doesn't look simple. Take note of if the columns are currently moveable so the state can
        # be restored when unfrozen
        if self._restoreColumnMovable == None:
            self._restoreColumnMovable = self.columnsMoveable()
        self.setColumnsMoveable(False)

    def frozenWidth(self) -> int:
        frozenWidth = 0
        if self._frozenColumnVisualIndex != None:
            for column in range(self.columnCount()):
                if self.isColumnHidden(column):
                    # Ignore hidden columns
                    continue

                visualIndex = self.visualColumn(column)
                if visualIndex <= self._frozenColumnVisualIndex:
                    frozenWidth += self.columnWidth(column)
        return frozenWidth

    def frozenHeight(self) -> int:
        frozenHeight = 0
        if self._frozenColumnVisualIndex != None:
            for row in range(self.rowCount()):
                frozenHeight += self.rowHeight(row)
        return frozenHeight

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(FrozenColumnListTable._StateVersion)

        stream.writeInt32(self._frozenColumnVisualIndex if self._frozenColumnVisualIndex != None else -1)

        baseState = super().saveState()
        stream.writeUInt32(baseState.count() if baseState else 0)
        if baseState:
            stream.writeRawData(baseState.data())

        return state

    def restoreState(self, state: QtCore.QByteArray) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != FrozenColumnListTable._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore FrozenColumnListTable state (Incorrect version)')
            return False

        # Restoring the frozen column index MUST be done before restoring the main widget state. If
        # you don't, and the restored state is a frozen state, then when you unfreeze moving columns
        # will still be disabled. This occurs because freezing the columns causes the if movable
        # columns is currently enabled to be stored. If the frozen index is restored after the main
        # widget movable columns will have been disabled as the saved state will have movable columns
        # disabled (as it was created when the table was frozen).
        frozenColumnIndex = stream.readInt32()
        self.setFrozenColumnVisualIndex(frozenColumnIndex if frozenColumnIndex >= 0 else None)

        count = stream.readUInt32()
        if count <= 0:
            return True
        baseState = QtCore.QByteArray(stream.readRawData(count))
        if not super().restoreState(baseState):
            return False

        # Use the same state to restore the frozen column widget
        if not self._frozenColumnWidget.restoreState(baseState):
            # If this fails it means the frozen and main tables might be out of sync resulting
            # in odd bugs
            assert(False)
            return False

        # Force moving columns to be disabled on the frozen table widget. It may have been
        # enabled when using the main table widgets start to restore the frozen column
        self._frozenColumnWidget.setColumnsMoveable(False)

        # Force update of frozen column widget. When the column sizes are restored as part of the
        # state they events that trigger _updateFrozenWidgetGeometry aren't fired.
        self._updateFrozenWidgetGeometry()

        return True

    def setColumnCount(self, columns: int) -> None:
        result = super().setColumnCount(columns)
        self._frozenColumnWidget.setColumnCount(columns)
        self._updateFrozenWidgetColumns()
        self._updateFrozenWidgetGeometry()
        return result

    def setHorizontalHeaderLabels(self, labels: typing.Iterable[str]) -> None:
        self._frozenColumnWidget.setHorizontalHeaderLabels(labels)
        super().setHorizontalHeaderLabels(labels)

        unfrozenIcon = gui.loadIcon(gui.Icon.UnfrozenColumn)
        frozenIcon = gui.loadIcon(gui.Icon.FrozenColumn)
        for column in range(self.horizontalHeader().count()):
            item = self.horizontalHeaderItem(column)
            item.setData(QtCore.Qt.ItemDataRole.DecorationRole, unfrozenIcon)

            item = self._frozenColumnWidget.horizontalHeaderItem(column)
            item.setData(QtCore.Qt.ItemDataRole.DecorationRole, frozenIcon)

    def setHorizontalHeaderItem(self, column: int, item: QtWidgets.QTableWidgetItem) -> None:
        frozenItem = None
        if item:
            frozenItem = item.clone()
            item.setData(QtCore.Qt.ItemDataRole.DecorationRole, gui.loadIcon(gui.Icon.UnfrozenColumn))
            frozenItem.setData(QtCore.Qt.ItemDataRole.DecorationRole, gui.loadIcon(gui.Icon.FrozenColumn))

        self._frozenColumnWidget.setHorizontalHeaderItem(column, frozenItem)
        super().setHorizontalHeaderItem(column, item)

    def setColumnWidth(self, column: int, width: int) -> None:
        self._frozenColumnWidget.setColumnWidth(column, width)
        return super().setColumnWidth(column, width)

    def setColumnHidden(self, column: int, hide: bool) -> None:
        self._frozenColumnWidget.setColumnHidden(column, hide)
        return super().setColumnHidden(column, hide)

    def hideColumn(self, column: int) -> None:
        self._frozenColumnWidget.hideColumn(column)
        return super().hideColumn(column)

    def showColumn(self, column: int) -> None:
        self._frozenColumnWidget.showColumn(column)
        return super().showColumn(column)

    def setRowHidden(self, row: int, hide: bool) -> None:
        self._frozenColumnWidget.setRowHidden(row, hide)
        return super().setRowHidden(row, hide)

    def hideRow(self, row: int) -> None:
        self._frozenColumnWidget.hideRow(row)
        return super().hideRow(row)

    def showRow(self, row: int) -> None:
        self._frozenColumnWidget.showRow(row)
        super().showRow(row)

    def resizeColumnsToContents(self) -> None:
        self._frozenColumnWidget.resizeColumnsToContents()
        return super().resizeColumnsToContents()

    def setSizeAdjustPolicy(self, policy: QtWidgets.QAbstractScrollArea.SizeAdjustPolicy) -> None:
        self._frozenColumnWidget.setSizeAdjustPolicy(policy)
        return super().setSizeAdjustPolicy(policy)

    def setSortingEnabled(self, enable: bool) -> None:
        # The frozen widget can be None here as this function is called by the base
        # ListTable __init__ function
        result = super().setSortingEnabled(enable)
        if self._frozenColumnWidget:
            hasChanged = self._frozenColumnWidget.isSortingEnabled() != enable
            self._frozenColumnWidget.setSortingEnabled(enable)

            if hasChanged:
                # Connect/disconnect signals that copy sorting between main and frozen tables when sorting is
                # enabled/disabled. This is necessary as having a signal connected to sortIndicatorChanged
                # forces sorting to be enabled even if setSortingEnabled is passed False (the arrows aren't
                # showing but clicking the header still sorts)
                if enable:
                    self.horizontalHeader().sortIndicatorChanged.connect(self._sortIndicatorChanged)
                    self._frozenColumnWidget.horizontalHeader().sortIndicatorChanged.connect(self._frozenSortIndicatorChanged)
                else:
                    self.horizontalHeader().sortIndicatorChanged.disconnect(self._sortIndicatorChanged)
                    self._frozenColumnWidget.horizontalHeader().sortIndicatorChanged.disconnect(self._frozenSortIndicatorChanged)
        return result

    def addRow(self) -> int:
        result = super().addRow()
        self._frozenColumnWidget.addRow()
        self._updateFrozenWidgetGeometry()
        return result

    def insertRow(self, row: int) -> None:
        result = super().insertRow(row)
        self._frozenColumnWidget.insertRow(row)
        self._updateFrozenWidgetGeometry()
        return result

    def removeRow(self, row: int) -> None:
        result = super().removeRow(row)
        self._frozenColumnWidget.removeRow(row)
        self._updateFrozenWidgetGeometry()
        return result

    def setRowCount(self, count: int) -> None:
        result = super().setRowCount(count)
        self._frozenColumnWidget.setRowCount(count)
        self._updateFrozenWidgetGeometry()
        return result

    def setItem(self, row: int, column: int, item: QtWidgets.QTableWidgetItem) -> None:
        self._frozenColumnWidget.setItem(row, column, item.clone() if item else None)
        return super().setItem(row, column, item)

    def setAlternatingRowColors(self, enable: bool) -> None:
        # The frozen widget can be None here as this function is called by the base
        # ListTable __init__ function
        if self._frozenColumnWidget:
            self._frozenColumnWidget.setAlternatingRowColors(enable)
        return super().setAlternatingRowColors(enable)

    def setSelectionMode(self, mode: QtWidgets.QAbstractItemView.SelectionMode) -> None:
        if self._frozenColumnWidget:
            self._frozenColumnWidget.setSelectionMode(mode)
        return super().setSelectionMode(mode)

    def setSelectionBehavior(self, behavior: QtWidgets.QAbstractItemView.SelectionBehavior) -> None:
        # The frozen widget can be None here as this function is called by the base
        # ListTable __init__ function
        if self._frozenColumnWidget:
            self._frozenColumnWidget.setSelectionBehavior(behavior)
        return super().setSelectionBehavior(behavior)

    def setContextMenuPolicy(self, policy: QtCore.Qt.ContextMenuPolicy) -> None:
        self._frozenColumnWidget.setContextMenuPolicy(policy)
        return super().setContextMenuPolicy(policy)

    # To use cell widgets the derived class will need to override setFrozenColumnVisualIndex
    # so it can remove the old cell widgets before the update and add new ones after the update.
    # This is necessary as there is no way to detach a cell widget from one table and move it to
    # another table (removeCellWidget causes the widget to be destroyed). See WaypointTable for
    # an example
    def setCellWidget(self, row: int, column: int, widget: QtWidgets.QWidget) -> None:
        if self._frozenColumnVisualIndex != None:
            visualIndex = self.visualColumn(column)
            if visualIndex <= self._frozenColumnVisualIndex:
                # Add the widget to the frozen table instead
                return self._frozenColumnWidget.setCellWidget(row, column, widget)
        return super().setCellWidget(row, column, widget)

    def removeCellWidget(self, row: int, column: int) -> None:
        if self._frozenColumnVisualIndex != None:
            visualIndex = self.visualColumn(column)
            if visualIndex <= self._frozenColumnVisualIndex:
                # Remove the widget to the frozen table instead
                return self._frozenColumnWidget.removeCellWidget(row, column)
        return super().removeCellWidget(row, column)

    def cellWidget(self, row: int, column: int) -> QtWidgets.QWidget:
        if self._frozenColumnVisualIndex != None:
            visualIndex = self.visualColumn(column)
            if visualIndex <= self._frozenColumnVisualIndex:
                # Get the widget from the frozen table instead
                return self._frozenColumnWidget.cellWidget(row, column)
        return super().cellWidget(row, column)

    def setItemDelegate(self, delegate: QtWidgets.QAbstractItemDelegate) -> None:
        if self._frozenColumnWidget:
            self._frozenColumnWidget.setItemDelegate(delegate)
        return super().setItemDelegate(delegate)

    def setItemDelegateForColumn(
            self,
            column: int,
            delegate: QtWidgets.QAbstractItemDelegate
            ) -> None:
        if self._frozenColumnWidget:
            self._frozenColumnWidget.setItemDelegateForColumn(column, delegate)
        return super().setItemDelegateForColumn(column, delegate)

    def setItemDelegateForRow(
            self,
            row: int,
            delegate: QtWidgets.QAbstractItemDelegate
            ) -> None:
        if self._frozenColumnWidget:
            self._frozenColumnWidget.setItemDelegateForRow(row, delegate)
        return super().setItemDelegateForRow(row, delegate)

    def setIconSize(self, size: QtCore.QSize) -> None:
        if self._frozenColumnWidget:
            self._frozenColumnWidget.setIconSize(size)
        return super().setIconSize(size)

    def setStyle(self, style: QtWidgets.QStyle) -> None:
        if self._frozenColumnWidget:
            self._frozenColumnWidget.setStyle(style)
        return super().setStyle(style)

    def setStyleSheet(self, styleSheet: str) -> None:
        if self._frozenColumnWidget:
            self._frozenColumnWidget.setStyleSheet(styleSheet)
        super().setStyleSheet(styleSheet)

    def eventFilter(self, object: object, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.ToolTip:
            assert(isinstance(event, QtGui.QHelpEvent))
            position = event.pos()
            # Event position is in full table coordinates where as items seem to have a coordinate
            # space that covers the area minus the row and column headers
            position.setY(position.y() - self.horizontalHeader().height())

            if object == self:
                if position.x() < self.frozenWidth():
                    return True
            elif object == self._frozenColumnWidget:
                item = self._frozenColumnWidget.itemAt(position)
                if item:
                    # Generating the tooltip on demand like this is problematic
                    # as a tooltip set on an item at this point won't be actually
                    # displayed. Storing the tooltips would also cause additional
                    # headaches for tables where the tooltip content can change
                    # (e.g. hex tooltips change if map style changes). The solution
                    # is to just manually display the tooltip.
                    toolTip = self._createToolTip(item)
                    if toolTip:
                        QtWidgets.QToolTip.showText(event.globalPos(), toolTip)
        return super().eventFilter(object, event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        result = super().resizeEvent(event)
        self._updateFrozenWidgetGeometry()
        return result

    def _updateFrozenWidgetGeometry(self) -> None:
        dataWidth = self.frozenWidth()
        dataHeight = min(self.viewport().height(), self.frozenHeight())
        rect = QtCore.QRect(
            self.verticalHeader().width(),
            0,
            dataWidth + self.frameWidth(),
            dataHeight + self.horizontalHeader().height())
        self._frozenColumnWidget.setGeometry(rect)

    def _updateFrozenWidgetColumns(self) -> None:
        self._frozenColumnWidget.horizontalHeader().setFixedHeight(
            self.horizontalHeader().height())

        columnCount = self._frozenColumnWidget.columnCount()
        for column in range(columnCount):
            self._frozenColumnWidget.setColumnWidth(column, self.columnWidth(column))

    def _copySelection(
            self,
            fromTable: ListTable,
            toTable: ListTable
            ) -> None:
        if self._signalLoopBlock:
            return # Ignore the request to copy

        self._signalLoopBlock = True

        try:
            toTable.selectionModel().select(
                fromTable.selectionModel().selection(),
                QtCore.QItemSelectionModel.SelectionFlag.Clear | QtCore.QItemSelectionModel.SelectionFlag.Select)
        finally:
            self._signalLoopBlock = False

    def _itemChanged(self, item: QtWidgets.QTableWidgetItem) -> None:
        # Copy data for each role only if its changed. It's important to do this rather than just
        # cloning a new copy of the item and inserting into the frozen table as that causes sorting.
        # This can then mean the tables can get out of sync if sorting by columns that contain the
        # same value.
        frozenItem = self._frozenColumnWidget.item(item.row(), item.column())
        for role in FrozenColumnListTable._DataRoleValues:
            oldData = frozenItem.data(role)
            newData = item.data(role)
            if oldData != newData:
                frozenItem.setData(role, newData)

    def _hideColumnAction(self, action):
        super()._userHideColumnAction(action)

        index = action.data()
        if self._frozenColumnVisualIndex != None:
            if index <= self._frozenColumnVisualIndex:
                pass

    def _userHideColumnAction(self, action: QtWidgets.QAction) -> None:
        super()._userHideColumnAction(action)
        self._updateFrozenWidgetGeometry()

    def _columnWidthChanged(
            self,
            logicalIndex: int,
            oldSize: int,
            newSize: int
            ) -> None:
        super()._columnWidthChanged(
            logicalIndex=logicalIndex,
            oldSize=oldSize,
            newSize=newSize)

        self._frozenColumnWidget.setColumnWidth(logicalIndex, newSize)
        self._updateFrozenWidgetGeometry()

    def _frozenColumnWidthChanged(
            self,
            logicalIndex: int,
            oldSize: int,
            newSize: int
            ) -> None:
        # Mirror the new column width in the main widget if the new size is for one of the frozen
        # columns
        if self._frozenColumnVisualIndex != None:
            visualIndex = self.visualColumn(logicalIndex)
            if visualIndex <= self._frozenColumnVisualIndex:
                self.setColumnWidth(logicalIndex, newSize)

    def _rowHeightChanged(
            self,
            logicalIndex: int,
            oldSize: int,
            newSize: int
            ) -> None:
        self._frozenColumnWidget.setRowHeight(logicalIndex, newSize)

    def _itemSelectionChanged(self) -> None:
        self._copySelection(
            fromTable=self,
            toTable=self._frozenColumnWidget)

    def _frozenItemSelectionChanged(self) -> None:
        self._copySelection(
            fromTable=self._frozenColumnWidget,
            toTable=self)

    def _frozenContextMenuRequested(
            self,
            point: QtCore.QPoint
            ) -> None:
        self.customContextMenuRequested.emit(point)

    def _columnMoved(
            self,
            logicalIndex: int,
            oldVisualIndex: int,
            newVisualIndex: int
            ) -> None:
        self._frozenColumnWidget.horizontalHeader().moveSection(oldVisualIndex, newVisualIndex)

    # For reasons I don't understand, using these functions rather than having the signals directly
    # connected to the other tables sortByColumn functions, fixes issues I was seeing on older
    # versions of macOS where the sorting on the frozen and non-frozen tables would get out of sync.
    def _sortIndicatorChanged(
            self,
            logicalIndex: int,
            order: QtCore.Qt.SortOrder
            ) -> None:
        self._frozenColumnWidget.sortByColumn(logicalIndex, order)

    def _frozenSortIndicatorChanged(
            self,
            logicalIndex: int,
            order: QtCore.Qt.SortOrder
            ) -> None:
        self.sortByColumn(logicalIndex, order)

    def _headerIconClicked(
            self,
            logicalIndex: int
            ) -> None:
        visualIndex = self.visualColumn(logicalIndex)
        if visualIndex == self._frozenColumnVisualIndex:
            self.setFrozenColumnVisualIndex(None)
        else:
            self.setFrozenColumnVisualIndex(visualIndex)
