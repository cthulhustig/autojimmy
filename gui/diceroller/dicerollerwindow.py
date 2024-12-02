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
    <html>
    <p></p>
    </html>
""".format(name=app.AppName)


# TODO: Test that history timestamps are shown in local time not utc
# TODO: Switch to explicit saving rather than live saving
# - Would be good to make it optional
# - Should only be changes to the roller config, renaming and changing
#   ordering should still be saved live
#   - Doing this will require changes so the config widget is NOT using
#     the same instance of the roller that is held by the tree widget,
#     otherwise the updated config will be "saved" if the roller (or its
#     group is renamed). This has a downside however as any changes to the
#     roller held by the tree (e.g. renames or changes to the parent from moving
#     it to a different group) won't automatically be reflected in the
#     instance held by the config widget. It's not as simple as just giving
#     the config widget a new copy of the roller when ever the copy in the
#     tree changes as that would nuke any unsaved changes made by the config
#     widget.
# - Would need a way to indicate unsaved rollers in the tree
# - Would need a save button added to the toolbar
# - Would need a revert button added to the toolbar
# - Would need prompt to save anything modified when closing the window
# - I think this needs a refactor
#   - Update the window to be the thing that loads the list of groups at
#     startup and maintains it. Conceptually this copy should mirror what
#     is currently saved.
#   - Tree widget is passed the list groups to display (in sorted order) but
#     rather than holding groups/rollers in the user data it just holds the
#     object id
#   - Move the stuff that stores the order of groups between sessions into
#     the window. It should pass the list to the tree in the order it should
#     be listed.
#   - Update tree widget so it sends an explicit renamed event when an object
#     is renamed by double clicking on the item in the tree.
#     - Event sends the id of the renamed object
#     - Window listens for event and updates the name on the object in its
#       cache then writes it to the database.
#     - IMPORTANT: If the renamed object is the roller being edited the window
#       will also need to set the new name on the instance of the roller held
#       by the config widget
#   - Update tree widget so it sends an explicit objects moved event when
#     objects are dragged and dropped (groups or rollers)
#     - I'm not sure what if any parameters make sense for this event
#     - Main window would listen for the event and retrieve the new
#       order of things from the tree widget and compare it with it's cached
#       copy of the objects to work out the new state. At which point it will
#       update it's cached copy of the objects and update the database (or
#       ini file if group order has changed)
#       - This will probably be very similar to what the tree currently does
#         in _handleMovedRollers (I think it's basically moving that code
#     - IMPORTANT: If the roller currently being edited was moved then the
#       window will need to update the parent of the instance held by the
#       config widget.
#       - VERY IMPORTANT: Remember the parent of the roller will actually
#         be the id of a list object rather than the group so i'll need to
#         copy the parent id from the roller in the windows cache rather
#         than just taking the id from the group

# - IDEA: I think this could be simplified if I update the management tree
#   to deal with object ids rather than holding instances of the object.
#   - Would need the event used to notify of rename and position move split
#     into separate events that would notify the main window
#     - Rename would read the new name back from the tree, read
# - IDEA: It might be easier if I split the roller config out of the main
#   roller and into its own db object. With the result being the roller
#   becomes just a name and single mandatory config
#
# TODO: This trigger might be useful to prevent loops being created in the
# hierarchy table
"""
CREATE TRIGGER prevent_loop
BEFORE INSERT ON hierarchyTable
BEGIN
    -- Check if the new relationship creates a loop
    WITH RECURSIVE check_cte(id, child) AS (
        SELECT NEW.id, NEW.child
        UNION ALL
        SELECT h.id, h.child
        FROM hierarchyTable h
        JOIN check_cte cte ON h.child = cte.id
    )
    SELECT RAISE(ABORT, 'Loop detected')
    WHERE EXISTS (SELECT 1 FROM check_cte WHERE child = NEW.id);
END;
"""

class DiceRollerWindow(gui.WindowWidget):
    _MaxRollResults = 1000

    def __init__(self) -> None:
        super().__init__(
            title='Dice Roller',
            configSection='DiceRoller')

        self._rollInProgress = False
        self._objectMap: typing.Dict[
            str,
            typing.Union[
                diceroller.DiceRollerGroup,
                diceroller.DiceRoller
            ]] = {}
        self._rollerGroupMap: typing.Dict[str, str] = {}
        self._lastResults: typing.Dict[
            str,
            diceroller.DiceRollResult
            ] = {}

        self._randomGenerator = common.RandomGenerator()
        logging.info(f'Dice Roller random generator seed: {self._randomGenerator.seed()}')

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
        if not self._objectMap:
            self._createInitialGroup()

    def keyPressEvent(self, event: typing.Optional[QtGui.QKeyEvent]):
        if event:
            key = event.key()
            if self._rollInProgress:
                isSkipKey  = key == QtCore.Qt.Key.Key_Space or \
                    key == QtCore.Qt.Key.Key_Escape or \
                    key == QtCore.Qt.Key.Key_Return
                if isSkipKey:
                    self._resultsWidget.skipAnimation()
                    event.accept()
                    return
            else:
                isRollKey = key == QtCore.Qt.Key.Key_Return
                if isRollKey:
                    self._rollDice()
                    event.accept()
                    return

        return super().keyPressEvent(event)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        super().firstShowEvent(e)

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
            self._rollerTree.restoreState(storedValue)

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
        self._settings.setValue('ManagerState', self._rollerTree.saveState())
        self._settings.setValue('ResultsState', self._resultsWidget.saveState())
        self._settings.setValue('HistoryState', self._historyWidget.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _createRollerManagerControls(self) -> None:
        self._rollerTree = gui.DiceRollerTree()
        self._rollerTree.currentObjectChanged.connect(
            self._rollerTreeCurrentObjectChanged)
        self._rollerTree.objectRenamed.connect(
            self._rollerTreeObjectRenamed)
        self._rollerTree.orderChanged.connect(
            self._rollerTreeOrderChanged)

        self._rollerToolbar = QtWidgets.QToolBar('Toolbar')
        self._rollerToolbar.setIconSize(QtCore.QSize(32, 32))
        self._rollerToolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        self._rollerToolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        self._newRollerAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.NewGrid), 'New Roller', self)
        self._newRollerAction.triggered.connect(self._createNewRoller)
        self._rollerTree.addAction(self._newRollerAction)
        self._rollerToolbar.addAction(self._newRollerAction)

        self._newGroupAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.NewList), 'New Group', self)
        self._newGroupAction.triggered.connect(self._createNewGroup)
        self._rollerTree.addAction(self._newGroupAction)
        self._rollerToolbar.addAction(self._newGroupAction)

        self._renameAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.RenameFile), 'Rename...', self)
        self._renameAction.triggered.connect(self._renameObject)
        self._rollerTree.addAction(self._renameAction)
        self._rollerToolbar.addAction(self._renameAction)

        self._copyAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.CopyFile), 'Copy...', self)
        self._copyAction.triggered.connect(self._copyObject)
        self._rollerTree.addAction(self._copyAction)
        self._rollerToolbar.addAction(self._copyAction)

        self._deleteAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DeleteFile), 'Delete...', self)
        self._deleteAction.triggered.connect(self._deleteObjects)
        self._rollerTree.addAction(self._deleteAction)
        self._rollerToolbar.addAction(self._deleteAction)

        self._importAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.ImportFile), 'Import...', self)
        self._importAction.triggered.connect(self._importObjects)
        self._rollerTree.addAction(self._importAction)
        self._rollerToolbar.addAction(self._importAction)

        self._exportAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.ExportFile), 'Export...', self)
        self._exportAction.triggered.connect(self._exportObjects)
        self._rollerTree.addAction(self._exportAction)
        self._rollerToolbar.addAction(self._exportAction)

        self._rollerTree.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)

        groupLayout = QtWidgets.QHBoxLayout()
        groupLayout.setContentsMargins(0, 0, 0, 0)
        groupLayout.addWidget(self._rollerToolbar)
        groupLayout.addWidget(self._rollerTree)

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
        self._resultsWidget.rollComplete.connect(self._virtualRollComplete)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._resultsWidget)

        self._resultsGroupBox = QtWidgets.QGroupBox('Roll')
        self._resultsGroupBox.setLayout(groupLayout)

    def _createRollHistoryControls(self) -> None:
        self._historyWidget = gui.DiceRollHistoryWidget()

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._historyWidget)

        self._historyGroupBox = QtWidgets.QGroupBox('History')
        self._historyGroupBox.setLayout(groupLayout)

    def _rollDice(self) -> None:
        roller = self._currentRoller()
        if not roller or self._rollInProgress:
            return

        group = self._groupFromRoller(roller)
        if not group:
            message = 'Failed to find group for dice roller'
            logging.error(message)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message)
            return

        results = diceroller.rollDice(
            label=f'{group.name()} - {roller.name()}',
            roller=roller,
            seed=self._randomGenerator.randbits(128))

        self._rollInProgress = True
        self._updateControlEnablement()

        self._setCurrentResults(
            results=results,
            animate=True)

    def _syncToDatabase(
            self,
            currentId: typing.Optional[str] = None # None means no change (not explicitly set to None)
            ) -> None:
        try:
            groups = objectdb.ObjectDbManager.instance().readObjects(
                classType=diceroller.DiceRollerGroup)
        except Exception as ex:
            logging.error('Failed to sync manager to database', exc_info=ex)
            # Continue to sync the UI
            groups = []

        self._objectMap.clear()
        self._rollerGroupMap.clear()
        for group in groups:
            assert(isinstance(group, diceroller.DiceRollerGroup))
            self._objectMap[group.id()] = group
            for roller in group.rollers():
                self._objectMap[roller.id()] = roller
                self._rollerGroupMap[roller.id()] = group.id()

        with gui.SignalBlocker(self._rollerTree):
            self._rollerTree.setGroups(groups)
            if currentId != None:
                self._rollerTree.setCurrentObject(objectId=currentId)
        rollerId = self._rollerTree.currentRoller()
        roller = None
        if rollerId:
            roller = self._objectMap.get(rollerId)
        self._setCurrentRoller(roller=roller)

    def _setCurrentRoller(
            self,
            roller: typing.Optional[diceroller.DiceRoller],
            results: typing.Optional[diceroller.DiceRollResult] = None
            ) -> None:
        if roller and not results:
            results = self._lastResults.get(roller.id())

        if roller:
            with gui.SignalBlocker(self._rollerTree):
                self._rollerTree.setCurrentObject(objectId=roller.id())

        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(roller=roller)

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setRoller(roller=roller)
            if results:
                self._setCurrentResults(
                    results=results,
                    animate=False)

        self._rollInProgress = False

        self._updateControlEnablement()

    def _setCurrentResults(
            self,
            results: typing.Optional[diceroller.DiceRollResult],
            animate: bool = False
            ) -> None:
        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setResults(
                results=results,
                animate=animate)

    def _yieldGroups(self) -> typing.Generator[diceroller.DiceRollerGroup, None, None]:
        for object in self._objectMap.values():
            if isinstance(object, diceroller.DiceRollerGroup):
                yield object

    def _yieldRollers(self) -> typing.Generator[diceroller.DiceRoller, None, None]:
        for object in self._objectMap.values():
            if isinstance(object, diceroller.DiceRoller):
                yield object

    def _yieldSelectedObjects(self) -> typing.Generator[
            typing.Union[diceroller.DiceRollerGroup, diceroller.DiceRoller],
            None,
            None
            ]:
        seenIds = set()
        for objectId in self._rollerTree.selectedObjects():
            object = self._objectMap.get(objectId)
            if object:
                seenIds.add(objectId)
                yield object
        # Due to the way selection in the tree widget it's possible for the
        # current item to be set but not part of the selection. For example
        # if you delete an item one of the remaining items will become the
        # current item but it won't be selected. When in this state the item
        # has a fainter highlight but it is highlighted. From the point of
        # view of the item is considered selected when in this state so this
        # code yields the current object if it's set and hasn't already been
        # yielded
        currentId = self._rollerTree.currentObject()
        if currentId and currentId not in seenIds:
            currentObject = self._objectMap.get(currentId)
            if currentObject:
                yield currentObject

    def _currentObject(self) -> typing.Optional[typing.Union[diceroller.DiceRoller, diceroller.DiceRollerGroup]]:
        return self._objectMap.get(self._rollerTree.currentObject())

    def _currentGroup(self) -> typing.Optional[diceroller.DiceRollerGroup]:
        currentObject = self._currentObject()
        if not currentObject:
            return None
        if isinstance(currentObject, diceroller.DiceRollerGroup):
            return currentObject
        assert(isinstance(currentObject, diceroller.DiceRoller))
        return self._groupFromRoller(roller=currentObject)

    def _currentRoller(self) -> typing.Optional[diceroller.DiceRoller]:
        currentObject = self._currentObject()
        if isinstance(currentObject, diceroller.DiceRoller):
            return currentObject
        return None

    def _objectFromId(
            self,
            objectId: str
            ) -> typing.Optional[typing.Union[diceroller.DiceRoller, diceroller.DiceRollerGroup]]:
        return self._objectMap.get(objectId)

    def _groupFromRoller(
            self,
            roller: diceroller.DiceRoller
            ) -> typing.Optional[diceroller.DiceRollerGroup]:
        groupId = self._rollerGroupMap.get(roller.id())
        if not groupId:
            return None
        return self._objectMap.get(groupId)

    def _currentResults(self) -> typing.Optional[diceroller.DiceRollResult]:
        return self._resultsWidget.results()

    def _updateControlEnablement(self) -> None:
        currentObject = self._currentObject()
        hasSelection = currentObject != None
        self._renameAction.setEnabled(hasSelection)
        self._deleteAction.setEnabled(hasSelection)

        hasCurrentRoller = isinstance(currentObject, diceroller.DiceRoller)
        self._managerGroupBox.setEnabled(not self._rollInProgress)
        self._configGroupBox.setEnabled(hasCurrentRoller and not self._rollInProgress)
        self._historyGroupBox.setEnabled(not self._rollInProgress)

    def _generateGroupName(self) -> str:
        groupNames = set([group.name() for group in self._yieldGroups()])
        return DiceRollerWindow._generateNewName(
            baseName='New Group',
            currentNames=groupNames)

    def _generateRollerName(self, group: diceroller.DiceRollerGroup) -> str:
        rollerNames = set([roller.name() for roller in group.rollers()])
        return DiceRollerWindow._generateNewName(
            baseName='New Roller',
            currentNames=rollerNames)

    def _createInitialGroup(self) -> None:
        group = diceroller.DiceRollerGroup(
            name=self._generateGroupName())
        roller = diceroller.DiceRoller(
            name=self._generateRollerName(group=group),
            dieCount=1,
            dieType=common.DieType.D6)
        group.addRoller(roller)

        try:
            objectdb.ObjectDbManager.instance().createObject(
                object=group)
        except Exception as ex:
            message = 'Failed to add initial group to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase(currentId=roller.id())

    def _createNewRoller(self) -> None:
        group = self._currentGroup()
        isNewGroup = not group
        if isNewGroup:
            group = diceroller.DiceRollerGroup(
                name=self._generateGroupName())
        else:
            group = copy.deepcopy(group)

        roller = diceroller.DiceRoller(
            name=self._generateRollerName(group=group),
            dieCount=1,
            dieType=common.DieType.D6)
        group.addRoller(roller=roller)

        try:
            if isNewGroup:
                objectdb.ObjectDbManager.instance().createObject(
                    object=group)
            else:
                objectdb.ObjectDbManager.instance().updateObject(
                    object=group)
        except Exception as ex:
            message = 'Failed to write updated group to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase(currentId=roller.id())
        self._rollerTree.editObjectName(objectId=roller.id())

    def _createNewGroup(self) -> None:
        group = diceroller.DiceRollerGroup(
            name=self._generateGroupName())

        try:
            objectdb.ObjectDbManager.instance().createObject(
                object=group)
        except Exception as ex:
            message = 'Failed to add new group to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase(currentId=group.id())
        self._rollerTree.editObjectName(objectId=group.id())

    def _renameObject(self) -> None:
        currentObject = self._currentObject()
        if isinstance(currentObject, diceroller.DiceRollerGroup):
            title = 'Group Name'
            typeString = 'group'
        elif isinstance(currentObject, diceroller.DiceRoller):
            title = 'Dice Roller Name'
            typeString = 'dice roller'
        else:
            return

        oldName = currentObject.name()
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

        currentObject = copy.deepcopy(currentObject)
        currentObject.setName(name=newName)

        try:
            objectdb.ObjectDbManager.instance().updateObject(
                object=currentObject)
        except Exception as ex:
            message = 'Failed to write updated object to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase(currentId=currentObject.id())

    def _copyObject(self) -> None:
        currentObject = self._currentObject()
        group = None
        roller = None
        if isinstance(currentObject, diceroller.DiceRollerGroup):
            # Make a copy of the group and all its rollers
            group = currentObject.copyConfig()
        elif isinstance(currentObject, diceroller.DiceRoller):
            # Make a copy of the current roller within its current group
            group = self._groupFromRoller(currentObject)
            group = copy.deepcopy(group)
            roller = currentObject.copyConfig()
            group.addRoller(roller)
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
            message = 'Failed to write copied object to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase(
            currentId=roller.id() if roller else group.id())

    def _deleteObjects(self) -> None:
        groups: typing.List[diceroller.DiceRollerGroup] = []
        rollers: typing.List[diceroller.DiceRoller] = []
        for object in self._yieldSelectedObjects():
            if isinstance(object, diceroller.DiceRollerGroup):
                groups.append(object)
            elif isinstance(object, diceroller.DiceRoller):
                rollers.append(object)

        confirmation = None
        if len(groups) == 0:
            if len(rollers) == 1:
                roller = rollers[0]
                assert(isinstance(roller, diceroller.DiceRoller))
                confirmation = 'Are you sure you want to delete dice roller {name}?'.format(
                    name=roller.name())
            else:
                confirmation = 'Are you sure you want to delete {count} dice rollers?'.format(
                    count=len(rollers))
        if len(rollers) == 0:
            if len(groups) == 1:
                group = groups[0]
                assert(isinstance(group, diceroller.DiceRollerGroup))
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
            message = 'Failed to delete objects from objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase()

        for roller in rollers:
            if roller.id() in self._lastResults:
                del self._lastResults[roller.id()]

        for group in groups:
            for roller in group.rollers():
                if roller.id() in self._lastResults:
                    del self._lastResults[roller.id()]

    def _importObjects(self) -> None:
        path, _ = gui.FileDialogEx.getOpenFileName(
            parent=self,
            caption='Import Dice Rollers',
            filter=f'{gui.JSONFileFilter};;{gui.AllFileFilter}',
            lastDirKey='DiceRollerWindowImportExportDir')
        if not path:
            return None # User cancelled

        try:
            with open(path, 'r', encoding='UTF8') as file:
                data = file.read()
            groups = diceroller.deserialiseGroups(
                serialData=data)
        except Exception as ex:
            message = f'Failed to read \'{path}\''
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        try:
            with objectdb.ObjectDbManager.instance().createTransaction() as transaction:
                for group in groups:
                    objectdb.ObjectDbManager.instance().createObject(
                        object=group,
                        transaction=transaction)
        except Exception as ex:
            message = 'Failed to import imported groups into objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase()

    def _exportObjects(self) -> None:
        path, _ = gui.FileDialogEx.getSaveFileName(
            parent=self,
            caption='Export Dice Rollers',
            filter=f'{gui.JSONFileFilter};;{gui.AllFileFilter}',
            lastDirKey='DiceRollerWindowImportExportDir',
            defaultFileName='rollers.json')
        if not path:
            return # User cancelled

        exportGroups: typing.Dict[str, diceroller.DiceRollerGroup] = {}
        try:
            selectedObjects = list(self._yieldSelectedObjects())
            explicitGroupIds = set()
            for object in selectedObjects:
                if isinstance(object, diceroller.DiceRollerGroup):
                    explicitGroupIds.add(object.id())

            for object in selectedObjects:
                if isinstance(object, diceroller.DiceRollerGroup):
                    exportGroups[object.id()] = object.copyConfig(copyIds=True)
                elif isinstance(object, diceroller.DiceRoller):
                    group = self._groupFromRoller(roller=object)
                    if group.id() in explicitGroupIds:
                        # Group is already being exported so no need to export
                        # individual roller
                        continue
                    if group.id() in exportGroups:
                        group = exportGroups[group.id()]
                    else:
                        group = group.copyConfig(copyIds=True)
                        group.clearRollers()
                        exportGroups[group.id()] = group
                    group.addRoller(object.copyConfig(copyIds=True))
        except Exception as ex:
            message = 'Failed to clone objects for export'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        try:
            data = diceroller.serialiseGroups(
                groups=exportGroups.values())

            with open(path, 'w', encoding='UTF8') as file:
                file.write(data)
        except Exception as ex:
            message = f'Failed to write \'{path}\''
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

    def _rollerTreeCurrentObjectChanged(
            self,
            objectId: typing.Optional[str]
            ) -> None:
        currentObject = self._objectFromId(objectId)
        currentRoller = None
        if isinstance(currentObject, diceroller.DiceRoller):
            currentRoller = currentObject
        self._setCurrentRoller(roller=currentRoller)

    def _rollerTreeObjectRenamed(
            self,
            objectId: str,
            newName: str
            ) -> None:
        renamedObject = self._objectFromId(objectId=objectId)
        if not renamedObject:
            # TODO: Handle this
            return

        renamedObject = copy.deepcopy(renamedObject)
        renamedObject.setName(name=newName)

        try:
            objectdb.ObjectDbManager.instance().updateObject(
                object=renamedObject)
        except Exception as ex:
            message = 'Failed to write renamed object to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase(currentId=renamedObject.id())

    def _rollerTreeOrderChanged(self) -> None:
        updatedGroups: typing.List[diceroller.DiceRollerGroup] = []
        for groupId in self._rollerTree.groups():
            oldGroup = self._objectFromId(objectId=groupId)
            assert(isinstance(oldGroup, diceroller.DiceRollerGroup))
            newGroup = copy.deepcopy(oldGroup)
            newGroup.clearRollers()

            for rollerId in self._rollerTree.rollers(groupId=groupId):
                oldRoller = self._objectFromId(objectId=rollerId)
                assert(isinstance(oldRoller, diceroller.DiceRoller))
                newRoller = copy.deepcopy(oldRoller)
                newGroup.addRoller(newRoller)

            oldGroup = self._objectFromId(newGroup.id())
            if newGroup != oldGroup:
                updatedGroups.append(newGroup)

        if not updatedGroups:
            return # Nothing to do

        try:
            with objectdb.ObjectDbManager.instance().createTransaction() as transaction:
                # Delete objects first to avoid foreign key errors if objects are
                # being moved from one parent to anther
                for group in updatedGroups:
                    objectdb.ObjectDbManager.instance().deleteObject(
                        id=group.id(),
                        transaction=transaction)
                for group in updatedGroups:
                    objectdb.ObjectDbManager.instance().createObject(
                        object=group,
                        transaction=transaction)
        except Exception as ex:
            message = 'Failed to write repositioned objects to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Fall through to sync to database in order to revert ui to a
            # consistent state

        self._syncToDatabase()

    def _rollerConfigChanged(self) -> None:
        roller = self._currentRoller()
        if not roller:
            return

        try:
            objectdb.ObjectDbManager.instance().updateObject(
                object=roller)
        except Exception as ex:
            message = 'Failed to write updated roller to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            # Continue, may as well sync results even if it
            # couldn't be written

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.syncToRoller()

    def _virtualRollComplete(self) -> None:
        # NOTE: Handling of the roll completion is delayed to allow the event
        # loop to process. This notification may have been triggered by the user
        # skipping the roll animation. If that is the case then we want the
        # event loop to process so that the animation control can redraw so the
        # roll result is displayed. If we were to handle the roll completion
        # immediately, the animation would freeze in place for a noticeable
        # amount of time (a few 100 ms) before the results were displayed.
        QtCore.QTimer.singleShot(1, self._delayedRollComplete)

    def _delayedRollComplete(self) -> None:
        roller = self._currentRoller()
        results = self._currentResults()
        if not roller or not results or not self._rollInProgress:
            return

        self._rollInProgress = False
        self._lastResults[roller.id()] = results
        self._updateControlEnablement()

        try:
            objectdb.ObjectDbManager.instance().createObject(
                object=results)
        except Exception as ex:
            message = 'Failed to add roll results to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)

        # Enforce a max number of historic results
        self._purgeHistory()

    def _purgeHistory(self) -> None:
        try:
            results = list(self._historyWidget.results())
            if len(results) <= DiceRollerWindow._MaxRollResults:
                return

            results.sort(
                key=lambda result: result.timestamp(),
                reverse=True)
            results = results[DiceRollerWindow._MaxRollResults:]
            with objectdb.ObjectDbManager.instance().createTransaction() as transaction:
                for result in results:
                    objectdb.ObjectDbManager.instance().deleteObject(
                        id=result.id(),
                        transaction=transaction)
        except Exception as ex:
            message = 'Failed to purge old history from objectdb'
            logging.error(message, exc_info=ex)

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='DiceRollerWelcome')
        message.exec()

    @staticmethod
    def _generateNewName(
            baseName: str,
            currentNames: typing.Iterable[str]
            ) -> str:
        index = 1
        while True:
            newName = baseName if index < 2 else f'{baseName} {index}'
            if newName not in currentNames:
                return newName
            index += 1
