import multiverse
import typing
from PyQt5 import QtCore

class DataDownloadJob(QtCore.QThread):
    # Signals MUST be defined at the class level (i.e. static). Qt does magic
    # when the super() is called to create per-instance interfaces to the
    # signals
    _progressSignal = QtCore.pyqtSignal([multiverse.DataStore.UpdateStage, int, int])
    _finishedSignal = QtCore.pyqtSignal([str], [Exception])

    _remainingTimeSmoothingFactor = 0.05

    def __init__(
            self,
            parent: QtCore.QObject,
            progressCallback: typing.Callable[[multiverse.DataStore.UpdateStage, int, int], typing.Any],
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            ) -> None:
        super().__init__(parent=parent)

        if progressCallback:
            self._progressSignal[multiverse.DataStore.UpdateStage, int, int].connect(progressCallback)
        if finishedCallback:
            self._finishedSignal[str].connect(finishedCallback)
            self._finishedSignal[Exception].connect(finishedCallback)

        self._cancelled = False
        self._lastProgressTime = None
        self._avgFileDownloadTime = None

    def cancel(self, block=False) -> None:
        self._cancelled = True
        if block:
            self.quit()
            self.wait()

    def isCancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        try:
            multiverse.DataStore.instance().downloadSnapshot(
                progressCallback=self._handleProgressUpdate,
                isCancelledCallback=self.isCancelled)

            self._finishedSignal[str].emit('Finished')
        except Exception as ex:
            self._finishedSignal[Exception].emit(ex)

    def _handleProgressUpdate(
            self,
            stage: multiverse.DataStore.UpdateStage,
            progress: int,
            total: int
            ) -> None:
        self._progressSignal[multiverse.DataStore.UpdateStage, int, int].emit(stage, progress, total)
