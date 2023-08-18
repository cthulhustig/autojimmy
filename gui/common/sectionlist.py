import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# https://stackoverflow.com/questions/55969916/how-to-remove-qtreeview-indentation
class _SectionListItemDelegate(QtWidgets.QStyledItemDelegate):
    def paint(
            self,
            painter: QtGui.QPainter,
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> None:
        widget = option.widget
        assert(isinstance(widget, QtWidgets.QTreeWidget))
        item: QtWidgets.QTreeWidgetItem = widget.itemFromIndex(index)

        hasIndicator = False
        hasItemWidget = widget.itemWidget(item, index.column()) != None
        if index.column() == 0 and not hasItemWidget:
            indicatorPolicy = item.childIndicatorPolicy()
            if indicatorPolicy == QtWidgets.QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator:
                hasIndicator = True
            elif indicatorPolicy == QtWidgets.QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicatorWhenChildless:
                hasIndicator = item.childCount() > 0

        # Don't show focus highlight as tree list items aren't "selectable"
        modifiedOption = QtWidgets.QStyleOptionViewItem(option)
        modifiedOption.state &= ~QtWidgets.QStyle.StateFlag.State_HasFocus

        if hasIndicator:
            modifiedOption.rect.adjust(modifiedOption.rect.height(), 0, 0, 0)

        super().paint(painter, modifiedOption, index)

        if hasIndicator:
            backgroundBrush = item.background(index.column())
            painter.setBrush(backgroundBrush)
            painter.setPen(backgroundBrush.color())
            # Not sure what I'm missing but for some reason the this rect needs to be 1 pixel
            # shorter than the one used by the item and the indicator
            painter.drawRect(QtCore.QRect(
                0,
                modifiedOption.rect.y(),
                modifiedOption.rect.height(),
                modifiedOption.rect.height() - 1))

            indicatorOption = QtWidgets.QStyleOptionViewItem()
            indicatorOption.rect = QtCore.QRect(
                0,
                modifiedOption.rect.y(),
                modifiedOption.rect.height(),
                modifiedOption.rect.height())
            indicatorOption.state = option.state
            style = widget.style() if widget else QtWidgets.QApplication.style()
            style.drawPrimitive(
                QtWidgets.QStyle.PrimitiveElement.PE_IndicatorBranch,
                indicatorOption,
                painter,
                widget)

class SectionList(QtWidgets.QWidget):
    selectionChanged = QtCore.pyqtSignal()
    currentChanged = QtCore.pyqtSignal()

    _StateVersion = 'SectionList_v1'

    _SectionHeaderColourRole = QtGui.QPalette.ColorRole.AlternateBase
    _TreeItemPadding = 2

    @typing.overload
    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...
    @typing.overload
    def __init__(self, contents: str, parent: typing.Optional[QtWidgets.QWidget] = ...) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._selectionMode = QtWidgets.QListWidget.SelectionMode.SingleSelection
        self._contextMenuPolicy = QtCore.Qt.ContextMenuPolicy.NoContextMenu

        self._treeWidget = QtWidgets.QTreeWidget()
        self._treeWidget.setColumnCount(1)
        self._treeWidget.header().setStretchLastSection(True)
        self._treeWidget.setHeaderHidden(True)
        self._treeWidget.setStyleSheet(f'QTreeView::item {{ padding: {SectionList._TreeItemPadding}px; }}')
        self._treeWidget.setVerticalScrollMode(QtWidgets.QTreeView.ScrollMode.ScrollPerPixel)
        self._treeWidget.verticalScrollBar().setSingleStep(10) # This seems to give a decent scroll speed without big jumps
        self._treeWidget.setAutoScroll(False)
        self._treeWidget.setIndentation(0)
        self._treeWidget.setItemDelegate(_SectionListItemDelegate())
        self._treeWidget.installEventFilter(self)
        self._treeWidget.clicked.connect(self._treeClicked)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._treeWidget)

        self.setLayout(widgetLayout)

    def sectionCount(self) -> int:
        rootItem = self._treeWidget.invisibleRootItem()
        return rootItem.childCount()

    def itemCount(self) -> int:
        count = 0
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            count += listWidget.count()
        return count

    def sectionItemCount(self, section: int) -> int:
        listWidget = self._listWidget(section)
        if not listWidget:
            return -1
        return listWidget.count()

    def isEmpty(self) -> bool:
        return self.itemCount() <= 0

    def isSectionEmpty(self, section: int) -> bool:
        return self.sectionItemCount(section) <= 0

    def sectionLabel(self, section: int) -> typing.Optional[str]:
        sectionItem = self._sectionItem(section)
        if not section:
            return None
        return sectionItem.text(0)

    def addSection(
            self,
            label: str,
            expanded: bool = True
            ) -> int:
        index = self.sectionCount()
        self.insertSection(index=index, label=label, expanded=expanded)
        return index

    def insertSection(
            self,
            index: int,
            label: str,
            expanded: bool = True
            ) -> None:
        rootItem = self._treeWidget.invisibleRootItem()

        palette = QtWidgets.QApplication.palette()
        headerColour = palette.color(SectionList._SectionHeaderColourRole)

        sectionItem = QtWidgets.QTreeWidgetItem([label])
        sectionItem.setFlags(sectionItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable) # Not selectable
        sectionItem.setBackground(0, headerColour)
        rootItem.insertChild(index, sectionItem)

        listItem = QtWidgets.QTreeWidgetItem()
        listItem.setFlags(sectionItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
        sectionItem.addChild(listItem)

        listWidget = gui.ResizingListWidget()
        listWidget.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        listWidget.setSelectionMode(self._selectionMode)
        listWidget.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        listWidget.addActions(self._treeWidget.actions())
        listWidget.setContextMenuPolicy(self._contextMenuPolicy)
        listWidget.itemSelectionChanged.connect(lambda: self._listSelectionChanged(listWidget))
        listWidget.currentItemChanged.connect(lambda: self._listCurrentChanged(listWidget))
        listWidget.itemChanged.connect(lambda: self._listContentChanged(listItem, listWidget))
        listWidget.model().rowsInserted.connect(lambda: self._listContentChanged(listItem, listWidget))
        listWidget.model().rowsRemoved.connect(lambda: self._listContentChanged(listItem, listWidget))

        self._treeWidget.setItemWidget(listItem, 0, listWidget)
        self._updateSectionSizes()

        self.expandSection(index, expanded)

    def removeSection(
            self,
            section: int
            ) -> None:
        sectionItem = self._sectionItem(section)
        if not sectionItem:
            return
        listWidget = self._listWidget(section)
        if not listWidget:
            return

        self._disconnectListWidget(listWidget)
        self._treeWidget.removeItemWidget(sectionItem, 0)
        self._updateSectionSizes()

    def item(
            self,
            section: int,
            row: int
            ) -> typing.Optional[QtWidgets.QListWidgetItem]:
        listWidget = self._listWidget(section)
        if not listWidget:
            return None
        return listWidget.item(row)

    def addItem(
            self,
            section: int,
            item: typing.Union[str, QtWidgets.QListWidgetItem]
            ) -> None:
        listWidget = self._listWidget(section)
        if listWidget == None:
            return
        listWidget.addItem(item)

    def insertItem(
            self,
            section: int,
            row: int,
            item: typing.Union[str, QtWidgets.QListWidgetItem]
            ) -> None:
        listWidget = self._listWidget(section)
        if listWidget == None:
            return
        listWidget.insertItem(row, item)

    def removeItem(
            self,
            section: int,
            row: int
            ) -> typing.Optional[QtWidgets.QListWidgetItem]:
        self.takeItem(section, row)

    def takeItem(
            self,
            section: int,
            row: int
            ) -> None:
        listWidget = self._listWidget(section)
        if listWidget == None:
            return
        listWidget.takeItem(row)

    def clear(self) -> None:
        # Disconnect widget handlers before clearing the tree so we can send single
        # selection/current item changed events
        hasCurrent = False
        hasSelection = False
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            if listWidget.hasSelection():
                hasSelection = True
            if listWidget.hasCurrentItem():
                hasCurrent = True
            self._disconnectListWidget(listWidget)

        self._treeWidget.clear()

        if hasSelection:
            self.selectionChanged.emit()
        if hasCurrent:
            self.currentChanged.emit()

    def selectionMode(self) -> QtWidgets.QListWidget.SelectionMode:
        return self._selectionMode

    def setSelectionMode(self, mode: QtWidgets.QListWidget.SelectionMode) -> None:
        self._selectionMode = mode
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            listWidget.setSelectionMode(self._selectionMode)

    def hasSelection(self) -> bool:
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            if listWidget.hasSelection():
                return True
        return False

    def selectedItems(self) -> typing.Iterable[QtWidgets.QListWidgetItem]:
        items = []
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            items.extend(listWidget.selectedItems())
        return items

    def selectedSectionItems(
            self,
            section: int
            ) -> typing.Iterable[QtWidgets.QListWidgetItem]:
        listWidget = self._listWidget(section)
        if not listWidget:
            return []
        return listWidget.selectedItems()

    def selectedItemCount(self) -> int:
        count = 0
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            count += listWidget.selectionCount()
        return count

    def selectedSectionItemCount(
            self,
            section: int
            ) -> int:
        listWidget = self._listWidget(section)
        if not listWidget:
            return []
        return listWidget.selectionCount()

    def clearSelection(self) -> None:
        if not self.hasSelection():
            return # Nothing to do

        with gui.SignalBlocker(widget=self):
            for section in range(self.sectionCount()):
                listWidget = self._listWidget(section)
                listWidget.clearSelection()

        self.selectionChanged.emit()
        self.currentChanged.emit()

    def currentSection(self) -> int:
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            if listWidget.currentItem():
                return section
        return -1

    def hasCurrentItem(self) -> bool:
        return self.currentItem() != None

    def currentItem(self) -> typing.Optional[QtWidgets.QListWidgetItem]:
        section = self.currentSection()
        if section < 0:
            return None
        listWidget = self._listWidget(section)
        return listWidget.currentItem()

    @typing.overload
    def setCurrentItem(self, item: QtWidgets.QListWidgetItem) -> None: ...
    @typing.overload
    def setCurrentItem(self, item: QtWidgets.QListWidgetItem, command: QtCore.QItemSelectionModel.SelectionFlag) -> None: ...

    def setCurrentItem(self, *args, **kwargs) -> None:
        item: QtWidgets.QListWidgetItem = args[0]
        if not item:
            raise ValueError('Invalid item parameter')
        listWidget = item.listWidget()
        listWidget.setCurrentItem(*args, **kwargs)

    def currentRow(self) -> typing.Tuple[int, int]:
        section = self.currentSection()
        if section < 0:
            return (-1, -1)
        listWidget = self._listWidget(section)
        row = listWidget.currentRow()
        return (section, row)

    def sortSection(
            self,
            section: int,
            order: QtCore.Qt.SortOrder
            ) -> None:
        listWidget = self._listWidget(section)
        if not listWidget:
            return
        listWidget.sortItems(order)

    def sortSections(
            self,
            order: QtCore.Qt.SortOrder
            ) -> None:
        for section in range(self.sectionCount()):
            self.sortSection(section, order)

    def isSectionExpanded(
            self,
            section: int
            ) -> bool:
        sectionItem = self._sectionItem(section)
        if not sectionItem:
            return False
        return sectionItem.isExpanded()

    def expandSection(
            self,
            section: int,
            expand: bool
            ) -> None:
        sectionItem = self._sectionItem(section)
        if not sectionItem:
            return
        sectionItem.setExpanded(expand)

    def expandAllSections(self, expand: bool) -> None:
        for section in range(self.sectionCount()):
            self.expandSection(section, expand)

    def expandSectionByLabel(
            self,
            label: str,
            expand: bool
            ) -> None:
        for section in range(self.sectionCount()):
            sectionItem = self._sectionItem(section)
            if not sectionItem or label != sectionItem.text(0):
                continue
            sectionItem.setExpanded(expand)

    def setContextMenuPolicy(self, policy: QtCore.Qt.ContextMenuPolicy) -> None:
        # Don't set the policy on the tree as the menu should only be displayed whe clicking on the
        # list section. Note that actions ARE added to the tree but is just because they need to be
        # stored somewhere (so they can be added to sections that are created after the actions are
        # added) and as actions on the tree widget is a convenient place to do that.
        self._contextMenuPolicy = policy
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            listWidget.setContextMenuPolicy(policy)

    def contextMenuPolicy(self) -> QtCore.Qt.ContextMenuPolicy:
        return self._contextMenuPolicy

    def actions(self) -> typing.List[QtWidgets.QAction]:
        return self._treeWidget.actions()

    def removeAction(self, action: QtWidgets.QAction) -> None:
        self._treeWidget.removeAction(action)
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            listWidget.removeAction(action)

    def insertActions(
            self,
            before: QtWidgets.QAction,
            actions: typing.Iterable[QtWidgets.QAction]
            ) -> None:
        self._treeWidget.addActions(before, actions)
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            listWidget.insertActions(before, actions)

    def insertAction(
            self,
            before: QtWidgets.QAction,
            action: QtWidgets.QAction
            ) -> None:
        self._treeWidget.insertAction(before, action)
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            listWidget.insertAction(before, action)

    def addActions(self, actions: typing.Iterable[QtWidgets.QAction]) -> None:
        self._treeWidget.addActions(actions)
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            listWidget.addActions(actions)

    def addAction(self, action: QtWidgets.QAction) -> None:
        self._treeWidget.addAction(action)
        for section in range(self.sectionCount()):
            listWidget = self._listWidget(section)
            listWidget.addAction(action)

    def eventFilter(self, source: object, event: QtCore.QEvent) -> bool:
        result = super().eventFilter(source, event)
        if source == self._treeWidget:
            if event.type() == QtCore.QEvent.Type.KeyPress:
                assert(isinstance(event, QtGui.QKeyEvent))
                if event.key() == QtCore.Qt.Key.Key_Up:
                    # Move focus onto the list in the section above the current one
                    self._handleCursorScroll(scrollUp=True)
                    return True
                elif event.key() == QtCore.Qt.Key.Key_Down:
                    # Move focus onto the list in the section below the current one
                    self._handleCursorScroll(scrollUp=False)
                    return True
                elif event.key() == QtCore.Qt.Key.Key_Left or event.key() == QtCore.Qt.Key.Key_Right:
                    # Filter out left/right key presses. In a normal tree control they cause elements
                    # to be expanded/collapsed but they act a little odd in this control
                    return True
        return result

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(SectionList._StateVersion)

        stream.writeUInt32(self.sectionCount())
        for section in range(self.sectionCount()):
            label = self.sectionLabel(section)
            if not label:
                continue
            expanded = self.isSectionExpanded(section)
            stream.writeQString(label)
            stream.writeBool(expanded)

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != SectionList._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore SectionList state (Incorrect version)')
            return False

        count = stream.readUInt32()
        for _ in range(count):
            label = stream.readQString()
            expanded = stream.readBool()
            self.expandSectionByLabel(
                label=label,
                expand=expanded)

        return True

    def _handleCursorScroll(
            self,
            scrollUp: bool
            ) -> None:
        lastSection = self.sectionCount() - 1

        section = self.currentSection()
        if section < 0:
            # No item currently selected so start at the start or end of the sections depending on
            # which direction we're scrolling
            section = (lastSection + 1) if scrollUp else -1

        # Find the next expanded section that has items in its list for focus to be moved to
        listWidget = None
        while True:
            section += -1 if scrollUp else 1
            if (section < 0) or (section > lastSection):
                return # No expanded sections to move on to

            sectionItem = self._sectionItem(section)
            if sectionItem and sectionItem.isExpanded():
                listWidget = self._listWidget(section)
                if listWidget.count() > 0:
                    break

        assert(listWidget)

        # Move focus to the next list
        nextRow = (listWidget.count() - 1) if scrollUp else 0
        listWidget.setCurrentItem(listWidget.item(nextRow))
        listWidget.setFocus()

    def _treeClicked(self, index: QtCore.QModelIndex) -> None:
        # Perform single click expand/collapse but only for section items
        item = self._treeWidget.itemFromIndex(index)
        if item.parent() != None:
            # Item has a parent so it's not a section item
            return

        if self._treeWidget.isExpanded(index):
            self._treeWidget.collapse(index)
        else:
            self._treeWidget.expand(index)

            """
            # Set focus to list widget in expanded section
            listItem = item.child(0)
            listWidget = self._treeWidget.itemWidget(listItem, 0) if listItem else None
            if listWidget:
                listWidget.setFocus()
            """

    def _sectionItem(self, section: int) -> typing.Optional[QtWidgets.QTreeWidgetItem]:
        rootItem = self._treeWidget.invisibleRootItem()
        return rootItem.child(section)

    def _listItem(self, section: int) -> typing.Optional[QtWidgets.QTreeWidgetItem]:
        sectionItem = self._sectionItem(section)
        if not sectionItem:
            return None
        return sectionItem.child(0)

    def _listWidget(self, section: int) -> typing.Optional[gui.ListWidgetEx]:
        listItem = self._listItem(section)
        if not listItem:
            return None
        return self._treeWidget.itemWidget(listItem, 0)

    def _listSelectionChanged(self, listWidget: QtWidgets.QListWidget) -> None:
        for section in range(self.sectionCount()):
            otherListWidget = self._listWidget(section)
            if otherListWidget == listWidget:
                continue

            with gui.SignalBlocker(widget=otherListWidget):
                otherListWidget.clearSelection()

        self.selectionChanged.emit()

    def _listCurrentChanged(self, listWidget: QtWidgets.QListWidget) -> None:
        selectionChanged = False
        for section in range(self.sectionCount()):
            otherListWidget = self._listWidget(section)
            if otherListWidget == listWidget:
                continue

            with gui.SignalBlocker(widget=otherListWidget):
                if otherListWidget.hasSelection():
                    otherListWidget.clearSelection()
                    selectionChanged = True
                otherListWidget.setCurrentItem(None, QtCore.QItemSelectionModel.SelectionFlag.Current)

        self._ensureCurrentItemVisible()

        if selectionChanged:
            self.selectionChanged.emit()
        self.currentChanged.emit()

    def _listContentChanged(
            self,
            listItem: QtWidgets.QTreeWidgetItem,
            listWidget: QtWidgets.QListWidget
            ) -> None:
        listItem.setSizeHint(0, self._calculateSectionSize(listWidget))
        self._treeWidget.updateGeometries()

    def _disconnectListWidget(
            self,
            listWidget: QtWidgets.QListWidget
            ) -> None:
        # Disconnect the handlers from the list widget. This will disconnect _ALL_ handlers but
        # that's ok as the lists are internal to this class is the only one that should be listening
        # for them
        listWidget.itemSelectionChanged.disconnect()
        listWidget.currentItemChanged.disconnect()
        listWidget.itemChanged.disconnect()
        listWidget.model().rowsInserted.disconnect()
        listWidget.model().rowsRemoved.disconnect()

    def _updateSectionSizes(self) -> None:
        for section in range(self.sectionCount()):
            listItem = self._listItem(section)
            if not listItem:
                continue
            listWidget = self._listWidget(section)
            if not listWidget:
                continue
            listItem.setSizeHint(0, self._calculateSectionSize(listWidget))
        self._treeWidget.updateGeometries()

    def _calculateSectionSize(
            self,
            listWidget: QtWidgets.QListWidget
            ) -> QtCore.QSize:
        size = listWidget.sizeHint()
        size.setHeight(size.height() + (SectionList._TreeItemPadding * 2))
        return size

    def _ensureCurrentItemVisible(self) -> None:
        currentItem = self.currentItem()
        if not currentItem:
            return
        listWidget = currentItem.listWidget()
        if not listWidget:
            return

        scrollBar = self._treeWidget.verticalScrollBar()
        if not scrollBar:
            return

        itemRect = listWidget.visualItemRect(currentItem)
        top = self._treeWidget.viewport().mapFromGlobal(
            listWidget.viewport().mapToGlobal(itemRect.topLeft())).y()
        bottom = top + itemRect.height()

        viewRect = self._treeWidget.viewport().rect()
        scrollAmount = None
        if top < viewRect.top():
            scrollAmount = top - viewRect.top()
        elif bottom > viewRect.bottom():
            scrollAmount = bottom - viewRect.bottom()

        if scrollAmount:
            currentScrollPos = scrollBar.sliderPosition()
            scrollBar.setSliderPosition(currentScrollPos + scrollAmount)
