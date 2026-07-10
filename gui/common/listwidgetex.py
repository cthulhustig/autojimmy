
import typing
from PyQt5 import QtCore, QtWidgets, QtGui

class ListWidgetEx(QtWidgets.QListWidget):
    def isEmpty(self) -> bool:
        return self.count() <= 0

    def removeRow(self, row: int) -> None:
        self.takeItem(row)

    def hasCurrentItem(self) -> bool:
        return self.currentItem() != None

    def hasSelection(self) -> bool:
        return self.selectionModel().hasSelection()

    def selectionCount(self) -> int:
        count = 0
        for row in range(self.count()):
            item = self.item(row)
            if not item:
                continue
            if item.isSelected():
                count += 1
        return count

    def itemFromWidget(
            self,
            widget: QtWidgets.QWidget
            ) -> typing.Optional[QtWidgets.QListWidgetItem]:
        for item in self.items():
            itemWidget = self.itemWidget(item)
            if itemWidget == widget:
                return item
        return None

    def rowData(self, row: int, role: QtCore.Qt.ItemDataRole) -> typing.Any:
        item = self.item(row)
        return item.data(role) if item else None

    def currentData(self, role: QtCore.Qt.ItemDataRole) -> typing.Any:
        currentItem = self.currentItem()
        return currentItem.data(role) if currentItem else None

class ResizingListWidget(ListWidgetEx):
    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, text: str, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Minimum)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def sizeHint(self) -> QtCore.QSize:
        sizeHint = super().sizeHint()

        height = 0
        for row in range(self.count()):
            item = self.item(row)
            index = self.indexFromItem(item)
            rect = self.rectForIndex(index)
            height += rect.height()

        contentMargin = self.contentsMargins()
        sizeHint.setHeight(height + contentMargin.top() + contentMargin.bottom())

        return sizeHint

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        # If the widget has been resized then the size hint will also have changed.
        # Call updateGeometry to make sure any layouts are notified of the change.
        self.updateGeometry()
        return super().resizeEvent(a0)