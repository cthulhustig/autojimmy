import gunsmith
import traveller
import proxy
import typing
from PyQt5 import QtCore

class StartupJob(QtCore.QThread):
    # Signals MUST be defined at the class level (i.e. static). Qt does magic
    # when the super() is called to create per-instance interfaces to the
    # signals
    _progressSignal = QtCore.pyqtSignal([str, int, int])
    _finishedSignal = QtCore.pyqtSignal([str], [Exception])

    def __init__(
            self,
            parent: QtCore.QObject,
            startProxy: bool,
            progressCallback: typing.Callable[[str, int, int], typing.Any],
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            ) -> None:
        super().__init__(parent=parent)

        self._startProxy = startProxy
        self._dataType = None

        if progressCallback:
            self._progressSignal[str, int, int].connect(progressCallback)
        if finishedCallback:
            self._finishedSignal[str].connect(finishedCallback)
            self._finishedSignal[Exception].connect(finishedCallback)

        self.start()

    def run(self) -> None:
        try:
            self._dataType = 'Loading: Sector - '
            traveller.WorldManager.instance().loadSectors(
                progressCallback=self._handleProgressUpdate)

            self._dataType = 'Loading: Weapon - '
            gunsmith.WeaponStore.instance().loadWeapons(
                progressCallback=self._handleProgressUpdate)
            
            if self._startProxy:
                self._dataType = 'Proxy: '
                proxy.MapProxy.instance().start(
                    progressCallback=self._handleProgressUpdate)

            self._finishedSignal[str].emit('Finished')
        except Exception as ex:
            self._finishedSignal[Exception].emit(ex)

    def _handleProgressUpdate(
            self,
            stage: str,
            current: int,
            total: int
            ) -> None:
        self._progressSignal[str, int, int].emit(self._dataType + stage, current, total)