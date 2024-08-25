from PyQt5.QtGui import QPaintEvent
import app
import common
import diceroller
import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

_WelcomeMessage = """
    TODO
""".format(name=app.AppName)

# TODO: Does this need to take interface scaling into account?
class FullSizeTextWidget(QtWidgets.QWidget):
    def __init__(
            self,
            text: str = '',
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)
        self._text = text
        self._configureFont()

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text
        self._configureFont()
        self.repaint()

    def resizeEvent(self, a0: QtGui.QResizeEvent | None) -> None:
        super().resizeEvent(a0)
        self._configureFont()

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QtGui.QPainter(self)

        usableArea = self.rect()
        painter.drawText(
            usableArea,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter,
            self._text)
        painter.end()

    # Based on some code from here
    # https://stackoverflow.com/questions/42652738/how-to-automatically-increase-decrease-text-size-in-label-in-qt
    def _configureFont(self) -> None:
        text = self.text()
        font = self.font()
        size = font.pointSize()
        fontMetrics = QtGui.QFontMetrics(font)
        usableArea = self.rect()
        contentRect = fontMetrics.boundingRect(
            usableArea,
            0,
            text)

        # decide whether to increase or decrease
        if (contentRect.height() > usableArea.height()) or \
            (contentRect.width() > usableArea.width()):
            step = -1
        else:
            step = 1

        # iterate until text fits best into rectangle of label
        while(True):
            font.setPointSize(size + step)
            fontMetrics = QtGui.QFontMetrics(font)
            contentRect = fontMetrics.boundingRect(
                usableArea,
                0,
                text)
            if (step < 0):
                if (size <= 1):
                    break
                size += step
                if (contentRect.height() < usableArea.height()) and \
                    (contentRect.width() < usableArea.width()):
                    # Stop as soon as the new size would mean both the
                    # content dimensions are within the usable area
                    break
            else:
                if (contentRect.height() > usableArea.height()) or \
                    (contentRect.width() > usableArea.width()):
                    # Stop as soon as the new size would mean either of
                    # the content dimensions were larger than the usable
                    # area
                    break
                size += step

        font.setPointSize(size)
        self.setFont(font)

class DiceRollResultsWidget(QtWidgets.QWidget):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        self._results = None

        self._totalWidget = FullSizeTextWidget()

        self._targetWidget = FullSizeTextWidget()
        self._targetWidget.setHidden(True)

        widgetLayout = QtWidgets.QVBoxLayout()
        widgetLayout.setContentsMargins(0, 0, 0, 0)
        widgetLayout.addWidget(self._totalWidget, 5)
        widgetLayout.addWidget(self._targetWidget, 1)

        self.setLayout(widgetLayout)

    def setResults(
            self,
            results: typing.Optional[diceroller.DiceRollResult]
            ) -> None:
        if results:
            total = results.total()
            target = results.target()
            effect = results.effect()
            self._totalWidget.setText(str(total.value()))
            if target:
                targetText = 'Pass' if total.value() >= target.value() else 'Fail'
                if effect and effect.value() > 0:
                    targetText += f' (Effect: {effect.value()})'
                self._targetWidget.setText(targetText)
            self._targetWidget.setHidden(target == None)
        else:
            self._totalWidget.setText('')
            self._targetWidget.setText('')
            self._targetWidget.setHidden(True)

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

        self._rollButton = QtWidgets.QPushButton('Roll Dice')
        self._rollButton.clicked.connect(self._rollDice)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.setContentsMargins(0, 0, 0, 0)
        groupLayout.addWidget(self._rollerConfigWidget)
        groupLayout.addWidget(self._rollButton)

        self._configGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configGroupBox.setLayout(groupLayout)

    def _createRollResultsControls(self) -> None:
        self._simpleResultsWidget = DiceRollResultsWidget()
        self._detailedResultsWidget = gui.DiceRollResultsTable()

        self._rollDisplayModeTabView = gui.TabWidgetEx()
        self._rollDisplayModeTabView.setTabPosition(QtWidgets.QTabWidget.TabPosition.East)
        self._rollDisplayModeTabView.addTab(self._simpleResultsWidget, 'Simple')
        self._rollDisplayModeTabView.addTab(self._detailedResultsWidget, 'Detailed')

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._rollDisplayModeTabView)

        self._resultsGroupBox = QtWidgets.QGroupBox('Roll')
        self._resultsGroupBox.setLayout(groupLayout)

    def _rollDice(self) -> None:
        result = self._roller.roll()
        self._simpleResultsWidget.setResults(result)
        self._detailedResultsWidget.setResults(result)

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='DiceRollerWelcome')
        message.exec()
