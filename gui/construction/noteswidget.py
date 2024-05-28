from PyQt5.QtCore import QEvent, QObject
import construction
import gui
import typing
from PyQt5 import QtCore, QtWidgets, QtGui

class NotesWidget(QtWidgets.QWidget):
    _ColumnNames = ['Source', 'Note']

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._table = gui.ListTable()

        self._table = gui.ListTable()
        self._table.setColumnHeaders(NotesWidget._ColumnNames)
        self._table.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self._table.setWordWrap(True)
        self._table.setAlternatingRowColors(False)
        self._table.setSortingEnabled(False)
        self._table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().sectionResized.connect(
            self._table.resizeRowsToContents)
        self._table.installEventFilter(self)
        
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._table)

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

                    self._table.setItem(
                        row, 0,
                        QtWidgets.QTableWidgetItem(source))
                    
                    self._table.setItem(
                        row, 1,
                        QtWidgets.QTableWidgetItem(note))

                    seenNotes.add(key)
        self._table.resizeRowsToContents()

    def clear(self) -> None:
        self._table.removeAllRows()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        width = event.size().width()
        maxWidth = int(width * 0.33)
        self._table.horizontalHeader().setMaximumSectionSize(maxWidth)
        return super().resizeEvent(event)
    
    def copySelectionToClipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        if not clipboard:
            return
        
        content = ''
        for row in self._table.selectedRows():
            item = self._table.item(row, 0)
            source = item.text() if item else None
            item = self._table.item(row, 1)
            note = item.text() if item else None
            if source and note:
                content += f'{source} -- {note}\n'
        if content:
            clipboard.setText(content)
            
    def eventFilter(self, object: QObject, event: QEvent) -> bool:
        if object == self._table:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.matches(QtGui.QKeySequence.StandardKey.Copy):
                    self.copySelectionToClipboard()
                    event.accept()
                    return True

        return super().eventFilter(object, event)

    


        