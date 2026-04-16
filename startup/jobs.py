import app
import astronomer
import gunsmith
import logging
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

        # If the config doesn't have a universe set, set it to the stock universe
        # NOTE: It will be set to an empty string (rather than None) if not set
        currentUniverseId = app.Config.instance().value(option=app.ConfigOption.Universe)
        if not currentUniverseId:
            stockUniverseInfo = multiverse.UniverseManager.instance().stockUniverseInfo()
            if stockUniverseInfo is None:
                raise RuntimeError('No stock universe found after import')
            app.Config.instance().setValue(
                option=app.ConfigOption.Universe,
                value=stockUniverseInfo.id())

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

        # Always update the config to set the universe to the imported custom
        # universe
        app.Config.instance().setValue(
            option=app.ConfigOption.Universe,
            value=multiverse.customUniverseId())

class InitWorldManager(app.StartupJob):
    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to init world manager.'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        currentUniverseId = app.Config.instance().value(option=app.ConfigOption.Universe)
        currentUniverseInfo = multiverse.UniverseManager.instance().universeInfo(currentUniverseId)
        if currentUniverseInfo is None:
            stockUniverseInfo = multiverse.UniverseManager.instance().stockUniverseInfo()
            if stockUniverseInfo is None:
                raise RuntimeError(f'Configured universe "{currentUniverseId}" wasn\'t found, and there is no stock universe')

            # TODO: This really needs a popup, not sure what should be responsible for displaying
            # it though (this runs in a thread). Have a look at how import custom sectors works
            # as it looks like it might handle non fatal errors
            logging.error(f'Configured universe "{currentUniverseId}" wasn\'t found, defaulting to stock universe')
            app.Config.instance().setValue(
                option=app.ConfigOption.Universe,
                value=stockUniverseInfo.id())

        astronomer.WorldManager.instance().setCurrentUniverse(
            universeId=currentUniverseId,
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
