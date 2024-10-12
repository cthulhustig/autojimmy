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

# TODO: Need to be able to duplicate rollers (and maybe groups)
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
        self._syncToManager()
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
            self._managementTreeSelectionChanged)

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

    def _syncToManager(self) -> None:
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

        self._objectItemMap.clear()
        with gui.SignalBlocker(self._managerTree):
            for groupIndex, group in enumerate(groups):
                assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
                groupItem = self._managerTree.topLevelItem(groupIndex)
                if not groupItem:
                    groupItem = DiceRollerWindow._createGroupItem(group=group)
                    self._managerTree.addTopLevelItem(groupItem)
                    self._objectItemMap[group.id()] = groupItem
                for rollerIndex, roller in enumerate(group.rollers()):
                    rollerItem = groupItem.child(rollerIndex)
                    if not rollerItem:
                        rollerItem = DiceRollerWindow._createRollerItem(
                            roller=roller,
                            groupItem=groupItem)
                        self._objectItemMap[roller.id()] = rollerItem

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

    # NOTE: When a new roller is selected the current results are intentionally
    # not cleared. This is done to make it easier for the user to add the effect
    # from the previous roll to the modifiers of the next roll. The exception to
    # this is the highlight of the rolled result on the probability graph as the
    # result of the previous roll is irrelevant to the the probability of the
    # next roll
    def _setCurrentRoller(
            self,
            roller: typing.Optional[diceroller.DiceRollerDatabaseObject]
            ) -> None:
        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(roller=roller)

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setRoller(roller=roller)

        with gui.SignalBlocker(self._historyWidget):
            self._historyWidget.setRoller(roller=roller)

        self._roller = roller
        self._results = None
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

        rollerItem = DiceRollerWindow._createRollerItem(
            roller=roller,
            groupItem=item)
        rollerItem.setSelected(True)
        self._managerTree.setCurrentItem(rollerItem)
        self._objectItemMap[roller.id()] = rollerItem

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

        groupItem = DiceRollerWindow._createGroupItem(group=group)
        self._managerTree.addTopLevelItem(groupItem)

        rollerItem = DiceRollerWindow._createRollerItem(
            roller=roller,
            groupItem=groupItem)

        # It looks like you have to expand after the item has been
        # added to the control
        groupItem.setExpanded(True)
        rollerItem.setSelected(True)
        self._managerTree.setCurrentItem(rollerItem)
        self._objectItemMap[group.id()] = groupItem
        self._objectItemMap[roller.id()] = rollerItem

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

        object = copy.deepcopy(object)
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

        item.setData(0, QtCore.Qt.ItemDataRole.DisplayRole, newName)
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, object)

        if isinstance(object, diceroller.DiceRollerDatabaseObject):
            self._setCurrentRoller(roller=object)

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
            for roller in object.rollers():
                del self._objectItemMap[roller.id()]

            if self._roller:
                clearCurrent = object.containsRoller(id=self._roller.id())
        elif isinstance(object, diceroller.DiceRollerDatabaseObject):
            parent = item.parent()
            parent.removeChild(item)

            group = parent.data(0, QtCore.Qt.ItemDataRole.UserRole)
            assert(isinstance(group, diceroller.DiceRollerGroupDatabaseObject))
            group.removeRoller(object.id())

            del self._objectItemMap[object.id()]

            if self._roller:
                clearCurrent = object.id() == self._roller.id()

        if clearCurrent:
            self._setCurrentRoller(roller=None)
            with gui.SignalBlocker(self._historyWidget):
                self._historyWidget.purgeHistory(roller=object)

    def _managementTreeSelectionChanged(self) -> None:
        item = self._managerTree.currentItem()
        roller = None
        if item and item.parent():
            # It's a roller (rather than a group)
            roller = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        self._setCurrentRoller(roller=roller)

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

        with gui.SignalBlocker(self._managerTree):
            item = self._objectItemMap[roller.id()]
            item.setData(0, QtCore.Qt.ItemDataRole.DisplayRole, roller.name())
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, roller)
            self._managerTree.clearSelection()
            item.setSelected(True)

        self._setCurrentRoller(roller=roller)

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setResults(
                results=results,
                animate=False)

        self._results = results

    def _virtualRollComplete(self) -> None:
        if not self._rollInProgress:
            return

        self._rollInProgress = False
        self._updateControlEnablement()

        with gui.SignalBlocker(self._historyWidget):
            self._historyWidget.addResult(self._results)

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='DiceRollerWelcome')
        message.exec()

    @staticmethod
    def _createGroupItem(
            group: diceroller.DiceRollerGroupDatabaseObject
            ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([group.name()])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, group)
        return item

    @staticmethod
    def _createRollerItem(
            roller: diceroller.DiceRollerDatabaseObject,
            groupItem: QtWidgets.QTreeWidgetItem,
            ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([roller.name()])
        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, roller)
        if groupItem:
            groupItem.addChild(item)
        return item
