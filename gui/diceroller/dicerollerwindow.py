import app
import common
import copy
import diceroller
import gui
import logging
import objectdb
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: Welcome message
_WelcomeMessage = """
    TODO
""".format(name=app.AppName)

# TODO: The more I think about it the more I think the history window restoring the
# config and results is a bad idea
# - It's confusing for the user if they don't realise how it works
# - It's going to complicate storing history in the db
# TODO: Ability to re-order roller tree
# TODO: Ability to move rollers from one group to another
# TODO: Need json import/export
# - Ideally selecting multiple rollers to export to a single file (ideally
#   from multiple groups)
# TODO: Automatically create a default roller if one doesn't exist (i.e. new db)
# TODO: Management tree improvements
# - Save/load previous state
#   - What was selected
#   - What was expanded
# - When a new roller is added it should make sure the parent is expanded (otherwise you can't see where it is)
# TODO: Better names for new groups/rollers (they always have the same name)
# TODO: The fact naming new groups/rollers is done as a separate operation to creating it is clunky as hell
# - I expect the user would want to give it some kind of meaningful name the vast a majority of times
# - Prompting for the name when the user clicks new would be one option
# - Another option would be to allow editing of names directly in controls (see how you can edit file names in VS code from the Explorer Window)
# - Whatever I do, the default group/roller created at startup can have a default name
# TODO: Need a way to bundle multiple calls to objectdb into a single transaction
# - This would be used anywhere multiple calls are used to perform an operation (e.g. delete)
# - This only works because objectdb doesn't maintain any internal state (caches etc) so we don't need to worry about
# rolling it back
# TODO: Store historic results in the objectdb?
# - Would need some kind of max number (fifo) to avoid db bloat
# - Complicated by the fact they have they hold an instance of a roller but
# with the config from when the roll was made. It means those objects (which
# would need stored in the db) will have the same id as the current version
# of the object that is already in the db
# - Complicated by the fact they use ScalarCalculations (history would be lost)


class DiceRollerManagerTree(gui.TreeWidgetEx):
    currentObjectChanged = QtCore.pyqtSignal()
    objectRenamed = QtCore.pyqtSignal(objectdb.DatabaseObject)
    objectsMoved = QtCore.pyqtSignal()

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
            object: typing.Union[
                diceroller.DiceRollerGroupDatabaseObject,
                diceroller.DiceRollerDatabaseObject,
                str]
            ) -> None:
        if isinstance(object, diceroller.DiceRollerGroupDatabaseObject) or \
            isinstance(object, diceroller.DiceRollerDatabaseObject):
            object = object.id()
        item = self._objectItemMap.get(object)
        if not item:
            return
        if item != self.currentItem():
            self.setCurrentItem(item)
        if not item.isSelected():
            item.setSelected(True)

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
                self._objectItemMap[roller.id()] = rollerItem

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
                self.objectsMoved.emit()
            else:
                self._groupOrdering.clear()
                for index in range(self.topLevelItemCount()):
                    item = self.topLevelItem(index)
                    group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                    assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
                    self._groupOrdering.append(group.id())

        event.accept()

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(DiceRollerManagerTree._StateVersion)

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
        if (not newName) or (newName == oldName):
            return # Nothing to do
        object.setName(newName)
        self.objectRenamed.emit(object)

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
        for requiredIndex, groupId in enumerate(list(self._groupOrdering)):
            item = self._objectItemMap.get(groupId)
            if not item:
                self._groupOrdering.remove(groupId)
                continue
            currentIndex = self.indexOfTopLevelItem(item)
            if requiredIndex != currentIndex:
                self.takeTopLevelItem(currentIndex)
                self.insertTopLevelItem(requiredIndex, item)
        for index in range(len(self._groupOrdering), self.topLevelItemCount()):
            item = self.topLevelItem(index)
            group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
            self._groupOrdering.append(group.id())

        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
            item.setExpanded(group.id() not in self._collapsedGroups)
        for groupId in list(self._collapsedGroups):
            if groupId not in self._objectItemMap:
                self._collapsedGroups.remove(groupId)

class DiceRollerWindow(gui.WindowWidget):
    # When rolling the dice the rolled value can be calculated instantly,
    # however, displaying it straight away can be problematic.  If the new
    # result is the same as the previous result as, to the user, it might
    # not be obvious that the click was registered and a new roll occurred.
    # To try and avoid this confusion, the various results windows should
    # be cleared for a short period of time before showing the new results.
    _ResultsDelay = 700

    def __init__(self) -> None:
        super().__init__(
            title='Dice Roller',
            configSection='DiceRoller')

        self._roller = None
        self._results = None
        self._rollInProgress = False
        self._objectItemMap: typing.Dict[str, QtWidgets.QTreeWidgetItem] = {}

        self._createRollerManagerControls()
        self._createRollerConfigControls()
        self._createRollResultsControls()
        self._createRollHistoryControls()

        self._horizontalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._horizontalSplitter.addWidget(self._managerGroupBox)
        self._horizontalSplitter.addWidget(self._configGroupBox)
        self._horizontalSplitter.addWidget(self._resultsGroupBox)

        self._verticalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._verticalSplitter.addWidget(self._horizontalSplitter)
        self._verticalSplitter.addWidget(self._historyGroupBox)

        windowLayout = QtWidgets.QHBoxLayout()
        windowLayout.addWidget(self._verticalSplitter)

        self.setLayout(windowLayout)
        self._syncToDatabase()

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='HorzSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._horizontalSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='VertSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._verticalSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ManagerState',
            type=QtCore.QByteArray)
        if storedValue:
            self._managerTree.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ResultsState',
            type=QtCore.QByteArray)
        if storedValue:
            self._resultsWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='HistoryState',
            type=QtCore.QByteArray)
        if storedValue:
            self._historyWidget.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('HorzSplitterState', self._horizontalSplitter.saveState())
        self._settings.setValue('VertSplitterState', self._verticalSplitter.saveState())
        self._settings.setValue('ManagerState', self._managerTree.saveState())
        self._settings.setValue('ResultsState', self._resultsWidget.saveState())
        self._settings.setValue('HistoryState', self._historyWidget.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _createRollerManagerControls(self) -> None:
        self._managerTree = DiceRollerManagerTree()
        self._managerTree.currentObjectChanged.connect(
            self._managerTreeCurrentRollerChanged)
        self._managerTree.objectRenamed.connect(
            self._managerTreeObjectRenamed)
        self._managerTree.objectsMoved.connect(
            self._managerTreeRollersMoved)

        self._managerToolbar = QtWidgets.QToolBar('Toolbar')
        self._managerToolbar.setIconSize(QtCore.QSize(32, 32))
        self._managerToolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        self._managerToolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._newRollerAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.NewGrid), 'New Roller', self)
        self._newRollerAction.triggered.connect(self._newRollerClicked)
        self._managerTree.addAction(self._newRollerAction)
        self._managerToolbar.addAction(self._newRollerAction)

        self._newGroupAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.NewList), 'New Group', self)
        self._newGroupAction.triggered.connect(self._newGroupClicked)
        self._managerTree.addAction(self._newGroupAction)
        self._managerToolbar.addAction(self._newGroupAction)

        self._renameAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.RenameFile), 'Rename...', self)
        self._renameAction.triggered.connect(self._renameClicked)
        self._managerTree.addAction(self._renameAction)
        self._managerToolbar.addAction(self._renameAction)

        self._copyAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.CopyFile), 'Copy...', self)
        self._copyAction.triggered.connect(self._copyClicked)
        self._managerTree.addAction(self._copyAction)
        self._managerToolbar.addAction(self._copyAction)

        self._deleteAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DeleteFile), 'Delete...', self)
        self._deleteAction.triggered.connect(self._deleteClicked)
        self._managerTree.addAction(self._deleteAction)
        self._managerToolbar.addAction(self._deleteAction)

        self._managerTree.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)

        groupLayout = QtWidgets.QHBoxLayout()
        groupLayout.setContentsMargins(0, 0, 0, 0)
        groupLayout.addWidget(self._managerToolbar)
        groupLayout.addWidget(self._managerTree)

        self._managerGroupBox = QtWidgets.QGroupBox('Dice Rollers')
        self._managerGroupBox.setLayout(groupLayout)

    def _createRollerConfigControls(self) -> None:
        self._rollerConfigWidget = gui.DiceRollerConfigWidget()
        self._rollerConfigWidget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self._rollerConfigWidget.configChanged.connect(
            self._rollerConfigChanged)

        self._rollButton = QtWidgets.QPushButton('Roll Dice')
        self._rollButton.clicked.connect(self._rollDice)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.setContentsMargins(0, 0, 0, 0)
        groupLayout.addWidget(self._rollerConfigWidget)
        groupLayout.addWidget(self._rollButton)

        self._configGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configGroupBox.setLayout(groupLayout)

    def _createRollResultsControls(self) -> None:
        self._resultsWidget = gui.DiceRollDisplayWidget()
        self._resultsWidget.animationComplete.connect(self._virtualRollComplete)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._resultsWidget)

        self._resultsGroupBox = QtWidgets.QGroupBox('Roll')
        self._resultsGroupBox.setLayout(groupLayout)

    def _createRollHistoryControls(self) -> None:
        self._historyWidget = gui.DiceRollHistoryWidget()
        self._historyWidget.resultSelected.connect(self._historySelectionChanged)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._historyWidget)

        self._historyGroupBox = QtWidgets.QGroupBox('History')
        self._historyGroupBox.setLayout(groupLayout)

    def _syncToDatabase(self) -> None:
        try:
            with gui.SignalBlocker(self._managerTree):
                self._managerTree.syncToDatabase()
            self._setCurrentRoller(
                roller=self._managerTree.currentRoller())
        except Exception as ex:
            logging.error('Failed to sync UI to database', exc_info=ex)

    def _rollDice(self) -> None:
        if not self._roller or self._rollInProgress:
            return

        modifiers = []
        for modifier in self._roller.dynamicDMs():
            assert(isinstance(modifier, diceroller.DiceModifierDatabaseObject))
            if modifier.enabled():
                modifiers.append((modifier.name(), modifier.value()))

        self._results = diceroller.rollDice(
            dieCount=self._roller.dieCount(),
            dieType=self._roller.dieType(),
            constantDM=self._roller.constantDM(),
            hasBoon=self._roller.hasBoon(),
            hasBane=self._roller.hasBane(),
            dynamicDMs=modifiers,
            targetNumber=self._roller.targetNumber())

        self._rollInProgress = True
        self._updateControlEnablement()

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setResults(self._results)

    def _setCurrentRoller(
            self,
            roller: typing.Optional[diceroller.DiceRollerDatabaseObject],
            results: typing.Optional[diceroller.DiceRollResult] = None
            ) -> None:
        # TODO: Remove temp hack
        group = self._managerTree.groupFromRoller(roller=roller) if roller else None
        print('Current Roller: {group} - {roller}'.format(
            group=group.name() if group else 'Unknown',
            roller=roller.name() if roller else 'Unknown'))

        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(roller=roller)

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setRoller(roller=roller)
            if results:
                self._resultsWidget.setResults(
                    results=results,
                    animate=False)

        self._roller = roller
        self._results = results
        self._rollInProgress = False

        self._updateControlEnablement()

    def _updateControlEnablement(self) -> None:
        hasSelection = self._managerTree.currentItem() != None
        self._renameAction.setEnabled(hasSelection)
        self._deleteAction.setEnabled(hasSelection)

        self._managerGroupBox.setEnabled(not self._rollInProgress)
        self._configGroupBox.setEnabled(self._roller != None and not self._rollInProgress)
        self._historyGroupBox.setEnabled(not self._rollInProgress)

    def _newRollerClicked(self) -> None:
        if self._managerTree.groupCount() == 0:
            self._newGroupClicked()
            return

        group = self._managerTree.currentGroup()
        if not group:
            return

        roller = diceroller.DiceRollerDatabaseObject(
            name='Dice Roller',
            dieCount=1,
            dieType=common.DieType.D6)
        group = copy.deepcopy(group)
        group.addRoller(roller=roller)

        try:
            objectdb.ObjectDbManager.instance().updateObject(
                object=group)
        except Exception as ex:
            message = 'Failed to add roller to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase()
        self._managerTree.setCurrentObject(object=roller)
        # TODO: Select the roller that was added

    def _newGroupClicked(self) -> None:
        roller = diceroller.DiceRollerDatabaseObject(
            name='Dice Roller',
            dieCount=1,
            dieType=common.DieType.D6)
        group = diceroller.DiceRollerGroupDatabaseObject(
            name='Group',
            rollers=[roller])

        try:
            objectdb.ObjectDbManager.instance().createObject(
                object=group)
        except Exception as ex:
            message = 'Failed to create roller group in objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase()
        self._managerTree.setCurrentObject(object=roller)

    def _renameClicked(self) -> None:
        object = self._managerTree.currentObject()
        if isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
            title = 'Group Name'
            typeString = 'group'
        elif isinstance(object, diceroller.DiceRollerDatabaseObject):
            title = 'Dice Roller Name'
            typeString = 'dice roller'
        else:
            return

        oldName = object.name()
        newName, result = gui.InputDialogEx.getText(
            parent=self,
            title=title,
            label=f'Enter a name for the {typeString}',
            text=oldName)
        if not result:
            return

        object = copy.deepcopy(object)
        object.setName(name=newName)

        try:
            objectdb.ObjectDbManager.instance().updateObject(
                object=object)
        except Exception as ex:
            message = f'Failed to rename {typeString} in objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase()

    def _copyClicked(self) -> None:
        object = self._managerTree.currentObject()
        group = None
        roller = None
        if isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
            group = object.copyConfig()
            typeString = 'group'
        elif isinstance(object, diceroller.DiceRollerDatabaseObject):
            group = self._managerTree.groupFromRoller(roller=object)
            group = copy.deepcopy(group)
            roller = object.copyConfig()
            group.addRoller(roller)

            typeString = 'dice roller'
        else:
            return

        try:
            if roller:
                objectdb.ObjectDbManager.instance().updateObject(
                    object=group)
            else:
                objectdb.ObjectDbManager.instance().createObject(
                    object=group)
        except Exception as ex:
            message = f'Failed to write copied {typeString} to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase()
        self._managerTree.setCurrentObject(object=roller if roller else group)
        # TODO: Select the newly added roller/group

    def _deleteClicked(self) -> None:
        selection = self._managerTree.selectedObjects()
        if not selection:
            return

        groups: typing.List[diceroller.DiceRollerGroupDatabaseObject] = []
        rollers: typing.List[diceroller.DiceRollerDatabaseObject] = []
        for object in selection:
            if isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
                groups.append(object)
            elif isinstance(object, diceroller.DiceRollerDatabaseObject):
                rollers.append(object)

        confirmation = None
        if len(groups) == 0:
            if len(rollers) == 1:
                roller = rollers[0]
                assert(isinstance(roller, diceroller.DiceRollerDatabaseObject))
                confirmation = 'Are you sure you want to delete dice roller {name}?'.format(
                    name=roller.name())
            else:
                confirmation = 'Are you sure you want to delete {count} dice rollers?'.format(
                    count=len(rollers))
        if len(rollers) == 0:
            if len(groups) == 1:
                group = groups[0]
                assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
                confirmation = 'Are you sure you want to delete group {name} and the dice rollers it contains?'.format(
                    name=group.name())
            else:
                confirmation = 'Are you sure you want to delete {count} groups and the dice rollers they contain?'.format(
                    count=len(groups))
        else:
            confirmation = 'Are you sure you want to delete {count} items?'.format(
                count=len(rollers) + len(groups))

        if confirmation:
            answer = gui.MessageBoxEx.question(text=confirmation)
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        try:
            with objectdb.ObjectDbManager.instance().createTransaction() as transaction:
                for roller in rollers:
                    objectdb.ObjectDbManager.instance().deleteObject(
                        id=roller.id(),
                        transaction=transaction)

                for group in groups:
                    objectdb.ObjectDbManager.instance().deleteObject(
                        id=group.id(),
                        transaction=transaction)
        except Exception as ex:
            message = f'Failed to delete objects from objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase()

    def _managerTreeCurrentRollerChanged(self) -> None:
        self._setCurrentRoller(
            roller=self._managerTree.currentRoller())

    def _managerTreeObjectRenamed(
            self,
            object: objectdb.DatabaseObject
            ) -> None:
        typeString = None
        if isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
            typeString = 'group'
        elif isinstance(object, diceroller.DiceRollerDatabaseObject):
            typeString = 'dice roller'
        else:
            return

        try:
            objectdb.ObjectDbManager.instance().updateObject(
                object=object)
        except Exception as ex:
            message = f'Failed to rename {typeString} in objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Fall through to sync to database in order to revert ui to a
            # consistent state

        self._syncToDatabase()

    # TODO: I'm not sure how best to update this so it's not accessing the
    # items directly
    def _managerTreeRollersMoved(self) -> None:
        oldGroups: typing.Dict[str, diceroller.DiceRollerGroupDatabaseObject] = {}
        for group in self._managerTree.groups():
            oldGroups[group.id()] = copy.deepcopy(group)

        updatedGroups: typing.List[typing.Tuple[
            str, # Old group id
            diceroller.DiceRollerGroupDatabaseObject # New group to replace old (has a different id)
            ]] = []
        for groupIndex in range(self._managerTree.topLevelItemCount()):
            groupItem = self._managerTree.topLevelItem(groupIndex)
            newGroup = self._managerTree.objectFromItem(groupItem)
            assert(isinstance(newGroup, diceroller.DiceRollerGroupDatabaseObject))
            newGroup = copy.deepcopy(newGroup)
            newGroup.clearRollers()

            for rollerIndex in range(groupItem.childCount()):
                rollerItem = groupItem.child(rollerIndex)
                roller = self._managerTree.objectFromItem(rollerItem)
                assert(isinstance(roller, diceroller.DiceRollerDatabaseObject))
                roller = copy.deepcopy(roller)
                roller.setParent(None)
                newGroup.addRoller(roller)

            oldGroup = oldGroups[newGroup.id()]
            if newGroup != oldGroup:
                updatedGroups.append((oldGroup.id(), newGroup))

        if not updatedGroups:
            return

        try:
            with objectdb.ObjectDbManager.instance().createTransaction() as transaction:
                # As we're moving rollers between groups we need to delete all
                # the old groups then add the new groups (which have the same id
                # as the ones that were removed). This is done (rather than
                # doing delete, add, delete, add) to prevent foreign key issues
                # when adding one group that references a roller that is still
                # references by another group that is waiting to be deleted.
                for oldGroupId, _ in updatedGroups:
                    objectdb.ObjectDbManager.instance().deleteObject(
                        id=oldGroupId,
                        transaction=transaction)
                for _, newGroup in updatedGroups:
                    objectdb.ObjectDbManager.instance().createObject(
                        object=newGroup,
                        transaction=transaction)
        except Exception as ex:
            message = 'Failed to move rollers in objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Fall through to sync to database in order to revert ui to a
            # consistent state

        self._syncToDatabase()

    def _rollerConfigChanged(self) -> None:
        try:
            objectdb.ObjectDbManager.instance().updateObject(
                object=self._roller)
        except Exception as ex:
            message = f'Failed to update roller {self._roller.id()} in objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Continue, may as well sync results even if it
            # couldn't be written

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.syncToRoller()

    def _historySelectionChanged(
            self,
            roller: diceroller.DiceRollerDatabaseObject,
            results: diceroller.DiceRollResult
            ) -> None:
        # Make new copies of the historic roller and results. These
        # will be passed to the things like the configuration widget
        # so we don't want to modify the instances held by the history
        # widget
        if roller != None:
            roller = copy.deepcopy(roller)
        if results != None:
            results = copy.deepcopy(results)

        try:
            objectdb.ObjectDbManager.instance().updateObject(
                object=roller)
        except Exception as ex:
            message = f'Failed to restore historic roller {roller.id()} to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        # TODO: Select the correct roller in the tree
        self._syncToDatabase()
        self._setCurrentRoller(roller=self._roller, results=results)

    def _virtualRollComplete(self) -> None:
        if not self._rollInProgress:
            return

        self._rollInProgress = False
        self._updateControlEnablement()

        with gui.SignalBlocker(self._historyWidget):
            self._historyWidget.addResult(self._roller, self._results)

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='DiceRollerWelcome')
        message.exec()
