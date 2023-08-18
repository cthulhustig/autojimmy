import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class _CustomItemDelegate(QtWidgets.QStyledItemDelegate):
    tabCloseRequested = QtCore.pyqtSignal([int])

    def __init__(
        self,
        parent: typing.Optional[QtWidgets.QWidget] = None
    ):
        super().__init__(parent)

    def paint(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> None:
        customOption = QtWidgets.QStyleOptionViewItem(option)
        # Draw close icon on right hand side of list item rather than left
        customOption.decorationPosition = QtWidgets.QStyleOptionViewItem.Position.Right
        super().paint(painter, customOption, index)

    def editorEvent(
            self,
            event: QtCore.QEvent,
            model: QtCore.QAbstractItemModel,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> bool:
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            # Prevent processing of mouse button event if the close tab icon was clicked. For
            # consistency with other buttons the close request event isn't generated until the
            # mouse button is released
            assert(isinstance(event, QtGui.QMouseEvent))
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                if self._checkForIconClick(event.globalPos(), option, index):
                    # Prevent clicking on close icon from switching to that tab
                    return True
        elif event.type() == QtCore.QEvent.Type.MouseButtonRelease:
            # Prevent processing of the mouse event if the close tab icon has been clicked. Instead
            # a tab close request event.
            assert(isinstance(event, QtGui.QMouseEvent))
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                if self._checkForIconClick(event.globalPos(), option, index):
                    self.tabCloseRequested.emit(index.row())
                    return True
        return super().editorEvent(event, model, option, index)

    def _iconRect(
            self,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> QtCore.QRect:
        customOption = QtWidgets.QStyleOptionViewItem(option)
        customOption.decorationPosition = QtWidgets.QStyleOptionViewItem.Position.Right
        self.initStyleOption(customOption, index)
        widget = customOption.widget
        return widget.style().subElementRect(
            QtWidgets.QStyle.SubElement.SE_ItemViewItemDecoration,
            customOption,
            widget)

    def _checkForIconClick(
            self,
            globalPos: QtCore.QPoint,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> bool:
        iconRect = self._iconRect(option, index)
        return iconRect.isValid() and iconRect.contains(option.widget.mapFromGlobal(globalPos))

class _CustomListWidget(QtWidgets.QListWidget):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

    def sizeHint(self) -> QtCore.QSize:
        # Set the size hint so the list will be resized to the fit the contents
        s = QtCore.QSize()
        s.setHeight(super().sizeHint().height())
        s.setWidth(self.sizeHintForColumn(0))
        return s

# Vertical tab widget, similar to QTabBar
class VerticalTabBar(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()
    tabCloseRequested = QtCore.pyqtSignal([int])

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._tabsClosable = False

        itemDelegate = _CustomItemDelegate()
        itemDelegate.tabCloseRequested.connect(self._closeTabRequested)

        self._list = _CustomListWidget()
        self._list.selectionModel().selectionChanged.connect(
            lambda: self.selectionChanged.emit())
        self._list.setItemDelegate(itemDelegate)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list, 0)

        self.setLayout(layout)

    def addTab(
            self,
            text: str
            ) -> int:
        item = QtWidgets.QListWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        if self._tabsClosable:
            item.setIcon(gui.loadIcon(gui.Icon.CloseTab))

        self._list.addItem(item)
        self._list.setMinimumWidth(self._list.sizeHintForColumn(0) + 20)
        if self._list.count() == 1:
            # This is the first tab so select the item
            self._list.setCurrentRow(0)
        return self._list.count() - 1 # Return tab index

    def removeTab(
            self,
            index: int
            ) -> None:
        self._list.takeItem(index)

    def count(self) -> int:
        return self._list.count()

    def currentIndex(self) -> int:
        indexes = self._list.selectedIndexes()
        if not indexes:
            return -1
        assert(len(indexes) == 1)
        return indexes[0].row()

    def setCurrentIndex(
            self,
            index: int,
            ) -> None:
        item = self._list.item(index)
        if not item:
            return
        self._list.setCurrentItem(item)

    def setTabsClosable(self, closable) -> None:
        self._tabsClosable = closable

        icon = None
        if self._tabsClosable:
            icon = gui.loadIcon(gui.Icon.CloseTab)

        for row in range(self._list.count()):
            item = self._list.item(row)
            item.setIcon(icon)

    def tabsClosable(self) -> bool:
        return self._tabsClosable

    def _closeTabRequested(
            self,
            index: int
            ) -> None:
        self.tabCloseRequested.emit(index)

# Vertical tab widget with associated widget per tab, similar to QTabWidget
class VerticalTabWidget(QtWidgets.QWidget):
    tabCloseRequested = QtCore.pyqtSignal([int])

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._tabsClosable = False

        itemDelegate = _CustomItemDelegate()
        itemDelegate.tabCloseRequested.connect(self._closeTabRequested)

        self._list = _CustomListWidget()
        self._list.selectionModel().selectionChanged.connect(self._selectionChanged)
        self._list.setItemDelegate(itemDelegate)

        self._stack = QtWidgets.QStackedWidget()

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list, 0)
        layout.addWidget(self._stack, 1)

        self.setLayout(layout)

    def addTab(
            self,
            widget: QtWidgets.QWidget,
            text: str
            ) -> None:
        self._stack.addWidget(widget)

        item = QtWidgets.QListWidgetItem(text)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, widget)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        if self._tabsClosable:
            item.setIcon(gui.loadIcon(gui.Icon.CloseTab))

        self._list.addItem(item)
        self._list.setMinimumWidth(self._list.sizeHintForColumn(0) + 20)
        if self._list.count() == 1:
            # This is the first tab so select the item
            self._list.setCurrentRow(0)

    def removeTab(
            self,
            index: int
            ) -> None:
        widget = self.widget(index)
        if widget:
            self._stack.removeWidget(widget)
        self._list.takeItem(index)

    def count(self) -> int:
        return self._list.count()

    def widget(
            self,
            index: int
            ) -> QtWidgets.QWidget:
        item = self._list.item(index)
        if not item:
            return None
        widget = item.data(QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(widget, QtWidgets.QWidget))
        return widget

    def indexOf(
            self,
            widget: QtWidgets.QWidget
            ) -> int:
        return self._stack.indexOf(widget)

    def currentWidget(self) -> typing.Optional[QtWidgets.QWidget]:
        currentIndex = self.currentIndex()
        if currentIndex < 0:
            return None
        return self.widget(currentIndex)

    def currentIndex(self) -> int:
        indexes = self._list.selectedIndexes()
        if not indexes:
            return -1
        assert(len(indexes) == 1)
        return indexes[0]

    def setCurrentWidget(
            self,
            widget: QtWidgets.QWidget
            ) -> None:
        index = self.indexOf(widget)
        if index < 0:
            return
        item = self._list.item(index)
        if not item:
            return
        self._list.setCurrentItem(item)
        self._stack.setCurrentWidget(widget)

    def setCurrentIndex(
            self,
            index: int,
            ) -> None:
        widget = self.widget(index)
        if not widget:
            return
        self.setCurrentWidget(widget)

    def setTabsClosable(self, closable) -> None:
        self._tabsClosable = closable

        icon = None
        if self._tabsClosable:
            icon = gui.loadIcon(gui.Icon.CloseTab)

        for row in range(self._list.count()):
            item = self._list.item(row)
            item.setIcon(icon)

    def tabsClosable(self) -> bool:
        return self._tabsClosable

    def _selectionChanged(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        widget = item.data(QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(widget, QtWidgets.QWidget))
        self._stack.setCurrentWidget(widget)

    def _closeTabRequested(
            self,
            index: int
            ) -> None:
        self.tabCloseRequested.emit(index)
