import datetime
import travellermap
import typing
from PyQt5 import QtCore

class DataDownloadJob(QtCore.QThread):
    # Signals MUST be defined at the class level (i.e. static). Qt does magic
    # when the super() is called to create per-instance interfaces to the
    # signals
    _progressSignal = QtCore.pyqtSignal([str, int, int], [str, int, int, datetime.timedelta])
    _finishedSignal = QtCore.pyqtSignal([str], [Exception])

    _remainingTimeSmoothingFactor = 0.05

    def __init__(
            self,
            parent: QtCore.QObject,
            travellerMapUrl: str,
            progressCallback: typing.Callable[[str, int, int, typing.Optional[datetime.timedelta]], typing.Any],
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            ) -> None:
        super().__init__(parent=parent)

        self._travellerMapUrl = travellerMapUrl

        if progressCallback:
            self._progressSignal[str, int, int].connect(progressCallback)
            self._progressSignal[str, int, int, datetime.timedelta].connect(progressCallback)
        if finishedCallback:
            self._finishedSignal[str].connect(finishedCallback)
            self._finishedSignal[Exception].connect(finishedCallback)

        self._cancelled = False
        self._lastProgressTime = None
        self._avgFileDownloadTime = None

        self.start()

    def cancel(self, block=False) -> None:
        self._cancelled = True
        if block:
            self.quit()
            self.wait()

    def isCancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        try:
            travellermap.DataStore.instance().downloadData(
                travellerMapUrl=self._travellerMapUrl,
                progressCallback=self._handleProgressUpdate,
                isCancelledCallback=self.isCancelled)

            self._finishedSignal[str].emit('Finished')
        except Exception as ex:
            self._finishedSignal[Exception].emit(ex)

    def _handleProgressUpdate(
            self,
            filePath: str,
            current: int,
            total: int
            ) -> None:
        now = datetime.datetime.utcnow()
        remainingTime = None
        if self._lastProgressTime:
            timeForLastFile = now - self._lastProgressTime
            if self._avgFileDownloadTime:
                self._avgFileDownloadTime = (self._remainingTimeSmoothingFactor * timeForLastFile) + \
                    ((1.0 - self._remainingTimeSmoothingFactor) * self._avgFileDownloadTime)
            else:
                self._avgFileDownloadTime = timeForLastFile

            remainingFiles = (total - current) + 1
            remainingTime = self._avgFileDownloadTime * remainingFiles
        self._lastProgressTime = now

        if remainingTime:
            self._progressSignal[str, int, int, datetime.timedelta].emit(filePath, current, total, remainingTime)
        else:
            self._progressSignal[str, int, int].emit(filePath, current, total)
