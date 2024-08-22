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

class RollResultWidget(QtWidgets.QWidget):
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

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        self._settings.setValue('SplitterState', self._splitter.saveState())

        self._settings.endGroup()

        super().saveSettings()

    def _createRollerConfigControls(self) -> None:
        self._rollerConfigWidget = gui.DiceRollerConfigWidget(
            roller=self._roller)
        self._rollerConfigWidget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            QtWidgets.QSizePolicy.Policy.MinimumExpanding)

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.setContentsMargins(0, 0, 0, 0)
        groupLayout.addWidget(self._rollerConfigWidget)

        self._configGroupBox = QtWidgets.QGroupBox('Configuration')
        self._configGroupBox.setLayout(groupLayout)

    def _createRollResultsControls(self) -> None:
        self._rollButton = QtWidgets.QPushButton('Roll Dice')
        self._rollButton.clicked.connect(self._rollDice)

        self._resultsWidget = RollResultWidget()

        groupLayout = QtWidgets.QVBoxLayout()
        groupLayout.addWidget(self._rollButton)
        groupLayout.addWidget(self._resultsWidget)

        self._resultsGroupBox = QtWidgets.QGroupBox('Roll')
        self._resultsGroupBox.setLayout(groupLayout)

    def _rollDice(self) -> None:
        result = self._roller.roll()
        total=result.total()
        self._resultsWidget.setText(str(total.value()))

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='DiceRollerWelcome')
        message.exec()
