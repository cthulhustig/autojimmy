import app
import common
import copy
import diceroller
import gui
import logging
import objectdb
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Dice Roller window allows you to configure dice rollers for different
    situations. Die types for most traveller variants are supported, along with
    customisable modifiers, boons/banes and flux. Dice rollers are arranged in
    groups to allow easy management of dice rollers for different characters or
    games.</p>
    <p>Tip: The modifiers that are added to a dice roller have check boxes that
    can be used to turn them on and off depending on if they apply for the roll
    you're about to make. The main reason I added the dice roller to {name} was
    to speed up combat when using weapons created with the Mongoose 2e Field
    Catalogue rules. Some of the weapons created with these rules can have a lot
    of modifiers that apply in different situations, so I wanted a system that
    would allow me to pre-configure modifiers, then in game I can just enable
    the ones that apply for the situation at hand, for example the modifiers
    that apply based on the target's range.</p>
    </html>
""".format(name=app.AppName)

# This code is intended to draw a button with an downwards arrow. The way the
# arrow is drawn is intended to mimic how Qt would normally draw the drop down
# arrow for a QToolButton that has a menu attached to it. The stock QToolButton
# implementation uses the Text colour for the drop down arrow, but, it sets the
# alpha on the colour to 160. The result of this is the drop down arrow is
# noticeably dimmer than the icons for other buttons in the toolbar (to the
# point it looks like it's disabled)
# https://codebrowser.dev/qt5/qtbase/src/widgets/styles/qfusionstyle.cpp.html#560
# https://codebrowser.dev/qt5/qtbase/src/widgets/styles/qfusionstyle.cpp.html#_ZL20qt_fusion_draw_arrowN2Qt9ArrowTypeEP8QPainterPK12QStyleOptionRK5QRectRK6QColor
class _DropdownButton(QtWidgets.QToolButton):
    def paintEvent(self, event):
        option = QtWidgets.QStyleOptionToolButton()
        self.initStyleOption(option)

        interfaceScale = app.ConfigEx.instance().asFloat(
            option=app.ConfigOption.InterfaceScale)
        dpi = gui.QStyleHelper.dpi(option) * interfaceScale
        arrowWidth = int(gui.QStyleHelper.dpiScaled(14, dpi))
        arrowHeight = int(gui.QStyleHelper.dpiScaled(8, dpi))
        arrowMax = min(arrowWidth, arrowHeight)
        rectMax = min(self.width(), self.height())
        size = min(arrowMax, rectMax)

        arrowRect = QtCore.QRectF()
        arrowRect.setWidth(size)
        arrowRect.setHeight(arrowHeight * size / arrowWidth)
        arrowRect.moveTo(
            (self.width() - arrowRect.width()) / 2.0,
            (self.height() - arrowRect.height()) / 2.0)

        triangle = QtGui.QPolygonF()
        triangle.append(arrowRect.topLeft())
        triangle.append(arrowRect.topRight())
        triangle.append(QtCore.QPointF(arrowRect.center().x(), arrowRect.bottom()))

        colour = self.palette().color(QtGui.QPalette.ColorRole.Text)

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(colour)
        painter.drawPolygon(triangle)

class _DropdownWidgetAction(gui.WidgetActionEx):
    _WidgetWidth = 10

    def __init__(
            self,
            menu: QtWidgets.QMenu,
            text: typing.Optional[str] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            text=text,
            parent=parent)
        self._menu = menu

    def createWidget(
            self,
            parent: typing.Optional[QtWidgets.QWidget]
            ) -> QtWidgets.QWidget:
        interfaceScale = app.ConfigEx.instance().asFloat(
            option=app.ConfigOption.InterfaceScale)
        width = int(_DropdownWidgetAction._WidgetWidth * interfaceScale)
        widget = _DropdownButton(parent=parent)
        widget.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        widget.setMenu(self._menu)
        widget.setFixedWidth(width)
        widget.setToolTip(self.text())
        return widget

class _MenuAction(gui.ActionEx):
    def __init__(
            self,
            menu: QtWidgets.QMenu,
            text: str,
            parent: QtWidgets.QWidget
            ) -> None:
        super().__init__(text, parent)
        self.setMenu(menu)

class DiceRollerWindow(gui.WindowWidget):
    _MaxRollResults = 1000
    _IconSize = 24

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

    def keyPressEvent(self, event: typing.Optional[QtGui.QKeyEvent]):
        if event:
            key = event.key()
            if self._rollInProgress:
                isSkipKey = key == QtCore.Qt.Key.Key_Space or \
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

    def showEvent(self, e):
        if not e.spontaneous():
            self._loadData()
        return super().showEvent(e)

    def closeEvent(self, e: QtGui.QCloseEvent):
        if not self._saveOnClose():
            e.ignore()
            return # User cancelled so don't close the window

        return super().closeEvent(e)

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

        interfaceScale = app.ConfigEx.instance().asFloat(
            option=app.ConfigOption.InterfaceScale)
        iconSize = int(DiceRollerWindow._IconSize * interfaceScale)
        self._rollerToolbar = QtWidgets.QToolBar()
        self._rollerToolbar.setIconSize(QtCore.QSize(iconSize, iconSize))
        self._rollerToolbar.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self._rollerToolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Minimum)

        #
        # New
        #
        self._newRollerAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.NewFile),
            'New Dice Roller',
            self)
        self._newRollerAction.setShortcut(QtGui.QKeySequence.StandardKey.New)
        self._newRollerAction.triggered.connect(self._createNewRoller)

        self._newGroupAction = QtWidgets.QAction('New Group', self)
        self._newGroupAction.setShortcut(QtGui.QKeySequence('Ctrl+Shift+N'))
        self._newGroupAction.triggered.connect(self._createNewGroup)

        menu = QtWidgets.QMenu()
        menu.addAction(self._newRollerAction)
        menu.addAction(self._newGroupAction)

        self._rollerToolbar.addAction(self._newRollerAction)
        self._rollerToolbar.addAction(_DropdownWidgetAction(menu=menu, text='New', parent=self))
        self._rollerTree.addAction(_MenuAction(menu, 'New', self))

        #
        # Save
        #
        self._saveSelectedAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.SaveFile),
            'Save',
            self)
        self._saveSelectedAction.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        self._saveSelectedAction.triggered.connect(self._saveSelectedRollers)

        self._saveAllAction = QtWidgets.QAction('Save All', self)
        self._saveAllAction.setShortcut(QtGui.QKeySequence('Ctrl+Shift+S'))
        self._saveAllAction.triggered.connect(self._saveAllRollers)

        self._autoSaveAction = gui.ActionEx('Autosave', self)
        self._autoSaveAction.setCheckable(True)
        self._autoSaveAction.setChecked(False) # Should work like construction windows by default
        self._autoSaveAction.triggered.connect(self._autoSaveToggled)

        menu = QtWidgets.QMenu(self)
        menu.addAction(self._saveSelectedAction)
        menu.addAction(self._saveAllAction)
        menu.addSeparator()
        menu.addAction(self._autoSaveAction)

        self._rollerToolbar.addAction(self._saveSelectedAction)
        self._rollerToolbar.addAction(_DropdownWidgetAction(menu, 'Save', self))
        self._rollerTree.addAction(_MenuAction(menu, 'Save', self))

        #
        # Rename
        #
        self._renameAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.RenameFile), 'Rename...', self)
        self._renameAction.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_F2))
        self._renameAction.triggered.connect(self._renameCurrentObject)
        self._rollerTree.addAction(self._renameAction)
        self._rollerToolbar.addAction(self._renameAction)

        #
        # Revert
        #
        self._revertSelectedAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.Reload),
            'Revert...',
            self)
        self._revertSelectedAction.setShortcut(QtGui.QKeySequence('Ctrl+R'))
        self._revertSelectedAction.triggered.connect(self._revertSelectedRollers)

        self._revertAllAction = QtWidgets.QAction('Revert All...', self)
        self._revertAllAction.setShortcut(QtGui.QKeySequence('Ctrl+Shift+R'))
        self._revertAllAction.triggered.connect(self._revertAllRollers)

        menu = QtWidgets.QMenu()
        menu.addAction(self._revertSelectedAction)
        menu.addAction(self._revertAllAction)

        self._rollerToolbar.addAction(self._revertSelectedAction)
        self._rollerToolbar.addAction(_DropdownWidgetAction(menu, 'Revert', self))
        self._rollerTree.addAction(_MenuAction(menu, 'Revert', self))

        #
        # Copy
        #
        self._copyAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.CopyFile), 'Copy', self)
        self._copyAction.triggered.connect(self._copyCurrentObject)
        self._rollerTree.addAction(self._copyAction)
        self._rollerToolbar.addAction(self._copyAction)

        #
        # Delete
        #
        self._deleteAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.DeleteFile), 'Delete...', self)
        self._deleteAction.triggered.connect(self._deleteSelectedObjects)
        self._deleteAction.setShortcut(QtGui.QKeySequence.StandardKey.Delete)
        self._rollerTree.addAction(self._deleteAction)
        self._rollerToolbar.addAction(self._deleteAction)

        #
        # Import
        #
        self._importAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.ImportFile), 'Import...', self)
        self._importAction.triggered.connect(self._importObjects)
        self._rollerTree.addAction(self._importAction)
        self._rollerToolbar.addAction(self._importAction)

        #
        # Export
        #
        self._exportAction = QtWidgets.QAction(
            gui.loadIcon(gui.Icon.ExportFile), 'Export...', self)
        self._exportAction.triggered.connect(self._exportSelectedObjects)
        self._rollerTree.addAction(self._exportAction)
        self._rollerToolbar.addAction(self._exportAction)

        self._rollerTree.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)

        groupLayout = QtWidgets.QVBoxLayout()
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

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.setContentsMargins(0, 0, 0, 0)
        groupLayout.addWidget(self._rollerConfigWidget)

        self._configGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configGroupBox.setLayout(groupLayout)

    def _createRollResultsControls(self) -> None:
        self._resultsWidget = gui.DiceRollDisplayWidget()
        self._resultsWidget.rollComplete.connect(self._virtualRollComplete)

        self._rollButton = QtWidgets.QPushButton('Roll Dice')
        self._rollButton.clicked.connect(self._rollDice)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._resultsWidget)
        groupLayout.addWidget(self._rollButton)

        self._resultsGroupBox = QtWidgets.QGroupBox('Roll')
        self._resultsGroupBox.setLayout(groupLayout)

    def _createRollHistoryControls(self) -> None:
        self._historyWidget = gui.DiceRollHistoryWidget()

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._historyWidget)

        self._historyGroupBox = QtWidgets.QGroupBox('History')
        self._historyGroupBox.setLayout(groupLayout)

    def _loadData(self) -> None:
        try:
            exceptionList: typing.List[Exception] = []
            groups = objectdb.ObjectDbManager.instance().readObjects(
                classType=diceroller.DiceRollerGroup,
                bestEffort=True,
                exceptionList=exceptionList)

            if exceptionList:
                for ex in exceptionList:
                    logging.error('An error occurred while loading dice roller groups from the database', exc_info=ex)
                gui.MessageBoxEx.critical(f'Failed to load some dice roller data from database, consult log for more details.')
        except Exception as ex:
            message = 'Failed to load dice roller data from database'
            logging.error(message, exc_info=ex)
            return

        self._editRollers.clear()

        with gui.SignalBlocker(self._rollerTree):
            self._rollerTree.clearModifiedRollers()
            self._rollerTree.setContents(groups=groups)

        if not self._rollerTree.groupCount():
            self._createInitialGroup()
        currentObject = self._rollerTree.currentObject()
        self._setCurrentObject(objectId=currentObject.id() if currentObject else None)

    def _rollDice(self) -> None:
        # NOTE: Get the current EDIT roller from the config widget
        roller = self._rollerConfigWidget.roller()
        if not roller or self._rollInProgress:
            return

        group = self._rollerTree.groupFromRoller(rollerId=roller.id())
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

    def _updateControlEnablement(self) -> None:
        currentObject = self._rollerTree.currentObject()
        hasSelection = currentObject != None
        hasCurrentRoller = isinstance(currentObject, diceroller.DiceRoller)
        isAnyModified = self._rollerTree.hasModifiedRoller()
        isSelectionModified = False
        for selectedObject in self._rollerTree.selectedObjects():
            if isinstance(selectedObject, diceroller.DiceRoller):
                isSelectionModified = self._rollerTree.isRollerModified(rollerId=selectedObject.id())
            elif isinstance(selectedObject, diceroller.DiceRollerGroup):
                isSelectionModified = any(self._rollerTree.isRollerModified(rollerId=roller.id()) for roller in selectedObject.rollers())
            if isSelectionModified:
                break

        self._renameAction.setEnabled(hasSelection)
        self._deleteAction.setEnabled(hasSelection)

        self._saveSelectedAction.setEnabled(isSelectionModified)
        self._saveAllAction.setEnabled(isAnyModified)

        self._revertSelectedAction.setEnabled(isSelectionModified)
        self._revertAllAction.setEnabled(isAnyModified)

        self._managerGroupBox.setEnabled(not self._rollInProgress)
        self._configGroupBox.setEnabled(hasCurrentRoller and not self._rollInProgress)
        self._historyGroupBox.setEnabled(not self._rollInProgress)
        # NOTE: Disabling the results group when a roll is in progress is
        # important. If it's not disabled then for reasons I can't figure out
        # the DiceRollerWindow doesn't get an event when the space key is
        # pressed to skip the roll animation (other key events are received).
        # It seems to have something to do with the roll button being in that
        # group as it was working without disabling the results group when the
        # button was in the config group
        self._resultsGroupBox.setEnabled(hasCurrentRoller and not self._rollInProgress)

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
            newGroup = self._rollerTree.groupFromRoller(
                rollerId=currentObject.id())
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
        for object in self._rollerTree.selectedObjects():
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
            selectedObjects = self._rollerTree.selectedObjects()
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
                    group = self._rollerTree.groupFromRoller(rollerId=object.id())
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

    def _saveCurrentRoller(self) -> None:
        currentRoller = self._rollerTree.currentRoller()
        if currentRoller:
            self._saveRollers(objects=[currentRoller])

    def _saveSelectedRollers(self) -> None:
        self._saveRollers(objects=self._rollerTree.selectedObjects())

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
                self._rollerTree.replaceRoller(roller=roller)
                self._rollerTree.setRollerModified(
                    rollerId=roller.id(),
                    modified=False)

        self._updateControlEnablement()

    def _saveOnClose(self) -> bool: # False if the user cancelled, otherwise True
        modified = self._rollerTree.modifiedRollers()
        nameMap: typing.Dict[
            str,
            diceroller.DiceRoller
            ] = {}
        for roller in modified:
            group = self._rollerTree.groupFromRoller(rollerId=roller.id())
            if group:
                name = f'{group.name()} > {roller.name()}'
                nameMap[name] = roller

        if not nameMap:
            return True

        prompt = gui.ListSelectDialog(
            title='Modified Dice Rollers',
            text='Do you want to save these modified dice rollers?',
            selectable=nameMap.keys(),
            showYesNoCancel=True,
            defaultState=QtCore.Qt.CheckState.Checked)
        if prompt.exec() == QtWidgets.QDialog.DialogCode.Rejected:
            return False # The use cancelled

        toSave = []
        for name in prompt.selected():
            roller = nameMap.get(name)
            if roller:
                toSave.append(roller)

        self._saveRollers(objects=toSave)
        self._rollerTree.clearModifiedRollers()

        return True

    def _revertCurrentRoller(self) -> None:
        currentRoller = self._rollerTree.currentRoller()
        if currentRoller:
            self._revertRollers(objects=[currentRoller])

    def _revertSelectedRollers(self) -> None:
        self._revertRollers(objects=self._rollerTree.selectedObjects())

    def _revertAllRollers(self) -> None:
        revertRollers = self._rollerTree.modifiedRollers()
        if revertRollers:
            self._revertRollers(objects=revertRollers)

    def _revertRollers(
            self,
            objects: typing.Iterable[typing.Union[
                diceroller.DiceRoller,
                diceroller.DiceRollerGroup]],
            promptConfirm: bool = True
            ) -> None:
        rollersToRevert: typing.List[diceroller.DiceRoller] = []
        for object in objects:
            if isinstance(object, diceroller.DiceRoller):
                if self._rollerTree.isRollerModified(rollerId=object.id()):
                    rollersToRevert.append(object)
            elif isinstance(object, diceroller.DiceRollerGroup):
                for roller in object.rollers():
                    if self._rollerTree.isRollerModified(rollerId=roller.id()):
                        rollersToRevert.append(roller)

        if not rollersToRevert:
            return

        if promptConfirm:
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
