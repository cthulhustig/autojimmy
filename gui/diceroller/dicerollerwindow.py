import app
import common
import diceroller
import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    TODO
""".format(name=app.AppName)

# TODO: I think I need some kind of animation or something to show
# random numbers scrolling by or something. The main issue it solves
# is that, if you happen to roll the same number as you previously
# rolled, it's not obvious anything actually happened so the user
# might think they miss clicked and roll again rather than realising
# what is displayed is their new roll
# - The main thing when implementing this is that the actual roll
# should be made at the very start so the final value is known the
# entire time the animation is playing.
# TODO: There success/failure types based on effect that I should
# probably display (e.g. 'Effect: # (Type)') (Core 2e p59 and 2022 p61)
# TODO: Should show possible range of roll as settings are changed
# - A graph showing probability of different values would be pretty cool
# TODO: Remove blank space at bottom of modifier list (when it's shown)
class DiceRollerWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Dice Roller',
            configSection='DiceRoller')

        self._roller = diceroller.DiceRoller(
            name='Hack Roller',
            dieCount=1,
            dieType=common.DieType.D6)

        self._createRollerConfigControls()
        self._createRollResultsControls()

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._configGroupBox)
        self._splitter.addWidget(self._resultsGroupBox)

        windowLayout = QtWidgets.QHBoxLayout()
        windowLayout.addWidget(self._splitter)

        self.setLayout(windowLayout)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='SplitterState',
            type=QtCore.QByteArray)
        if storedValue:
            self._splitter.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='RollDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._rollDisplayModeTabView.restoreState(storedValue)

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('SplitterState', self._splitter.saveState())
        self._settings.setValue('RollDisplayModeState', self._rollDisplayModeTabView.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _createRollerConfigControls(self) -> None:
        self._rollerConfigWidget = gui.DiceRollerConfigWidget(
            roller=self._roller)
        self._rollerConfigWidget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self._rollerConfigWidget.configChanged.connect(
            self._configChanged)

        self._rollButton = QtWidgets.QPushButton('Roll Dice')
        self._rollButton.clicked.connect(self._rollDice)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.setContentsMargins(0, 0, 0, 0)
        groupLayout.addWidget(self._rollerConfigWidget)
        groupLayout.addWidget(self._rollButton)

        self._configGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configGroupBox.setLayout(groupLayout)

    def _createRollResultsControls(self) -> None:
        self._simpleResultsWidget = gui.DiceRollResultsWidget()
        self._detailedResultsWidget = gui.DiceRollResultsTable()
        self._probabilityGraph = gui.DiceRollerProbabilityGraph()

        # TODO: This should be changed when I support multiple rollers
        self._probabilityGraph.setRoller(self._roller)

        self._rollDisplayModeTabView = gui.TabWidgetEx()
        self._rollDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._rollDisplayModeTabView.addTab(self._simpleResultsWidget, 'Simple')
        self._rollDisplayModeTabView.addTab(self._detailedResultsWidget, 'Detailed')
        self._rollDisplayModeTabView.addTab(self._probabilityGraph, 'Probabilities')

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._rollDisplayModeTabView)

        self._resultsGroupBox = QtWidgets.QGroupBox('Roll')
        self._resultsGroupBox.setLayout(groupLayout)

    def _configChanged(self) -> None:
        self._probabilityGraph.syncToRoller()

    def _rollDice(self) -> None:
        result = self._roller.roll()
        self._simpleResultsWidget.setResults(result)
        self._detailedResultsWidget.setResults(result)
        self._probabilityGraph.setHighlightRoll(result.total())

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='DiceRollerWelcome')
        message.exec()
