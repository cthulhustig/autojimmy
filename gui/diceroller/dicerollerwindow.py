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


# TODO: The current behaviour if there is an error in the database isn't great
# - If there is any error with one object it doesn't read anything
# - It should probably try to load as much as possible and return any errors
#   along with what it could load
#   - Might make sense to have this behaviour as optional
# TODO: Get rid of separate group/roller add buttons and have a single button
#   with the document icon (or maybe a plus icon)
# - Switch to having one of those buttons with an arrow to get multiple options
# - By default clicking the button should add a roller
#   - This will already causes a group to be added if there is none
# - There should be menu options for add group and add roller
# TODO: Test that history timestamps are shown in local time not utc
# TODO: Switch to explicit saving rather than live saving
# - Would need a revert button added to the toolbar
# - Would need prompt to save anything modified when closing the window
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
        self._editRollers: typing.Dict[
            str,
            diceroller.DiceRoller
            ] = {}
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

        try:
            groups = objectdb.ObjectDbManager.instance().readObjects(
                classType=diceroller.DiceRollerGroup)
        except Exception as ex:
            # TODO: Not sure what to do here, possibly just let the exception pass up
            logging.error('Failed to sync manager to database', exc_info=ex)

        self._rollerTree.setContents(groups)
        if not self._rollerTree.groupCount():
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
                # Handle using return to roll the dice here rather than a
                # shortcut on the roll button. If a shortcut is used, when you
                # do an inline rename of a roller in the tree, hitting return to
                # finish the rename also causes the dice to be rolled
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

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='AutosaveState',
            type=QtCore.QByteArray)
        if storedValue:
            self._autoSaveAction.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('HorzSplitterState', self._horizontalSplitter.saveState())
        self._settings.setValue('VertSplitterState', self._verticalSplitter.saveState())
        self._settings.setValue('ManagerState', self._rollerTree.saveState())
        self._settings.setValue('ResultsState', self._resultsWidget.saveState())
        self._settings.setValue('HistoryState', self._historyWidget.saveState())
        self._settings.setValue('AutosaveState', self._autoSaveAction.saveState())

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

        # TODO: I should probably have a save keyboard short cut but it should
        # only save the current config not all the selected ones
        self._saveAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.SaveFile), 'Save...', self)
        self._saveAction.triggered.connect(self._saveSelectedRollers)
        self._rollerTree.addAction(self._saveAction)
        self._rollerToolbar.addAction(self._saveAction)

        self._renameAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.RenameFile), 'Rename...', self)
        self._renameAction.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_F2))
        self._renameAction.triggered.connect(self._renameCurrentObject)
        self._rollerTree.addAction(self._renameAction)
        self._rollerToolbar.addAction(self._renameAction)

        self._revertAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.Reload), 'Revert...', self)
        self._revertAction.triggered.connect(self._revertSelectedRollers)
        self._rollerTree.addAction(self._revertAction)
        self._rollerToolbar.addAction(self._revertAction)

        self._copyAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.CopyFile), 'Copy...', self)
        self._copyAction.triggered.connect(self._copyCurrentObject)
        self._rollerTree.addAction(self._copyAction)
        self._rollerToolbar.addAction(self._copyAction)

        self._deleteAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DeleteFile), 'Delete...', self)
        self._deleteAction.triggered.connect(self._deleteSelectedObjects)
        self._deleteAction.setShortcut(QtGui.QKeySequence.StandardKey.Delete)
        self._rollerTree.addAction(self._deleteAction)
        self._rollerToolbar.addAction(self._deleteAction)

        self._importAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.ImportFile), 'Import...', self)
        self._importAction.triggered.connect(self._importObjects)
        self._rollerTree.addAction(self._importAction)
        self._rollerToolbar.addAction(self._importAction)

        self._exportAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.ExportFile), 'Export...', self)
        self._exportAction.triggered.connect(self._exportSelectedObjects)
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

        self._autoSaveAction = gui.ActionEx('Autosave', self)
        self._autoSaveAction.setCheckable(True)
        self._autoSaveAction.setChecked(False) # Works like construction windows by default
        self._autoSaveAction.triggered.connect(self._autoSaveToggled)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.setContentsMargins(0, 0, 0, 0)
        groupLayout.addWidget(self._rollerConfigWidget)
        groupLayout.addWidget(self._rollButton)

        self._configGroupBox = gui.GroupBoxEx('Configuration')
        self._configGroupBox.enableMenuButton(True)
        self._configGroupBox.addAction(self._autoSaveAction)
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
        # NOTE: Get the current EDIT roller from the config widget
        roller = self._rollerConfigWidget.roller()
        if not roller or self._rollInProgress:
            return

        group = self._rollerTree.groupFromRoller(roller=roller.id())
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


        # TODO: Remove hack
        """
        count = 1000
        for index in range(count):
            hackResult = diceroller.rollDice(
                label=f'HACK {index}',
                roller=roller,
                seed=self._randomGenerator.randbits(128))
            objectdb.ObjectDbManager.instance().createObject(
                object=hackResult)
        self._purgeHistory()
        """


        self._rollInProgress = True
        self._updateControlEnablement()

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setResults(
                results=results,
                animate=True)

    # NOTE: This intentionally uses an object id to avoid confusion over if
    # current or edit rollers are expected
    def _setCurrentObject(
            self,
            objectId: typing.Optional[str]
            ) -> None:
        with gui.SignalBlocker(self._rollerTree):
            self._rollerTree.setCurrentObject(objectId=objectId)

        currentRoller = self._rollerTree.currentRoller()
        editRoller = None
        results = None
        if currentRoller:
            editRoller = self._editRollers.get(currentRoller.id())
            if not editRoller:
                editRoller = copy.deepcopy(currentRoller)
                self._editRollers[currentRoller.id()] = editRoller

            results = self._lastResults.get(currentRoller.id())

        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(roller=editRoller)

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setRoller(roller=editRoller)
            if results:
                self._resultsWidget.setResults(
                    results=results,
                    animate=False)

        self._rollInProgress = False

        self._updateControlEnablement()

    def _selectedObjects(self) -> typing.Iterable[typing.Union[
            diceroller.DiceRoller,
            diceroller.DiceRollerGroup
            ]]:
        selection = []
        seen = set()
        for selected in self._rollerTree.selectedObjects():
            seen.add(selected.id())
            selection.append(selected)
        # Due to the way selection in the tree widget it's possible for the
        # current item to be set but not part of the selection. For example
        # if you delete an item one of the remaining items will become the
        # current item but it won't be selected. When in this state the item
        # has a fainter highlight but it is highlighted. From the point of
        # view of the item is considered selected when in this state so this
        # code yields the current object if it's set and hasn't already been
        # yielded
        current = self._rollerTree.currentObject()
        if current and current.id() not in seen:
            selection.append(current)

        return selection

    def _updateControlEnablement(self) -> None:
        currentObject = self._rollerTree.currentObject()
        hasSelection = currentObject != None
        hasCurrentRoller = isinstance(currentObject, diceroller.DiceRoller)
        hasModified = False
        for selectedObject in self._selectedObjects():
            if isinstance(selectedObject, diceroller.DiceRoller):
                hasModified = self._rollerTree.isRollerModified(rollerId=selectedObject.id())
            elif isinstance(selectedObject, diceroller.DiceRollerGroup):
                hasModified = any(self._rollerTree.isRollerModified(rollerId=roller.id()) for roller in selectedObject.rollers())
            if hasModified:
                break

        self._renameAction.setEnabled(hasSelection)
        self._deleteAction.setEnabled(hasSelection)
        self._saveAction.setEnabled(hasModified)
        self._revertAction.setEnabled(hasModified)

        self._managerGroupBox.setEnabled(not self._rollInProgress)
        self._configGroupBox.setEnabled(hasCurrentRoller and not self._rollInProgress)
        self._historyGroupBox.setEnabled(not self._rollInProgress)

    def _generateGroupName(self) -> str:
        groupNames = set([group.name() for group in self._rollerTree.groups()])
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

        with gui.SignalBlocker(self._rollerTree):
            self._rollerTree.addGroup(group=group)

        self._setCurrentObject(objectId=roller.id())

    def _createNewRoller(self) -> None:
        group = self._rollerTree.currentGroup()
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

        with gui.SignalBlocker(self._rollerTree):
            if isNewGroup:
                self._rollerTree.addGroup(group=group)
            else:
                self._rollerTree.addRoller(
                    groupId=group.id(),
                    roller=roller)

        self._setCurrentObject(objectId=roller.id())
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

        with gui.SignalBlocker(self._rollerTree):
            self._rollerTree.addGroup(group=group)

        self._setCurrentObject(objectId=group.id())
        self._rollerTree.editObjectName(objectId=group.id())

    def _renameCurrentObject(self) -> None:
        currentObject = self._rollerTree.currentObject()
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

        with gui.SignalBlocker(self._rollerTree):
            self._rollerTree.renameObject(
                objectId=currentObject.id(),
                newName=newName)

        editRoller = self._editRollers.get(currentObject.id())
        if editRoller:
            editRoller.setName(newName)

        self._setCurrentObject(objectId=currentObject.id())

    def _copyCurrentObject(self) -> None:
        currentObject = self._rollerTree.currentObject()
        newGroup = None
        newRoller = None
        if isinstance(currentObject, diceroller.DiceRollerGroup):
            # Make a copy of the group and all its rollers. The generated objects
            # will have different ids to the source object it was copied from.
            newGroup = currentObject.copyConfig()

            # Iterate over the rollers of the ORIGINAL group and check if there
            # is an edit version. If there is it should be used in place of the
            # equivalent roller in the copy group.
            for index, srcRoller in enumerate(currentObject.rollers()):
                editRoller = self._editRollers.get(srcRoller.id())
                if editRoller:
                    editRoller = editRoller.copyConfig()
                    newGroup.replaceRoller(
                        index=index,
                        roller=editRoller)
        elif isinstance(currentObject, diceroller.DiceRoller):
            # Make a hierarchical copy of the group the source roller is in. The
            # objects in this hierarchy will have the same ids as the object
            # they were copied from
            newGroup = self._rollerTree.groupFromRoller(currentObject)
            newGroup = copy.deepcopy(newGroup)

            # If there is an edit version of the selected roller it should be used
            # as the source, if not just use the version retrieved from the tree
            # (this should be the same as what is currently in the db). The copy
            # made here will have a different id to the roller it was copied from
            editRoller = self._editRollers.get(currentObject.id())
            srcRoller = editRoller if editRoller else currentObject
            newRoller = srcRoller.copyConfig()
            newGroup.addRoller(newRoller)
        else:
            return

        try:
            if newRoller:
                objectdb.ObjectDbManager.instance().updateObject(
                    object=newGroup)
            else:
                objectdb.ObjectDbManager.instance().createObject(
                    object=newGroup)
        except Exception as ex:
            message = 'Failed to write copied object to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        with gui.SignalBlocker(self._rollerTree):
            if newRoller:
                self._rollerTree.addRoller(
                    groupId=newGroup.id(),
                    roller=newRoller)
            else:
                self._rollerTree.addGroup(group=newGroup)

        self._setCurrentObject(
            objectId=newRoller.id() if newRoller else newGroup.id())

    def _deleteSelectedObjects(self) -> None:
        groups: typing.List[diceroller.DiceRollerGroup] = []
        rollers: typing.List[diceroller.DiceRoller] = []
        for object in self._selectedObjects():
            if isinstance(object, diceroller.DiceRollerGroup):
                groups.append(object)
            elif isinstance(object, diceroller.DiceRoller):
                rollers.append(object)

        confirmation = None
        if len(groups) == 0:
            if len(rollers) == 1:
                roller = rollers[0]
                confirmation = 'Are you sure you want to delete dice roller {name}?'.format(
                    name=roller.name())
            else:
                confirmation = 'Are you sure you want to delete {count} dice rollers?'.format(
                    count=len(rollers))
        if len(rollers) == 0:
            if len(groups) == 1:
                group = groups[0]
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

        with gui.SignalBlocker(self._rollerTree):
            for roller in rollers:
                self._rollerTree.deleteObject(objectId=roller.id())
            for group in groups:
                self._rollerTree.deleteObject(objectId=group.id())

        for roller in rollers:
            if roller.id() in self._editRollers:
                del self._editRollers[roller.id()]

            if roller.id() in self._lastResults:
                del self._lastResults[roller.id()]

        for group in groups:
            for roller in group.rollers():
                if roller.id() in self._editRollers:
                    del self._editRollers[roller.id()]

                if roller.id() in self._lastResults:
                    del self._lastResults[roller.id()]

        currentObject = self._rollerTree.currentObject()
        self._setCurrentObject(objectId=currentObject.id() if currentObject else None)

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

        with gui.SignalBlocker(self._rollerTree):
            for group in groups:
                self._rollerTree.addGroup(group=group)

        currentObject = self._rollerTree.currentObject()
        self._setCurrentObject(objectId=currentObject.id() if currentObject else None)

    def _exportSelectedObjects(self) -> None:
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
            selectedObjects = list(self._selectedObjects())
            explicitGroups: typing.Set[str] = set()
            for object in selectedObjects:
                if isinstance(object, diceroller.DiceRollerGroup):
                    explicitGroups.add(object.id())

            for object in selectedObjects:
                if isinstance(object, diceroller.DiceRollerGroup):
                    group = copy.deepcopy(object)

                    # If is an edit version of any of the rollers in the group then
                    # they should be exported
                    for index, roller in enumerate(group.rollers()):
                        editRoller = self._editRollers.get(roller.id())
                        if editRoller:
                            editRoller = copy.deepcopy(editRoller)
                            group.replaceRoller(index, editRoller)

                    exportGroups[group.id()] = group
                elif isinstance(object, diceroller.DiceRoller):
                    group = self._rollerTree.groupFromRoller(object)
                    if group.id() in explicitGroups:
                        # Group is already being exported so no need to export
                        # individual roller
                        continue

                    # If there is an edit version of the roller then it should be
                    # exported
                    roller = self._editRollers.get(object.id())
                    roller = copy.deepcopy(roller if roller else object)

                    if group.id() in exportGroups:
                        group = exportGroups[group.id()]
                    else:
                        group = copy.deepcopy(group)
                        group.clearRollers()
                        exportGroups[group.id()] = group
                    group.addRoller(roller)
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

    def _saveSelectedRollers(self) -> None:
        self._saveRollers(objects=self._selectedObjects())

    def _saveAllRollers(self) -> None:
        modifiedRollers = self._rollerTree.modifiedRollers()
        if modifiedRollers:
            self._saveRollers(objects=modifiedRollers)

    def _saveRollers(
            self,
            objects: typing.Iterable[typing.Union[
                diceroller.DiceRoller,
                diceroller.DiceRollerGroup]]
            ) -> None:
        rollersToSave: typing.List[diceroller.DiceRoller] = []
        for object in objects:
            if isinstance(object, diceroller.DiceRoller):
                editRoller = self._editRollers.get(object.id())
                if editRoller:
                    rollersToSave.append(copy.deepcopy(editRoller))
            elif isinstance(object, diceroller.DiceRollerGroup):
                for roller in object.rollers():
                    editRoller = self._editRollers.get(roller.id())
                    if editRoller:
                        rollersToSave.append(copy.deepcopy(editRoller))

        if not rollersToSave:
            return

        try:
            with objectdb.ObjectDbManager.instance().createTransaction() as transaction:
                for roller in rollersToSave:
                    objectdb.ObjectDbManager.instance().updateObject(
                        object=roller,
                        transaction=transaction)
        except Exception as ex:
            message = 'Failed to save dice roller to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        with gui.SignalBlocker(self._rollerTree):
            for roller in rollersToSave:
                self._rollerTree.replaceRoller(
                    rollerId=roller.id(),
                    roller=roller)
                self._rollerTree.setRollerModified(
                    rollerId=roller.id(),
                    modified=False)

        self._updateControlEnablement()

    def _revertSelectedRollers(self) -> None:
        rollersToRevert: typing.List[diceroller.DiceRoller] = []
        for object in self._selectedObjects():
            if isinstance(object, diceroller.DiceRoller):
                if self._rollerTree.isRollerModified(rollerId=object.id()):
                    rollersToRevert.append(object)
            elif isinstance(object, diceroller.DiceRollerGroup):
                for roller in object.rollers():
                    if self._rollerTree.isRollerModified(rollerId=roller.id()):
                        rollersToRevert.append(roller)

        rollerCount = len(rollersToRevert)
        if rollerCount == 1:
            singleRoller = rollersToRevert[0]
            prompt = f'Are you sure you want to revert \'{singleRoller.name()}\'?'
        else:
            prompt = f'Are you sure you want to revert {rollerCount} dice rollers?'

        answer = gui.MessageBoxEx.question(parent=self, text=prompt)
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        for roller in rollersToRevert:
            if roller.id() in self._editRollers:
                del self._editRollers[roller.id()]
            self._rollerTree.setRollerModified(
                rollerId=roller.id(),
                modified=False)

        currentRoller = self._rollerConfigWidget.roller()
        self._setCurrentObject(
            objectId=currentRoller.id() if currentRoller else None)

    def _autoSaveToggled(self, value: int) -> None:
        if value:
            self._saveAllRollers()

    def _rollerTreeCurrentObjectChanged(
            self,
            currentObject: typing.Optional[typing.Union[
                diceroller.DiceRoller,
                diceroller.DiceRollerGroup
            ]]) -> None:
        # Post the update to set the current object as the tree generates this
        # notification after the current item is updated but before the current
        # selection is updated (i.e. the previous current object is still
        # selected). This would cause issues as updating the current object
        # causes actions to be enabled/disabled and some of them do this based
        # on the "current" selection which needs to be the selection as it will
        # be once the tree has finished updating.
        objectId = currentObject.id() if currentObject else None
        QtCore.QTimer.singleShot(0, lambda: self._setCurrentObject(objectId))

    def _rollerTreeObjectRenamed(
            self,
            renamedObject: typing.Union[
                diceroller.DiceRoller,
                diceroller.DiceRollerGroup
            ]) -> None:
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

        editRoller = self._editRollers.get(renamedObject.id())
        if editRoller:
            editRoller.setName(renamedObject.name())

        self._setCurrentObject(objectId=renamedObject.id())

    def _rollerTreeOrderChanged(
            self,
            updatedObjects: typing.Iterable[typing.Union[
                diceroller.DiceRoller,
                diceroller.DiceRollerGroup
            ]],
            deletedObjectIds: typing.Iterable[str]
            ) -> None:
        try:
            with objectdb.ObjectDbManager.instance().createTransaction() as transaction:
                for object in updatedObjects:
                    objectdb.ObjectDbManager.instance().updateObject(
                        object=object,
                        transaction=transaction)
                for objectId in deletedObjectIds:
                    objectdb.ObjectDbManager.instance().deleteObject(
                        id=objectId,
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

        currentObject = self._rollerTree.currentObject()
        self._setCurrentObject(objectId=currentObject.id() if currentObject else None)

    def _rollerConfigChanged(self) -> None:
        editRoller = self._rollerConfigWidget.roller()
        if not editRoller:
            return

        if self._autoSaveAction.isChecked():
            self._saveRollers([editRoller])
        else:
            self._rollerTree.setRollerModified(
                rollerId=editRoller.id(),
                modified=True)

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.syncToRoller()

        self._updateControlEnablement()

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
        roller = self._rollerTree.currentRoller()
        results = self._resultsWidget.results()
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
