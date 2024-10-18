import copy
import diceroller
import gui
import logging
import objectdb
import typing
from PyQt5 import QtWidgets, QtCore

class DiceRollerManagerTree(gui.TreeWidgetEx):
    currentObjectChanged = QtCore.pyqtSignal()
    objectsChanged = QtCore.pyqtSignal(
        list, # Created objects
        list, # Updated objects
        list # Deleted objects
        )

    _StateVersion = 'DiceRollerManagerTree_v1'

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
        itemDelegate = gui.StyledItemDelegateEx()
        self.setItemDelegate(itemDelegate)
        self.currentItemChanged.connect(self._currentItemChanged)
        self.itemChanged.connect(self._itemChanged)
        self.itemExpanded.connect(self._itemExpanded)
        self.itemCollapsed.connect(self._itemCollapsed)

    def groups(self) -> typing.Iterable[diceroller.DiceRollerGroupDatabaseObject]:
        groups = []
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            groups.append(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
        return groups

    def groupCount(self) -> int:
        return self.topLevelItemCount()

    def currentObject(self) -> typing.Optional[typing.Union[
            diceroller.DiceRollerGroupDatabaseObject,
            diceroller.DiceRollerDatabaseObject]]:
        item = self.currentItem()
        if item:
            return item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return None

    def currentGroup(self) -> typing.Optional[diceroller.DiceRollerGroupDatabaseObject]:
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

    def currentRoller(self) -> typing.Optional[diceroller.DiceRollerDatabaseObject]:
        item = self.currentItem()
        if item and item.parent() != None:
            return item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return None

    def setCurrentObject(
            self,
            object: typing.Optional[typing.Union[
                diceroller.DiceRollerGroupDatabaseObject,
                diceroller.DiceRollerDatabaseObject,
                str]]
            ) -> None:
        if object is None:
            self.setCurrentItem(None)
            return

        if isinstance(object, diceroller.DiceRollerGroupDatabaseObject) or \
            isinstance(object, diceroller.DiceRollerDatabaseObject):
            object = object.id()
        item = self._objectItemMap.get(object)
        if not item:
            return
        if item != self.currentItem():
            self.setCurrentItem(item)

    def selectedObjects(self) -> typing.Iterable[typing.Union[
                diceroller.DiceRollerGroupDatabaseObject,
                diceroller.DiceRollerDatabaseObject]]:
        objects = []
        for item in self.selectedItems():
            objects.append(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
        return objects

    def objectFromItem(
            self,
            item: QtWidgets.QTreeWidgetItem
            ) -> typing.Union[
                diceroller.DiceRollerGroupDatabaseObject,
                diceroller.DiceRollerDatabaseObject]:
        return item.data(0, QtCore.Qt.ItemDataRole.UserRole)

    def groupFromRoller(
            self,
            roller: typing.Union[
                diceroller.DiceRollerDatabaseObject,
                str]
            ) -> typing.Optional[diceroller.DiceRollerGroupDatabaseObject]:
        if isinstance(roller, diceroller.DiceRollerDatabaseObject):
            roller = roller.id()
        item = self._objectItemMap.get(roller)
        if not item:
            return None
        parent = item.parent()
        return parent.data(0, QtCore.Qt.ItemDataRole.UserRole)

    def syncToDatabase(self) -> None:
        groups = objectdb.ObjectDbManager.instance().readObjects(
            classType=diceroller.DiceRollerGroupDatabaseObject)

        selectionIds = set([object.id() for object in self.selectedObjects()])
        currentObject = self.currentObject()

        self._objectItemMap.clear()

        while self.topLevelItemCount() > len(groups):
            groupItem = self.takeTopLevelItem(
                self.topLevelItemCount() - 1)

        for index, group in enumerate(groups):
            assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
            groupItem = self.topLevelItem(index)
            if groupItem == None:
                groupItem = QtWidgets.QTreeWidgetItem()
                groupItem.setFlags(groupItem.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
                self.addTopLevelItem(groupItem)
                groupItem.setExpanded(True)
            groupItem.setText(0, group.name())
            groupItem.setData(0, QtCore.Qt.ItemDataRole.UserRole, group)
            groupItem.setSelected(group.id() in selectionIds)
            self._objectItemMap[group.id()] = groupItem

            rollers = group.rollers()

            while groupItem.childCount() > len(rollers):
                rollerItem = groupItem.takeChild(groupItem.childCount() - 1)

            for index, roller in enumerate(rollers):
                assert(isinstance(roller, diceroller.DiceRollerDatabaseObject))
                rollerItem = groupItem.child(index)
                if rollerItem == None:
                    rollerItem = QtWidgets.QTreeWidgetItem([roller.name()])
                    rollerItem.setFlags(groupItem.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
                    groupItem.addChild(rollerItem)
                rollerItem.setText(0, roller.name())
                rollerItem.setData(0, QtCore.Qt.ItemDataRole.UserRole, roller)
                rollerItem.setSelected(roller.id() in selectionIds)
                self._objectItemMap[roller.id()] = rollerItem

        self.setCurrentObject(object=currentObject.id() if currentObject else None)

        self._restoreItemStates()

    def startDrag(
            self,
            supportedActions: typing.Union[QtCore.Qt.DropActions, QtCore.Qt.DropAction]
            ) -> None:
        dragItems = self._dragSelection()
        if not dragItems:
            return

        hasRollerSelected = False
        for item in dragItems:
            if item.parent() != None:
                hasRollerSelected = True
                break

        # If there is one ore more rollers selected then they must be dropped
        # into a group so don't allow dropping into the root item. If no
        # rollers are selected then it is just groups that are being dragged so
        # allow dropping into the root item so they can be reordered
        rootItem = self.invisibleRootItem()
        if hasRollerSelected:
            rootItem.setFlags(rootItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsDropEnabled)
        else:
            rootItem.setFlags(rootItem.flags() | QtCore.Qt.ItemFlag.ItemIsDropEnabled)

        for groupIndex in range(self.topLevelItemCount()):
            groupItem = self.topLevelItem(groupIndex)

            # If there is one or more rollers selected then allow them to be
            # dropped into another group (groups that are also selected will be
            # flattened when the drop occurs). If there are no rollers selected
            # then it is just groups being dragged so don't allow them to be
            # dropped into another group
            if hasRollerSelected:
                groupItem.setFlags(groupItem.flags() | QtCore.Qt.ItemFlag.ItemIsDropEnabled)
            else:
                groupItem.setFlags(groupItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsDropEnabled)

            # Never allow dropping into a roller
            for rollerIndex in range(groupItem.childCount()):
                rollerItem = groupItem.child(rollerIndex)
                rollerItem.setFlags(rollerItem.flags() & ~QtCore.Qt.ItemFlag.ItemIsDropEnabled)

        return super().startDrag(supportedActions)

    def dropEvent(self, event):
        dropItem = self.itemAt(event.pos())
        if not dropItem:
            event.ignore()
            return

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

        dropIndicatorPos = self.dropIndicatorPosition()

        # Handle dropping the selected items based on the drop indicator
        validPositions = (QtWidgets.QAbstractItemView.DropIndicatorPosition.AboveItem,
                          QtWidgets.QAbstractItemView.DropIndicatorPosition.BelowItem,
                          QtWidgets.QAbstractItemView.DropIndicatorPosition.OnItem)
        if dropIndicatorPos in validPositions:
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

            if hasRollerSelected:
                self._handleMovedRollers()
            else:
                self._handleMovedGroups()

        event.accept()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(DiceRollerManagerTree._StateVersion)

        currentObject = self.currentObject()
        stream.writeQString(currentObject.id() if currentObject else '')

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
        if version != DiceRollerManagerTree._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore DiceRollerManagerTree state (Incorrect version)')
            return False

        currentId = stream.readQString()
        if currentId:
            self.setCurrentObject(object=currentId)

        count = stream.readUInt32()
        self._groupOrdering.clear()
        for _ in range(count):
            self._groupOrdering.append(stream.readQString())

        count = stream.readUInt32()
        self._collapsedGroups.clear()
        for _ in range(count):
            self._collapsedGroups.add(stream.readQString())

        self._restoreItemStates()

        return True

    def _currentItemChanged(self) -> None:
        self.currentObjectChanged.emit()

    def _itemChanged(
            self,
            item: QtWidgets.QTreeWidgetItem,
            column: int
            ) -> None:
        if column != 0:
            return
        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not isinstance(object, diceroller.DiceRollerGroupDatabaseObject) and \
            not isinstance(object, diceroller.DiceRollerDatabaseObject):
            return
        newName = item.text(0)
        oldName = object.name()
        if not newName:
            # Don't allow empty names so set item text back to original value.
            # Use a signal blocker to avoid it triggering another item changed
            # event
            with gui.SignalBlocker(self):
                item.setText(0, oldName)
            return
        elif newName == oldName:
            return # Nothing to do
        object.setName(newName)
        self.objectsChanged.emit(
            [], # No objects created
            [object], # Renamed object updated
            []) # No objects delete

    def _itemExpanded(
            self,
            item: QtWidgets.QTreeWidgetItem
            ) -> None:
        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
            return
        if object.id() in self._collapsedGroups:
            self._collapsedGroups.remove(object.id())

    def _itemCollapsed(
            self,
            item: QtWidgets.QTreeWidgetItem
            ) -> None:
        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
            return
        self._collapsedGroups.add(object.id())

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

    def _restoreItemStates(self) -> None:
        # Move any groups that are out of order
        requiredIndex = 0
        while requiredIndex < len(self._groupOrdering):
            groupId = self._groupOrdering[requiredIndex]
            item = self._objectItemMap.get(groupId)
            if not item:
                self._groupOrdering.remove(groupId)
                continue
            currentIndex = self.indexOfTopLevelItem(item)
            if requiredIndex != currentIndex:
                self.takeTopLevelItem(currentIndex)
                self.insertTopLevelItem(requiredIndex, item)
            requiredIndex += 1

        # Add any groups that aren't in the group order list
        for index in range(len(self._groupOrdering), self.topLevelItemCount()):
            item = self.topLevelItem(index)
            group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
            self._groupOrdering.append(group.id())

        # Set expansion/collapsed state of groups
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
            item.setExpanded(group.id() not in self._collapsedGroups)

        # Remove groups that are no longer present from collapsed groups
        for groupId in list(self._collapsedGroups):
            if groupId not in self._objectItemMap:
                self._collapsedGroups.remove(groupId)

    def _handleMovedGroups(self) -> None:
        self._groupOrdering.clear()
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
            self._groupOrdering.append(group.id())

    def _handleMovedRollers(self) -> None:
        oldGroups: typing.Dict[str, diceroller.DiceRollerGroupDatabaseObject] = {}
        for group in self.groups():
            oldGroups[group.id()] = copy.deepcopy(group)

        updatedGroups: typing.List[diceroller.DiceRollerGroupDatabaseObject] = []
        for groupIndex in range(self.topLevelItemCount()):
            groupItem = self.topLevelItem(groupIndex)
            newGroup = self.objectFromItem(groupItem)
            assert(isinstance(newGroup, diceroller.DiceRollerGroupDatabaseObject))
            newGroup = copy.deepcopy(newGroup)
            newGroup.clearRollers()

            for rollerIndex in range(groupItem.childCount()):
                rollerItem = groupItem.child(rollerIndex)
                roller = self.objectFromItem(rollerItem)
                assert(isinstance(roller, diceroller.DiceRollerDatabaseObject))
                roller = copy.deepcopy(roller)
                roller.setParent(None)
                newGroup.addRoller(roller)

            oldGroup = oldGroups[newGroup.id()]
            if newGroup != oldGroup:
                updatedGroups.append(newGroup)

        if not updatedGroups:
            return

        oldCurrentObject = self.currentObject()
        if oldCurrentObject:
            oldCurrentObject = oldCurrentObject.id()

        with gui.SignalBlocker(self):
            for group in updatedGroups:
                groupItem = self._objectItemMap[group.id()]
                groupItem.setText(0, group.name())
                groupItem.setData(0, QtCore.Qt.ItemDataRole.UserRole, group)

                rollers = group.rollers()
                assert(len(rollers) == groupItem.childCount())
                for rollerIndex, roller in enumerate(rollers):
                    assert(isinstance(roller, diceroller.DiceRollerDatabaseObject))
                    rollerItem = self._objectItemMap[roller.id()]
                    rollerItem.setText(0, roller.name())
                    rollerItem.setData(0, QtCore.Qt.ItemDataRole.UserRole, roller)

        newCurrentObject = self.currentObject()
        if newCurrentObject:
            newCurrentObject = newCurrentObject.id()

        if oldCurrentObject != newCurrentObject:
            self.currentObjectChanged.emit()

        self.objectsChanged.emit(
            updatedGroups, # New version of object created
            [], # No objects updated
            updatedGroups) # Old version of object deleted
