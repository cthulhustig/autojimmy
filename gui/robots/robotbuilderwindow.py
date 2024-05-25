import app
import common
import construction
import enum
import gui
import robots
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: Add welcome message
_WelcomeMessage = """
TODO
""".format(name=app.AppName)

class _RobotStoreList(gui.ConstructableStoreList):
    _DefaultTechLevel = 12
    _DefaultWeaponSet = traveller.StockWeaponSet.CSC2023

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            constructableStore=robots.RobotStore.instance().constructableStore(),
            parent=parent)
        self._exportJob = None
        
    def createConstructable(
            self,
            name: str
            ) -> construction.ConstructableInterface:
        return robots.Robot(
            name=name,
            techLevel=_RobotStoreList._DefaultTechLevel,
            weaponSet=_RobotStoreList._DefaultWeaponSet)
    
    def importConstructable(self) -> None:
        # TODO: Implement import
        pass

    def exportConstructable(self) -> None:
        # TODO: Implement export
        pass

class RobotBuilderWindow(gui.WindowWidget):
    _PDFFilter = 'PDF (*.pdf)'
    _JSONFilter = 'JSON (*.json)'
    _CSVFilter = 'CSV (*.csv)'

    _ConfigurationBottomSpacing = 300

    def __init__(self) -> None:
        super().__init__(
            title='Robot Builder',
            configSection='RobotBuilder')

        self._unnamedIndex = 1        

        self._setupRobotListControls()
        self._setupCurrentRobotControls()
        self._setupResultsControls()

        self._verticalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self._verticalSplitter.addWidget(self._robotsGroupBox)
        self._verticalSplitter.addWidget(self._currentRobotGroupBox)

        self._horizontalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._horizontalSplitter.addWidget(self._verticalSplitter)
        self._horizontalSplitter.addWidget(self._manifestGroupBox)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._horizontalSplitter)

        self.setLayout(windowLayout)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        QtCore.QTimer.singleShot(0, self._showWelcomeMessage)
        super().firstShowEvent(e)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='VerticalSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._verticalSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='HorizontalSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._horizontalSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RobotStoreListState',
            type=QtCore.QByteArray)
        if storedValue:
            self._robotSelector.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CurrentRobotDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._currentRobotDisplayModeTabView.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ConfigurationState',
            type=QtCore.QByteArray)
        if storedValue:
            self._configurationWidget.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ResultsDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._resultsDisplayModeTabView.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('VerticalSplitterState', self._verticalSplitter.saveState())
        self._settings.setValue('HorizontalSplitterState', self._horizontalSplitter.saveState())
        self._settings.setValue('RobotStoreListState', self._robotSelector.saveState())
        self._settings.setValue('CurrentRobotDisplayModeState', self._currentRobotDisplayModeTabView.saveState())
        self._settings.setValue('ConfigurationState', self._configurationWidget.saveState())
        self._settings.setValue('ResultsDisplayModeState', self._resultsDisplayModeTabView.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def closeEvent(self, e: QtGui.QCloseEvent):
        if not self._promptSaveModified():
            e.ignore()
            return # User cancelled so don't close the window

        return super().closeEvent(e)

    def _setupRobotListControls(self) -> None:
        self._robotSelector = _RobotStoreList()
        self._robotSelector.currentChanged.connect(self._selectedRobotChanged)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._robotSelector)

        self._robotsGroupBox = QtWidgets.QGroupBox('Robots')
        self._robotsGroupBox.setLayout(layout)

    def _setupCurrentRobotControls(self) -> None:
        robot = self._robotSelector.current()
        assert(isinstance(robot, robots.Robot))

        self._configurationWidget = gui.RobotConfigWidget(robot=robot)
        self._configurationWidget.robotModified.connect(self._robotModified)

        # Wrap the configuration widget in a layout with a spacing at the bottom. This is an effort to avoid
        # the usability issue where adding items at the bottom of the configuration widget would appear of
        # the bottom of the control and require scrolling. This isn't a great solution but it does make it a
        # bit better.
        spacerLayout = QtWidgets.QVBoxLayout()
        spacerLayout.setContentsMargins(0, 0, 0, 0)
        spacerLayout.addWidget(self._configurationWidget)
        spacerLayout.addSpacing(RobotBuilderWindow._ConfigurationBottomSpacing)
        wrapperWidget = QtWidgets.QWidget()
        wrapperWidget.setLayout(spacerLayout)

        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(wrapperWidget)

        # Use a plain text edit for the notes as we don't want the advanced stuff (tables etc)
        # supported by QTextEdit. This text could end up in the notes section of a pdf so
        # advanced formatting is out
        self._userNotesTextEdit = QtWidgets.QPlainTextEdit()
        self._userNotesTextEdit.setPlainText(robot.userNotes() if robot else '')
        self._userNotesTextEdit.textChanged.connect(self._userNotesChanged)

        self._currentRobotDisplayModeTabView = gui.TabWidgetEx()
        self._currentRobotDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self._currentRobotDisplayModeTabView.addTab(scrollArea, 'Configuration')
        self._currentRobotDisplayModeTabView.addTab(self._userNotesTextEdit, 'User Notes')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._currentRobotDisplayModeTabView)

        self._currentRobotGroupBox = QtWidgets.QGroupBox('Current Robot')
        self._currentRobotGroupBox.setLayout(layout)

    def _setupResultsControls(self) -> None:
        self._manifestTable = gui.RobotManifestTable()

        self._resultsDisplayModeTabView = gui.TabWidgetEx()
        self._resultsDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._resultsDisplayModeTabView.addTab(self._manifestTable, 'Manifest')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._resultsDisplayModeTabView)

        self._manifestGroupBox = QtWidgets.QGroupBox('Results')
        self._manifestGroupBox.setLayout(layout)

        self._updateResults()

    def _robotModified(self, value: int) -> None:
        self._robotSelector.markCurrentModified()
        self._updateResults()

    def _updateResults(self) -> None:
        robot = self._configurationWidget.robot()

        print('----------------------------------------')
        for attributeId in robots.RobotAttributeId:
            attribute = robot.attribute(attributeId=attributeId)
            if not attribute:
                continue
            value=attribute.value()
            if isinstance(value, common.ScalarCalculation):
                print(f'{attributeId.value}={value.value()}')
            elif isinstance(value, common.DiceRoll):
                print(f'{attributeId.value}={value}')
            elif isinstance(value, enum.Enum):
                print(f'{attributeId.value}={value.value}')
            else:
                print(attributeId.value)

        for skillDef in traveller.AllStandardSkills:
            skill = robot.skill(skillDef=skillDef)
            if not skill:
                continue
            specialities = skill.specialities()
            if specialities:
                for speciality in specialities:
                    level = skill.level(speciality=speciality)
                    string = skill.name(speciality=speciality)
                    string += f' {level.value()}'
                    print(string)
            else:
                level = skill.level()
                print(f'{skill.name()} {level.value()}')


        seenNotes = set()
        for step in robot.steps():
            for note in step.notes():
                note = f'{step.type()}: {step.name()}: {note}'
                if note not in seenNotes:
                    print(note)
                    seenNotes.add(note)

        self._manifestTable.setManifest(manifest=robot.manifest())

    def _selectedRobotChanged(self) -> None:
        robot = self._robotSelector.current()
        isRobot = isinstance(robot, robots.Robot)

        if isRobot:
            isUserSection = self._robotSelector.currentSection() == \
                gui.ConstructableStoreList.Section.UserSection

            # Block signals from configuration widget while configuration widget
            # is updated as the generated change notification would cause the
            # robot to be marked as dirty. Doing this means we need to manually
            # update the result widgets
            with gui.SignalBlocker(widget=self._configurationWidget):
                self._configurationWidget.setRobot(robot=robot)

            with gui.SignalBlocker(widget=self._userNotesTextEdit):
                # Use setPLainText to reset undo/redo history
                self._userNotesTextEdit.setPlainText(robot.userNotes())
                self._userNotesTextEdit.setReadOnly(not isUserSection)

        self._currentRobotDisplayModeTabView.setHidden(not isRobot)

        self._updateResults()

    def _userNotesChanged(self) -> None:
        robot = self._robotSelector.current()
        if not isinstance(robot, robots.Robot):
            return
        robot.setUserNotes(notes=self._userNotesTextEdit.toPlainText())
        self._robotSelector.markCurrentModified()

    def _promptSaveModified(self) -> bool: # False if the user cancelled, otherwise True
        modifiedRobots: typing.List[robots.Robot] = []
        for robot in self._robotSelector.constructables():
            if self._robotSelector.isModified(constructable=robot):
                modifiedRobots.append(robot)
        if not modifiedRobots:
            return True # Nothing to do

        if len(modifiedRobots) == 1:
            robot = modifiedRobots[0]
            answer = gui.MessageBoxEx.question(
                parent=self,
                text=f'The Robot \'{robot.name()}\' has been modified, do you want to save it?',
                buttons=QtWidgets.QMessageBox.StandardButton.Yes | \
                    QtWidgets.QMessageBox.StandardButton.No | \
                    QtWidgets.QMessageBox.StandardButton.Cancel)
            if answer == QtWidgets.QMessageBox.StandardButton.Cancel:
                return False # User cancelled

            robotToSave = []
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                robotToSave.append(robot)
        else:
            dlg = gui.ConstructableSelectDialog(
                parent=self,
                title='Unsaved Robots',
                text='Do you want to save these modified robots?',
                constructables=modifiedRobots,
                showYesNoCancel=True,
                defaultState=QtCore.Qt.CheckState.Checked,
                configSection='UnsavedRobotsDialog')
            if dlg.exec() == QtWidgets.QDialog.DialogCode.Rejected:
                return False # The use cancelled
            robotToSave = dlg.selected()

        for robot in robotToSave:
            # TODO: This call goes nowhere
            if not self._promptSaveRobot(robot=robot):
                return False # The use cancelled

        # Revert all weapons. Updating the list box and selected weapon when the
        # window is being closed seems counter intuitive but, due to the way the
        # app handles windows, this same window may be redisplayed if the user
        # opens the Gunsmith again. We don't want them to see the modified
        # weapons that they said not to save so best to reset everything
        currentWeapon = self._robotSelector.current()
        for robot in self._robotSelector.constructables():
            if self._robotSelector.isModified(constructable=robot):
                self._robotSelector.revert(constructable=robot)
            if robot == currentWeapon:
                # The current weapon was reverted so force an update of the
                # configuration and results controls
                self._selectedRobotChanged()

        # Remove any unsaved weapons for the same reason the modified weapons
        # were removed
        self._robotSelector.removeUnsaved()

        return True # The user didn't cancel

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='RobotBuilderWelcome')
        message.exec()
