import app
import gui
import robots
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: Add welcome message
_WelcomeMessage = """
TODO
""".format(name=app.AppName)

class RobotBuilderWindow(gui.WindowWidget):
    _DefaultTechLevel = 12

    _ConfigurationBottomSpacing = 100

    def __init__(self) -> None:
        super().__init__(
            title='Robot Builder',
            configSection='RobotBuilder')
        
        # TODO: Hacky hard coded robot
        self._robot = robots.Robot(
            robotName='Test Robot',
            techLevel=RobotBuilderWindow._DefaultTechLevel)

        self._setupCurrentRobotControls()
        self._setupResultsControls()

        self._horizontalSplitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._horizontalSplitter.addWidget(self._currentRobotGroupBox)
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
            key='HorizontalSplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._horizontalSplitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='CurrentRobotDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._currentRobotDisplayModeTabView.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RobotConfigurationState',
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

        self._settings.setValue('HorizontalSplitterState', self._horizontalSplitter.saveState())
        self._settings.setValue('CurrentRobotDisplayModeState', self._currentRobotDisplayModeTabView.saveState())
        self._settings.setValue('RobotConfigurationState', self._configurationWidget.saveState())
        self._settings.setValue('ResultsDisplayModeState', self._resultsDisplayModeTabView.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _setupCurrentRobotControls(self) -> None:
        self._configurationWidget = gui.RobotConfigWidget(robot=self._robot)
        self._configurationWidget.robotChanged.connect(self._robotModified)

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
        self._userNotesTextEdit.setPlainText(self._robot.userNotes() if self._robot else '')
        self._userNotesTextEdit.textChanged.connect(self._robotNotesChanged)

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
        self._updateResults()

    def _updateResults(self) -> None:
        self._manifestTable.setManifest(manifest=self._robot.manifest())

    def _robotNotesChanged(self) -> None:
        self._robot.setUserNotes(notes=self._userNotesTextEdit.toPlainText())

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='RobotBuilderWelcome')
        message.exec()
