import app
import gui
import logging
import typing
from PyQt5 import QtCore, QtGui, QtWidgets

class StartupJobThread(QtCore.QThread):
    progress = QtCore.pyqtSignal([str, int, int])

    def __init__(
            self,
            job: app.StartupJob,
            parent: QtCore.QObject
            ) -> None:
        super().__init__(parent=parent)
        self._job = job

    def run(self) -> None:
        self._job.run(self.notifyProgressUpdate)

    def notifyProgressUpdate(
            self,
            stage: str,
            current: int,
            total: int
            ) -> None:
        self.progress[str, int, int].emit(stage, current, total)

# This intentionally doesn't inherit from DialogEx. We don't want it saving its size as it
# can cause incorrect sizing if the font scaling is increased then decreased
class StartupProgressDialog(QtWidgets.QDialog):
    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
            ) -> None:
        super().__init__(parent=parent)

        self._jobQueue: typing.List[app.StartupJob] = [] # NOTE: This is a queue of job types
        self._currentJob = None
        self._currentThread = None
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

    def setMultiverseSyncDir(self, directory: typing.Optional[str]) -> None:
        self._multiverseSyncDir = directory

    def setCustomSectorImportDir(self, directory: typing.Optional[str]) -> None:
        self._customSectorImportDir = directory

    def addJob(self, job: app.StartupJob) -> None:
        self._jobQueue.append(job)

    def exception(self) -> typing.Optional[Exception]:
        return self._exception

    def exec(self) -> int:
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
            self._currentJob = self._jobQueue.pop(0)
            self._currentThread = StartupJobThread(
                job=self._currentJob,
                parent=self)
            self._currentThread.finished.connect(self._jobFinished)
            self._currentThread.progress.connect(self._updateProgress)
            self._currentThread.start()
        except Exception as ex:
            self._exception = ex
            self.close()

    def _updateProgress(
            self,
            stage: str,
            current: int,
            total: int
            ) -> None:
        self._textLabel.setText(stage)
        self._progressBar.setMaximum(int(total))
        self._progressBar.setValue(int(current))

    def _jobFinished(self) -> None:
        self._currentThread.finished.disconnect(self._jobFinished)
        self._currentThread.progress.disconnect(self._updateProgress)

        message = self._currentJob.errorMessage()
        if message:
            exception = self._currentJob.exception()
            logging.error(message, exc_info=exception)
            gui.MessageBoxEx.critical(message, exception=exception)

        shouldContinue = self._currentJob.shouldContinue()

        # Wait for thread to finish to prevent "QThread: Destroyed while thread is still running"
        # and a crash on Linux
        self._currentThread.wait()
        self._currentThread = None
        self._currentJob = None

        if shouldContinue:
            if len(self._jobQueue) > 0:
                self._startNextJob()
            else:
                # There are no more jobs on the queue so call accept to close the
                # dialog and indicate all mandatory startup jobs completed
                # successfully
                self.accept()
        else:
            self.close()
