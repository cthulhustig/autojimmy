import astronomer
import gunsmith
import multiverse
import robots
import typing
from PyQt5 import QtCore

class StartupJobBase(QtCore.QThread):
    # Signals MUST be defined at the class level (i.e. static). Qt does magic
    # when the super() is called to create per-instance interfaces to the
    # signals
    _progressSignal = QtCore.pyqtSignal([str, int, int])
    _finishedSignal = QtCore.pyqtSignal([str], [Exception])

    def __init__(
            self,
            parent: QtCore.QObject,
            progressCallback: typing.Callable[[str, int, int], typing.Any],
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            ) -> None:
        super().__init__(parent=parent)

        if progressCallback:
            self._progressSignal[str, int, int].connect(progressCallback)
        if finishedCallback:
            self._finishedSignal[str].connect(finishedCallback)
            self._finishedSignal[Exception].connect(finishedCallback)

    def run(self) -> None:
        try:
            self.executeJob()
            self._finishedSignal[str].emit('Finished')
        except Exception as ex:
            self._finishedSignal[Exception].emit(ex)

    def executeJob(self) -> None:
        raise RuntimeError('The executeJob method must be implemented by classes derived from StartupJobBase')

    def _handleProgressUpdate(
            self,
            stage: str,
            current: int,
            total: int
            ) -> None:
        self._progressSignal[str, int, int].emit(stage, current, total)

class SyncMultiverseDbJob(StartupJobBase):
    def __init__(
            self,
            parent: QtCore.QObject,
            directoryPath: str,
            progressCallback: typing.Callable[[str, int, int], typing.Any],
            finishedCallback: typing.Callable[[typing.Union[str, Exception]], typing.Any],
            ) -> None:
        super().__init__(parent, progressCallback, finishedCallback)
        self._directoryPath = directoryPath

    def executeJob(self) -> None:
        multiverse.MultiverseDb.instance().importDefaultUniverse(
            directoryPath=self._directoryPath,
            progressCallback=self._handleProgressUpdate)

class LoadSectorsJob(StartupJobBase):
    def executeJob(self) -> None:
        astronomer.WorldManager.instance().loadSectors(
            progressCallback=self._handleProgressUpdate)

class LoadRobotsJob(StartupJobBase):
    def executeJob(self) -> None:
        robots.RobotStore.instance().loadRobots(
            progressCallback=self._handleProgressUpdate)

class LoadWeaponsJob(StartupJobBase):
    def executeJob(self) -> None:
        gunsmith.WeaponStore.instance().loadWeapons(
            progressCallback=self._handleProgressUpdate)
