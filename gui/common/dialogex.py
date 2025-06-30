import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class DialogEx(QtWidgets.QDialog):
    def __init__(
            self,
            title: typing.Optional[str] = None,
            configSection: typing.Optional[str] = None,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent)

        if title != None:
            self.setWindowTitle(title)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowContextHelpButtonHint, False)
        self._configSection = configSection
        self._settings = gui.globalWindowSettings()
        self._hasBeenShown = False

    def showMaximizeButton(self, show: bool = True) -> None:
        self.setWindowFlag(QtCore.Qt.WindowType.WindowMaximizeButtonHint, show)

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            # Setting up the title bar needs to be done before the window is show to take effect. It
            # needs to be done every time the window is shown as the setting is lost if the window is
            # closed then reshown. Do this before calling first show so we don't get stuck with the
            # wrong title bar if a derived class overrides firstShowEvent and blocks
            gui.configureWindowTitleBar(widget=self)

        if not self._hasBeenShown:
            self.firstShowEvent(e)
            self._hasBeenShown = True

        return super().showEvent(e)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        self.loadSettings()

    def done(self, result: int):
        self.saveSettings()
        return super().done(result)

    # Derived classes should override this to load custom settings when the window is shown for the
    # first time
    def loadSettings(self) -> None:
        if not self._configSection:
            return

        self._settings.beginGroup(self._configSection)
        storedGeometry = gui.safeLoadSetting(
            settings=self._settings,
            key='WindowGeometry',
            type=QtCore.QByteArray)
        if storedGeometry:
            self.restoreGeometry(storedGeometry)
        self._settings.endGroup()

    # Derived classes should override this to store custom settings when the window is closed
    def saveSettings(self) -> None:
        if not self._configSection:
            return

        self._settings.beginGroup(self._configSection)
        self._settings.setValue('WindowGeometry', self.saveGeometry())
        self._settings.endGroup()
