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
        self._managerTree = gui.DiceRollerManagerTree()
        self._managerTree.currentObjectChanged.connect(
            self._managerTreeCurrentObjectChanged)
        self._managerTree.objectsChanged.connect(
            self._managerTreeObjectsChanged)

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

    def _syncToDatabase(
            self,
            currentId: typing.Optional[str] = None # None means no change (not explicitly set to None)
            ) -> None:
        try:
            with gui.SignalBlocker(self._managerTree):
                self._managerTree.syncToDatabase()
                if currentId is not None:
                    self._managerTree.setCurrentObject(object=currentId)
            self._setCurrentRoller(
                roller=self._managerTree.currentRoller())
        except Exception as ex:
            logging.error('Failed to sync UI to database', exc_info=ex)

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

        self._syncToDatabase(currentId=roller.id())

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

        self._syncToDatabase(currentId=roller.id())

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
        while True:
            newName, result = gui.InputDialogEx.getText(
                parent=self,
                title=title,
                label=f'Enter a name for the {typeString}',
                text=oldName)
            if not result:
                return
            if newName:
                break
            gui.MessageBoxEx.critical(
                parent=self,
                text='Name can\'t be empty')

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

        self._syncToDatabase(
            currentId=roller.id() if roller else group.id())

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

    def _managerTreeCurrentObjectChanged(self) -> None:
        self._setCurrentRoller(
            roller=self._managerTree.currentRoller())

    def _managerTreeObjectsChanged(
            self,
            createdObjects: typing.Iterable[typing.Union[
                diceroller.DiceRollerGroupDatabaseObject,
                diceroller.DiceRollerDatabaseObject]],
            updatedObjects: typing.Iterable[typing.Union[
                diceroller.DiceRollerGroupDatabaseObject,
                diceroller.DiceRollerDatabaseObject]],
            deletedObjects: typing.Iterable[typing.Union[
                diceroller.DiceRollerGroupDatabaseObject,
                diceroller.DiceRollerDatabaseObject]]
            ) -> None:
        try:
            with objectdb.ObjectDbManager.instance().createTransaction() as transaction:
                # Delete objects first to avoid foreign key errors if objects are
                # being moved from one parent to anther
                for object in deletedObjects:
                    objectdb.ObjectDbManager.instance().deleteObject(
                        id=object.id(),
                        transaction=transaction)
                for object in createdObjects:
                    objectdb.ObjectDbManager.instance().createObject(
                        object=object,
                        transaction=transaction)
                for object in updatedObjects:
                    objectdb.ObjectDbManager.instance().updateObject(
                        object=object,
                        transaction=transaction)
        except Exception as ex:
            message = 'Failed to write modified objects to objectdb'
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
