import app
import gui
import jobs
import logging
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

# This intentionally doesn't inherit from DialogEx. We don't want it saving its size as it
# can cause incorrect sizing if the font scaling is increased then decreased
class StartupProgressDialog(QtWidgets.QDialog):
    _JobProgressPrefixMap = {
        jobs.LoadSectorsJob: '',
        jobs.LoadWeaponsJob: 'Loading: Weapon - ',
        jobs.LoadRobotsJob: 'Loading: Robot - '}

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._jobQueue: typing.List[typing.Type[jobs.StartupJobBase]] = [] # NOTE: This is a queue of job types
        self._currentJob = None
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
        self.setFixedWidth(int(300 * gui.interfaceScale()))
        self.setSizeGripEnabled(False)

        # Setting up the title bar needs to be done before the window is show to take effect. It
        # needs to be done every time the window is shown as the setting is lost if the window is
        # closed then reshown
        gui.configureWindowTitleBar(widget=self)

    def exception(self) -> typing.Optional[Exception]:
        return self._exception

    def exec(self) -> int:
        self._jobQueue.append(jobs.LoadSectorsJob)
        self._jobQueue.append(jobs.LoadWeaponsJob)
        self._jobQueue.append(jobs.LoadRobotsJob)

        self._startNextJob()

        return super().exec()

    def showEvent(self, e: QtGui.QShowEvent) -> None:
        if not e.spontaneous():
            # Setting up the title bar needs to be done before the window is show to take effect. It
            # needs to be done every time the window is shown as the setting is lost if the window is
            # closed then reshown
            gui.configureWindowTitleBar(widget=self)

        return super().showEvent(e)

    def _startNextJob(self) -> None:
        try:
            jobType = self._jobQueue.pop(0)
            self._currentJob = jobType(
                parent=self,
                progressCallback=self._updateProgress,
                finishedCallback=self._jobFinished)
            self._currentJob.start()
        except Exception as ex:
            self._exception = ex
            self.close()

    def _updateProgress(
            self,
            stage: str,
            current: int,
            total: int
            ) -> None:
        prefix = StartupProgressDialog._JobProgressPrefixMap.get(type(self._currentJob))
        if prefix:
            stage = prefix + stage

        self._textLabel.setText(stage)
        self._progressBar.setMaximum(int(total))
        self._progressBar.setValue(int(current))

    def _jobFinished(
            self,
            result: typing.Union[str, Exception]
            ) -> None:
        if isinstance(result, Exception):
            self._exception = result
            self.close()

        # Wait for thread to finish to prevent "QThread: Destroyed while thread is still running"
        # and a crash on Linux
        self._currentJob.wait()
        self._currentJob = None

        if self._exception is None:
            if len(self._jobQueue) > 0:
                self._startNextJob()
            else:
                self.accept()
