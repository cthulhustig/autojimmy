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

        milieuToUniverseMap = {}
        for milieu in multiverse.SnapshotManager.instance().listMilieu():
            universeId = multiverse.UniverseManager.instance().createUniverse(
                name=milieu,
                milieu=milieu,
                description=f'Traveller Map data for {milieu}',
                importTravellerMap=True,
                progressCallback=progressCallback,
                reporter=reporter)
            milieuToUniverseMap[milieu] = universeId

        if self._legacyCustomSectorPath is not None:
            milieuToProcess: typing.List[typing.Tuple[
                str,# Milieu
                str # Path to directory containing legacy custom sectors
                ]] = []
            for milieu in os.listdir(self._legacyCustomSectorPath):
                customMilieuSectorsPath = os.path.join(self._legacyCustomSectorPath, milieu)
                if os.path.isdir(customMilieuSectorsPath):
                    milieuToProcess.append((milieu, customMilieuSectorsPath))

            for milieu, milieuPath in milieuToProcess:
                # Import custom sectors into the default universe that was
                # previously created for this milieu. There shouldn't really
                # be legacy custom sectors for unknown milieu, but if it
                # somehow happens, just create a new empty universe for them
                # to be imported into
                try:
                    universeId = milieuToUniverseMap.get(milieu)
                    if universeId is None:
                        universeId = multiverse.UniverseManager.instance().createUniverse(
                            name=milieu,
                            milieu=milieu,
                            description=f'Legacy custom sectors for {milieu}',
                            importTravellerMap=False,
                            progressCallback=progressCallback,
                            reporter=reporter)

                    multiverse.importLegacyCustomSectors(
                        directoryPath=milieuPath,
                        universeId=universeId,
                        milieu=milieu,
                        progressCallback=progressCallback,
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
