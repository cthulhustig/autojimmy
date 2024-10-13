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
# TODO: Store historic results in the objectdb?
# - Would need some kind of max number (fifo) to avoid db bloat
# - Complicated by the fact they have they hold an instance of a roller but
# with the config from when the roll was made. It means those objects (which
# would need stored in the db) will have the same id as the current version
# of the object that is already in the db
# - Complicated by the fact they use ScalarCalculations (history would be lost)
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
        self._syncManagerTree()
        self._updateControlEnablement()

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
        self._settings.setValue('ResultsState', self._resultsWidget.saveState())
        self._settings.setValue('HistoryState', self._historyWidget.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _createRollerManagerControls(self) -> None:
        self._managerTree = gui.TreeWidgetEx()
        self._managerTree.setColumnCount(1)
        self._managerTree.header().setStretchLastSection(True)
        self._managerTree.setHeaderHidden(True)
        self._managerTree.setVerticalScrollMode(QtWidgets.QTreeView.ScrollMode.ScrollPerPixel)
        self._managerTree.verticalScrollBar().setSingleStep(10) # This seems to give a decent scroll speed without big jumps
        self._managerTree.setAutoScroll(False)
        self._managerTree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        itemDelegate = gui.StyledItemDelegateEx()
        itemDelegate.setHighlightCurrentItem(enabled=False)
        self._managerTree.setItemDelegate(itemDelegate)
        self._managerTree.itemSelectionChanged.connect(
            self._managerTreeSelectionChanged)
        self._managerTree.itemChanged.connect(
            self._managerTreeItemChanged)

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

    def _syncManagerTree(self) -> None:
        try:
            groups = objectdb.ObjectDbManager.instance().readObjects(
                classType=diceroller.DiceRollerGroupDatabaseObject)
        except Exception as ex:
            message = 'Failed to read roller groups from objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        for index, group in enumerate(groups):
            assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
            groupItem = self._managerTree.topLevelItem(index)
            self._syncManagerTreeGroup(
                group=group,
                groupItem=groupItem)

        while self._managerTree.topLevelItemCount() > len(groups):
            groupItem = self._managerTree.takeTopLevelItem(
                self._managerTree.topLevelItemCount() - 1)
            group = groupItem.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
            del self._objectItemMap[group.id()]

    def _syncManagerTreeGroup(
            self,
            group: diceroller.DiceRollerGroupDatabaseObject,
            groupItem: typing.Optional[QtWidgets.QTreeWidgetItem] = None,
            makeSelected: bool = False
            ) -> QtWidgets.QTreeWidgetItem:
        if groupItem == None:
            groupItem = QtWidgets.QTreeWidgetItem([group.name()])
            groupItem.setFlags(groupItem.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            self._managerTree.addTopLevelItem(groupItem)
            groupItem.setExpanded(True)
        else:
            groupItem.setText(0, group.name())
            oldGroup = groupItem.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(oldGroup, diceroller.DiceRollerGroupDatabaseObject))
            del self._objectItemMap[oldGroup.id()]
        groupItem.setData(0, QtCore.Qt.ItemDataRole.UserRole, group)
        self._objectItemMap[group.id()] = groupItem

        rollers = group.rollers()
        for index, roller in enumerate(group.rollers()):
            rollerItem = groupItem.child(index)
            self._syncManagerTreeRoller(
                roller=roller,
                rollerItem=rollerItem,
                groupItem=groupItem)

        while groupItem.childCount() > len(rollers):
            rollerItem = groupItem.takeChild(groupItem.childCount() - 1)
            roller = rollerItem.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(roller, diceroller.DiceRollerGroupDatabaseObject))
            del self._objectItemMap[roller.id()]

        if makeSelected:
            groupItem.setSelected(True)
            self._managerTree.setCurrentItem(groupItem)

        return groupItem

    def _syncManagerTreeRoller(
            self,
            roller: diceroller.DiceRollerDatabaseObject,
            rollerItem: typing.Optional[QtWidgets.QTreeWidgetItem] = None,
            groupItem: typing.Optional[QtWidgets.QTreeWidgetItem] = None,
            makeSelected: bool = False
            ) -> QtWidgets.QTreeWidgetItem:
        if rollerItem == None:
            rollerItem = QtWidgets.QTreeWidgetItem([roller.name()])
            rollerItem.setFlags(groupItem.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            if groupItem:
                groupItem.addChild(rollerItem)
        else:
            rollerItem.setText(0, roller.name())
            oldRoller = rollerItem.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(oldRoller, diceroller.DiceRollerDatabaseObject))
            del self._objectItemMap[oldRoller.id()]
        rollerItem.setData(0, QtCore.Qt.ItemDataRole.UserRole, roller)
        self._objectItemMap[roller.id()] = rollerItem

        if makeSelected:
            rollerItem.setSelected(True)
            self._managerTree.setCurrentItem(rollerItem)

        return rollerItem

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
        if self._managerTree.topLevelItemCount() == 0:
            self._newGroupClicked()
            return

        item = self._managerTree.currentItem()
        if not item:
            # TODO: Do something
            return
        if item.parent() != None:
            item = item.parent()
        group = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))

        try:
            roller = diceroller.DiceRollerDatabaseObject(
                name='New Roller',
                dieCount=1,
                dieType=common.DieType.D6)
            group.addRoller(roller)
            objectdb.ObjectDbManager.instance().updateObject(
                object=group)
        except Exception as ex:
            message = f'Failed to create roller {roller.id()} in objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncManagerTreeRoller(
            roller=roller,
            groupItem=item,
            makeSelected=True)

    def _newGroupClicked(self) -> None:
        try:
            roller = diceroller.DiceRollerDatabaseObject(
                name='New Roller',
                dieCount=1,
                dieType=common.DieType.D6)
            group = diceroller.DiceRollerGroupDatabaseObject(
                name='Roller Group',
                rollers=[roller])

            objectdb.ObjectDbManager.instance().createObject(
                object=group)
        except Exception as ex:
            message = f'Failed to create roller group {group.id()} in objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        groupItem = self._syncManagerTreeGroup(group=group)
        rollerItem = groupItem.child(0)
        if rollerItem:
            rollerItem.setSelected(True)
            self._managerTree.setCurrentItem(rollerItem)

    def _renameClicked(self) -> None:
        item = self._managerTree.currentItem()
        if not item:
            # TODO: Do something?
            return

        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
            title = 'Group Name'
            objectType = 'group'
            oldName = object.name()
        elif isinstance(object, diceroller.DiceRollerDatabaseObject):
            title = 'Dice Roller Name'
            objectType = 'dice roller'
            oldName = object.name()
        else:
            return

        newName, result = gui.InputDialogEx.getText(
            parent=self,
            title=title,
            label=f'Enter a name for the {objectType}',
            text=oldName)
        if not result:
            return

        object.setName(name=newName)

        try:
            objectdb.ObjectDbManager.instance().updateObject(
                object=object)
        except Exception as ex:
            message = f'Failed to rename {object.id()} in objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        item.setText(0, newName)
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, object)

    def _copyClicked(self) -> None:
        item = self._managerTree.currentItem()
        if not item:
            # TODO: Do something?
            return

        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        group = None
        roller = None
        try:
            if isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
                group = object.copyConfig()
                objectdb.ObjectDbManager.instance().createObject(
                    object=group)
            elif isinstance(object, diceroller.DiceRollerDatabaseObject):
                roller = object.copyConfig()

                groupItem = item.parent()
                group = groupItem.data(0, QtCore.Qt.ItemDataRole.UserRole)
                assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
                group.addRoller(roller)

                objectdb.ObjectDbManager.instance().updateObject(
                    object=group)
        except Exception as ex:
            # TODO: Handle this
            return

        if roller:
            self._syncManagerTreeRoller(
                roller=roller,
                groupItem=item.parent(),
                makeSelected=True)
        elif group:
            self._syncManagerTreeGroup(
                group=group,
                makeSelected=True)

    def _deleteClicked(self) -> None:
        item = self._managerTree.currentItem()
        if not item:
            # TODO: Do something?
            return

        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        confirmation = None
        if isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
            rollerCount = object.rollerCount()
            if rollerCount > 0: # Only ask for confirmation if the group is not empty
                confirmation = f'Are you sure you want to delete group {object.name()}? This will also delete the {rollerCount} dice rollers it contains.'
        elif isinstance(object, diceroller.DiceRollerDatabaseObject):
            confirmation = f'Are you sure you want to delete dice roller {object.name()}?'
        else:
            return

        if confirmation:
            answer = gui.MessageBoxEx.question(text=confirmation)
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        try:
            objectdb.ObjectDbManager.instance().deleteObject(
                id=object.id())
        except Exception as ex:
            message = f'Failed to delete roller {object.id()} from objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        clearCurrent = False
        if isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
            itemIndex = self._managerTree.indexOfTopLevelItem(item)
            self._managerTree.takeTopLevelItem(itemIndex)

            del self._objectItemMap[object.id()]

            with gui.SignalBlocker(self._historyWidget):
                for roller in object.rollers():
                    del self._objectItemMap[roller.id()]
                    self._historyWidget.purgeHistory(roller=roller)

            if self._roller:
                clearCurrent = object.containsRoller(id=self._roller.id())
        elif isinstance(object, diceroller.DiceRollerDatabaseObject):
            parent = item.parent()
            parent.removeChild(item)

            group = parent.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
            group.removeRoller(object.id())

            del self._objectItemMap[object.id()]
            with gui.SignalBlocker(self._historyWidget):
                self._historyWidget.purgeHistory(roller=object)

            if self._roller:
                clearCurrent = object.id() == self._roller.id()

        if clearCurrent:
            self._setCurrentRoller(roller=None)

    def _managerTreeSelectionChanged(self) -> None:
        item = self._managerTree.currentItem()
        roller = None
        if item and item.parent():
            # It's a roller (rather than a group)
            roller = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        self._setCurrentRoller(roller=roller)

    def _managerTreeItemChanged(
            self,
            item: QtWidgets.QTreeWidgetItem,
            column: int
            ) -> None:
        object = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        typeText = None
        if isinstance(object, diceroller.DiceRollerGroupDatabaseObject):
            typeText = 'group'
        elif isinstance(object, diceroller.DiceRollerDatabaseObject):
            typeText = 'dice roller'
        else:
            return
        newName = item.text(0)
        if (not newName) or (newName == object.name()):
            return # Nothing to do
        object.setName(newName)

        try:
            objectdb.ObjectDbManager.instance().updateObject(
                object=object)
        except Exception as ex:
            message = f'Failed to update {typeText} {object.id()} in objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

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

        # Block signals from the manager tree as we want to manually
        # handle selection change
        with gui.SignalBlocker(self._managerTree):
            item = self._objectItemMap[roller.id()]
            self._syncManagerTreeRoller(
                roller=roller,
                rollerItem=item,
                makeSelected=True)

        self._setCurrentRoller(
            roller=roller,
            results=results)

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
