import common
import enum
import gui
import gunsmith
import logging
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_UnsavedWeaponSuffix = ' (Unsaved)'

class _WeaponData(object):
    def __init__(
            self,
            weapon: gunsmith.Weapon,
            unnamed: bool,
            modified: bool,
            ) -> None:
        self._weapon = weapon
        self._unnamed = unnamed
        self._modified = modified

    def weapon(self) -> gunsmith.Weapon:
        return self._weapon

    def setWeapon(self, weapon: gunsmith.Weapon) -> None:
        self._weapon = weapon

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
        if text.endswith(_UnsavedWeaponSuffix):
            return text[:-len(_UnsavedWeaponSuffix)]
        return text

class WeaponStoreList(QtWidgets.QWidget):
    class Section(enum.Enum):
        UserWeapons = 0
        ExampleWeapons = 1

    selectionChanged = QtCore.pyqtSignal()
    currentChanged = QtCore.pyqtSignal()

    _StateVersion = '_WeaponStoreList_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)
        self._unnamedWeaponIndex = 1

        self._list = gui.SectionList()
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._userWeaponSection = self._list.addSection('User Weapons')
        self._exampleWeaponSection = self._list.addSection('Example Weapons')
        self._list.selectionChanged.connect(lambda: self.selectionChanged.emit())
        self._list.currentChanged.connect(lambda: self.currentChanged.emit())

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

        self.setLayout(layout)

        self._synchronise()

    def weapons(self) -> typing.Collection[gunsmith.Weapon]:
        weapons = []
        for section in range(self._list.sectionCount()):
            for row in range(self._list.sectionItemCount(section=section)):
                item = self._list.item(section=section, row=row)
                if not item:
                    continue
                weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if not weaponData:
                    continue
                weapons.append(weaponData.weapon())
        return weapons

    def isEmpty(
            self,
            section: typing.Optional[Section] = None
            ) -> bool:
        if section:
            if section == WeaponStoreList.Section.UserWeapons:
                return self._list.sectionItemCount(section=self._userWeaponSection) <= 0
            elif section == WeaponStoreList.Section.ExampleWeapons:
                return self._list.sectionItemCount(section=self._exampleWeaponSection) <= 0
            else:
                return True

        return self._list.isEmpty()

    def isWeaponUnnamed(
            self,
            weapon: gunsmith.Weapon
            ) -> bool:
        _, item = self._findItemByWeapon(weapon=weapon)
        if not item:
            return False
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return False
        return weaponData.isUnnamed()

    def isWeaponStored(
            self,
            weapon: gunsmith.Weapon
            ) -> bool:
        _, item = self._findItemByWeapon(weapon=weapon)
        if not item:
            return False
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return False
        return gunsmith.WeaponStore.instance().isStored(weapon=weaponData.weapon())

    def isWeaponReadOnly(
            self,
            weapon: gunsmith.Weapon
            ) -> bool:
        _, item = self._findItemByWeapon(weapon=weapon)
        if not item:
            return False
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return False
        return gunsmith.WeaponStore.instance().isReadOnly(weapon=weaponData.weapon())

    def isWeaponModified(
            self,
            weapon: gunsmith.Weapon
            ) -> bool:
        _, item = self._findItemByWeapon(weapon=weapon)
        if not item:
            return False
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return False
        return weaponData.isModified()

    def currentWeapon(self) -> typing.Optional[gunsmith.Weapon]:
        item = self._list.currentItem()
        if not item:
            return None
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return None
        return weaponData.weapon()

    def currentWeaponName(self) -> typing.Optional[str]:
        item = self._list.currentItem()
        if not item:
            return None
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return None
        weapon = weaponData.weapon()
        return weapon.weaponName()

    def isCurrentWeaponUnnamed(self) -> bool:
        item = self._list.currentItem()
        if not item:
            return False
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return False
        return weaponData.isUnnamed()

    def isCurrentWeaponStored(self) -> bool:
        item = self._list.currentItem()
        if not item:
            return False
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return False
        return gunsmith.WeaponStore.instance().isStored(weapon=weaponData.weapon())

    def isCurrentWeaponReadOnly(self) -> bool:
        item = self._list.currentItem()
        if not item:
            return False
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return False
        return gunsmith.WeaponStore.instance().isReadOnly(weapon=weaponData.weapon())

    def isCurrentWeaponModified(self) -> bool:
        item = self._list.currentItem()
        if not item:
            return False
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return False
        return weaponData.isModified()

    def markCurrentWeaponModified(self) -> None:
        item = self._list.currentItem()
        if not item:
            return False
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return False
        weaponData.setModified(True)
        self._updateItem(item)

    def selectionCount(self) -> int:
        return self._list.selectedItemCount()

    def hasCurrent(self) -> bool:
        return self.currentWeapon() != None

    def currentSection(self) -> typing.Optional['WeaponStoreList.Section']:
        currentSection = self._list.currentSection()
        if currentSection == self._userWeaponSection:
            return WeaponStoreList.Section.UserWeapons
        elif currentSection == self._exampleWeaponSection:
            return WeaponStoreList.Section.ExampleWeapons
        return None

    def hasSelection(self) -> bool:
        return self.selectionCount() > 0

    def addWeapon(
            self,
            weapon: gunsmith.Weapon,
            makeCurrent: bool = True
            ) -> None:
        _, item = self._findItemByWeapon(weapon=weapon)
        if item:
            return # Weapon is already in the list

        gunsmith.WeaponStore.instance().addWeapon(weapon=weapon)

        weaponData = _WeaponData(
            weapon=weapon,
            unnamed=False,
            modified=True)

        item = self._addWeaponData(
            weaponData=weaponData,
            section=self._userWeaponSection)
        self._updateItem(item)
        self._sortList()

        if makeCurrent:
            self._list.setCurrentItem(item, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def newWeapon(
            self,
            weaponType: gunsmith.WeaponType,
            techLevel: int,
            weaponName: typing.Optional[str] = None,
            makeCurrent: bool = True
            ) -> gunsmith.Weapon:
        unnamed = False
        if not weaponName:
            weaponName = f'<Unnamed Weapon {self._unnamedWeaponIndex}>'
            self._unnamedWeaponIndex += 1
            unnamed = True

        weapon = gunsmith.WeaponStore.instance().newWeapon(
            weaponType=weaponType,
            weaponName=weaponName,
            techLevel=techLevel)

        weaponData = _WeaponData(
            weapon=weapon,
            unnamed=unnamed,
            # Don't count new weapons as modified until the user actually makes a change
            modified=False)

        item = self._addWeaponData(
            weaponData=weaponData,
            section=self._userWeaponSection)
        self._updateItem(item)
        self._sortList()

        if makeCurrent:
            self._list.setCurrentItem(item, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect)

        return weapon

    def saveWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        section, item = self._findItemByWeapon(weapon=weapon)
        if not item:
            return
        self._internalSaveWeapon(section=section, item=item)

    def saveCurrentWeapon(self) -> None:
        section, row = self._list.currentRow()
        if section < 0 or row < 0:
            return # No current weapon
        item = self._list.item(section, row)
        if not item:
            return
        self._internalSaveWeapon(section=section, item=item)

    def deleteCurrentWeapon(self) -> None:
        section, row = self._list.currentRow()
        if section < 0 or row < 0:
            return # No current weapon
        if section != self._userWeaponSection:
            return # Can't delete read-only weapon
        item = self._list.item(section, row)
        if not item:
            return
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)

        if weaponData:
            gunsmith.WeaponStore.instance().deleteWeapon(weapon=weaponData.weapon())

        self._list.takeItem(row)
        self._forceSelection()

    def deleteSelectedWeapons(self) -> None:
        selectionCount = self._list.sectionItemCount(self._userWeaponSection)
        if not selectionCount:
            return # Nothing to do

        with gui.SignalBlocker(widget=self._list):
            for row in range(selectionCount - 1, -1, -1):
                item = self._list.item(self._userWeaponSection, row)
                if not item or not item.isSelected():
                    continue
                weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if weaponData:
                    gunsmith.WeaponStore.instance().deleteWeapon(weapon=weaponData.weapon())
                self._list.takeItem(self._userWeaponSection, row)

            self._forceSelection()

        self.selectionChanged.emit()
        self.currentChanged.emit()

    def removeUnsavedWeapons(self) -> None:
        for section in range(self._list.sectionCount()):
            for row in range(self._list.sectionItemCount(section=section) - 1, -1, -1):
                item = self._list.item(section=section, row=row)
                if not item:
                    continue
                weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if not weaponData:
                    continue
                if gunsmith.WeaponStore.instance().isStored(weapon=weaponData.weapon()):
                    continue
                self._list.removeItem(section=section, row=row)
        self._forceSelection()

    def renameWeapon(
            self,
            weapon: gunsmith.Weapon,
            newName: str
            ) -> None:
        section, item = self._findItemByWeapon(weapon=weapon)
        if not item:
            return
        self._internalRenameWeapon(
            section=section,
            item=item,
            newName=newName,
            sortList=True)

    def renameCurrentWeapon(
            self,
            newName: str
            ) -> None:
        section, row = self._list.currentRow()
        if section < 0 or row < 0:
            return # No current weapon
        item = self._list.item(section, row)
        if not item:
            return
        self._internalRenameWeapon(
            section=section,
            item=item,
            newName=newName,
            sortList=True)

    def revertWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> None:
        _, item = self._findItemByWeapon(weapon=weapon)
        if not item:
            return
        self._internalRevertWeapon(item=item, sortList=True)

    def revertCurrentWeapon(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        self._internalRevertWeapon(item=item, sortList=True)

    def revertSelectedWeapons(self) -> None:
        for item in self._list.selectedItems():
            if not item:
                continue
            self._internalRevertWeapon(
                item=item,
                sortList=False) # List will be sorted at the end

        self._sortList() # Sort list as weapon name may have changed

    def revertAllWeapons(
            self,
            removeUnsaved: bool = False
            ) -> None:
        for section in range(self._list.sectionCount()):
            for row in range(self._list.sectionItemCount(section=section)):
                item = self._list.item(section=section, row=row)
                if not item:
                    continue
                self._internalRevertWeapon(
                    item=item,
                    sortList=False) # List will be sorted at the end

        if removeUnsaved:
            self.removeUnsavedWeapons()

        self._sortList() # Sort list as weapon name may have changed

    def copyCurrentWeapon(
            self,
            makeCurrent: bool = True
            ) -> gunsmith.Weapon:
        origItem = self._list.currentItem()
        if not origItem:
            return
        origWeaponData: _WeaponData = origItem.data(QtCore.Qt.ItemDataRole.UserRole)
        if not origWeaponData:
            return

        origWeapon = origWeaponData.weapon()
        copyWeapon = gunsmith.WeaponStore.instance().copyWeapon(
            weapon=origWeapon,
            newWeaponName=self._generateCopyWeaponName(
                origWeaponName=origWeapon.weaponName()))

        copyWeaponData = _WeaponData(
            weapon=copyWeapon,
            unnamed=False,
            modified=True) # New weapon is modified as its not been saved yet

        copyItem = self._addWeaponData(
            weaponData=copyWeaponData,
            section=self._userWeaponSection)
        self._updateItem(copyItem)
        self._sortList()

        if makeCurrent:
            self._list.setCurrentItem(
                copyItem,
                QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect | QtCore.QItemSelectionModel.SelectionFlag.Current)

        return copyWeapon

    def copySelectedWeapons(
            self,
            makeSelected: bool = True
            ) -> typing.Mapping[gunsmith.Weapon, gunsmith.Weapon]:
        selectedItems = self._list.selectedItems()
        if not selectedItems:
            return {} # Nothing to do

        weaponMap: typing.Mapping[gunsmith.Weapon, gunsmith.Weapon] = {}

        # Block signals to prevent multiple selection changed signals as new weapons are added
        # a single event will be manually generated at the end
        with gui.SignalBlocker(widget=self._list):
            oldCurrentItem = self._list.currentItem()
            newCurrentItem = None

            if makeSelected:
                self._list.clearSelection()

            for origItem in selectedItems:
                if not origItem:
                    continue
                origWeaponData: _WeaponData = origItem.data(QtCore.Qt.ItemDataRole.UserRole)
                if not origWeaponData:
                    continue

                origWeapon = origWeaponData.weapon()
                copyWeapon = gunsmith.WeaponStore.instance().copyWeapon(
                    weapon=origWeapon,
                    newWeaponName=self._generateCopyWeaponName(
                        origWeaponName=origWeapon.weaponName()))
                weaponMap[origWeapon] = copyWeapon

                copyWeaponData = _WeaponData(
                    weapon=copyWeapon,
                    unnamed=False,
                    modified=True) # New weapon is modified as its not been saved yet

                copyItem = self._addWeaponData(
                    weaponData=copyWeaponData,
                    section=self._userWeaponSection)
                copyItem.setSelected(makeSelected)
                self._updateItem(copyItem)

                if makeSelected and origItem == oldCurrentItem:
                    newCurrentItem = copyItem

            if makeSelected:
                self.selectionChanged.emit()
                if newCurrentItem:
                    self._list.setCurrentItem(newCurrentItem)
                    self.currentChanged.emit()

        self._sortList()

        return weaponMap

    def importWeapon(
            self,
            weapon: gunsmith.Weapon,
            makeCurrent: bool = True
            ) -> None:
        # Write the weapon first, if this fails an exception will be thrown and the list won't be
        # updated
        gunsmith.WeaponStore.instance().saveWeapon(weapon=weapon)

        weaponData = _WeaponData(
            weapon=weapon,
            unnamed=False,
            modified=False)
        item = self._addWeaponData(
            weaponData=weaponData,
            section=self._userWeaponSection)

        self._updateItem(item)
        self._sortList()

        if makeCurrent:
            self._list.setCurrentItem(item, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def selectByWeaponName(
            self,
            weaponName: str
            ) -> bool:
        _, item = self._findItemByName(weaponName=weaponName)
        if not item:
            return False
        self._list.setCurrentItem(item, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect)
        return True

    def hasWeaponWithName(
            self,
            weaponName: str
            ) -> None:
        _, item = self._findItemByName(weaponName=weaponName)
        return item != None

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        listState = self._list.saveState()
        stream.writeUInt32(listState.count() if listState else 0)
        if listState:
            stream.writeRawData(listState.data())

        weaponName = self.currentWeaponName()
        stream.writeQString(weaponName if weaponName else '')

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != self._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug('Failed to restore WeaponStoreList state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count > 0:
            listState = QtCore.QByteArray(stream.readRawData(count))
            if not self._list.restoreState(listState):
                return False

        weaponName = stream.readQString()
        if weaponName and not self.selectByWeaponName(weaponName=weaponName):
            logging.debug(f'Failed to restore WeaponStoreList state (Unknown weapon "{weaponName}")')
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

    def _addWeaponData(
            self,
            weaponData: _WeaponData,
            section: int
            ) -> QtWidgets.QListWidgetItem:
        item = _CustomListWidgetItem()
        item.setData(QtCore.Qt.ItemDataRole.UserRole, weaponData)
        self._list.addItem(section=section, item=item)
        return item

    def _findItemByWeapon(
            self,
            weapon: gunsmith.Weapon
            ) -> typing.Tuple[typing.Optional[int], typing.Optional[QtWidgets.QListWidgetItem]]:
        for section in range(self._list.sectionCount()):
            for row in range(self._list.sectionItemCount(section)):
                item = self._list.item(section, row)
                if not item:
                    continue
                weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if not weaponData:
                    continue
                if weapon == weaponData.weapon():
                    return (section, item)
        return (None, None)

    # Note that if multiple weapons have the same name this will return the first
    def _findItemByName(
            self,
            weaponName: str
            ) -> typing.Tuple[typing.Optional[int], typing.Optional[QtWidgets.QListWidgetItem]]:
        for section in range(self._list.sectionCount()):
            for row in range(self._list.sectionItemCount(section)):
                item = self._list.item(section, row)
                if not item:
                    continue
                weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if not weaponData:
                    continue
                weapon = weaponData.weapon()
                if weapon.weaponName() == weaponName:
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
            QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect | QtCore.QItemSelectionModel.SelectionFlag.Current)

    def _synchronise(self) -> None:
        newWeapons = gunsmith.WeaponStore.instance().weapons()
        userWeapons = set()
        exampleWeapons = set()
        for weapon in newWeapons:
            if gunsmith.WeaponStore.instance().isReadOnly(weapon):
                exampleWeapons.add(weapon)
            else:
                userWeapons.add(weapon)

        with gui.SignalBlocker(widget=self._list):
            self._updateSection(
                weapons=userWeapons,
                section=self._userWeaponSection)
            self._updateSection(
                weapons=exampleWeapons,
                section=self._exampleWeaponSection)

        self._sortList()
        self._forceSelection()

    def _updateSection(
            self,
            weapons: typing.Container[gunsmith.Weapon],
            section: int
            ) -> None:
        oldWeapons: typing.Dict[gunsmith.Weapon, QtWidgets.QListWidgetItem] = {}

        for row in range(self._list.sectionItemCount(section) - 1, -1, -1):
            item = self._list.item(section, row)
            weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if not weaponData:
                continue
            weapon = weaponData.weapon()
            if weapon not in weapons:
                self._list.takeItem(row)
            else:
                oldWeapons[weapon] = item

        for weapon in weapons:
            item = oldWeapons.get(weapon)
            if not item:
                weaponData = _WeaponData(
                    weapon=weapon,
                    unnamed=False, # New weapon found so it can't be unnamed
                    modified=False) # New weapon found so it can't be modified
                item = self._addWeaponData(
                    weaponData=weaponData,
                    section=section)
            self._updateItem(item)

    def _updateItem(
            self,
            item: QtWidgets.QListWidgetItem,
            ) -> None:
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            item.setText('Invalid Weapon Data')
            return
        weapon = weaponData.weapon()
        if not weapon:
            item.setText('Invalid Weapon')
            return
        text = weapon.weaponName()
        if weaponData.isModified():
            text += _UnsavedWeaponSuffix
        item.setText(text)

    def _generateCopyWeaponName(
            self,
            origWeaponName: str
            ) -> str:
        copyWeaponName = origWeaponName + ' - Copy'
        copyCount = 1
        while gunsmith.WeaponStore.instance().hasWeapon(weaponName=copyWeaponName):
            copyCount += 1
            copyWeaponName = origWeaponName + f' - Copy ({copyCount})'
        return copyWeaponName

    def _internalSaveWeapon(
            self,
            section: int,
            item: QtWidgets.QListWidgetItem
            ) -> None:
        if section != self._userWeaponSection:
            return # Can't save read-only weapon
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return

        gunsmith.WeaponStore.instance().saveWeapon(weapon=weaponData.weapon())

        weaponData.setModified(False)
        self._updateItem(item)

    def _internalRenameWeapon(
            self,
            section: int,
            item: QtWidgets.QListWidgetItem,
            newName: str,
            sortList: bool
            ) -> None:
        if section != self._userWeaponSection:
            return # Can't rename read-only weapon
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return

        weapon = weaponData.weapon()
        weapon.setWeaponName(newName)

        weaponData.setUnnamed(False)
        weaponData.setModified(True)
        self._updateItem(item)

        if sortList:
            self._sortList()

    def _internalRevertWeapon(
            self,
            item: QtWidgets.QListWidgetItem,
            sortList: bool
            ) -> None:
        weaponData: _WeaponData = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not weaponData:
            return
        if not gunsmith.WeaponStore.instance().isStored(weapon=weaponData.weapon()):
            return # Weapon isn't saved so nothing to revert

        gunsmith.WeaponStore.instance().revertWeapon(weapon=weaponData.weapon())

        weaponData.setModified(False)
        self._updateItem(item)

        if sortList:
            self._sortList()
