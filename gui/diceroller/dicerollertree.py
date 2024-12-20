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

class _CustomItemDelegate(QtWidgets.QStyledItemDelegate):
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
    currentObjectChanged = QtCore.pyqtSignal(object)
    objectRenamed = QtCore.pyqtSignal(object)
    orderChanged = QtCore.pyqtSignal([
        list, # Modified objects
        list # Deleted object ids
        ])

    _StateVersion = 'DiceRollerTree_v1'

    _ColumnNames = [
        'Dice Rollers',
        'Modified'
    ]

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._objectItemMap: typing.Dict[str, QtWidgets.QTreeWidgetItem] = {}
        self._groupOrdering: typing.List[str] = []
        self._collapsedGroups: typing.Set[str] = set()
        self._modifiedRollers: typing.Set[str] = set()

        self.setColumnCount(len(DiceRollerTree._ColumnNames))
        self.setHeaderLabels(DiceRollerTree._ColumnNames)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.header().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setVerticalScrollMode(QtWidgets.QTreeView.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(10) # This seems to give a decent scroll speed without big jumps
        self.setAutoScroll(False)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAllColumnsShowFocus(True)
        itemDelegate = _CustomItemDelegate()
        itemDelegate.itemEdited.connect(self._itemEdited)
        self.setItemDelegate(itemDelegate)
        self.currentItemChanged.connect(self._currentItemChanged)
        self.itemExpanded.connect(self._itemExpanded)
        self.itemCollapsed.connect(self._itemCollapsed)

    def groups(self) -> typing.Iterable[diceroller.DiceRollerGroup]:
        groups = []
        for index in range(self.topLevelItemCount()):
            groupItem = self.topLevelItem(index)
            groups.append(groupItem.data(0, QtCore.Qt.ItemDataRole.UserRole))
        return groups

    def groupCount(self) -> int:
        return self.topLevelItemCount()

    def addGroup(self, group: diceroller.DiceRollerGroup) -> None:
        item = self._createItem(object=group)
        self.addTopLevelItem(item)
        item.setExpanded(True)
        self._objectItemMap[group.id()] = item

        for roller in group.rollers():
            child = self._createItem(object=roller)
            item.addChild(child)
            self._objectItemMap[roller.id()] = child

        self._captureGroupOrdering()

    def insertGroup(
            self,
            index: int,
            group: diceroller.DiceRollerGroup
            ) -> None:
        item = self._createItem(object=group)
        self.insertTopLevelItem(index, item)
        item.setExpanded(True)
        self._objectItemMap[group.id()] = item

        for roller in group.rollers():
            child = self._createItem(object=roller)
            item.addChild(child)
            self._objectItemMap[roller.id()] = child

        self._captureGroupOrdering()

    def rollers(
            self,
            groupId: typing.Optional[str] = None
            ) -> typing.Iterable[diceroller.DiceRoller]:
        rollers = []
        if groupId != None:
            groupItem = self._objectItemMap.get(groupId)
            if groupItem:
                for index in range(groupItem.childCount()):
                    rollerItem = groupItem.child(index)
                    rollers.append(rollerItem.data(0, QtCore.Qt.ItemDataRole.UserRole))
        else:
            for item in self._objectItemMap.values():
                if item.parent() != None:
                    rollers.append(item.data(0, QtCore.Qt.ItemDataRole.UserRole))

        return rollers

    def rollerCount(
            self,
            groupId: str
            ) -> int:
        groupItem = self._objectItemMap.get(groupId)
        if not groupItem:
            return 0
        return groupItem.childCount()

    def addRoller(
            self,
            groupId: str,
            roller: diceroller.DiceRoller
            ) -> None:
        parent = self._objectItemMap.get(groupId)
        if parent.parent():
            raise ValueError(f'ID {groupId} doesn\'t map to a group')

        group = parent.data(0, QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(group, diceroller.DiceRollerGroup))
        assert(parent.childCount() == group.rollerCount())
        group.addRoller(roller)

        item = self._createItem(object=roller)
        parent.addChild(item)
        self._objectItemMap[roller.id()] = item

    def insertRoller(
            self,
            groupId: str,
            index: int,
            roller: diceroller.DiceRoller
            ) -> None:
        parent = self._objectItemMap.get(groupId)
        if parent.parent():
            raise ValueError(f'ID {groupId} doesn\'t map to a group')

        group = parent.data(0, QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(group, diceroller.DiceRollerGroup))
        assert(parent.childCount() == group.rollerCount())
        group.insertRoller(index, roller)

        item = self._createItem(object=roller)
        parent.insertChild(index, item)
        self._objectItemMap[roller.id()] = item

    def modifiedRollers(self) -> typing.Iterable[diceroller.DiceRoller]:
        rollers = []
        for item in self._objectItemMap.values():
            if not item.parent():
                continue # Skip groups
            roller = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(roller, diceroller.DiceRoller))
            if roller.id() in self._modifiedRollers:
                rollers.append(roller)
        return rollers

    def setRollerModified(
            self,
            rollerId: str,
            modified: bool
            ) -> None:
        item = self._objectItemMap.get(rollerId)
        if not item:
            raise ValueError(f'ID {rollerId} doesn\'t map to an object')

        parent = item.parent()
        if not parent:
            raise ValueError(f'ID {rollerId} doesn\'t map to a roller')

        item.setText(1, '*' if modified else '')
        if modified:
            self._modifiedRollers.add(rollerId)
        elif rollerId in self._modifiedRollers:
            self._modifiedRollers.remove(rollerId)

    def isRollerModified(self, rollerId: str) -> bool:
        return rollerId in self._modifiedRollers

    def hasModifiedRoller(self) -> bool:
        return len(self._modifiedRollers) > 0

    def clearModifiedRollers(self) -> None:
        for rollerId in self._modifiedRollers:
            item = self._objectItemMap.get(rollerId)
            if item:
                item.setText(1, '')
        self._modifiedRollers.clear()

    # NOTE: This expects the new roller to have the same id as an existing
    # roller instance.
    def replaceRoller(
            self,
            roller: diceroller.DiceRoller
            ) -> None:
        item = self._objectItemMap.get(roller.id())
        if not item:
            raise ValueError(f'ID {roller.id()} doesn\'t map to an object')

        parent = item.parent()
        if not parent:
            raise ValueError(f'ID {roller.id()} doesn\'t map to a roller')

        index = parent.indexOfChild(item)

        group = parent.data(0, QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(group, diceroller.DiceRollerGroup))
        assert(parent.childCount() == group.rollerCount())
        group.replaceRoller(index, roller)

        self._configureItem(item=item, object=roller)

    def setContents(
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
        currentObject = self.currentObject()

        self._objectItemMap.clear()

        while self.topLevelItemCount() > len(groups):
            groupItem = self.takeTopLevelItem(
                self.topLevelItemCount() - 1)

        for index, group in enumerate(groups):
            assert(isinstance(group, diceroller.DiceRollerGroup))
            groupItem = self.topLevelItem(index)
            shouldSelect = group.id() in selectionIds
            if groupItem:
                self._configureItem(
                    item=groupItem,
                    object=group,
                    selected=shouldSelect)
            else:
                groupItem = self._createItem(
                    object=group,
                    selected=shouldSelect)
                self.addTopLevelItem(groupItem)
                groupItem.setExpanded(True)

            self._objectItemMap[group.id()] = groupItem

            rollers = group.rollers()

            while groupItem.childCount() > len(rollers):
                rollerItem = groupItem.takeChild(groupItem.childCount() - 1)

            for index, roller in enumerate(rollers):
                assert(isinstance(roller, diceroller.DiceRoller))
                rollerItem = groupItem.child(index)
                shouldSelect = roller.id() in selectionIds
                if rollerItem:
                    self._configureItem(
                        item=rollerItem,
                        object=roller,
                        selected=shouldSelect)
                else:
                    rollerItem = self._createItem(
                        object=roller,
                        selected=shouldSelect)
                    groupItem.addChild(rollerItem)

                self._objectItemMap[roller.id()] = rollerItem

        self.setCurrentObject(objectId=currentObject.id() if currentObject else None)

        self._restoreExpandStates()

    def renameObject(self, objectId: str, newName: str) -> None:
        item = self._objectItemMap.get(objectId)
        if not item:
            raise ValueError(f'ID {objectId} doesn\'t map to an object')

        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(object, diceroller.DiceRoller) or
               isinstance(object, diceroller.DiceRollerGroup))
        object.setName(newName)
        item.setText(0, newName)

    def deleteObject(self, objectId: str) -> None:
        item = self._objectItemMap.get(objectId)
        if not item:
            raise ValueError(f'ID {objectId} doesn\'t map to an object')

        # Remove object from item map
        del self._objectItemMap[objectId]

        parent = item.parent()
        if parent:
            # Remove roller item from group item
            parent.removeChild(item)

            # Remove roller from group
            group = parent.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroup))
            roller = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(roller, diceroller.DiceRoller))
            group.removeRoller(roller.id())

            # Remove roller from modified rollers
            if objectId in self._modifiedRollers:
                self._modifiedRollers.remove(objectId)
        else:
            # Remove group item from tree
            self.takeTopLevelItem(self.indexOfTopLevelItem(item))

            # Remove group from group ordering
            if objectId in self._groupOrdering:
                self._groupOrdering.remove(objectId)

            # Remove group from collapsed groups
            if objectId in self._collapsedGroups:
                self._collapsedGroups.remove(objectId)

            for index in range(item.childCount()):
                child = item.child(index)
                roller = child.data(0, QtCore.Qt.ItemDataRole.UserRole)
                assert(isinstance(roller, diceroller.DiceRoller))

                # Remove roller from item map
                if roller.id() in self._objectItemMap:
                    del self._objectItemMap[roller.id()]

                # Remove roller from modified rollers
                if roller.id() in self._modifiedRollers:
                    self._modifiedRollers.remove(roller.id())

    def objectFromId(self, id: str) -> typing.Optional[typing.Union[
            diceroller.DiceRoller,
            diceroller.DiceRollerGroup
            ]]:
        item = self._objectItemMap.get(id)
        if item:
            return item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return None

    def groupFromRoller(
            self,
            rollerId: str
            ) -> typing.Optional[diceroller.DiceRollerGroup]:
        item = self._objectItemMap.get(rollerId)
        if not item:
            return None
        parent = item.parent()
        if parent == None:
            return None
        return parent.data(0, QtCore.Qt.ItemDataRole.UserRole)

    def currentObject(self) -> typing.Optional[typing.Union[
            diceroller.DiceRoller,
            diceroller.DiceRollerGroup
            ]]:
        item = self.currentItem()
        if item:
            return item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return None

    def currentGroup(self) -> typing.Optional[diceroller.DiceRollerGroup]:
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

    def currentRoller(self) -> typing.Optional[diceroller.DiceRoller]:
        item = self.currentItem()
        if item and item.parent() != None:
            return item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        return None

    def setCurrentObject(
            self,
            objectId: typing.Optional[str],
            ) -> None:
        if object is None:
            self.setCurrentItem(None)
            return

        item = self._objectItemMap.get(objectId)
        if not item:
            return
        if item != self.currentItem():
            self.setCurrentItem(item)

    def selectedObjects(self) -> typing.Iterable[typing.Union[
            diceroller.DiceRoller,
            diceroller.DiceRollerGroup
            ]]:
        selection = []
        for item in self.selectedItems():
            selection.append(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
        return selection

    def editObjectName(
            self,
            objectId: str
            ) -> None:
        item = self._objectItemMap.get(objectId)
        if not item:
            raise ValueError(f'ID {object} doesn\'t map to an object')

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
        updatedGroups: typing.List[diceroller.DiceRollerGroup] = []
        deletedGroups: typing.List[str] = []
        if hasRollerSelected:
            movedGroupItems = [item for item in dragItems if item.parent() == None]

            rollerItems = []
            for item in dragItems:
                parent = item.parent()
                if parent == None:
                    # Add all rollers from the group as they'll be added to the
                    # new group
                    group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                    assert(isinstance(group, diceroller.DiceRollerGroup))

                    # Remove the dropped group item from the tree as the dropped group
                    # will be deleted
                    index = self.indexOfTopLevelItem(item)
                    self.takeTopLevelItem(index)
                    del self._objectItemMap[group.id()]

                    # Add roller items to the list that will become the new drop item list
                    for index in range(item.childCount()):
                        rollerItems.append(item.child(index))

                    # Add deleted group to list used to notify observers
                    if group.id() not in deletedGroups:
                        deletedGroups.append(group.id())
                else:
                    if parent in movedGroupItems:
                        # Skip rollers that are part of a group that is also being moved
                        continue

                    # Remove the roller item from the tree
                    parent.removeChild(item)

                    # Remove the roller from its current group
                    roller = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                    assert(isinstance(roller, diceroller.DiceRoller))
                    group = parent.data(0, QtCore.Qt.ItemDataRole.UserRole)
                    assert(isinstance(group, diceroller.DiceRollerGroup))
                    group.removeRoller(id=roller.id())

                    # Add roller items to the list that will become the new drop item list
                    rollerItems.append(item)

                    # Add modified group to list used to notify observers
                    if not any(updated.id() == group.id() for updated in updatedGroups):
                        updatedGroups.append(group)

            dragItems = rollerItems

        # Perform the drop for all selected items
        for item in dragItems:
            wasExpanded = item.isExpanded()

            if not hasRollerSelected:
                self.takeTopLevelItem(
                    self.indexOfTopLevelItem(item))

            if dropIndicatorPos == QtWidgets.QAbstractItemView.DropIndicatorPosition.OnItem:
                # Drop INTO the target item
                parent = dropItem
                index = parent.childCount()
            else:
                 # Drop BETWEEN items (as a sibling)
                parent = dropItem.parent()
                if parent == None:
                    parent = self.invisibleRootItem()
                index = parent.indexOfChild(dropItem)
                if dropIndicatorPos == QtWidgets.QAbstractItemView.DropIndicatorPosition.BelowItem:
                    index += 1
                    dropItem = item # Add next drop item after this one

            parent.insertChild(index, item)

            if hasRollerSelected:
                # The item being dropped is for a roller so insert the roller into
                # the group represented by the parent item at the same location as
                # it was inserted into the tree
                roller = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                assert(isinstance(roller, diceroller.DiceRoller))
                group = parent.data(0, QtCore.Qt.ItemDataRole.UserRole)
                assert(isinstance(group, diceroller.DiceRollerGroup))
                group.insertRoller(index, roller)

                # Add modified group to list used to notify observers
                if not any(updated.id() == group.id() for updated in updatedGroups):
                    updatedGroups.append(group)

            item.setExpanded(wasExpanded)

        self._captureGroupOrdering()

        if updatedGroups or deletedGroups:
            self.orderChanged.emit(updatedGroups, deletedGroups)

    def selectionChanged(
            self,
            selected: QtCore.QItemSelection,
            deselected: QtCore.QItemSelection
            ) -> None:
        super().selectionChanged(selected, deselected)

        # Select the current item if it's not already selected. This can happen
        # if the user clicks in an area of the tree where there are no items or
        # after the currently active item is removed from the tree
        current = self.currentIndex()
        if not selected.contains(current):
            item = self.itemFromIndex(current)
            if item:
                with gui.SignalBlocker(self):
                    item.setSelected(True)

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(DiceRollerTree._StateVersion)

        current = self.currentObject()
        stream.writeQString(current.id() if current else '')

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

    # NOTE: This function intentionally doesn't support expanding the
    # created item as you can't do that until after the item has been
    # added to the tree. Having the function add the item to the tree
    # isn't really an option either as it varies if the item is to be
    # added or inserted
    def _createItem(
            self,
            object: typing.Union[
                diceroller.DiceRoller,
                diceroller.DiceRollerGroup],
            selected: bool = False
            ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem()
        self._configureItem(
            item=item,
            object=object,
            selected=selected)
        return item

    def _configureItem(
            self,
            item: QtWidgets.QTreeWidgetItem,
            object: typing.Union[
                diceroller.DiceRoller,
                diceroller.DiceRollerGroup],
            selected: typing.Optional[bool] = None, # None means don't change
            expanded: typing.Optional[bool] = None # None means don't change
            ):
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
        item.setText(0, object.name())
        item.setText(1, '*' if object.id() in self._modifiedRollers else '')
        item.setTextAlignment(1, int(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter))
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, object)
        if selected != None:
            item.setSelected(selected)
        if expanded != None:
            item.setExpanded(expanded)

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
        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(object, diceroller.DiceRoller) or
               isinstance(object, diceroller.DiceRollerGroup))
        oldName = object.name()
        newName = item.text(0)
        if newName != oldName:
            object.setName(newName)
            self.objectRenamed.emit(object)

    def _itemExpanded(
            self,
            item: QtWidgets.QTreeWidgetItem
            ) -> None:
        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(object, diceroller.DiceRoller) or
               isinstance(object, diceroller.DiceRollerGroup))
        if object.id() in self._collapsedGroups:
            self._collapsedGroups.remove(object.id())

    def _itemCollapsed(
            self,
            item: QtWidgets.QTreeWidgetItem
            ) -> None:
        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(object, diceroller.DiceRoller) or
               isinstance(object, diceroller.DiceRollerGroup))
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

    def _captureGroupOrdering(self) -> None:
        self._groupOrdering.clear()
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroup))
            self._groupOrdering.append(group.id())

    def _restoreGroupOrdering(self) -> None:
        currentItem = self.currentItem()

        items = {}
        while self.topLevelItemCount() > 0:
            item = self.takeTopLevelItem(0)
            group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroup))
            items[group.id()] = item
        for groupId in self._groupOrdering:
            item = items.get(groupId)
            if item:
                self.addTopLevelItem(item)
                del items[groupId]
        for item in items.values():
            self.addTopLevelItem(item)

        if currentItem:
            with gui.SignalBlocker(self):
                self.setCurrentItem(currentItem)

    def _restoreExpandStates(self) -> None:
        # Set expansion/collapsed state of groups
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroup))
            item.setExpanded(group.id() not in self._collapsedGroups)

        # Remove groups that are no longer present from collapsed groups
        for groupId in list(self._collapsedGroups):
            if groupId not in self._objectItemMap:
                self._collapsedGroups.remove(groupId)
