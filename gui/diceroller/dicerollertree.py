import diceroller
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class _CustomValidator(QtGui.QValidator):
    def validate(
            self,
            input: typing.Optional[str],
            pos: int
            ) -> typing.Tuple[QtGui.QValidator.State, str, int]:
        if not input:
            # Prevent empty names (but allow the edit to be temporarily empty)
            return (QtGui.QValidator.State.Intermediate, input, pos)
        return (QtGui.QValidator.State.Acceptable, input, pos)

class _CustomItemDelegate(gui.StyledItemDelegateEx):
    itemEdited = QtCore.pyqtSignal(QtCore.QModelIndex)

    def createEditor(
            self,
            parent: typing.Optional[QtWidgets.QWidget],
            option: QtWidgets.QStyleOptionViewItem,
            index: QtCore.QModelIndex
            ) -> typing.Optional[QtWidgets.QWidget]:
        editor = gui.LineEditEx(parent)
        validator = _CustomValidator(editor)
        editor.setValidator(validator)
        return editor

    def setModelData(
            self,
            editor: typing.Optional[QtWidgets.QWidget],
            model: typing.Optional[QtCore.QAbstractItemModel],
            index: QtCore.QModelIndex
            ) -> None:
        result = super().setModelData(editor, model, index)
        self.itemEdited.emit(index)
        return result

class DiceRollerTree(gui.TreeWidgetEx):
    currentObjectChanged = QtCore.pyqtSignal(object) # Object id string or None
    objectRenamed = QtCore.pyqtSignal([str, str])
    orderChanged = QtCore.pyqtSignal()

    _StateVersion = 'DiceRollerTree_v1'

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._objectItemMap: typing.Dict[str, QtWidgets.QTreeWidgetItem] = {}
        self._groupOrdering: typing.List[str] = []
        self._collapsedGroups: typing.Set[str] = set()

        self.setColumnCount(1)
        self.header().setStretchLastSection(True)
        self.setHeaderHidden(True)
        self.setVerticalScrollMode(QtWidgets.QTreeView.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(10) # This seems to give a decent scroll speed without big jumps
        self.setAutoScroll(False)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        itemDelegate = _CustomItemDelegate()
        itemDelegate.itemEdited.connect(self._itemEdited)
        self.setItemDelegate(itemDelegate)
        self.currentItemChanged.connect(self._currentItemChanged)
        self.itemExpanded.connect(self._itemExpanded)
        self.itemCollapsed.connect(self._itemCollapsed)

    def groups(self) -> typing.Iterable[str]:
        groups = []
        for index in range(self.topLevelItemCount()):
            groupItem = self.topLevelItem(index)
            groups.append(groupItem.data(0, QtCore.Qt.ItemDataRole.UserRole))
        return groups

    def groupCount(self) -> int:
        return self.topLevelItemCount()

    def rollers(
            self,
            groupId: str
            ) -> typing.Iterable[str]:
        rollers = []
        groupItem = self._objectItemMap.get(groupId)
        if groupItem:
            for index in range(groupItem.childCount()):
                rollerItem = groupItem.child(index)
                rollers.append(rollerItem.data(0, QtCore.Qt.ItemDataRole.UserRole))
        return rollers

    def rollerCount(
            self,
            groupId: str
            ) -> int:
        groupItem = self._objectItemMap.get(groupId)
        if not groupItem:
            return 0
        return groupItem.childCount()

    def setGroups(
            self,
            groups: typing.Iterable[diceroller.DiceRollerGroup]
            ) -> None:
        if self._groupOrdering:
            groupMap = {group.id(): group for group in groups}
            orderedGroups = []
            for groupId in list(self._groupOrdering):
                group = groupMap.get(groupId)
                if group:
                    orderedGroups.append(group)
                else:
                    self._groupOrdering.remove(groupId)
            for group in groups:
                if group.id() not in self._groupOrdering:
                    orderedGroups.append(group)
                    self._groupOrdering.append(group.id())
            groups = orderedGroups

        selectionIds = []
        for item in self.selectedItems():
            selectionIds.append(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
        currentId = self.currentObject()

        self._objectItemMap.clear()

        while self.topLevelItemCount() > len(groups):
            groupItem = self.takeTopLevelItem(
                self.topLevelItemCount() - 1)

        for index, group in enumerate(groups):
            assert(isinstance(group, diceroller.DiceRollerGroup))
            groupItem = self.topLevelItem(index)
            if groupItem == None:
                groupItem = QtWidgets.QTreeWidgetItem()
                groupItem.setFlags(groupItem.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
                self.addTopLevelItem(groupItem)
                groupItem.setExpanded(True)
            groupItem.setText(0, group.name())
            groupItem.setData(0, QtCore.Qt.ItemDataRole.UserRole, group.id())
            groupItem.setSelected(group.id() in selectionIds)
            self._objectItemMap[group.id()] = groupItem

            rollers = group.rollers()

            while groupItem.childCount() > len(rollers):
                rollerItem = groupItem.takeChild(groupItem.childCount() - 1)

            for index, roller in enumerate(rollers):
                assert(isinstance(roller, diceroller.DiceRoller))
                rollerItem = groupItem.child(index)
                if rollerItem == None:
                    rollerItem = QtWidgets.QTreeWidgetItem([roller.name()])
                    rollerItem.setFlags(groupItem.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
                    groupItem.addChild(rollerItem)
                rollerItem.setText(0, roller.name())
                rollerItem.setData(0, QtCore.Qt.ItemDataRole.UserRole, roller.id())
                rollerItem.setSelected(roller.id() in selectionIds)
                self._objectItemMap[roller.id()] = rollerItem

        self.setCurrentObject(objectId=currentId)

        self._restoreExpandStates()

    def currentObject(self) -> typing.Optional[str]:
        item = self.currentItem()
        if item:
            return item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return None

    def currentGroup(self) -> typing.Optional[str]:
        item = self.currentItem()
        if not item:
            return None
        parent = item.parent()
        if parent == None:
            # Current item is a group
            return item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        else:
            # Current item is a roller so use parent to get group
            return parent.data(0, QtCore.Qt.ItemDataRole.UserRole)

    def currentRoller(self) -> typing.Optional[str]:
        item = self.currentItem()
        if item and item.parent() != None:
            return item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return None

    def setCurrentObject(
            self,
            objectId: typing.Optional[str]
            ) -> None:
        if objectId is None:
            self.setCurrentItem(None)
            return

        item = self._objectItemMap.get(objectId)
        if not item:
            return
        if item != self.currentItem():
            self.setCurrentItem(item)

    def selectedObjects(self) -> typing.Iterable[str]:
        selection = []
        for item in self.selectedItems():
            selection.append(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
        return selection

    def groupFromRoller(
            self,
            rollerId: str
            ) -> typing.Optional[str]:
        rollerItem = self._objectItemMap.get(rollerId)
        if not rollerItem or not rollerItem.parent():
            return None
        groupItem = rollerItem.parent()
        return groupItem.data(0, QtCore.Qt.ItemDataRole.UserRole)

    def editObjectName(
            self,
            objectId: str
            ) -> None:
        item = self._objectItemMap.get(objectId)
        if not item:
            return
        modelIndex = self.indexFromItem(item)
        if not modelIndex:
            return
        self.edit(modelIndex)

    def startDrag(
            self,
            supportedActions: typing.Union[QtCore.Qt.DropActions, QtCore.Qt.DropAction]
            ) -> None:
        dragItems = self._dragSelection()
        if not dragItems:
            return

        hasRollerSelected = False
        hasGroupSelected = False
        for item in dragItems:
            if item.parent() != None:
                hasRollerSelected = True
            else:
                hasGroupSelected = True

        # If groups are selected allow them to be dropped into a different position
        rootItem = self.invisibleRootItem()
        if hasGroupSelected and not hasRollerSelected:
            rootItem.setFlags(rootItem.flags() | QtCore.Qt.ItemFlag.ItemIsDropEnabled)
        else:
            rootItem.setFlags(rootItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsDropEnabled)

        for groupIndex in range(self.topLevelItemCount()):
            groupItem = self.topLevelItem(groupIndex)

            # If rollers are selected then allow them to be dropped into a different
            # group or a new position within its current group
            if hasRollerSelected and not hasGroupSelected:
                groupItem.setFlags(groupItem.flags() | QtCore.Qt.ItemFlag.ItemIsDropEnabled)
            else:
                groupItem.setFlags(groupItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsDropEnabled)

            # Never allow dropping onto a roller
            for rollerIndex in range(groupItem.childCount()):
                rollerItem = groupItem.child(rollerIndex)
                rollerItem.setFlags(rollerItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsDropEnabled)

        return super().startDrag(supportedActions)

    def dropEvent(self, event):
        dropIndicatorPos = self.dropIndicatorPosition()
        validPositions = (QtWidgets.QAbstractItemView.DropIndicatorPosition.AboveItem,
                          QtWidgets.QAbstractItemView.DropIndicatorPosition.BelowItem,
                          QtWidgets.QAbstractItemView.DropIndicatorPosition.OnItem)
        if dropIndicatorPos not in validPositions:
            event.ignore()
            return

        dropItem = self.itemAt(event.pos())
        if not dropItem:
            event.ignore()
            return

        event.accept()

        dragItems = self._dragSelection()

        hasRollerSelected = False
        for item in dragItems:
            if item.parent() != None:
                hasRollerSelected = True
                break

        # If any rollers are selected then the rollers from any groups
        # that are selected should also be dropped into the drop group
        if hasRollerSelected:
            groupItems = []
            for item in dragItems:
                if item.parent() == None:
                    index = self.indexOfTopLevelItem(item)
                    self.takeTopLevelItem(index)
                    groupItems.append(item)

            rollerItems = []
            for item in dragItems:
                if item.parent() != None:
                    if item.parent() not in groupItems:
                        rollerItems.append(item)
                else:
                    for index in range(item.childCount()):
                        rollerItems.append(item.child(index))
            dragItems = rollerItems

        # Perform the drop for all selected items
        for item in dragItems:
            # Remove the item from its original parent
            parent = item.parent()
            if parent == None:
                parent = self.invisibleRootItem()
            wasExpanded = item.isExpanded()
            parent.removeChild(item)

            # Reinsert item at the target location
            if dropIndicatorPos == QtWidgets.QAbstractItemView.DropIndicatorPosition.OnItem:
                # Drop INTO the target item
                dropItem.addChild(item)
            else:
                # Drop BETWEEN items (as a sibling)
                parent = dropItem.parent()
                if parent == None:
                    parent = self.invisibleRootItem()
                index = parent.indexOfChild(dropItem)
                if dropIndicatorPos == QtWidgets.QAbstractItemView.DropIndicatorPosition.BelowItem:
                    parent.insertChild(index + 1, item)
                    dropItem = item
                else:
                    parent.insertChild(index, item)
            item.setExpanded(wasExpanded)

        self._groupOrdering.clear()
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            self._groupOrdering.append(item.data(0, QtCore.Qt.ItemDataRole.UserRole))

        self.orderChanged.emit()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(DiceRollerTree._StateVersion)

        currentId = self.currentObject()
        stream.writeQString(currentId if currentId else '')

        stream.writeUInt32(len(self._groupOrdering))
        for id in self._groupOrdering:
            stream.writeQString(id)

        stream.writeUInt32(len(self._collapsedGroups))
        for id in self._collapsedGroups:
            stream.writeQString(id)

        return state

    def restoreState(self, state: QtCore.QByteArray) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != DiceRollerTree._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore DiceRollerTree state (Incorrect version)')
            return False

        currentId = stream.readQString()
        if currentId:
            self.setCurrentObject(objectId=currentId)

        count = stream.readUInt32()
        self._groupOrdering.clear()
        for _ in range(count):
            self._groupOrdering.append(stream.readQString())

        count = stream.readUInt32()
        self._collapsedGroups.clear()
        for _ in range(count):
            self._collapsedGroups.add(stream.readQString())

        self._restoreGroupOrdering()
        self._restoreExpandStates()

        return True

    def _currentItemChanged(
            self,
            current: QtWidgets.QTreeWidgetItem,
            previous: QtWidgets.QTreeWidgetItem
            ) -> None:
        self.currentObjectChanged.emit(
            current.data(0, QtCore.Qt.ItemDataRole.UserRole) if current else None)

    def _itemEdited(
            self,
            index: QtCore.QModelIndex
            ) -> None:
        item = self.itemFromIndex(index)
        if not item:
            return
        objectId = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        newName = item.text(0)
        self.objectRenamed.emit(objectId, newName)

    def _itemExpanded(
            self,
            item: QtWidgets.QTreeWidgetItem
            ) -> None:
        objectId = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if objectId in self._collapsedGroups:
            self._collapsedGroups.remove(objectId)

    def _itemCollapsed(
            self,
            item: QtWidgets.QTreeWidgetItem
            ) -> None:
        objectId = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        self._collapsedGroups.add(objectId)

    def _dragSelection(self) -> typing.Iterable[QtWidgets.QTreeWidgetItem]:
        items = []
        for groupIndex in range(self.topLevelItemCount()):
            groupItem = self.topLevelItem(groupIndex)
            if groupItem.isSelected():
                items.append(groupItem)
            for rollerIndex in range(groupItem.childCount()):
                rollerItem = groupItem.child(rollerIndex)
                if rollerItem.isSelected():
                    items.append(rollerItem)
        return items

    def _restoreGroupOrdering(self) -> None:
        items = {}
        while self.topLevelItemCount() > 0:
            item = self.takeTopLevelItem(0)
            groupId = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            items[groupId] = item
        for groupId in self._groupOrdering:
            item = items.get(groupId)
            if item:
                self.addTopLevelItem(item)
                del items[groupId]
        for item in items.values():
            self.addTopLevelItem(item)

    def _restoreExpandStates(self) -> None:
        # Set expansion/collapsed state of groups
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            groupId = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            item.setExpanded(groupId not in self._collapsedGroups)

        # Remove groups that are no longer present from collapsed groups
        for groupId in list(self._collapsedGroups):
            if groupId not in self._objectItemMap:
                self._collapsedGroups.remove(groupId)
