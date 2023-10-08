import travellermap
import typing
from PyQt5 import QtCore

class PosterJob(QtCore.QThread):
    _finishedSignal = QtCore.pyqtSignal([str], [Exception])

    def __init__(
            self,
            parent: QtCore.QObject,
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            ) -> None:
        super().__init__(parent=parent)

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
            # TODO: Generate posters

            self._finishedSignal[str].emit('Finished')
        except Exception as ex:
            self._finishedSignal[Exception].emit(ex)

