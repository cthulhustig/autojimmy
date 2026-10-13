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
            self,
            legacyCustomSectorPath: typing.Optional[str] = None
            ) -> None:
        super().__init__()
        self._legacyCustomSectorPath = legacyCustomSectorPath

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

        if multiverse.UniverseManager.instance().universeInfos():
            logging.info(f'Skipping creation of default universe {milieu!r} as universe register is not empty')
            return

        snapshotMilieu = multiverse.SnapshotManager.instance().listMilieu()
        customSectorMilieu: typing.List[typing.Tuple[
            str,# Milieu
            str # Path to directory containing legacy custom sectors
            ]] = []
        if self._legacyCustomSectorPath is not None:
            for milieu in os.listdir(self._legacyCustomSectorPath):
                customMilieuSectorsPath = os.path.join(self._legacyCustomSectorPath, milieu)
                if not os.path.isdir(customMilieuSectorsPath):
                    continue

                if milieu not in snapshotMilieu:
                    logging.warning(f'Ignoring custom sectors from unrecognised milieu {milieu!r}')
                    continue

                customSectorMilieu.append((milieu, customMilieuSectorsPath))

        milieuToUniverseMap = {}
        for milieu in snapshotMilieu:
            progressMessage = f'Creating Universe {milieu}'
            progressSteps = 1000
            progressWrapper = lambda p: progressCallback(progressMessage, int(p * progressSteps), progressSteps)

            universeId = multiverse.UniverseManager.instance().createUniverse(
                name=milieu,
                milieu=milieu,
                description=f'Traveller Map data for {milieu}',
                importTravellerMap=True,
                progress=common.ProgressTracker(weight=1, updateCallback=progressWrapper),
                reporter=reporter)
            milieuToUniverseMap[milieu] = universeId

        if customSectorMilieu:
            progressMessage = f'Importing Legacy Custom Sectors'
            progressSteps = 1000
            progressWrapper = lambda p: progressCallback(progressMessage, int(p * progressSteps), progressSteps)
            progress = common.ProgressTracker(weight=1, updateCallback=progressWrapper)
            taskCount = len(customSectorMilieu)
            taskWeight = 1 / taskCount

            for milieu, milieuPath in customSectorMilieu:
                try:
                    universeId = milieuToUniverseMap.get(milieu)
                    multiverse.importLegacyCustomSectors(
                        directoryPath=milieuPath,
                        universeId=universeId,
                        milieu=milieu,
                        progress=progress.createChild(weight=taskWeight),
                        reporter=reporter)
                except Exception as ex:
                    # Failure to import legacy custom sector data is not treated
                    # as a hard failure a we don't want to block starting the app
                    # just because there is something dodgy in one of the sectors
                    # TODO: Log something and continue, need to somehow notify the user as well
                    pass

        # If there is no active universe set it to M1105 if there is a
        # default universe for that Milieu. If there isn't an M1105 for
        # some unforeseen reason, leave it unset so the user will be
        # prompted to select a universe later
        # NOTE: It will be set to an empty string (rather than None) if
        # it's not set
        currentUniverseId = app.Config.instance().value(option=app.ConfigOption.Universe)
        if not currentUniverseId and 'M1105' in milieuToUniverseMap:
            app.Config.instance().setValue(
                option=app.ConfigOption.Universe,
                value=milieuToUniverseMap['M1105'])

class LoadUniverseJob(jobs.ProgressJob):
    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to init world manager.'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        progressMessage = f'Loading Universe'
        progressSteps = 1000
        progressWrapper = lambda p: progressCallback(progressMessage, int(p * progressSteps), progressSteps)

        azathoth.UniverseEditor.instance().loadUniverse(
            universeId=app.Config.instance().value(option=app.ConfigOption.Universe),
            progress=common.ProgressTracker(weight=1, updateCallback=progressWrapper))

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
