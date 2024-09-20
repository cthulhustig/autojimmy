import app
import common
import diceroller
import gui
import objectdb
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
# TODO: Need a roll history window
# - Important in case the user somehow manages to clear the previous
# results when switching from attack to damage roll as they wouldn't
# be able to go back to see what the effect was. Currently the old
# result will remain until you next click roll but I shouldn't assume
# that will always be the case in all situations
# - If i'm storing things in the database I could make an all time
# roll history but that might just be pointless db bloat
# - What would be really cool is if it was a list rather than just
# text so you could click on things to go back to see all the
# details of previous rolls (basically it would put the results
# back in the results window)
class DiceRollerWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Dice Roller',
            configSection='DiceRoller')

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
            key='RollDisplayModeState',
            type=QtCore.QByteArray)
        if storedValue:
            self._rollDisplayModeTabView.restoreState(storedValue)

        storedValue = gui.safeLoadSetting(
            settings=self._settings,
            key='ProbabilitiesState',
            type=QtCore.QByteArray)
        if storedValue:
            self._probabilityGraph.restoreState(storedValue)

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
        self._settings.setValue('RollDisplayModeState', self._rollDisplayModeTabView.saveState())
        self._settings.setValue('ProbabilitiesState', self._probabilityGraph.saveState())
        self._settings.setValue('HistoryState', self._historyWidget.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _createRollerManagerControls(self) -> None:
        self._rollerManagerWidget = gui.DiceRollerManagerWidget()
        self._rollerManagerWidget.rollerSelected.connect(self._rollerSelected)
        self._rollerManagerWidget.rollerDeleted.connect(self._rollerDeleted)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.setContentsMargins(0, 0, 0, 0)
        groupLayout.addWidget(self._rollerManagerWidget)

        self._managerGroupBox = QtWidgets.QGroupBox('Dice Rollers')
        self._managerGroupBox.setLayout(groupLayout)

    def _createRollerConfigControls(self) -> None:
        self._rollerConfigWidget = gui.DiceRollerConfigWidget()
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

        self._rollDisplayModeTabView = gui.TabWidgetEx()
        self._rollDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._rollDisplayModeTabView.addTab(self._simpleResultsWidget, 'Simple')
        self._rollDisplayModeTabView.addTab(self._detailedResultsWidget, 'Detailed')
        self._rollDisplayModeTabView.addTab(self._probabilityGraph, 'Probabilities')

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._rollDisplayModeTabView)

        self._resultsGroupBox = QtWidgets.QGroupBox('Roll')
        self._resultsGroupBox.setLayout(groupLayout)

    def _createRollHistoryControls(self) -> None:
        self._historyWidget = gui.DiceRollHistoryWidget()
        self._historyWidget.resultSelected.connect(self._historySelectionChanged)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._historyWidget)

        self._historyGroupBox = QtWidgets.QGroupBox('History')
        self._historyGroupBox.setLayout(groupLayout)

    def _rollerSelected(self, roller: diceroller.DiceRollerDatabaseObject) -> None:
        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(roller=roller)

        with gui.SignalBlocker(self._probabilityGraph):
            self._probabilityGraph.setRoller(roller=roller)

    def _rollerDeleted(self, roller: diceroller.DiceRollerDatabaseObject) -> None:
        currentRoller = self._rollerConfigWidget.roller()
        if not currentRoller or (roller.id() != currentRoller.id()):
            return

        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(None)

        with gui.SignalBlocker(self._probabilityGraph):
            self._probabilityGraph.setRoller(None)

        with gui.SignalBlocker(self._historyWidget):
            self._historyWidget.purgeHistory(roller)

    def _configChanged(self) -> None:
        with gui.SignalBlocker(self._probabilityGraph):
            self._probabilityGraph.syncToRoller()

    # TODO: This is borked, it's passing the historic roller object to
    # the config, this roller will have the correct parent id set to
    # reference the group it was part of but this instance of the roller
    # won't be the one in the list of roller instances held by the group
    # that the manager widget is using.
    # This means config changes will be made to the historic roller by
    # the config widget (and written to the db), however if you were then
    # to write the group held by the manager widget, it would revert the
    # changes that had been made to the roller.
    def _historySelectionChanged(
            self,
            roller: diceroller.DiceRollerDatabaseObject,
            result: diceroller.DiceRollResult
            ) -> None:
        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(roller=roller)

        with gui.SignalBlocker(self._simpleResultsWidget):
            self._simpleResultsWidget.setResults(result)

        with gui.SignalBlocker(self._detailedResultsWidget):
            self._detailedResultsWidget.setResults(result)

        with gui.SignalBlocker(self._probabilityGraph):
            self._probabilityGraph.setRoller(roller=roller)
            self._probabilityGraph.setHighlightRoll(result.total())

    def _rollDice(self) -> None:
        roller = self._rollerConfigWidget.roller()
        if not roller:
            # TODO: Do something?
            return
        modifiers = []
        for modifier in roller.dynamicDMs():
            assert(isinstance(modifier, diceroller.DiceModifierDatabaseObject))
            if modifier.enabled():
                modifiers.append((modifier.name(), modifier.value()))
        result = diceroller.rollDice(
            dieCount=roller.dieCount(),
            dieType=roller.dieType(),
            constantDM=roller.constantDM(),
            hasBoon=roller.hasBoon(),
            hasBane=roller.hasBane(),
            dynamicDMs=modifiers,
            targetNumber=roller.targetNumber())

        with gui.SignalBlocker(self._simpleResultsWidget):
            self._simpleResultsWidget.setResults(result)

        with gui.SignalBlocker(self._detailedResultsWidget):
            self._detailedResultsWidget.setResults(result)

        with gui.SignalBlocker(self._probabilityGraph):
            self._probabilityGraph.setHighlightRoll(result.total())

        with gui.SignalBlocker(self._historyWidget):
            self._historyWidget.addResult(roller, result)

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='DiceRollerWelcome')
        message.exec()
