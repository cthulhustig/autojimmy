import app
import astronomer
import gunsmith
import multiverse
import robots
import typing

class ImportStockUniverseJob(app.StartupJob):
    def __init__(
            self
            ) -> None:
        super().__init__()

    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to import stock universe.'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        multiverse.importStockUniverseSnapshot(
            progressCallback=progressCallback)

class ImportLegacyCustomSectorsJob(app.StartupJob):
    def __init__(
            self,
            directoryPath: str
            ) -> None:
        super().__init__()
        self._directoryPath = directoryPath

    def shouldContinue(self):
        # Failure to import legacy custom sectors doesn't prevent startup
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
            appVersion=app.AppVersion,
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
