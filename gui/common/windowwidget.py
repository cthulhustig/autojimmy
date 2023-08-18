import gui
import typing
from PyQt5 import QtWidgets, QtCore, QtGui

class WindowWidget(QtWidgets.QWidget):
    def __init__(
            self,
            title: str,
            configSection: str,
            parent: typing.Optional['QtWidgets.QWidget'] = None,
            flags: QtCore.Qt.WindowType = QtCore.Qt.WindowType(0)
            ) -> None:
        super().__init__(parent=parent, flags=flags)

        self.setWindowTitle(title)
        self._configSection = configSection
        self._settings = None
        self._hasBeenShown = False

    def bringToFront(self) -> None:
        self.setWindowState(
            self.windowState() & ~QtCore.Qt.WindowState.WindowMinimized | QtCore.Qt.WindowState.WindowActive)
        self.show()
        self.activateWindow()

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not self._hasBeenShown:
            self.firstShowEvent(e)
            self._hasBeenShown = True

        if not e.spontaneous():
            # Trigger loading the settings the first time the window is shown
            if not self._settings:
                self._settings = gui.globalWindowSettings()
                self.loadSettings()

            # Setting up the title bar needs to be done before the window is show to take effect. It
            # needs to be done every time the window is shown as the setting is lost if the window is
            # closed then reshown
            gui.configureWindowTitleBar(widget=self)

        return super().showEvent(e)

    def firstShowEvent(self, e: QtGui.QShowEvent) -> None:
        pass

    def closeEvent(self, e: QtGui.QCloseEvent):
        self.saveSettings()
        return super().closeEvent(e)

    # Derived classes should override this to load custom settings when the window is shown for the
    # first time
    def loadSettings(self) -> None:
        self._settings.beginGroup(self._configSection)
        isMaximised = gui.safeLoadSetting(
            settings=self._settings,
            key='WindowIsMaximised',
            type=bool,
            default=False)
        storedGeometry = gui.safeLoadSetting(
            settings=self._settings,
            key='WindowGeometry',
            type=QtCore.QRect if isMaximised else QtCore.QByteArray)
        if storedGeometry:
            if isMaximised:
                self.setGeometry(storedGeometry)
            else:
                self.restoreGeometry(storedGeometry)
        if isMaximised:
            self.showMaximized()
        self._settings.endGroup()

    # Derived classes should override this to store custom settings when the window is closed
    def saveSettings(self) -> None:
        self._settings.beginGroup(self._configSection)
        isMaximised = self.isMaximized()
        self._settings.setValue('WindowIsMaximised', isMaximised)
        if  isMaximised:
            self._settings.setValue('WindowGeometry', self.normalGeometry())
        else:
            self._settings.setValue('WindowGeometry', self.saveGeometry())
        self._settings.endGroup()
