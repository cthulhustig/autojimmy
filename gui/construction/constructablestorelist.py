import common
import construction
import enum
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_UnsavedSuffix = ' (Unsaved)'

class _ListItemData(object):
    def __init__(
            self,
            constructable: construction.ConstructableInterface,
            unnamed: bool,
            modified: bool,
            ) -> None:
        self._constructable = constructable
        self._unnamed = unnamed
        self._modified = modified

    def constructable(self) -> construction.ConstructableInterface:
        return self._constructable

    def setConstructable(self, constructable: construction.ConstructableInterface) -> None:
        self._constructable = constructable

    def isUnnamed(self) -> bool:
        return self._unnamed

    def setUnnamed(self, unnamed: bool) -> None:
        self._unnamed = unnamed

    def isModified(self) -> bool:
        return self._modified

    def setModified(self, modified: bool) -> None:
        self._modified = modified

class _CustomListWidgetItem(QtWidgets.QListWidgetItem):
    def __lt__(self, other: QtWidgets.QListWidgetItem) -> bool:
        try:
            lhs = common.naturalSortKey(
                string=_CustomListWidgetItem._stripUnsavedSuffix(self.text()))
            rhs = common.naturalSortKey(
                string=_CustomListWidgetItem._stripUnsavedSuffix(other.text()))
            return lhs < rhs
        except Exception:
            return super().__lt__(other)

    @staticmethod
    def _stripUnsavedSuffix(text: str) -> str:
        if text.endswith(_UnsavedSuffix):
            return text[:-len(_UnsavedSuffix)]
        return text

class ConstructableStoreList(QtWidgets.QWidget):
    class Section(enum.Enum):
        UserSection = 0
        ExampleSection = 1

    selectionChanged = QtCore.pyqtSignal()
    currentChanged = QtCore.pyqtSignal()

    _StateVersion = '_ConstructableStoreList_v1'

    def __init__(
            self,
            constructableStore: construction.ConstructableStore,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)
        self._constructableStore = constructableStore

        self._list = gui.SectionList()
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._userSection = self._list.addSection(f'User {self._constructableStore.typeString()}s')
        self._exampleSection = self._list.addSection(f'Example {self._constructableStore.typeString()}s')
        self._list.selectionChanged.connect(lambda: self.selectionChanged.emit())
        self._list.currentChanged.connect(lambda: self.currentChanged.emit())

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

        self.setLayout(layout)

        self._synchronise()

    def constructables(self) -> typing.Collection[construction.ConstructableInterface]:
        results = []
        for section in range(self._list.sectionCount()):
            for row in range(self._list.sectionItemCount(section=section)):
                item = self._list.item(section=section, row=row)
                if not item:
                    continue
                itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if not itemData:
                    continue
                results.append(itemData.constructable())
        return results

    def isEmpty(
            self,
            section: typing.Optional[Section] = None
            ) -> bool:
        if section:
            if section == ConstructableStoreList.Section.UserSection:
                return self._list.sectionItemCount(section=self._userSection) <= 0
            elif section == ConstructableStoreList.Section.ExampleSection:
                return self._list.sectionItemCount(section=self._exampleSection) <= 0
            else:
                return True

        return self._list.isEmpty()

    def isUnnamed(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool:
        _, item = self._findItemByConstructable(
            constructable=constructable)
        if not item:
            return False
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return False
        return itemData.isUnnamed()

    def isStored(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool:
        _, item = self._findItemByConstructable(constructable=constructable)
        if not item:
            return False
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return False
        return self._constructableStore.isStored(
            constructable=itemData.constructable())

    def isReadOnly(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool:
        _, item = self._findItemByConstructable(
            constructable=constructable)
        if not item:
            return False
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return False
        return self._constructableStore.isReadOnly(
            constructable=itemData.constructable())

    def isModified(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool:
        _, item = self._findItemByConstructable(constructable=constructable)
        if not item:
            return False
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return False
        return itemData.isModified()

    def current(
            self
            ) -> typing.Optional[construction.ConstructableInterface]:
        item = self._list.currentItem()
        if not item:
            return None
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return None
        return itemData.constructable()

    def currentName(self) -> typing.Optional[str]:
        constructable = self.current()
        return constructable.name() if constructable else None

    def isCurrentUnnamed(self) -> bool:
        item = self._list.currentItem()
        if not item:
            return False
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return False
        return itemData.isUnnamed()

    def isCurrentStored(self) -> bool:
        current = self.current()
        if not current:
            return False
        return self._constructableStore.isStored(
            constructable=current)

    def isCurrentReadOnly(self) -> bool:
        current = self.current()
        if not current:
            return False
        return self._constructableStore.isReadOnly(
            constructable=current)

    def isCurrentModified(self) -> bool:
        item = self._list.currentItem()
        if not item:
            return False
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return False
        return itemData.isModified()

    def markCurrentModified(self) -> None:
        item = self._list.currentItem()
        if not item:
            return False
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return False
        itemData.setModified(True)
        self._updateItem(item)

    def selectionCount(self) -> int:
        return self._list.selectedItemCount()

    def hasCurrent(self) -> bool:
        return self.current() != None

    def currentSection(self) -> typing.Optional['ConstructableStoreList.Section']:
        currentSection = self._list.currentSection()
        if currentSection == self._userSection:
            return ConstructableStoreList.Section.UserSection
        elif currentSection == self._exampleSection:
            return ConstructableStoreList.Section.ExampleSection
        return None

    def hasSelection(self) -> bool:
        return self.selectionCount() > 0

    def add(
            self,
            constructable: construction.ConstructableInterface,
            makeCurrent: bool = True,
            writeToDisk: bool = False,
            unnamed: bool = False
            ) -> None:
        _, item = self._findItemByConstructable(
            constructable=constructable)
        if item:
            if writeToDisk:
                self.save(constructable=constructable)
            return

        self._constructableStore.add(constructable=constructable)
        if writeToDisk:
            self._constructableStore.save(constructable=constructable)

        itemData = _ListItemData(
            constructable=constructable,
            unnamed=unnamed,
            modified=not writeToDisk)

        item = self._addItem(
            itemData=itemData,
            section=self._userSection)
        self._updateItem(item)
        self._sortList()

        if makeCurrent:
            self._list.setCurrentItem(
                item,
                QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def save(
            self,
            constructable: construction.ConstructableInterface,
            ) -> None:
        section, item = self._findItemByConstructable(constructable=constructable)
        if not item:
            return
        self._internalSave(section=section, item=item)

    def saveCurrent(self) -> None:
        section, row = self._list.currentRow()
        if section < 0 or row < 0:
            return # No current selection
        item = self._list.item(section, row)
        if not item:
            return
        self._internalSave(section=section, item=item)

    def deleteCurrent(self) -> None:
        section, row = self._list.currentRow()
        if section < 0 or row < 0:
            return # No current selection
        if section != self._userSection:
            return # Can't delete read-only constructables
        item = self._list.item(section, row)
        if not item:
            return
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)

        if itemData:
            self._constructableStore.delete(constructable=itemData.constructable())

        self._list.takeItem(row)
        self._forceSelection()

    def deleteSelected(self) -> None:
        selectionCount = self._list.sectionItemCount(self._userSection)
        if not selectionCount:
            return # Nothing to do

        with gui.SignalBlocker(widget=self._list):
            for row in range(selectionCount - 1, -1, -1):
                item = self._list.item(self._userSection, row)
                if not item or not item.isSelected():
                    continue
                itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if itemData:
                    self._constructableStore.delete(
                        constructable=itemData.constructable())
                self._list.takeItem(self._userSection, row)

            self._forceSelection()

        self.selectionChanged.emit()
        self.currentChanged.emit()

    def removeUnsaved(self) -> None:
        for section in range(self._list.sectionCount()):
            for row in range(self._list.sectionItemCount(section=section) - 1, -1, -1):
                item = self._list.item(section=section, row=row)
                if not item:
                    continue
                itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if not itemData:
                    continue
                if self._constructableStore.isStored(
                    constructable=itemData.constructable()):
                    continue
                self._list.removeItem(section=section, row=row)
        self._forceSelection()

    def rename(
            self,
            constructable: construction.ConstructableInterface,
            newName: str
            ) -> None:
        section, item = self._findItemByConstructable(
            constructable=constructable)
        if not item:
            return
        self._internalRename(
            section=section,
            item=item,
            newName=newName,
            sortList=True)

    def renameCurrent(
            self,
            newName: str
            ) -> None:
        section, row = self._list.currentRow()
        if section < 0 or row < 0:
            return # No current selection
        item = self._list.item(section, row)
        if not item:
            return
        self._internalRename(
            section=section,
            item=item,
            newName=newName,
            sortList=True)

    def revert(
            self,
            constructable: construction.ConstructableInterface,
            ) -> None:
        _, item = self._findItemByConstructable(
            constructable=constructable)
        if not item:
            return
        self._internalRevert(item=item, sortList=True)

    def revertCurrent(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        self._internalRevert(item=item, sortList=True)

    def revertSelected(self) -> None:
        for item in self._list.selectedItems():
            if not item:
                continue
            self._internalRevert(
                item=item,
                sortList=False) # List will be sorted at the end

        self._sortList() # Sort list as names may have changed

    def revertAll(
            self,
            removeUnsaved: bool = False
            ) -> None:
        for section in range(self._list.sectionCount()):
            for row in range(self._list.sectionItemCount(section=section)):
                item = self._list.item(section=section, row=row)
                if not item:
                    continue
                self._internalRevert(
                    item=item,
                    sortList=False) # List will be sorted at the end

        if removeUnsaved:
            self.removeUnsaved()

        self._sortList() # Sort list as names may have changed

    def copyCurrent(
            self,
            makeCurrent: bool = True
            ) -> construction.ConstructableInterface:
        originalItem = self._list.currentItem()
        if not originalItem:
            return
        originalItemData: _ListItemData = originalItem.data(QtCore.Qt.ItemDataRole.UserRole)
        if not originalItemData:
            return

        originalConstructable = originalItemData.constructable()
        copyConstructable = self._constructableStore.copy(
            constructable=originalConstructable,
            newConstructableName=self._generateCopyName(
                originalName=originalConstructable.name()))

        copyItemData = _ListItemData(
            constructable=copyConstructable,
            unnamed=False,
            modified=True) # New constructable is modified as its not been saved yet

        copyItem = self._addItem(
            itemData=copyItemData,
            section=self._userSection)
        self._updateItem(copyItem)
        self._sortList()

        if makeCurrent:
            self._list.setCurrentItem(
                copyItem,
                QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect | \
                    QtCore.QItemSelectionModel.SelectionFlag.Current)

        return copyConstructable

    def copySelected(
            self,
            makeSelected: bool = True
            ) -> typing.Mapping[
                construction.ConstructableInterface,
                construction.ConstructableInterface]:
        selectedItems = self._list.selectedItems()
        if not selectedItems:
            return {} # Nothing to do

        constructablesMap: typing.Mapping[
            construction.ConstructableInterface,
            construction.ConstructableInterface] = {}

        # Block signals to prevent multiple selection changed signals as new
        # constructables are added a single event will be manually generated at
        # the end
        with gui.SignalBlocker(widget=self._list):
            oldCurrentItem = self._list.currentItem()
            newCurrentItem = None

            if makeSelected:
                self._list.clearSelection()

            for originalItem in selectedItems:
                if not originalItem:
                    continue
                originalItemData: _ListItemData = originalItem.data(
                    QtCore.Qt.ItemDataRole.UserRole)
                if not originalItemData:
                    continue

                originalConstructable = originalItemData.constructable()
                copyConstructable = self._constructableStore.copy(
                    constructable=originalConstructable,
                    newConstructableName=self._generateCopyName(
                        originalName=originalConstructable.name()))
                constructablesMap[originalConstructable] = copyConstructable

                copyItemData = _ListItemData(
                    constructable=copyConstructable,
                    unnamed=False,
                    modified=True) # New constructable is modified as its not been saved yet

                copyItem = self._addItem(
                    itemData=copyItemData,
                    section=self._userSection)
                copyItem.setSelected(makeSelected)
                self._updateItem(copyItem)

                if makeSelected and originalItem == oldCurrentItem:
                    newCurrentItem = copyItem

            if makeSelected:
                self.selectionChanged.emit()
                if newCurrentItem:
                    self._list.setCurrentItem(newCurrentItem)
                    self.currentChanged.emit()

        self._sortList()

        return constructablesMap

    def selectByName(
            self,
            constructableName: str
            ) -> bool:
        _, item = self._findItemByName(constructableName=constructableName)
        if not item:
            return False
        self._list.setCurrentItem(item, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect)
        return True

    def isNameInUse(
            self,
            constructableName: str
            ) -> None:
        _, item = self._findItemByName(constructableName=constructableName)
        return item != None

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        listState = self._list.saveState()
        stream.writeUInt32(listState.count() if listState else 0)
        if listState:
            stream.writeRawData(listState.data())

        constructableName = self.currentName()
        stream.writeQString(constructableName if constructableName else '')

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != self._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug('Failed to restore ConstructableStoreList state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count > 0:
            listState = QtCore.QByteArray(stream.readRawData(count))
            if not self._list.restoreState(listState):
                return False

        constructableName = stream.readQString()
        if constructableName and not self.selectByName(constructableName=constructableName):
            logging.debug(f'Failed to restore ConstructableStoreList state (Unknown {self._constructableStore.typeString()} "{constructableName}")')
            return False

        return True

    def setContextMenuPolicy(self, policy: QtCore.Qt.ContextMenuPolicy) -> None:
        self._list.setContextMenuPolicy(policy)

    def contextMenuPolicy(self) -> QtCore.Qt.ContextMenuPolicy:
        return self._list.contextMenuPolicy()

    def actions(self) -> typing.List[QtWidgets.QAction]:
        return self._list.actions()

    def removeAction(self, action: QtWidgets.QAction) -> None:
        self._list.removeAction(action)

    def insertActions(
            self,
            before: QtWidgets.QAction,
            actions: typing.Iterable[QtWidgets.QAction]
            ) -> None:
        self._list.addActions(before, actions)

    def insertAction(
            self,
            before: QtWidgets.QAction,
            action: QtWidgets.QAction
            ) -> None:
        self.insertAction(before, action)

    def addActions(self, actions: typing.Iterable[QtWidgets.QAction]) -> None:
        self._list.addActions(actions)

    def addAction(self, action: QtWidgets.QAction) -> None:
        self._list.addAction(action)

    def _addItem(
            self,
            itemData: _ListItemData,
            section: int
            ) -> QtWidgets.QListWidgetItem:
        item = _CustomListWidgetItem()
        item.setData(QtCore.Qt.ItemDataRole.UserRole, itemData)
        self._list.addItem(section=section, item=item)
        return item

    def _findItemByConstructable(
            self,
            constructable: construction.ConstructableInterface
            ) -> typing.Tuple[typing.Optional[int], typing.Optional[QtWidgets.QListWidgetItem]]:
        for section in range(self._list.sectionCount()):
            for row in range(self._list.sectionItemCount(section)):
                item = self._list.item(section, row)
                if not item:
                    continue
                itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if not itemData:
                    continue
                if constructable == itemData.constructable():
                    return (section, item)
        return (None, None)

    # Note that if multiple constructables have the same name this will return the first
    def _findItemByName(
            self,
            constructableName: str
            ) -> typing.Tuple[typing.Optional[int], typing.Optional[QtWidgets.QListWidgetItem]]:
        for section in range(self._list.sectionCount()):
            for row in range(self._list.sectionItemCount(section)):
                item = self._list.item(section, row)
                if not item:
                    continue
                itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if not itemData:
                    continue
                constructable = itemData.constructable()
                if constructable.name() == constructableName:
                    return (section, item)
        return (None, None)

    def _sortList(self) -> None:
        self._list.sortSections(QtCore.Qt.SortOrder.AscendingOrder)

    def _forceSelection(self) -> None:
        currentItem = self._list.currentItem()
        if currentItem:
            # There is a current item, just make sure it's actually selected
            currentItem.setSelected(True)
            return

        if self._list.isEmpty():
            return # Nothing to select

        currentItem = None
        for section in range(self._list.sectionCount()):
            currentItem = self._list.item(section=section, row=0)
            if currentItem:
                break
        if not currentItem:
            return
        currentItem.setSelected(True)
        self._list.setCurrentItem(
            currentItem,
            QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect | \
                QtCore.QItemSelectionModel.SelectionFlag.Current)

    def _synchronise(self) -> None:
        newConstructables = self._constructableStore.constructables()
        userConstructables = set()
        exampleConstructables = set()
        for constructable in newConstructables:
            if self._constructableStore.isReadOnly(constructable=constructable):
                exampleConstructables.add(constructable)
            else:
                userConstructables.add(constructable)

        with gui.SignalBlocker(widget=self._list):
            self._updateSection(
                constructables=userConstructables,
                section=self._userSection)
            self._updateSection(
                constructables=exampleConstructables,
                section=self._exampleSection)

        self._sortList()
        self._forceSelection()

    def _updateSection(
            self,
            constructables: typing.Container[construction.ConstructableInterface],
            section: int
            ) -> None:
        oldConstructables: typing.Dict[
            construction.ConstructableInterface,
            QtWidgets.QListWidgetItem] = {}

        for row in range(self._list.sectionItemCount(section) - 1, -1, -1):
            item = self._list.item(section, row)
            itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if not itemData:
                continue
            constructable = itemData.constructable()
            if constructable not in constructables:
                self._list.takeItem(row)
            else:
                oldConstructables[constructable] = item

        for constructable in constructables:
            item = oldConstructables.get(constructable)
            if not item:
                itemData = _ListItemData(
                    constructable=constructable,
                    unnamed=False, # New constructable found so it can't be unnamed
                    modified=False) # New constructable found so it can't be modified
                item = self._addItem(
                    itemData=itemData,
                    section=section)
            self._updateItem(item)

    def _updateItem(
            self,
            item: QtWidgets.QListWidgetItem,
            ) -> None:
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            item.setText(f'Invalid {self._constructableStore.typeString()} Data')
            return
        constructable = itemData.constructable()
        if not constructable:
            item.setText(f'Invalid {self._constructableStore.typeString()}')
            return
        text = constructable.name()
        if itemData.isModified():
            text += _UnsavedSuffix
        item.setText(text)

    def _generateCopyName(
            self,
            originalName: str
            ) -> str:
        copyName = originalName + ' - Copy'
        copyCount = 1
        while self._constructableStore.exists(name=copyName):
            copyCount += 1
            copyName = originalName + f' - Copy ({copyCount})'
        return copyName

    def _internalSave(
            self,
            section: int,
            item: QtWidgets.QListWidgetItem
            ) -> None:
        if section != self._userSection:
            return # Can't save read-only constructable
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return

        self._constructableStore.save(
            constructable=itemData.constructable())

        itemData.setModified(False)
        self._updateItem(item)

    def _internalRename(
            self,
            section: int,
            item: QtWidgets.QListWidgetItem,
            newName: str,
            sortList: bool
            ) -> None:
        if section != self._userSection:
            return # Can't rename read-only constructable
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return

        constructable = itemData.constructable()
        constructable.setName(newName)

        itemData.setUnnamed(False)
        itemData.setModified(True)
        self._updateItem(item)

        if sortList:
            self._sortList()

    def _internalRevert(
            self,
            item: QtWidgets.QListWidgetItem,
            sortList: bool
            ) -> None:
        itemData: _ListItemData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not itemData:
            return
        if not self._constructableStore.isStored(
            constructable=itemData.constructable()):
            return # Constructable isn't saved so nothing to revert

        self._constructableStore.revert(constructable=itemData.constructable())

        itemData.setModified(False)
        self._updateItem(item)

        if sortList:
            self._sortList()
