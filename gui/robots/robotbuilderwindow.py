import app
import common
import construction
import gui
import jobs
import logging
import os
import robots
import traveller
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    <html>
    <p>The Robot Builder window allows you to create robots using the rules
    from the Mongoose 2e Robot Handbook. It's aimed to aid in the creation of
    robots and is not intended to be a substitute for the rules book.</p>
    <p>A big thanks goes out to Geir Lanesskog, the book's author, for his help
    clarifying some of the rules. You can find the discussion we had around
    these clarifications in the thread below.<br>
    <a href='https://forum.mongoosepublishing.com/threads/robot-handbook-rule-clarifications.124669/'>https://forum.mongoosepublishing.com/threads/robot-handbook-rule-clarifications.124669/</a>
    </p>
    <p>Another big thanks goes to Technetium 98 on the Mongoose forum for
    creating the Google worksheet implementation of the Robot Handbook rules.
    It was an indispensable reference when it came to me implementing the Robot
    Builder.<br>
    <a href='https://forum.mongoosepublishing.com/threads/google-sheets-worksheets.123753/'>https://forum.mongoosepublishing.com/threads/google-sheets-worksheets.123753/</a>
    </p>
    <p>Unlike the robots in the Robots Handbook, by default, {name} does not
    include characteristic DMs when displaying final skill levels. This is
    done to avoid ambiguities and unnecessary complexities when dealing with
    robots that have manipulators with different characteristics or in cases
    where the 'standard' characteristic isn't the one that is appropriate one to
    use with the skill in the situation at hand. In game, this change means
    making skill checks for a robot is effectively identical to the process used
    when making skill checks for a meatbag traveller, the characteristic DM and
    any other situational DMs are added to the skill level to get the final DM.
    The only difference when dealing with robots is, in general, skills that
    would usually be paired with EDU or SOC characteristics, instead use the
    robots INT characteristic.</p>
    <p>If you try to recreate the robots from the Robots Handbook in {name},
    you may find there are some differences. Common reasons for this are:
    <ul style="margin-left:15px; -qt-list-indent:0;">
    <li>As mentioned above, the Robots Handbook includes characteristic DMs
    in final skill levels it gives for a robot whereas Auto-Jimmy doesn't do
    this by default.</li>
    <li>The Robots Handbook includes some information in a robot's worksheet
    that is actually situationally dependant. For example, the StarTek example
    robot is shown to have Athletics (Strength) 2 (p78), which appears to come
    from the Manipulator Athletics Skill Requirements rules (p26). The problem
    with just listing this with the rest of the robot's skills is that it
    doesn't apply when the robot is using its smaller manipulator, this fact
    would be very easy to miss from just looking at the robot's worksheet. To
    avoid this sort of confusion, instead of listing situationally dependant
    stats in the robots worksheet, {name} instead generates notes that cover
    how the robots base stats change in different situations.</li>
    <li>The worksheets from the Robots Handbook don't give a complete list of
    the components that make up the robot, so there can be different component
    configurations that give the same stats but with different costs or
    slot/bandwidth requirements.</li>
    <li>{name} includes some additional information in the worksheet that the
    Robots Handbook doesn't, an example of this is showing speeds and endurance
    values for primary & secondary locomotions and vehicle speed movement if the
    robot has them.</li>
    <li>Some of the robots in the Robot Handbook don't seem to follow the rules
    as written. For example, Ultra (p258) has Camouflage: Visual Concealment
    (p31) and Solar Coating (p33) but the rules say those components are
    incompatible with each other.</li>
    </ul></p>
    <p>Unfortunately, the Gunsmith and Robot Builder are not integrated at this
    time, which means it's not possible to select a custom weapon when arming
    a robot. Integrating custom weapons would be a surprisingly large amount of
    work, so it will have to wait for some future version. Your Terminators will
    need to make do with the weapons from the core rules and supply catalogues
    for now.</p>
    </html>
""".format(name=app.AppName)

class _RobotPDFExportDialog(gui.DialogEx):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            title='Robot PDF Export',
            configSection='RobotPDFExportDialog',
            parent=parent)

        self._includeEditableFieldsCheckBox = gui.CheckBoxEx('Include Editable Fields')
        self._includeEditableFieldsCheckBox.setChecked(True)

        self._includeManifestTableCheckBox = gui.CheckBoxEx('Include Manifest Table')
        self._includeManifestTableCheckBox.setChecked(True)

        self._applySkillModifiersCheckBox = gui.CheckBoxEx('Include Characteristic DMs in Skill Levels')
        self._applySkillModifiersCheckBox.setChecked(False)        

        self._blackAndWhiteCheckBox = gui.CheckBoxEx('Black && White')
        self._blackAndWhiteCheckBox.setChecked(False)

        self._okButton = QtWidgets.QPushButton('OK')
        self._okButton.setDefault(True)
        self._okButton.clicked.connect(self.accept)

        self._cancelButton = QtWidgets.QPushButton('Cancel')
        self._cancelButton.clicked.connect(self.reject)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addStretch()
        buttonLayout.addWidget(self._okButton)
        buttonLayout.addWidget(self._cancelButton)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._includeEditableFieldsCheckBox)
        windowLayout.addWidget(self._includeManifestTableCheckBox)
        windowLayout.addWidget(self._applySkillModifiersCheckBox)
        windowLayout.addWidget(self._blackAndWhiteCheckBox)
        windowLayout.addLayout(buttonLayout)

        self.setLayout(windowLayout)

        # Prevent the dialog being resized
        windowLayout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetFixedSize)
        self.setSizeGripEnabled(False)

    def isIncludeEditableFieldsChecked(self) -> bool:
        return self._includeEditableFieldsCheckBox.isChecked()

    def isIncludeManifestTableChecked(self) -> bool:
        return self._includeManifestTableCheckBox.isChecked()
    
    def isApplySkillModifiersChecked(self) -> bool:
        return self._applySkillModifiersCheckBox.isChecked()            

    def isBlackAndWhiteChecked(self) -> bool:
        return self._blackAndWhiteCheckBox.isChecked()

    # There is intentionally no saveSettings implementation as saving is only done if the user clicks ok
    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)          

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='IncludeEditableFields',
            type=QtCore.QByteArray)
        if storedValue:
            self._includeEditableFieldsCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='IncludeManifestTable',
            type=QtCore.QByteArray)
        if storedValue:
            self._includeManifestTableCheckBox.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ApplySkillModifiers',
            type=QtCore.QByteArray)
        if storedValue:
            self._applySkillModifiersCheckBox.restoreState(storedValue)                

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='BlackAndWhite',
            type=QtCore.QByteArray)
        if storedValue:
            self._blackAndWhiteCheckBox.restoreState(storedValue)

        self._settings.endGroup()

    def accept(self) -> None:
        self._settings.beginGroup(self._configSection)
        self._settings.setValue('IncludeEditableFields', self._includeEditableFieldsCheckBox.saveState())
        self._settings.setValue('IncludeManifestTable', self._includeManifestTableCheckBox.saveState())
        self._settings.setValue('ApplySkillModifiers', self._applySkillModifiersCheckBox.saveState())
        self._settings.setValue('BlackAndWhite', self._blackAndWhiteCheckBox.saveState())
        self._settings.endGroup()

        super().accept()

class _RobotManagerWidget(gui.ConstructableManagerWidget):
    _DefaultTechLevel = 12
    _DefaultWeaponSet = traveller.StockWeaponSet.CSC2023

    _StateVersion = '_RobotManagerWidget_v1'

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(
            constructableStore=robots.RobotStore.instance().constructableStore(),
            parent=parent)
        self._exportJob = None
        self._importExportPath = None

    def saveState(self) -> QtCore.QByteArray:
        state = QtCore.QByteArray()
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.WriteOnly)
        stream.writeQString(_RobotManagerWidget._StateVersion)

        stream.writeQString(self._importExportPath)

        baseState = super().saveState()
        stream.writeUInt32(baseState.count() if baseState else 0)
        if baseState:
            stream.writeRawData(baseState.data())

        return state
    
    def restoreState(self, state: QtCore.QByteArray) -> bool:
        stream = QtCore.QDataStream(state, QtCore.QIODevice.OpenModeFlag.ReadOnly)
        version = stream.readQString()
        if version != _RobotManagerWidget._StateVersion:
            # Wrong version so unable to restore state safely
            logging.debug(f'Failed to restore _RobotManagerWidget state (Incorrect version)')
            return False

        self._importExportPath = stream.readQString()

        count = stream.readUInt32()
        if count <= 0:
            return True
        baseState = QtCore.QByteArray(stream.readRawData(count))
        if not super().restoreState(baseState):
            return False

        return True           
        
    def createConstructable(
            self,
            name: str
            ) -> construction.ConstructableInterface:
        return robots.Robot(
            name=name,
            techLevel=_RobotManagerWidget._DefaultTechLevel,
            weaponSet=_RobotManagerWidget._DefaultWeaponSet)
    
    def importConstructable(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            directory=self._importExportPath if self._importExportPath else QtCore.QDir.homePath(),
            filter=gui.JSONFileFilter)
        if not path:
            return # User cancelled

        self._importExportPath = os.path.dirname(path)

        try:
            robot = robots.readRobot(filePath=path)
        except Exception as ex:
            message = f'Failed to load robot from {path}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

        robotName = robot.name()
        while self._constructableStore.exists(name=robotName):
            robotName, result = gui.InputDialogEx.getText(
                parent=self,
                title='Robot Name',
                label=f'A robot named \'{robotName}\' already exists.\nEnter a new name for the imported robot',
                text=robotName)
            if not result:
                return # User cancelled
        if robotName != robot.name():
            robot.setName(robotName)

        try:
            # No need to update buttons or results as import will trigger a selection change
            self._internalAdd(
                constructable=robot,
                unnamed=False,
                writeToDisk=True,
                makeCurrent=True,
                sortList=True)
        except Exception as ex:
            message = 'Failed to import robot'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            return

    def exportConstructable(self) -> None:
        if self._exportJob:
            gui.MessageBoxEx.information(
                parent=self,
                text='Unable to export while another export is in progress')
            return

        robot = self.current()
        if not  isinstance(robot, robots.Robot):
            gui.MessageBoxEx.information(
                parent=self,
                text='No robot to export')
            return

        defaultPath = os.path.join(
            self._importExportPath if self._importExportPath else QtCore.QDir.homePath(),
            common.sanitiseFileName(fileName=robot.name()) + '.pdf')

        path, filter = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Export File',
            directory=defaultPath,
            filter=f'{gui.PDFFileFilter};;{gui.JSONFileFilter}')
        if not path:
            return # User cancelled

        self._importExportPath = os.path.dirname(path)

        try:
            if filter == gui.PDFFileFilter:
                dlg = _RobotPDFExportDialog(parent=self)
                if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                    return # User cancelled

                self._progressDlg = _RobotPDFExportDialog(parent=self)

                self._exportJob = jobs.ExportRobotJob(
                    parent=self,
                    robot=robot,
                    filePath=path,
                    includeEditableFields=dlg.isIncludeEditableFieldsChecked(),
                    includeManifestTable=dlg.isIncludeManifestTableChecked(),
                    applySkillModifiers=dlg.isApplySkillModifiersChecked(),
                    colour=not dlg.isBlackAndWhiteChecked(),
                    progressCallback=self._progressDlg.update,
                    finishedCallback=lambda result: self._exportFinished(filePath=path, result=result))

                self.setDisabled(True)
            elif filter == gui.JSONFileFilter:
                robots.writeRobot(robot=robot, filePath=path)
            else:
                raise ValueError(f'Unexpected filter {filter}')
        except Exception as ex:
            message = f'Failed to export robot to {path}'
            logging.error(message, exc_info=ex)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=ex)
            
    def _exportFinished(
            self,
            filePath: str,
            result: typing.Union[str, Exception]
            ) -> None:
        self._progressDlg.close()
        self.setEnabled(True)

        if isinstance(result, Exception):
            message = f'Failed to export robot to {filePath}'
            logging.error(message, exc_info=result)
            gui.MessageBoxEx.critical(
                parent=self,
                text=message,
                exception=result)

        self._exportJob = None
        self._progressDlg = None

class RobotBuilderWindow(gui.WindowWidget):
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

        # TODO: This is a MASSIVE hack. There is a bug where, after the window
        # is first shown, the scroll view jumps back to the top of the config
        # widget if you add a finalisation component then remove it (e.g. adding
        # final cost rounding). I've not been able to work out what the correct
        # fix for this is but I did find it doesn't happen if you do anything
        # that causes the robot to be set on the configuration widget after
        # first display, even if just setting it to the same robot. The biggest
        # downside of the hack is I've not found a way to make saving/restoring
        # the scroll views position between sessions work with it in place.
        self._selectedRobotChanged()

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
            key='RobotManagementWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._robotManagementWidget.restoreState(storedValue)

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

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='InfoWidgetState',
            type=QtCore.QByteArray)
        if storedValue:
            self._infoWidget.restoreState(storedValue)            

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('VerticalSplitterState', self._verticalSplitter.saveState())
        self._settings.setValue('HorizontalSplitterState', self._horizontalSplitter.saveState())
        self._settings.setValue('RobotManagementWidgetState', self._robotManagementWidget.saveState())
        self._settings.setValue('CurrentRobotDisplayModeState', self._currentRobotDisplayModeTabView.saveState())
        self._settings.setValue('ConfigurationState', self._configurationWidget.saveState())
        self._settings.setValue('ResultsDisplayModeState', self._resultsDisplayModeTabView.saveState())
        self._settings.setValue('InfoWidgetState', self._infoWidget.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def closeEvent(self, e: QtGui.QCloseEvent):
        if not self._robotManagementWidget.promptSaveModified(revertUnsaved=True):
            e.ignore()
            return # User cancelled so don't close the window

        return super().closeEvent(e)

    def _setupRobotListControls(self) -> None:
        self._robotManagementWidget = _RobotManagerWidget()
        self._robotManagementWidget.currentChanged.connect(self._selectedRobotChanged)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._robotManagementWidget)

        self._robotsGroupBox = QtWidgets.QGroupBox('Robots')
        self._robotsGroupBox.setLayout(layout)

    def _setupCurrentRobotControls(self) -> None:
        robot = self._robotManagementWidget.current()
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

        configurationScrollArea = gui.ScrollAreaEx()
        configurationScrollArea.setWidgetResizable(True)
        configurationScrollArea.setWidget(wrapperWidget)

        # Use a plain text edit for the notes as we don't want the advanced stuff (tables etc)
        # supported by QTextEdit. This text could end up in the notes section of a pdf so
        # advanced formatting is out
        self._userNotesTextEdit = QtWidgets.QPlainTextEdit()
        self._userNotesTextEdit.setPlainText(robot.userNotes() if robot else '')
        self._userNotesTextEdit.textChanged.connect(self._userNotesChanged)

        self._currentRobotDisplayModeTabView = gui.TabWidgetEx()
        self._currentRobotDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self._currentRobotDisplayModeTabView.addTab(configurationScrollArea, 'Configuration')
        self._currentRobotDisplayModeTabView.addTab(self._userNotesTextEdit, 'User Notes')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._currentRobotDisplayModeTabView)

        self._currentRobotGroupBox = QtWidgets.QGroupBox('Current Robot')
        self._currentRobotGroupBox.setLayout(layout)

    def _setupResultsControls(self) -> None:
        self._usedSlotsLabel = QtWidgets.QLabel()
        self._usedBandwidthLabel = QtWidgets.QLabel()

        labelLayout = QtWidgets.QHBoxLayout()
        labelLayout.setContentsMargins(0, 0, 0, 0)
        labelLayout.addLayout(gui.createLabelledWidgetLayout(
            text='Used Slots: ',
            widget=self._usedSlotsLabel))
        labelLayout.addLayout(gui.createLabelledWidgetLayout(
            text='Used Bandwidth: ',
            widget=self._usedBandwidthLabel))

        self._manifestTable = gui.RobotManifestTable()
        self._infoWidget = gui.RobotInfoWidget()

        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidgetResizable(True)
        # Always show scroll bars as in reduces the amount the ui jumps around
        # when note filters change the table size as the user is typing
        scrollArea.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scrollArea.setWidget(self._infoWidget)

        self._resultsDisplayModeTabView = gui.TabWidgetEx()
        self._resultsDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._resultsDisplayModeTabView.addTab(self._manifestTable, 'Manifest')
        self._resultsDisplayModeTabView.addTab(scrollArea, 'Attributes')

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(labelLayout)
        layout.addWidget(self._resultsDisplayModeTabView)

        self._manifestGroupBox = QtWidgets.QGroupBox('Results')
        self._manifestGroupBox.setLayout(layout)

        self._updateResults()

    def _robotModified(self, value: int) -> None:
        self._robotManagementWidget.markCurrentModified()
        self._updateResults()

    def _updateResults(self) -> None:
        robot = self._configurationWidget.robot()

        defaultTextColour = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorRole.WindowText)

        usedSlots = robot.usedSlots().value()
        maxSlots = robot.maxSlots().value()
        slotsText = f'{usedSlots}/{maxSlots}'
        slotsColour = defaultTextColour
        if usedSlots > maxSlots:
            slotsText += ' - Limit Exceeded!'
            slotsColour = QtCore.Qt.GlobalColor.red
        self._usedSlotsLabel.setText(slotsText)
        palette = self._usedSlotsLabel.palette()
        palette.setColor(
            QtGui.QPalette.ColorRole.WindowText,
            slotsColour)
        self._usedSlotsLabel.setPalette(palette)

        usedBandwidth = robot.usedBandwidth().value()
        maxBandwidth = robot.maxBandwidth().value()
        bandwidthText = f'{usedBandwidth}/{maxBandwidth}'
        bandwidthColour = defaultTextColour
        if usedBandwidth > maxBandwidth:
            bandwidthText += ' - Limit Exceeded!'
            bandwidthColour = QtCore.Qt.GlobalColor.red
        self._usedBandwidthLabel.setText(bandwidthText)
        palette = self._usedBandwidthLabel.palette()
        palette.setColor(
            QtGui.QPalette.ColorRole.WindowText,
            bandwidthColour)
        self._usedBandwidthLabel.setPalette(palette)        

        self._manifestTable.setManifest(manifest=robot.manifest())
        self._infoWidget.setRobot(robot=robot)

    def _selectedRobotChanged(self) -> None:
        robot = self._robotManagementWidget.current()
        isRobot = isinstance(robot, robots.Robot)

        if isRobot:
            isReadOnly = self._robotManagementWidget.isReadOnly(
                constructable=robot)

            # Block signals from configuration widget while configuration widget
            # is updated as the generated change notification would cause the
            # robot to be marked as dirty. Doing this means we need to manually
            # update the result widgets
            with gui.SignalBlocker(widget=self._configurationWidget):
                self._configurationWidget.setRobot(robot=robot)

            with gui.SignalBlocker(widget=self._userNotesTextEdit):
                # Use setPLainText to reset undo/redo history
                self._userNotesTextEdit.setPlainText(robot.userNotes())
                self._userNotesTextEdit.setReadOnly(isReadOnly)

        self._currentRobotDisplayModeTabView.setHidden(not isRobot)

        self._updateResults()

    def _userNotesChanged(self) -> None:
        robot = self._robotManagementWidget.current()
        if not isinstance(robot, robots.Robot):
            return
        robot.setUserNotes(notes=self._userNotesTextEdit.toPlainText())
        self._robotManagementWidget.markCurrentModified()

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='RobotBuilderWelcome')
        message.exec()
