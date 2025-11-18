import app
import astronomer
import gunsmith
import multiverse
import robots
import typing

class SyncMultiverseDbJob(app.StartupJob):
    def __init__(
            self,
            directoryPath: str,
            isInitialImport: bool
            ) -> None:
        super().__init__()
        self._directoryPath = directoryPath
        self._isInitialImport = isInitialImport

    def shouldContinue(self) -> bool:
        if not self.exception():
            return True

        # An exception occurred. Abort startup if this is the initial import as there won't
        # be any data to load. If it's just an update to the default universe, continue
        # with the old data.
        return not self._isInitialImport

    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to import default universe.' if self._isInitialImport else 'Failed to update default universe'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        multiverse.MultiverseDb.instance().importDefaultUniverse(
            directoryPath=self._directoryPath,
            progressCallback=progressCallback)

class ImportCustomSectorsJob(app.StartupJob):
    def __init__(
            self,
            directoryPath: str
            ) -> None:
        super().__init__()
        self._directoryPath = directoryPath

    def shouldContinue(self):
        # Failure to import legacy custom sectors doesn't prevent startup
        # there just won't be any custom sectors
        return True

    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to import legacy custom sectors.'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        multiverse.importLegacyCustomSectors(
            directoryPath=self._directoryPath,
            progressCallback=progressCallback)

class LoadSectorsJob(app.StartupJob):
    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to load sectors.'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        astronomer.WorldManager.instance().loadSectors(
            progressCallback=progressCallback)

class LoadRobotsJob(app.StartupJob):
    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to load robots.'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        localProgressCallback = \
            lambda stage, progress, total: progressCallback('Loading: Robot - ' + stage, progress, total)
        robots.RobotStore.instance().loadRobots(
            progressCallback=localProgressCallback)

class LoadWeaponsJob(app.StartupJob):
    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to load weapons.'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        localProgressCallback = \
            lambda stage, progress, total: progressCallback('Loading: Weapon - ' + stage, progress, total)
        gunsmith.WeaponStore.instance().loadWeapons(
            progressCallback=localProgressCallback)
