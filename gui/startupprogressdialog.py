import app
import gui
import jobs
import logging
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

# This intentionally doesn't inherit from DialogEx. We don't want it saving its size as it
# can cause incorrect sizing if the font scaling is increased then decreased
class StartupProgressDialog(QtWidgets.QDialog):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._loadJob = None
        self._exception = None

        self._textLabel = QtWidgets.QLabel()
        self._progressBar = QtWidgets.QProgressBar()

        windowLayout = QtWidgets.QVBoxLayout()
        windowLayout.addWidget(self._textLabel)
        windowLayout.addWidget(self._progressBar)

        self.setWindowTitle('Starting')
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        self.setLayout(windowLayout)
        self.setWindowFlags(
            ((self.windowFlags() | QtCore.Qt.WindowType.CustomizeWindowHint | QtCore.Qt.WindowType.FramelessWindowHint) & ~QtCore.Qt.WindowType.WindowCloseButtonHint))
        self.setFixedWidth(int(300 * app.Config.instance().interfaceScale()))
        self.setSizeGripEnabled(False)

        # Setting up the title bar needs to be done before the window is show to take effect. It
        # needs to be done every time the window is shown as the setting is lost if the window is
        # closed then reshown
        gui.configureWindowTitleBar(widget=self)

    def exception(self) -> Exception:
        return self._exception

    def exec(self) -> int:
        try:
            self._loadJob = jobs.StartupJob(
                parent=self,
                startProxy=app.Config.instance().mapProxyPort() != 0,
                progressCallback=self._updateProgress,
                finishedCallback=self._startupFinished)
        except Exception as ex:
            self._exception = ex
            self.close()

        return super().exec()

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            # Setting up the title bar needs to be done before the window is show to take effect. It
            # needs to be done every time the window is shown as the setting is lost if the window is
            # closed then reshown
            gui.configureWindowTitleBar(widget=self)

        return super().showEvent(e)

    def _updateProgress(
            self,
            stage: str,
            current: int,
            total: int
            ) -> None:
        self._textLabel.setText(stage)
        self._progressBar.setMaximum(int(total))
        self._progressBar.setValue(int(current))

    def _startupFinished(
            self,
            result: typing.Union[str, Exception]
            ) -> None:
        if isinstance(result, Exception):
            self._exception = result
            self.close()
        else:
            self.accept()

        # Wait for thread to finish to prevent "QThread: Destroyed while thread is still running"
        # and a crash on Linux
        self._loadJob.wait()
        self._loadJob = None
