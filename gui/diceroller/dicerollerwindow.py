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

# TODO: Add support for lists containing pod types as as object lists.
# - Add new columns for each of the supported types (bool, int, float, string, enum, tuples)
#   - These columns and the existing object column, will need to be nullable
#   - I think enum could be problematic as I don't know which type of enum to use when reading
#   - Tuples could be tricky, not as simple as just treating them as lists as they won't have an
#     id. They probably aren't required
#   - I think the implementation might get lists of lists for free (not tested)
# - Will require quite a few changes
#   - DatabaseList will need updated so it only sets the parent of objects
#     (and some other stuff) if the object is a DatabaseEntity
#   - CRUD functions will need updated
#       - Read will need to read all columns and find the one that's not null to
#         know the type
# TODO: Store historic results in the objectdb?
# - Would need some kind of max number (fifo) to avoid db bloat
# - Complicated by the fact they have they hold an instance of a roller but
# with the config from when the roll was made. It means those objects (which
# would need stored in the db) will have the same id as the current version
# of the object that is already in the db
# - Complicated by the fact they use ScalarCalculations (history would be lost)
# TODO: Support for Flux???
# - p22 of T5 rules
# - T5 usually the lower the roll the better but also says some target
#   numbers are higher is better and even mentions that it could be
#   you need to roll the target number exactly for it to be a success
#   - Probably just a drop down on the target number to select the logic
#   - Would need to update the probability graph code


class DiceRollerWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Dice Roller',
            configSection='DiceRoller')

        self._roller = None
        self._results = None
        self._rollInProgress = False
        self._objectItemMap: typing.Dict[str, QtWidgets.QTreeWidgetItem] = {}
        self._lastResults = {}

        self._randomGenerator = common.RandomGenerator()
        logging.info(f'Dice Roller random generator seed: {self._randomGenerator.usedSeed()}')

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
        if self._managerTree.groupCount() == 0:
            self._createInitialGroup()

    def keyPressEvent(self, event: typing.Optional[QtGui.QKeyEvent]):
        if event and event.key() == QtCore.Qt.Key.Key_Space and self._rollInProgress:
            self._resultsWidget.skipAnimation()
            event.accept()
            return

        return super().keyPressEvent(event)

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
        self._newRollerAction.triggered.connect(self._createNewRoller)
        self._managerTree.addAction(self._newRollerAction)
        self._managerToolbar.addAction(self._newRollerAction)

        self._newGroupAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.NewList), 'New Group', self)
        self._newGroupAction.triggered.connect(self._createNewGroup)
        self._managerTree.addAction(self._newGroupAction)
        self._managerToolbar.addAction(self._newGroupAction)

        self._renameAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.RenameFile), 'Rename...', self)
        self._renameAction.triggered.connect(self._renameObject)
        self._managerTree.addAction(self._renameAction)
        self._managerToolbar.addAction(self._renameAction)

        self._copyAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.CopyFile), 'Copy...', self)
        self._copyAction.triggered.connect(self._copyObject)
        self._managerTree.addAction(self._copyAction)
        self._managerToolbar.addAction(self._copyAction)

        self._deleteAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DeleteFile), 'Delete...', self)
        self._deleteAction.triggered.connect(self._deleteObjects)
        self._managerTree.addAction(self._deleteAction)
        self._managerToolbar.addAction(self._deleteAction)

        self._importAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.ImportFile), 'Import...', self)
        self._importAction.triggered.connect(self._importObjects)
        self._managerTree.addAction(self._importAction)
        self._managerToolbar.addAction(self._importAction)

        self._exportAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.ExportFile), 'Export...', self)
        self._exportAction.triggered.connect(self._exportObjects)
        self._managerTree.addAction(self._exportAction)
        self._managerToolbar.addAction(self._exportAction)

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

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._historyWidget)

        self._historyGroupBox = QtWidgets.QGroupBox('History')
        self._historyGroupBox.setLayout(groupLayout)

    def _rollDice(self) -> None:
        if not self._roller or self._rollInProgress:
            return

        self._results = diceroller.rollDice(
            roller=self._roller,
            randomGenerator=self._randomGenerator)

        self._rollInProgress = True
        self._updateControlEnablement()

        self._setCurrentResults(
            results=self._results,
            animate=True)

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
            roller: typing.Optional[diceroller.DiceRoller],
            results: typing.Optional[diceroller.DiceRollResult] = None
            ) -> None:
        # TODO: Remove temp hack
        group = self._managerTree.groupFromRoller(roller=roller) if roller else None
        print('Current Roller: {group} - {roller}'.format(
            group=group.name() if group else 'Unknown',
            roller=roller.name() if roller else 'Unknown'))

        if roller and not results:
            results = self._lastResults.get(roller.id())

        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(roller=roller)

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setRoller(roller=roller)
            if results:
                self._setCurrentResults(
                    results=results,
                    animate=False)

        self._roller = roller
        self._results = results
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

    def _updateControlEnablement(self) -> None:
        hasSelection = self._managerTree.currentItem() != None
        self._renameAction.setEnabled(hasSelection)
        self._deleteAction.setEnabled(hasSelection)

        self._managerGroupBox.setEnabled(not self._rollInProgress)
        self._configGroupBox.setEnabled(self._roller != None and not self._rollInProgress)
        self._historyGroupBox.setEnabled(not self._rollInProgress)

    def _generateGroupName(self) -> str:
        groupNames = set([group.name() for group in self._managerTree.groups()])
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
        group = self._managerTree.currentGroup()
        newGroup = not group
        if newGroup:
            group = diceroller.DiceRollerGroup(
                name=self._generateGroupName())
            newGroup = True
        else:
            group = copy.deepcopy(group)

        roller = diceroller.DiceRoller(
            name=self._generateRollerName(group=group),
            dieCount=1,
            dieType=common.DieType.D6)
        group.addRoller(roller=roller)

        try:
            if newGroup:
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
        self._managerTree.editObjectName(object=roller)

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
        self._managerTree.editObjectName(object=group)

    def _renameObject(self) -> None:
        object = self._managerTree.currentObject()
        if isinstance(object, diceroller.DiceRollerGroup):
            title = 'Group Name'
            typeString = 'group'
        elif isinstance(object, diceroller.DiceRoller):
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
            message = 'Failed to write updated object to objectdb'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        self._syncToDatabase(currentId=object.id())

    def _copyObject(self) -> None:
        object = self._managerTree.currentObject()
        group = None
        roller = None
        if isinstance(object, diceroller.DiceRollerGroup):
            group = object.copyConfig()
        elif isinstance(object, diceroller.DiceRoller):
            group = self._managerTree.groupFromRoller(roller=object)
            group = copy.deepcopy(group)
            roller = object.copyConfig()
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
        objects = list(self._managerTree.selectedObjects())
        currentObject = self._managerTree.currentObject()
        if currentObject and currentObject not in objects:
            objects.append(currentObject)
        if not objects:
            return

        groups: typing.List[diceroller.DiceRollerGroup] = []
        rollers: typing.List[diceroller.DiceRoller] = []
        for object in objects:
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
            selectedObjects = list(self._managerTree.selectedObjects())
            currentObject = self._managerTree.currentObject()
            if currentObject and currentObject not in selectedObjects:
                selectedObjects.append(currentObject)
            if not selectedObjects:
                return

            explicitGroupIds = set()
            for object in selectedObjects:
                if isinstance(object, diceroller.DiceRollerGroup):
                    explicitGroupIds.add(object.id())

            for object in selectedObjects:
                if isinstance(object, diceroller.DiceRollerGroup):
                    exportGroups[object.id()] = object.copyConfig(copyIds=True)
                elif isinstance(object, diceroller.DiceRoller):
                    group = self._managerTree.groupFromRoller(roller=object.id())
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

    def _managerTreeCurrentObjectChanged(self) -> None:
        self._setCurrentRoller(
            roller=self._managerTree.currentRoller())

    def _managerTreeObjectsChanged(
            self,
            createdObjects: typing.Iterable[typing.Union[
                diceroller.DiceRollerGroup,
                diceroller.DiceRoller]],
            updatedObjects: typing.Iterable[typing.Union[
                diceroller.DiceRollerGroup,
                diceroller.DiceRoller]],
            deletedObjects: typing.Iterable[typing.Union[
                diceroller.DiceRollerGroup,
                diceroller.DiceRoller]]
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
        if not self._rollInProgress:
            return

        self._rollInProgress = False
        self._lastResults[self._roller.id()] = self._results
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
