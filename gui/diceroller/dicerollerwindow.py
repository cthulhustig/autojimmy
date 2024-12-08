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


# TODO: Get rid of separate group/roller add buttons and have a single button
#   with the document icon (or maybe a plus icon)
# - Switch to having one of those buttons with an arrow to get multiple options
# - By default clicking the button should add a roller
#   - This will already causes a group to be added if there is none
# - There should be menu options for add group and add roller
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
# - IMPORTANT: If the renamed object is the roller being edited the window
#   will also need to set the new name on the instance of the roller held
#   by the config widget
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
        if not self._rollerTree.groupCount():
            self._createInitialGroup()

    def keyPressEvent(self, event: typing.Optional[QtGui.QKeyEvent]):
        if event and self._rollInProgress:
            key = event.key()
            isSkipKey  = key == QtCore.Qt.Key.Key_Space or \
                key == QtCore.Qt.Key.Key_Escape or \
                key == QtCore.Qt.Key.Key_Return
            if isSkipKey:
                self._resultsWidget.skipAnimation()
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
        self._renameAction.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_F2))
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
        self._rollButton.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Return))
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
        # TODO: This will need to get the current edit roller
        roller = self._rollerTree.currentRoller()
        if not roller or self._rollInProgress:
            return

        group = self._rollerTree.groupFromRoller(roller)
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

        self._setCurrentResults(
            results=results,
            animate=True)

    # TODO: This will probably need a fair bit of rework
    # - I'm thinking reworking things so this function isn't needed any more
    # - Move the code from the second half of the function (updating
    #   _rollerTree etc) into _setCurrentRoller
    # - Rather than re-reading the database have the functions that currently
    #   call _syncToDatabase update the local copy of the objects with the
    #   modified objects they use to write to the database
    #   - Constructor
    #       - This will have to do an initial load then call _setCurrentRoller
    #   - Initial Group
    #       - Add the group & roller to the caches
    #       - Call _setCurrentRoller
    #   - New Roller
    #       - Just add the roller to the caches
    #       - Call _setCurrentRoller
    #   - New Group
    #       - Just add the group to the caches
    #       - Call _setCurrentRoller
    #   - Rename Object
    #       - Replace the currently cached object with the renamed one
    #       - If the renamed object is a roller apply the same rename to the corresponding edit object
    #       - Call _setCurrentRoller
    #   - Copy Object
    #       - Just add the object to the caches
    #       - Call _setCurrentRoller
    #   - Delete Object
    #       - Remove object from caches
    #       - If object is a group remove the corresponding rollers
    #       - If any rollers are removed then remove the corresponding edit object
    #       - Call _setCurrentRoller
    #   - Import Object
    #       - Add the object to the caches
    #       - Call _setCurrentRoller
    #   - Export Object
    #       - IMPORTANT: This will need to export the edit version of any objects
    #   - Object Renamed Event
    #       - Same as Rename Object
    #   - Order Changed Event
    #       - I suspect this is going to be complicated
    #       - Need to remove objects which have had their hierarchy changed
    #       - Add the updated objects that were written to the database
    #       - As long as the edit rollers cache is keyed by id there shouldn't be
    #         any need to update the edit rollers as they all still exist with the
    #         same id and no longer hold a reference to the parent that would need
    #         updated
    #       - Call _setCurrentRoller
    #   - Config Changed Event
    #       - Pass edit object to results window
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

        with gui.SignalBlocker(self._rollerTree):
            self._rollerTree.setContents(groups)
            if currentId != None:
                self._rollerTree.setCurrentObject(object=currentId)
        roller = self._rollerTree.currentRoller()
        self._setCurrentRoller(roller=roller)

    # TODO: This will a few different updates
    # - I think should probably take an optional roller id and use it use the correct
    #   version of the object to different widgets
    # - The code related to updating the roller tree from the above function should
    #   be moved here
    def _setCurrentRoller(
            self,
            roller: typing.Optional[diceroller.DiceRoller],
            results: typing.Optional[diceroller.DiceRollResult] = None
            ) -> None:
        if roller and not results:
            results = self._lastResults.get(roller.id())

        if roller:
            with gui.SignalBlocker(self._rollerTree):
                self._rollerTree.setCurrentObject(object=roller.id())

        # TODO: This should pass the edit version of the roller to results
        # widget
        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(roller=roller)

        # TODO: This should pass the edit version of the roller to results
        # widget
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

    # TODO: This will need some updating
    # - It's called from two places
    #   - Delete Objects: For this case it doesn't matter which version of rollers it
    #     uses as the configuration of the roller doesn't come into the delete process
    #   - Export Objects: For this case it needs to return the edit rollers
    #       - IMPORTANT: If a group contains the edit object it will need to make a copy
    #         of the object and use the edit instance of rollers.
    def _activeObjects(self) -> typing.Iterable[typing.Union[
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
        self._renameAction.setEnabled(hasSelection)
        self._deleteAction.setEnabled(hasSelection)

        hasCurrentRoller = isinstance(currentObject, diceroller.DiceRoller)
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

        self._syncToDatabase(currentId=roller.id())

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

        self._syncToDatabase(currentId=roller.id())
        self._rollerTree.editObjectName(object=roller.id())

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
        self._rollerTree.editObjectName(object=group.id())

    def _renameObject(self) -> None:
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

        self._syncToDatabase(currentId=currentObject.id())

    def _copyObject(self) -> None:
        currentObject = self._rollerTree.currentObject()
        group = None
        roller = None
        if isinstance(currentObject, diceroller.DiceRollerGroup):
            # Make a copy of the group and all its rollers
            group = currentObject.copyConfig()
        elif isinstance(currentObject, diceroller.DiceRoller):
            # Make a copy of the current roller within its current group
            group = self._rollerTree.groupFromRoller(currentObject)
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

    # TODO: This will need updated to remove the selected tree items
    def _deleteObjects(self) -> None:
        groups: typing.List[diceroller.DiceRollerGroup] = []
        rollers: typing.List[diceroller.DiceRoller] = []
        for object in self._activeObjects():
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
            selectedObjects = list(self._activeObjects())
            explicitGroupIds = set()
            for object in selectedObjects:
                if isinstance(object, diceroller.DiceRollerGroup):
                    explicitGroupIds.add(object.id())

            for object in selectedObjects:
                if isinstance(object, diceroller.DiceRollerGroup):
                    exportGroups[object.id()] = object.copyConfig(copyIds=True)
                elif isinstance(object, diceroller.DiceRoller):
                    group = self._rollerTree.groupFromRoller(object)
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
            currentObject: typing.Optional[typing.Union[
                diceroller.DiceRoller,
                diceroller.DiceRollerGroup
            ]]) -> None:
        currentRoller = None
        if isinstance(currentObject, diceroller.DiceRoller):
            currentRoller = currentObject
        self._setCurrentRoller(roller=currentRoller)

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

        self._syncToDatabase(currentId=renamedObject.id())

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

        self._syncToDatabase()

    # TODO: This will need a few updates
    # - It shouldn't update the db unless auto saving is enabled
    # - When it is updating the database it should get the edit version of the current roller
    # - If auto save is disabled it should mark the tree entry for the roller as modified
    # - There shouldn't be any need to update the edit objects as the config window should
    #   be updating the instance that is stored in the cache
    def _rollerConfigChanged(self) -> None:
        roller = self._rollerTree.currentRoller()
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

    # TODO: I don't think this needs any update. Which version of the
    # current roller it uses shouldn't be important as only the id is
    # actually used
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
