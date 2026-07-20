import app
import azathoth
import common
import gunsmith
import jobs
import logging
import multiverse
import os
import robots
import typing

class CreateDefaultUniversesJob(jobs.ProgressJob):
    def __init__(
            self
            ) -> None:
        super().__init__()

    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to import default universe.'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        # TODO: This is a temp hack, the messages need to be displayed to the user
        reporter = common.LoggingReporter(logLevel=logging.WARNING)

        defaultUniverseId = None
        for milieu in multiverse.SnapshotManager.instance().listMilieu():
            if multiverse.UniverseManager.instance().universeInfoByName(milieu) is not None:
                logging.info(f'Skipping creation of default universe {milieu!r} as it already exists')
                continue

            universeId = multiverse.UniverseManager.instance().createUniverse(
                name=milieu,
                milieu=milieu,
                description=f'Traveller Map data for {milieu}',
                importTravellerMap=True,
                progressCallback=progressCallback,
                reporter=reporter)
            if milieu == 'M1105':
                defaultUniverseId = universeId

        # NOTE: It will be set to an empty string (rather than None) if not set
        currentUniverseId = app.Config.instance().value(option=app.ConfigOption.Universe)
        if not currentUniverseId and defaultUniverseId:
            app.Config.instance().setValue(
                option=app.ConfigOption.Universe,
                value=defaultUniverseId)

class ImportLegacyCustomSectorsJob(jobs.ProgressJob):
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
        # TODO: Need to display any results to the user
        reporter = common.LoggingReporter(logLevel=logging.WARNING)

        basePath = os.path.join(self._directoryPath, 'milieu')
        if not os.path.isdir(basePath):
            # No custom universe data so nothing to do
            return

        for milieu in [d for d in os.listdir(basePath) if os.path.isdir(os.path.join(basePath, d))]:
            universeInfo = multiverse.UniverseManager.instance().universeInfoByName(name=milieu)
            if not universeInfo:
                # TODO: Not sure what to do here, it shouldn't happen as the CreateStockUniversesJob
                # should have created the stock universe for each Milieu
                continue

            universePath = os.path.join(basePath, milieu)
            multiverse.importLegacyCustomSectors(
                directoryPath=universePath,
                universeId=universeInfo.id(),
                progressCallback=progressCallback,
                reporter=reporter)

class LoadUniverseJob(jobs.ProgressJob):
    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to init world manager.'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        currentUniverseId = app.Config.instance().value(option=app.ConfigOption.Universe)
        azathoth.UniverseEditor.instance().loadUniverse(
            universeId=currentUniverseId,
            progressCallback=progressCallback)

class LoadRobotsJob(jobs.ProgressJob):
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

class LoadWeaponsJob(jobs.ProgressJob):
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
