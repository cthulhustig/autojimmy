import enum
import gui
import logging
import re
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class TableWidgetEx(QtWidgets.QTableWidget):
    _FocusRectStyle = 'QTableWidget:focus{{border:{width}px solid {colour};}}'
    _FocusRectRegex = re.compile(r'QTableWidget:focus\s*{.*?}')
    _FocusRectWidth = 4

    class MenuAction(enum.Enum):
        CopyAsHtml = enum.auto()
        CopyAsImage = enum.auto()
        ExportAsHtml = enum.auto()
        ExportAsImage = enum.auto()

    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, rows: int, columns: int, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(
            self,
            *args,
            **kwargs
            ) -> None:
        super().__init__(*args, **kwargs)
        self._showFocusRect = False

        self._menuActions: typing.Dict[typing.Tuple[enum.Enum, QtWidgets.QAction]] = {}

        action = QtWidgets.QAction('Copy as HTML', self)
        action.setEnabled(False) # No content
        action.triggered.connect(self.copyToClipboardAsHtml)
        self.setMenuAction(TableWidgetEx.MenuAction.CopyAsHtml, action)

        action = QtWidgets.QAction('Copy as Image', self)
        action.setEnabled(False) # No content
        action.triggered.connect(self.copyToClipboardAsImage)
        self.setMenuAction(TableWidgetEx.MenuAction.CopyAsImage, action)

        action = QtWidgets.QAction('Export as HTML...', self)
        action.setEnabled(False) # No content
        action.triggered.connect(self.promptExportAsHtml)
        self.setMenuAction(TableWidgetEx.MenuAction.ExportAsHtml, action)

        action = QtWidgets.QAction('Export as Image...', self)
        action.setEnabled(False) # No content
        action.triggered.connect(self.promptExportAsImage)
        self.setMenuAction(TableWidgetEx.MenuAction.ExportAsImage, action)

        self._hookModel()

    def setModel(self, model: typing.Optional[QtCore.QAbstractItemModel]) -> None:
        wasEmpty = self.isEmpty()

        self._unhookModel()
        super().setModel(model)
        self._hookModel()

        isEmpty = self.isEmpty()
        if isEmpty != wasEmpty:
            self.isEmptyChanged()

    # NOTE: A table not being empty just means it has cells, it doesn't
    # necessarily mean those cells have content (i.e. items) yet
    def isEmpty(self) -> bool:
        return self.rowCount() <= 0 or self.columnCount() <= 0

    # NOTE: This is called when the table transitions to and from having being
    # empty and not being empty. In this context not being empty means having
    # non zero number of cells (i.e. the row AND column count are non-zero), it
    # does not necessarily mean any of those cells contain items.
    def isEmptyChanged(self) -> None:
        self._syncTableWidgetExActions()

    def showFocusRect(self) -> bool:
        return self._showFocusRect

    def setShowFocusRect(self, enabled: bool) -> None:
        self._showFocusRect = enabled
        styleSheet = TableWidgetEx._FocusRectRegex.sub(self.styleSheet(), '')
        styleSheet.strip()
        self.setStyleSheet(styleSheet)

    def setStyleSheet(self, styleSheet: str) -> None:
        if self._showFocusRect and not TableWidgetEx._FocusRectRegex.match(styleSheet):
            palette = self.palette()
            focusColour = palette.color(QtGui.QPalette.ColorRole.Highlight)
            if styleSheet:
                styleSheet += ' '

            styleSheet += TableWidgetEx._FocusRectStyle.format(
                width=int(TableWidgetEx._FocusRectWidth * gui.interfaceScale()),
                colour=gui.colourToString(focusColour, includeAlpha=False))
        super().setStyleSheet(styleSheet)

    def contentToHtml(self) -> str:
        horzHeader = self.horizontalHeader()
        vertHeader = self.verticalHeader()
        hasHorzHeader = horzHeader and not horzHeader.isHidden()
        hasVertHeader = vertHeader and not vertHeader.isHidden()
        model = self.model()

        content = '<html>\n'
        content += '<head>\n'
        content += '<style>\n'
        content += 'table, th, td {\n'
        content += 'border: 1px solid black;\n'
        content += 'border-collapse: collapse;\n'
        content += '}\n'
        content += 'th, td {\n'
        content += 'padding: 5px;\n'
        content += '}\n'
        content += '</style>\n'
        content += '</head>\n'
        content += '<body>\n'
        content += '<table style="border: 1px solid black; border-collapse: collapse;">\n'

        if hasHorzHeader:
            content += '<tr>\n'
            for column in range(model.columnCount()):
                if self.isColumnHidden(column):
                    continue

                tableHeader = TableWidgetEx._formatTableHeader(
                    model=model,
                    index=column,
                    orientation=QtCore.Qt.Orientation.Horizontal)
                content += f'{tableHeader}\n'
            content += '</tr>\n'

        rowSpans = [0] * self.columnCount()
        row = 0
        while row < self.rowCount():
            rowHidden = self.isRowHidden(row)
            column = 0

            if not rowHidden:
                content += '<tr>\n'

            if hasVertHeader and not rowHidden:
                tableHeader = TableWidgetEx._formatTableHeader(
                    model=model,
                    index=column,
                    orientation=QtCore.Qt.Orientation.Vertical)
                content += f'{tableHeader}\n'

            while column < self.columnCount():
                rowSpan = rowSpans[column]
                if rowSpan > 0:
                    rowSpans[column] = rowSpan - 1
                    continue

                columnSpan = self.columnSpan(row, column)
                assert(columnSpan > 0)
                rowSpan = self.rowSpan(row, column)
                assert(rowSpan > 0)
                if not rowHidden and not self.isColumnHidden(column):
                    itemText = self._htmlCellText(row, column)
                    itemAlignment = self._htmlCellAlignment(row, column)
                    itemFont = self._htmlCellFont(row, column)

                    itemText = gui.textToHtmlContent(text=itemText, font=itemFont)
                    itemAlignment = gui.alignmentToHtmlStyle(alignment=itemAlignment)

                    content += '<td{style}{columnSpan}{rowSpan}>{itemText}</td>\n'.format(
                        style=f' style="{itemAlignment}"' if itemAlignment else '',
                        columnSpan=f' colspan="{columnSpan}"' if columnSpan > 1 else '',
                        rowSpan=f' rowspan="{rowSpan}"' if rowSpan > 1 else '',
                        itemText=itemText)

                if rowSpan > 1:
                    columnSpanEnd = column + columnSpan
                    while column < columnSpanEnd:
                        rowSpans[column] = rowSpan - 1
                        column += 1
                else:
                    column += columnSpan

            if not rowHidden:
                content += '</tr>\n'
            row += 1

        content += '</table>\n'
        content += '</body>\n'
        content += '</html>\n'

        return content

    def copyToClipboardAsHtml(self) -> None:
        gui.setClipboardContent(content=self.contentToHtml())

    def copyToClipboardAsImage(self) -> None:
        gui.setClipboardContent(content=self.grab())

    def promptExportAsHtml(self) -> None:
        content = self.contentToHtml()

        path, _ = gui.FileDialogEx.getSaveFileName(
            parent=self,
            caption='Export as HTML',
            filter=f'{gui.HTMLFileFilter};;{gui.AllFileFilter}')
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

    def promptExportAsImage(self) -> None:
        path, filter = gui.FileDialogEx.getSaveFileName(
            parent=self,
            caption='Export as Image',
            filter=f'{gui.BMPFileFilter};;{gui.JPEGFileFilter};;{gui.PNGFileFilter};;{gui.X11BitmapFileFilter};;{gui.X11PixmapFileFilter}')
        if not path:
            return # User cancelled

        if filter == gui.BMPFileFilter:
            format = 'BMP'
        elif filter == gui.JPEGFileFilter:
            format = 'JPG'
        elif filter == gui.PNGFileFilter:
            format = 'PNG'
        elif filter == gui.X11BitmapFileFilter:
            format = 'XBM'
        elif filter == gui.X11PixmapFileFilter:
            format = 'XPM'
        else:
            message = f'Unable to export image with unknown filter "{filter}"'
            logging.error(message)
            gui.MessageBoxEx.critical(parent=self, text=message)
            return

        image = self.grab()
        if not image.save(path, format):
            message = f'Failed to export content to "{path}"'
            logging.error(message)
            gui.MessageBoxEx.critical(parent=self, text=message)

    def menuAction(
            self,
            id: enum.Enum
            ) -> typing.Optional[QtWidgets.QAction]:
        return self._menuActions.get(id)

    def setMenuAction(
            self,
            id: enum.Enum,
            action: typing.Optional[QtWidgets.QAction]
            ) -> None:
        self._menuActions[id] = action

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        needsSeparator = False

        action = self.menuAction(TableWidgetEx.MenuAction.CopyAsHtml)
        if action:
            menu.addAction(action)
            needsSeparator = True

        action = self.menuAction(TableWidgetEx.MenuAction.CopyAsImage)
        if action:
            menu.addAction(action)
            needsSeparator = True

        if needsSeparator:
            menu.addSeparator()
            needsSeparator = False

        action = self.menuAction(TableWidgetEx.MenuAction.ExportAsHtml)
        if action:
            menu.addAction(action)

        action = self.menuAction(TableWidgetEx.MenuAction.ExportAsImage)
        if action:
            menu.addAction(action)

    def displayContextMenu(self, pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        self.fillContextMenu(menu=menu)

        viewport = self.viewport()
        globalPos = viewport.mapToGlobal(pos) if viewport else self.mapToGlobal(pos)
        menu.exec(globalPos)

    def keyPressEvent(self, event: typing.Optional[QtGui.QKeyEvent]) -> None:
        if event is not None and event.matches(QtGui.QKeySequence.StandardKey.Copy):
            if self.rowCount() > 0:
                self.copyToClipboardAsHtml()

            # NOTE: Don't call base implementation as there is a default
            # handler that copies the content of the current cell to the
            # clipboard which would replace what has just been set
            return

        super().keyPressEvent(event)

    def contextMenuEvent(self, event: typing.Optional[QtGui.QContextMenuEvent]) -> None:
        if self.contextMenuPolicy() != QtCore.Qt.ContextMenuPolicy.DefaultContextMenu:
            super().contextMenuEvent(event)
            return

        if event:
            self.displayContextMenu(pos=event.pos())
        #super().contextMenuEvent(event)

    def _hookModel(self) -> None:
        model = self.model()
        if model:
            model.rowsInserted.connect(self._handleRowsInserted)
            model.rowsRemoved.connect(self._handleRowsRemoved)
            model.columnsInserted.connect(self._handleColumnsInserted)
            model.columnsRemoved.connect(self._handleColumnsRemoved)

    def _unhookModel(self) -> None:
        model = self.model()
        if model:
            model.rowsInserted.disconnect(self._handleRowsInserted)
            model.rowsRemoved.disconnect(self._handleRowsRemoved)
            model.columnsInserted.disconnect(self._handleColumnsInserted)
            model.columnsRemoved.disconnect(self._handleColumnsRemoved)

    def _handleRowsInserted(
            self,
            parent: QtCore.QModelIndex,
            first: int,
            last: int
            ) -> None:
        # The table being empty has changed if the rows inserted are the only
        # rows in the table (i.e. it had none before the insert) _AND_ and the
        # column count is non-zero.
        # If the inserted rows are not the only rows in the table then either,
        # the column count is non-zero and the table is already non-empty _OR_
        # the column count is zero and the table is still empty, either way
        # there is no change
        # If the inserted rows are the only rows in the table but the column
        # count is zero, then the table is still considered empty as there are
        # no data cells to be displayed to the user
        count = (last - first) + 1
        if self.rowCount() == count and self.columnCount() > 0:
            self.isEmptyChanged()

    def _handleRowsRemoved(
            self,
            parent: QtCore.QModelIndex,
            first: int,
            last: int
            ) -> None:
        # The table being empty has changed if the row count is now zero (i.e.
        # the removed rows were the last remaining rows in the table) and the
        # column count is non-zero.
        # If the removed rows were not the last remaining rows then, either the
        # column count is non-zero and the table is still not empty _OR_ the
        # column count is zero and the table was already considered empty,
        # either way there has been no change
        # If the removed rows were the the only rows in the table but the column
        # count is already zero, then the table was already considered empty and
        # there is no change
        if self.rowCount() == 0 and self.columnCount() > 0:
            self.isEmptyChanged()

    def _handleColumnsInserted(
            self,
            parent: QtCore.QModelIndex,
            first: int,
            last: int
            ) -> None:
        # The table being empty has changed if the columns inserted are the
        # only columns in the table (i.e. it had none before the insert) _AND_
        # and the row count is non-zero.
        # If the inserted columns are not the only columns in the table then
        # either, the row count is non-zero and the table is already non-empty
        # _OR_ the row count is zero and the table is still empty, either way
        # there is no change
        # If the inserted columns are the only columns in the table but the row
        # count is zero, then the table is still considered empty as there are
        # no data cells to be displayed to the user
        count = (last - first) + 1
        if self.columnCount() == count and self.rowCount() > 0:
            self.isEmptyChanged()

    def _handleColumnsRemoved(
            self,
            parent: QtCore.QModelIndex,
            first: int,
            last: int
            ) -> None:
        # The table being empty has changed if the column count is now zero
        # (i.e. the removed columns were the last remaining rows in the table)
        # and the row count is non-zero.
        # If the removed columns were not the last remaining columns then,
        # either the row count is non-zero and the table is still not empty
        # _OR_ the row count is zero and the table was already considered empty,
        # either way there has been no change
        # If the removed columns were the the only columns in the table but the
        # row count is already zero, then the table was already considered empty
        # and there is no change
        if self.columnCount() == 0 and self.rowCount() > 0:
            self.isEmptyChanged()

    def _syncTableWidgetExActions(self) -> None:
        hasContent = self.rowCount() > 0 and self.columnCount() > 0

        action = self.menuAction(TableWidgetEx.MenuAction.CopyAsHtml)
        if action:
            action.setEnabled(hasContent)

        action = self.menuAction(TableWidgetEx.MenuAction.CopyAsImage)
        if action:
            action.setEnabled(hasContent)

        action = self.menuAction(TableWidgetEx.MenuAction.ExportAsHtml)
        if action:
            action.setEnabled(hasContent)

        action = self.menuAction(TableWidgetEx.MenuAction.ExportAsImage)
        if action:
            action.setEnabled(hasContent)

    def _htmlCellText(self, row: int, column: int) -> str:
        item = self.item(row, column)
        return item.text() if item else ''

    def _htmlCellAlignment(self, row: int, column: int) -> typing.Optional[int]:
        item = self.item(row, column)
        return item.textAlignment() if item else None

    def _htmlCellFont(self, row: int, column: int) -> typing.Optional[QtGui.QFont]:
        item = self.item(row, column)
        return item.font() if item else None

    @staticmethod
    def _formatTableHeader(
            model: QtCore.QAbstractItemModel,
            index: int,
            orientation: QtCore.Qt.Orientation
            ) -> str:
        headerText = model.headerData(
            index,
            orientation,
            QtCore.Qt.ItemDataRole.DisplayRole)
        headerAlignment = model.headerData(
            index,
            orientation,
            QtCore.Qt.ItemDataRole.TextAlignmentRole)
        headerFont = model.headerData(
            index,
            orientation,
            QtCore.Qt.ItemDataRole.FontRole)

        headerText = gui.textToHtmlContent(text=headerText, font=headerFont)
        headerAlignment = gui.alignmentToHtmlStyle(alignment=headerAlignment)

        return '<th{style}>{headerText}</th>'.format(
            style=f' style="{headerAlignment}"' if headerAlignment else '',
            headerText=headerText)
