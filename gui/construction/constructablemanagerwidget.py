import app
import common
import copy
import construction
import gui
import logging
import typing
from PyQt5 import QtWidgets, QtCore

class _CustomListWidgetItem(QtWidgets.QListWidgetItem):
    _UnsavedSuffix = ' (Unsaved)'

    def __init__(
            self,
            constructable: construction.ConstructableInterface,
            unnamed: bool,
            modified: bool,
            parent: typing.Optional[QtWidgets.QListWidget] = None
            ) -> None:
        super().__init__(parent)
        self._constructable = constructable
        self._unnamed = unnamed
        self._modified = modified
        self._updateText()

    def constructable(self) -> construction.ConstructableInterface:
        return self._constructable

    def setConstructable(self, constructable: construction.ConstructableInterface) -> None:
        self._constructable = constructable
        self._updateText()

    def isUnnamed(self) -> bool:
        return self._unnamed

    def setUnnamed(self, unnamed: bool) -> None:
        self._unnamed = unnamed
        self._updateText()

    def isModified(self) -> bool:
        return self._modified

    def setModified(self, modified: bool) -> None:
        self._modified = modified
        self._updateText()

    def _updateText(self) -> None:
        constructable = self.constructable()
        if not constructable:
            self.setText(f'<Invalid Constructable>')
            return
        text = constructable.name()
        if self.isModified():
            text += _CustomListWidgetItem._UnsavedSuffix
        self.setText(text)

    def __lt__(self, other: QtWidgets.QListWidgetItem) -> bool:
        try:
            if isinstance(other, _CustomListWidgetItem) and \
                    (self.isUnnamed() != other.isUnnamed()):
                return self.isUnnamed()

            lhs = common.naturalSortKey(
                string=_CustomListWidgetItem._stripUnsavedSuffix(self.text()))
            rhs = common.naturalSortKey(
                string=_CustomListWidgetItem._stripUnsavedSuffix(other.text()))
            return lhs < rhs
        except Exception:
            return super().__lt__(other)

    @staticmethod
    def _stripUnsavedSuffix(text: str) -> str:
        if text.endswith(_CustomListWidgetItem._UnsavedSuffix):
            return text[:-len(_CustomListWidgetItem._UnsavedSuffix)]
        return text

class ConstructableManagerWidget(QtWidgets.QWidget):
    currentChanged = QtCore.pyqtSignal()

    _StateVersion = 'ConstructableManagerWidget_v1'
    _IconSize = 32

    def __init__(
            self,
            constructableStore: construction.ConstructableStore,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)
        self._constructableStore = constructableStore
        self._unnamedIndex = 1

        self._sectionList = gui.SectionList()
        self._sectionList.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._userSection = self._sectionList.addSection(f'User {self._constructableStore.typeString()}s')
        self._exampleSection = self._sectionList.addSection(f'Example {self._constructableStore.typeString()}s')
        self._sectionList.currentChanged.connect(self._handleCurrentChanged)

        iconSize = int(ConstructableManagerWidget._IconSize * app.Config.instance().interfaceScale())
        self._toolbar = QtWidgets.QToolBar('Toolbar')
        self._toolbar.setIconSize(QtCore.QSize(iconSize, iconSize))
        self._toolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        self._toolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._newAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.NewFile), 'New', self)
        self._newAction.triggered.connect(self._newClicked)
        self._sectionList.addAction(self._newAction)
        self._toolbar.addAction(self._newAction)

        self._saveAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.SaveFile), 'Save...', self)
        self._saveAction.triggered.connect(self._saveClicked)
        self._sectionList.addAction(self._saveAction)
        self._toolbar.addAction(self._saveAction)

        self._renameAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.RenameFile), 'Rename...', self)
        self._renameAction.triggered.connect(self._renameClicked)
        self._sectionList.addAction(self._renameAction)
        self._toolbar.addAction(self._renameAction)

        self._revertAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.Reload), 'Revert...', self)
        self._revertAction.triggered.connect(self._revertClicked)
        self._sectionList.addAction(self._revertAction)
        self._toolbar.addAction(self._revertAction)

        self._copyAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.CopyFile), 'Copy', self)
        self._copyAction.triggered.connect(self._copyClicked)
        self._sectionList.addAction(self._copyAction)
        self._toolbar.addAction(self._copyAction)

        self._deleteAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DeleteFile), 'Delete...', self)
        self._deleteAction.triggered.connect(self._deleteClicked)
        self._sectionList.addAction(self._deleteAction)
        self._toolbar.addAction(self._deleteAction)

        self._importAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.ImportFile), 'Import...', self)
        self._importAction.triggered.connect(self._importClicked)
        self._sectionList.addAction(self._importAction)
        self._toolbar.addAction(self._importAction)

        self._exportAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.ExportFile), 'Export...', self)
        self._exportAction.triggered.connect(self._exportClicked)
        self._sectionList.addAction(self._exportAction)
        self._toolbar.addAction(self._exportAction)

        self._sectionList.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._sectionList)

        self.setLayout(layout)

        self._synchronise()

    def createConstructable(
            self,
            name: str
            ) -> construction.ConstructableInterface:
        raise RuntimeError(f'{type(self)} is derived from ConstructableManagerWidget so must implement createConstructable')

    def importConstructable(self) -> None:
        raise RuntimeError(f'{type(self)} is derived from ConstructableManagerWidget so must implement importConstructable')

    def exportConstructable(self) -> None:
        raise RuntimeError(f'{type(self)} is derived from ConstructableManagerWidget so must implement exportConstructable')

    def current(self) -> typing.Optional[construction.ConstructableInterface]:
        item = self._sectionList.currentItem()
        if not isinstance(item, _CustomListWidgetItem):
            return None
        return item.constructable()

    def isUnnamed(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool:
        _, item = self._findItemByConstructable(
            constructable=constructable)
        if not isinstance(item, _CustomListWidgetItem):
            return False
        return item.isUnnamed()

    def isCurrentUnnamed(self) -> bool:
        item = self._sectionList.currentItem()
        if not isinstance(item, _CustomListWidgetItem):
            return False
        return item.isUnnamed()

    def isStored(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool:
        _, item = self._findItemByConstructable(constructable=constructable)
        if not isinstance(item, _CustomListWidgetItem):
            return False
        return self._constructableStore.isStored(
            constructable=item.constructable())

    def isCurrentStored(self) -> bool:
        current = self.current()
        if not current:
            return False
        return self._constructableStore.isStored(
            constructable=current)

    def isReadOnly(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool:
        _, item = self._findItemByConstructable(
            constructable=constructable)
        if not isinstance(item, _CustomListWidgetItem):
            return False
        return self._constructableStore.isReadOnly(
            constructable=item.constructable())

    def isCurrentReadOnly(self) -> bool:
        current = self.current()
        if not current:
            return False
        return self._constructableStore.isReadOnly(
            constructable=current)

    def isModified(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool:
        _, item = self._findItemByConstructable(constructable=constructable)
        if not isinstance(item, _CustomListWidgetItem):
            return False
        return item.isModified()

    def isCurrentModified(self) -> bool:
        item = self._sectionList.currentItem()
        if not isinstance(item, _CustomListWidgetItem):
            return False
        return item.isModified()

    def markCurrentModified(self) -> None:
        item = self._sectionList.currentItem()
        if not isinstance(item, _CustomListWidgetItem):
            return
        item.setModified(True)
        self._updateButtons()

    def promptSave(
            self,
            constructable: construction.ConstructableInterface
            ) -> bool: # False if user cancelled, otherwise True
        readOnly = self.isReadOnly(constructable=constructable)
        unnamed = self.isUnnamed(constructable=constructable)

        oldName = constructable.name()
        newName = None
        if readOnly or unnamed:
            prompt = f'The {self._constructableStore.typeString()} \'{constructable.name()}\' is {"read only" if readOnly else "unsaved"}, enter a name to save it as.'
            while not newName:
                newName, result = gui.InputDialogEx.getText(
                    parent=self,
                    title=f'{self._constructableStore.typeString()} Name',
                    label=prompt,
                    text=oldName)
                if not result:
                    return False # User cancelled

                if not newName:
                    gui.MessageBoxEx.information(
                        parent=self,
                        text=f'The {self._constructableStore.typeString()} name can\'t be empty')
                elif self._constructableStore.exists(name=newName):
                    gui.MessageBoxEx.critical(
                        parent=self,
                        text=f'A {self._constructableStore.typeString()} named \'{newName}\' already exists')

                    # Trigger prompt for a new name but show what he use previously types
                    oldName = newName
                    newName = None

        sortList = False
        wasRenamed = False
        try:
            section, item = self._findItemByConstructable(
                constructable=constructable)
            originalItem = None
            if readOnly:
                # The constructable is readonly so to save it needs to copied
                # and saved as a new user constructable
                assert(newName)
                originalItem = item
                constructable = copy.deepcopy(constructable)
                constructable.setName(name=newName)
                self._internalAdd(
                    constructable=constructable,
                    makeCurrent=True, # Select the copy
                    writeToDisk=False,
                    unnamed=False,
                    sortList=False) # Only sort once at end
                sortList = True
                section, item = self._findItemByConstructable(
                    constructable=constructable)
                wasRenamed = True
            elif unnamed:
                # The constructable is unnamed so rename it before saving
                assert(newName)
                self._internalRename(
                    section=section,
                    item=item,
                    newName=newName,
                    sortList=False) # Only sort once at end
                sortList = True
                wasRenamed = True

            self._internalSave(section=section, item=item)

            if originalItem != None:
                # The modified constructable has been saved as something else so
                # revert the original version
                self._internalRevert(
                    item=originalItem,
                    sortList=False) # Only sort once at end
                sortList = True
        except Exception as ex:
            message = f'Failed to save {self._constructableStore.typeString()}(s)'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

        if sortList:
            self._sortList()

        if wasRenamed:
            # Handling the current item changing MUST be done after sorting to
            # ensure the view is moved to the correct location to ensure the
            # current item is visible
            self._handleCurrentChanged(ensureVisible=True)

        return True # User didn't cancel

    def promptSaveModified(
            self,
            revertUnsaved: bool = False
            ) -> bool: # False if the user cancelled, otherwise True
        allConstructables = self._constructableStore.constructables()
        allModified: typing.List[construction.ConstructableInterface] = []
        for constructable in allConstructables:
            if self.isModified(constructable=constructable):
                allModified.append(constructable)
        if not allModified:
            return True # Nothing to do

        if len(allModified) == 1:
            constructable = allModified[0]
            answer = gui.MessageBoxEx.question(
                parent=self,
                text=f'The {self._constructableStore.typeString()} \'{constructable.name()}\' has been modified, do you want to save it?',
                buttons=QtWidgets.QMessageBox.StandardButton.Yes | \
                QtWidgets.QMessageBox.StandardButton.No | \
                QtWidgets.QMessageBox.StandardButton.Cancel)
            if answer == QtWidgets.QMessageBox.StandardButton.Cancel:
                return False # User cancelled

            allToSave = []
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                allToSave.append(constructable)
        else:
            dlg = gui.ConstructableSelectDialog(
                parent=self,
                title=f'Unsaved {self._constructableStore.typeString()}s',
                text=f'Do you want to save these modified {self._constructableStore.typeString()}s?',
                constructables=allModified,
                showYesNoCancel=True,
                defaultState=QtCore.Qt.CheckState.Checked,
                configSection=f'Unsaved{self._constructableStore.typeString()}Dialog')
            if dlg.exec() == QtWidgets.QDialog.DialogCode.Rejected:
                return False # The use cancelled
            allToSave = dlg.selected()

        for constructable in allToSave:
            if not self.promptSave(constructable=constructable):
                return False # The use cancelled

        if revertUnsaved:
            current = self.current()
            sortList = False
            updateCurrent = False
            for constructable in allConstructables:
                _, item = self._findItemByConstructable(constructable=constructable)
                if item == None or not item.isModified():
                    continue

                self._internalRevert(
                    item=item,
                    sortList=False) # Sort once at the end
                sortList = True

                if constructable == current:
                    updateCurrent = True

            # Remove any unsaved constructables for the same reason the modified
            # constructables were removed
            self._deleteUnsaved()

            if sortList:
                self._sortList()

            if updateCurrent:
                # Handling the current item changing MUST be done after sorting to
                # ensure the view is moved to the correct location to ensure the
                # current item is visible
                self._handleCurrentChanged(ensureVisible=True)

        return True # The user didn't cancel

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(self._StateVersion)

        listState = self._sectionList.saveState()
        stream.writeUInt32(listState.count() if listState else 0)
        if listState:
            stream.writeRawData(listState.data())

        constructable = self.current()
        stream.writeQString(constructable.name() if constructable else '')

        return state

    def restoreState(
            self,
            state: QtCore.QByteArray
            ) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != self._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug('Failed to restore ConstructableManagerWidget state (Incorrect version)')
            return False

        count = stream.readUInt32()
        if count > 0:
            listState = QtCore.QByteArray(stream.readRawData(count))
            if not self._sectionList.restoreState(listState):
                return False

        constructableName = stream.readQString()
        if constructableName:
            _, item = self._findItemByName(constructableName=constructableName)
            if not item:
                logging.debug(f'Failed to restore ConstructableManagerWidget state (Unknown {self._constructableStore.typeString()} "{constructableName}")')
                return False
            self._makeItemCurrent(item=item)

        return True

    def _findItemByConstructable(
            self,
            constructable: construction.ConstructableInterface
            ) -> typing.Tuple[
                typing.Optional[int], # Section index
                typing.Optional[_CustomListWidgetItem]]: # List item
        for section in range(self._sectionList.sectionCount()):
            for row in range(self._sectionList.sectionItemCount(section)):
                item = self._sectionList.item(section, row)
                if not isinstance(item, _CustomListWidgetItem):
                    continue
                if constructable == item.constructable():
                    return (section, item)
        return (None, None)

    # Note that if multiple constructables have the same name this will return the first
    def _findItemByName(
            self,
            constructableName: str
            ) -> typing.Tuple[typing.Optional[int], typing.Optional[_CustomListWidgetItem]]:
        for section in range(self._sectionList.sectionCount()):
            for row in range(self._sectionList.sectionItemCount(section)):
                item = self._sectionList.item(section, row)
                if not isinstance(item, _CustomListWidgetItem):
                    continue
                constructable = item.constructable()
                if constructable.name() == constructableName:
                    return (section, item)
        return (None, None)

    def _makeItemCurrent(
            self,
            item: QtWidgets.QListWidgetItem
            ) -> None:
        self._sectionList.setCurrentItem(
            item,
            QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect |
            QtCore.QItemSelectionModel.SelectionFlag.Current)

    def _sortList(self) -> None:
        self._sectionList.sortSections(QtCore.Qt.SortOrder.AscendingOrder)

    def _forceSelection(self) -> None:
        currentItem = self._sectionList.currentItem()
        if currentItem:
            # There is a current item, just make sure it's actually selected
            currentItem.setSelected(True)
            return

        if self._sectionList.isEmpty():
            return # Nothing to select

        currentItem = None
        for section in range(self._sectionList.sectionCount()):
            currentItem = self._sectionList.item(section=section, row=0)
            if currentItem:
                break
        if not currentItem:
            return
        currentItem.setSelected(True)
        self._makeItemCurrent(item=currentItem)

    def _copySelected(
            self,
            makeSelected: bool = True
            ) -> typing.Mapping[
                construction.ConstructableInterface,
                construction.ConstructableInterface]:
        selectedItems = self._sectionList.selectedItems()
        if not selectedItems:
            return {} # Nothing to do

        constructablesMap: typing.Mapping[
            construction.ConstructableInterface,
            construction.ConstructableInterface] = {}

        # Block signals to prevent multiple selection changed signals as new
        # constructables are added a single event will be manually generated at
        # the end
        with gui.SignalBlocker(widget=self._sectionList):
            oldCurrentItem = self._sectionList.currentItem()
            newCurrentItem = None

            if makeSelected:
                self._sectionList.clearSelection()

            for originalItem in selectedItems:
                if not isinstance(originalItem, _CustomListWidgetItem):
                    continue

                originalConstructable = originalItem.constructable()
                copyConstructable = self._constructableStore.copy(
                    constructable=originalConstructable,
                    newConstructableName=self._generateCopyName(
                        originalName=originalConstructable.name()))
                constructablesMap[originalConstructable] = copyConstructable

                copyItem = self._internalAdd(
                    constructable=copyConstructable,
                    unnamed=False,
                    writeToDisk=False,
                    makeCurrent=False,
                    sortList=False) # Sort once at the end
                copyItem.setSelected(makeSelected)

                if makeSelected and originalItem == oldCurrentItem:
                    newCurrentItem = copyItem

            self._sortList()

            if makeSelected and newCurrentItem:
                self._sectionList.setCurrentItem(newCurrentItem)
                # Handling the current item changing MUST be done after sorting to
                # ensure the view is moved to the correct location to ensure the
                # current item is visible
                self._handleCurrentChanged(ensureVisible=True)

        return constructablesMap

    def _deleteSelected(self) -> None:
        selectionCount = self._sectionList.sectionItemCount(self._userSection)
        if not selectionCount:
            return # Nothing to do

        with gui.SignalBlocker(widget=self._sectionList):
            for row in range(selectionCount - 1, -1, -1):
                item = self._sectionList.item(self._userSection, row)
                if not isinstance(item, _CustomListWidgetItem) or not item.isSelected():
                    continue
                self._constructableStore.delete(
                    constructable=item.constructable())
                self._sectionList.takeItem(self._userSection, row)

            self._internalDefault()
            self._forceSelection()

        # No need to keep the current item visible when deleting as its just
        # which ever item that became current after the old current item was
        # deleted.
        self._handleCurrentChanged(ensureVisible=False)

    def _deleteUnsaved(self) -> None:
        for section in range(self._sectionList.sectionCount()):
            for row in range(self._sectionList.sectionItemCount(section=section) - 1, -1, -1):
                item = self._sectionList.item(section=section, row=row)
                if not isinstance(item, _CustomListWidgetItem):
                    continue
                if self._constructableStore.isStored(constructable=item.constructable()):
                    continue
                self._sectionList.removeItem(section=section, row=row)
        self._forceSelection()

    def _synchronise(self) -> None:
        newConstructables = self._constructableStore.constructables()
        userConstructables = set()
        exampleConstructables = set()
        for constructable in newConstructables:
            if self._constructableStore.isReadOnly(constructable=constructable):
                exampleConstructables.add(constructable)
            else:
                userConstructables.add(constructable)

        with gui.SignalBlocker(widget=self._sectionList):
            self._updateSection(
                constructables=userConstructables,
                section=self._userSection)
            self._updateSection(
                constructables=exampleConstructables,
                section=self._exampleSection)

        self._sortList()
        self._internalDefault()
        self._forceSelection()

    def _updateSection(
            self,
            constructables: typing.Container[construction.ConstructableInterface],
            section: int
            ) -> None:
        seenConstructables = set()

        for row in range(self._sectionList.sectionItemCount(section) - 1, -1, -1):
            item = self._sectionList.item(section, row)
            if not isinstance(item, _CustomListWidgetItem):
                continue
            constructable = item.constructable()
            if constructable not in constructables:
                self._sectionList.takeItem(row)
            else:
                seenConstructables[constructable] = item

        for constructable in constructables:
            if constructable in seenConstructables:
                continue
            item = _CustomListWidgetItem(
                constructable=constructable,
                unnamed=False, # New constructable found so it can't be unnamed
                modified=False) # New constructable found so it can't be modified
            self._sectionList.addItem(
                section=section,
                item=item)

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

    def _updateButtons(self) -> None:
        isReadOnly = self.isCurrentReadOnly()
        isModified = self.isCurrentModified()
        isStored = self.isCurrentStored()
        self._saveAction.setEnabled(isModified)
        self._renameAction.setEnabled(not isReadOnly)
        self._revertAction.setEnabled(isModified and isStored)
        self._deleteAction.setEnabled(not isReadOnly)

    def _handleCurrentChanged(
            self,
            ensureVisible: bool = False
            ) -> None:
        if ensureVisible:
            self._sectionList.ensureCurrentVisible()

        self._updateButtons()
        self.currentChanged.emit()

    def _newClicked(self) -> None:
        try:
            self._internalNew(
                makeCurrent=True,
                sortList=True)
        except Exception as ex:
            message = f'Failed to create new {self._constructableStore.typeString()}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

        self._handleCurrentChanged(ensureVisible=True)

    def _saveClicked(self) -> None:
        constructable = self.current()
        if not constructable:
            gui.MessageBoxEx.information(
                parent=self,
                text=f'No {self._constructableStore.typeString()} to save')
            return
        # No need for exception handling as that's handled by promptSave
        self.promptSave(constructable=constructable)

    def _renameClicked(self) -> None:
        constructable = self.current()
        if not constructable:
            gui.MessageBoxEx.information(
                parent=self,
                text=f'No {self._constructableStore.typeString()} to rename')
            return

        oldName = None if self.isCurrentUnnamed() else constructable.name()
        newName = None
        while not newName:
            newName, result = gui.InputDialogEx.getText(
                parent=self,
                title=f'{self._constructableStore.typeString()} Name',
                label=f'Enter a name for the {self._constructableStore.typeString()}',
                text=oldName)
            if not result:
                return False

            if not newName:
                gui.MessageBoxEx.information(
                    parent=self,
                    text=f'The {self._constructableStore.typeString()} name can\'t be empty')
            elif self._constructableStore.exists(name=newName):
                gui.MessageBoxEx.critical(
                    parent=self,
                    text=f'A {self._constructableStore.typeString()} named \'{newName}\' already exists')

                # Trigger prompt for a new name but show what he use previously types
                oldName = newName
                newName = None

        try:
            section, item = self._findItemByConstructable(
                constructable=constructable)
            self._internalRename(
                section=section,
                item=item,
                newName=newName,
                sortList=True)
        except Exception as ex:
            message = f'Failed to rename {self._constructableStore.typeString()}(s)'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

        self._handleCurrentChanged(ensureVisible=True)

    def _revertClicked(self) -> None:
        selectionCount = self._sectionList.selectedItemCount()
        if not selectionCount:
            gui.MessageBoxEx.information(
                parent=self,
                text=f'Select the {self._constructableStore.typeString()}(s) to revert')
            return

        if selectionCount == 1:
            constructable = self.current()
            prompt = f'Are you sure you want to revert \'{constructable.name()}\'?'
        else:
            prompt = f'Are you sure you want to revert {selectionCount} {self._constructableStore.typeString()}s?'

        answer = gui.MessageBoxEx.question(parent=self, text=prompt)
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            for item in self._sectionList.selectedItems():
                if not isinstance(item, _CustomListWidgetItem):
                    continue
                self._internalRevert(
                    item=item,
                    sortList=False) # List will be sorted at the end
        except Exception as ex:
            message = f'Failed to revert {self._constructableStore.typeString()}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

        self._sortList() # Sort list as names may have changed
        # Handling the current item changing MUST be done after sorting to
        # ensure the view is moved to the correct location to ensure the
        # current item is visible
        self._handleCurrentChanged(ensureVisible=True)

    def _copyClicked(self) -> None:
        if self._sectionList.selectedItemCount() < 0:
            gui.MessageBoxEx.information(
                parent=self,
                text=f'Select the {self._constructableStore.typeString()}(s) to copy')
            return

        try:
            self._copySelected(makeSelected=True)
        except Exception as ex:
            message = f'Failed to copy {self._constructableStore.typeString()}(s)'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _deleteClicked(self) -> None:
        selectionCount = self._sectionList.selectedItemCount()
        if not selectionCount:
            gui.MessageBoxEx.information(
                parent=self,
                text=f'Select the {self._constructableStore.typeString()}(s) to delete')
            return

        if selectionCount == 1:
            constructable = self.current()
            prompt = f'Are you sure you want to delete \'{constructable.name()}\'?'
        else:
            prompt = f'Are you sure you want to delete {selectionCount} {self._constructableStore.typeString()}s?'

        answer = gui.MessageBoxEx.question(parent=self, text=prompt)
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            self._deleteSelected()
        except Exception as ex:
            message = f'Failed to delete {self._constructableStore.typeString()}(s)'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _exportClicked(self) -> None:
        try:
            self.exportConstructable()
        except Exception as ex:
            message = f'Failed to export {self._constructableStore.typeString()}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    def _importClicked(self) -> None:
        try:
            self.importConstructable()
        except Exception as ex:
            message = f'Failed to import {self._constructableStore.typeString()}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

    #
    # NOTE: The following functions are intended to push requested changes to
    # the construable store and UI. They intentionally do not explicitly
    # generate the constructable changed notification but they may generate it
    # indirectly by causing the currently selected constructable to change.
    # The intention is these simple operations will make up more complex logic
    # and that logic should be responsible for generating the signal if needed.
    # If there is a possibility that the current item may indirectly be changed
    # then the caller should block signals from the segmented list control
    # before calling one of these functions
    #

    # Create a user constructable if there isn't one. This is done to make it
    # more obvious to the user what is going on. Without this, out the box, the
    # configuration would show one of the examples which the user might start
    # editing.
    def _internalDefault(self) -> bool:
        userConstructables = self._sectionList.sectionItemCount(
            section=self._userSection)
        if userConstructables > 0:
            return False

        self._internalNew(
            makeCurrent=True,
            sortList=False) # This is the first item so nothing to sort
        return True

    def _internalNew(
            self,
            makeCurrent: bool,
            sortList: bool
            ) -> typing.Optional[_CustomListWidgetItem]:
        while True:
            newName = f'<Unnamed {self._constructableStore.typeString()} {self._unnamedIndex}>'
            self._unnamedIndex += 1
            if not self._constructableStore.exists(name=newName):
                break

        # NOTE: There is no need to update the buttons or results display as
        # adding it will trigger a selection changed event which will cause
        # them to update
        constructable = self.createConstructable(newName)
        if not constructable:
            raise RuntimeError('Callback returned null constructable.')
        return self._internalAdd(
            constructable=constructable,
            unnamed=True,
            writeToDisk=False,
            makeCurrent=makeCurrent,
            sortList=sortList)

    def _internalAdd(
            self,
            constructable: construction.ConstructableInterface,
            unnamed: bool,
            writeToDisk: bool,
            makeCurrent: bool,
            sortList: bool
            ) -> _CustomListWidgetItem:
        self._constructableStore.add(constructable=constructable)
        if writeToDisk:
            self._constructableStore.save(constructable=constructable)

        item = _CustomListWidgetItem(
            constructable=constructable,
            unnamed=unnamed,
            modified=not writeToDisk)
        self._sectionList.addItem(
            section=self._userSection, # New constructables are always added to the user section
            item=item)

        if sortList:
            self._sortList()

        if makeCurrent:
            self._makeItemCurrent(item=item)

        return item

    def _internalSave(
            self,
            section: int,
            item: _CustomListWidgetItem
            ) -> None:
        if section != self._userSection:
            return # Can't save read-only constructable

        self._constructableStore.save(
            constructable=item.constructable())

        item.setModified(False)
        self._updateButtons()

    def _internalRename(
            self,
            section: int,
            item: _CustomListWidgetItem,
            newName: str,
            sortList: bool
            ) -> None:
        if section != self._userSection:
            return # Can't rename read-only constructable

        constructable = item.constructable()
        constructable.setName(newName)

        item.setUnnamed(False)
        item.setModified(True)
        self._updateButtons()

        if sortList:
            self._sortList()

    def _internalRevert(
            self,
            item: _CustomListWidgetItem,
            sortList: bool
            ) -> None:
        if not self._constructableStore.isStored(
                constructable=item.constructable()):
            return # Constructable isn't saved so nothing to revert

        self._constructableStore.revert(constructable=item.constructable())

        item.setModified(False)
        self._updateButtons()

        if sortList:
            self._sortList()
