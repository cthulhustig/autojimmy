import app
import common
import diceroller
import gui
import objectdb
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

# TODO: Welcome message
_WelcomeMessage = """
    TODO
""".format(name=app.AppName)

# TODO: This is a possibly useful example query that looks up a list id
# and returns a comma separated list of all the objects from the list
# as the value for the column rather than the list id. I believe if
# other columns required a lookup of an id then it would require a
# separate LEFT JOIN for that one. I think this would also allow
# different columns to reference different tables (i.e. if there was
# a string on integer table). I think I'd still want to get the list
# id (so objects could be constructed) but I think I could put the
# list object id's into a new column and return both
"""
SELECT
    dr.id,
    dr.name,
    dr.die_count,
    dr.die_type,
    dr.constant_dm,
    dr.has_boon,
    dr.has_bane,
    dr.target_number,
    GROUP_CONCAT(l.object, ',') AS dynamic_dms_list
FROM
    dice_rollers dr
LEFT JOIN
    lists l
ON
    dr.dynamic_dms = l.id
WHERE
    dr.id = 'db701681-82ef-4cf3-a77a-61aeafe0f836'
GROUP BY
    dr.id, dr.name, dr.die_count, dr.die_type, dr.constant_dm, dr.has_boon, dr.has_bane, dr.target_number;
"""
# TODO: It might be better to move the manager widget code into the
# window and have it construct the tree
# - I think it makes conceptual sense as it's controlling what the
#   window is displaying, it should also make fixing the roll history
#   easier
# - It would also allow me to move the database updating code out of
#   the config widget and into the main window so all the database
#   stuff is handled by it
#   - Could trigger it in the main window when it gets notified that
#       the roller has been updated
# TODO: Need to fix switching to previous roll with the history window
# - It's not updating the DiceRollerDatabaseObject held by the manager
#   widget that controls everything
# - Would be easier if manager stuff was in window (see above)
# TODO: Need to disable UI while roll animation is taking place
# - It will stop users accidentally double clicking the roll button
# - It will avoid any oddness with the user changing roller controls or
# switching to a different roller while the animation is in progress
# TODO: Need to use delayed edit notifications for text boxes as there
# is a noticeable lag as it updates the db every time you hit a key
# TODO: Probability graph needs tool tips to show exact probabilities for
# the column under the cursor
# - Will need to take probability type into account (i.e. 'X% change of
# rolling greater or equal to Y')
# TODO: Ability to reorder modifiers
# TODO: Need to be able to rename groups and rollers
# TODO: Need to be able to duplicate rollers (and maybe groups)
# TODO: Need json import/export
# - Ideally selecting multiple rollers to export to a single file (ideally
#   from multiple groups)
class DiceRollerWindow(gui.WindowWidget):
    # When rolling the dice the rolled value can be calculated instantly,
    # however, displaying it straight away can be problematic.  If the new
    # result is the same as the previous result as, to the user, it might
    # not be obvious that the click was registered and a new roll occurred.
    # To try and avoid this confusion, the various results windows should
    # be cleared for a short period of time before showing the new results.
    _ResultsDelay = 700

    def __init__(self) -> None:
        super().__init__(
            title='Dice Roller',
            configSection='DiceRoller')

        self._roller = None
        self._results = None

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
        self._settings.setValue('ResultsState', self._resultsWidget.saveState())
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
        self._resultsWidget = gui.DiceRollDisplayWidget()
        self._resultsWidget.animationComplete.connect(self._resultsAnimationComplete)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._resultsWidget)

        self._resultsGroupBox = QtWidgets.QGroupBox('Roll')
        self._resultsGroupBox.setLayout(groupLayout)

    def _createRollHistoryControls(self) -> None:
        self._historyWidget = gui.DiceRollHistoryWidget()
        self._historyWidget.resultSelected.connect(self._historySelectionChanged)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._historyWidget)

        self._historyGroupBox = QtWidgets.QGroupBox('History')
        self._historyGroupBox.setLayout(groupLayout)

    # NOTE: When a new roller is selected the current results are intentionally
    # not cleared. This is done to make it easier for the user to add the effect
    # from the previous roll to the modifiers of the next roll. The exception to
    # this is the highlight of the rolled result on the probability graph as the
    # result of the previous roll is irrelevant to the the probability of the
    # next roll
    def _rollerSelected(self, roller: diceroller.DiceRollerDatabaseObject) -> None:
        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(roller=roller)

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setRoller(roller=roller)

        self._roller = roller
        self._results = None

    def _rollerDeleted(self, roller: diceroller.DiceRollerDatabaseObject) -> None:
        currentRoller = self._rollerConfigWidget.roller()
        if not currentRoller or (roller.id() != currentRoller.id()):
            return

        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(None)

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setRoller(None)

        with gui.SignalBlocker(self._historyWidget):
            self._historyWidget.purgeHistory(roller)

        self._roller = None
        self._results = None

    def _configChanged(self) -> None:
        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.syncToRoller()

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
            results: diceroller.DiceRollResult
            ) -> None:
        self._roller = roller
        self._results = results

        with gui.SignalBlocker(self._rollerConfigWidget):
            self._rollerConfigWidget.setRoller(roller=roller)

        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setRoller(roller=roller)
            self._resultsWidget.setResults(
                results=results,
                animate=False)

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

        self._results = diceroller.rollDice(
            dieCount=roller.dieCount(),
            dieType=roller.dieType(),
            constantDM=roller.constantDM(),
            hasBoon=roller.hasBoon(),
            hasBane=roller.hasBane(),
            dynamicDMs=modifiers,
            targetNumber=roller.targetNumber())

        # TODO: Need to prevent user manipulating controls while roll animation is in progress
        with gui.SignalBlocker(self._resultsWidget):
            self._resultsWidget.setResults(self._results)

    def _resultsAnimationComplete(self) -> None:
        with gui.SignalBlocker(self._historyWidget):
            self._historyWidget.addResult(self._roller, self._results)

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='DiceRollerWelcome')
        message.exec()
