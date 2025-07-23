import gui
import logging
import re
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class TableWidgetEx(QtWidgets.QTableWidget):
    _FocusRectStyle = 'QTableWidget:focus{{border:{width}px solid {colour};}}'
    _FocusRectRegex = re.compile(r'QTableWidget:focus\s*{.*?}')
    _FocusRectWidth = 4

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

        self._copyContentToClipboardAsHtmlAction = QtWidgets.QAction('Copy as HTML', self)
        self._copyContentToClipboardAsHtmlAction.setEnabled(False) # No content to copy
        self._copyContentToClipboardAsHtmlAction.triggered.connect(self.copyContentToClipboardAsHtml)

        self._copyViewToClipboardAction = QtWidgets.QAction('Copy as Image', self)
        self._copyViewToClipboardAction.setEnabled(True)
        self._copyViewToClipboardAction.triggered.connect(self.copViewToClipboard)

        self._promptExportContentToHtmlAction = QtWidgets.QAction('Export to HTML...', self)
        self._promptExportContentToHtmlAction.setEnabled(False) # No content to copy
        self._promptExportContentToHtmlAction.triggered.connect(self.promptExportContentToHtml)

    def insertRow(self, row: int) -> None:
        super().insertRow(row)
        self._syncTableWidgetExActions()

    def removeRow(self, row):
        super().removeRow(row)
        self._syncTableWidgetExActions()

    def setRowCount(self, rows):
        super().setRowCount(rows)
        self._syncTableWidgetExActions()

    def insertColumn(self, column):
        super().insertColumn(column)
        self._syncTableWidgetExActions()

    def removeColumn(self, column):
        super().removeColumn(column)
        self._syncTableWidgetExActions()

    def setColumnCount(self, columns):
        super().setColumnCount(columns)
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
        content += 'padding: 2px;\n'
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
                    item = self.item(row, column)
                    itemText = item.text() if item else ''
                    itemAlignment = item.textAlignment() if item else None
                    itemFont = item.font() if item else None

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

    def copyContentToClipboardAsHtml(self) -> None:
        gui.setClipboardContent(content=self.contentToHtml())

    def copViewToClipboard(self) -> None:
        gui.setClipboardContent(content=self.grab())

    def promptExportContentToHtml(self) -> None:
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

    def copyContentToClipboardAsHtmlAction(self) -> QtWidgets.QAction:
        return self._copyContentToClipboardAsHtmlAction

    def setCopyContentToClipboardAsHtmlAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._copyContentToClipboardAsHtmlAction = action

    def copyViewToClipboardAction(self) -> QtWidgets.QAction:
        return self._copyViewToClipboardAction

    def setCopyViewToClipboardAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._copyViewToClipboardAction = action

    def promptExportContentToHtmlAction(self) -> QtWidgets.QAction:
        return self._promptExportContentToHtmlAction

    def setPromptExportContentToHtmlAction(
            self,
            action: QtWidgets.QAction
            ) -> None:
        self._promptExportContentToHtmlAction = action

    def fillContextMenu(self, menu: QtWidgets.QMenu) -> None:
        menu.addAction(self.copyContentToClipboardAsHtmlAction())
        menu.addAction(self.copyViewToClipboardAction())
        menu.addSeparator()
        menu.addAction(self.promptExportContentToHtmlAction())

    def displayContextMenu(self, pos: QtWidgets.QMenu) -> None:
        menu = QtWidgets.QMenu(self)
        self.fillContextMenu(menu=menu)

        viewport = self.viewport()
        globalPos = viewport.mapToGlobal(pos) if viewport else self.mapToGlobal(pos)
        menu.exec(globalPos)

    def keyPressEvent(self, event: typing.Optional[QtGui.QKeyEvent]) -> None:
        if event is not None and event.matches(QtGui.QKeySequence.StandardKey.Copy):
            # If there is no content, don't do anything but still accept
            # the event so the handling of the key press is consistent
            if self.rowCount() > 0:
                self.copyContentToClipboardAsHtml()
            event.accept()

        super().keyPressEvent(event)

    def contextMenuEvent(self, event: typing.Optional[QtGui.QContextMenuEvent]) -> None:
        super().contextMenuEvent(event)

        if event:
            self.displayContextMenu(pos=event.pos())

    def _syncTableWidgetExActions(self) -> None:
        hasContent = self.rowCount() > 0 and self.columnCount() > 0
        if self._copyContentToClipboardAsHtmlAction is not None:
            self._copyContentToClipboardAsHtmlAction.setEnabled(hasContent)
        if self._promptExportContentToHtmlAction is not None:
            self._promptExportContentToHtmlAction.setEnabled(hasContent)

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

        return '<th{style}>{headerText}</th>\n'.format(
            style=f' style="{headerAlignment}"' if headerAlignment else '',
            headerText=headerText)