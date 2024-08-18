import app
import common
import diceroller
import gui
from PyQt5 import QtWidgets

_WelcomeMessage = """
    TODO
""".format(name=app.AppName)

class DiceRollerWindow(gui.WindowWidget):
    def __init__(self) -> None:
        super().__init__(
            title='Dice Roller',
            configSection='DiceRoller')

        self._unnamedIndex = 1

        hackRoller = diceroller.DiceRoller(
            name='Hack Roller',
            dieCount=1,
            dieType=common.DieType.D6)
        self._rollerWidget = gui.DiceRollerWidget(
            roller=hackRoller)

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._rollerWidget)

        self.setLayout(windowLayout)

    def loadSettings(self) -> None:
        super().loadSettings()

        self._settings.beginGroup(self._configSection)

        # TODO: Load Settings

        self._settings.endGroup()

    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)

        # TODO: Save Settings

        self._settings.endGroup()

        super().saveSettings()

    def _showWelcomeMessage(self) -> None:
        message = gui.InfoDialog(
            parent=self,
            title=self.windowTitle(),
            html=_WelcomeMessage,
            noShowAgainId='DiceRollerWelcome')
        message.exec()
