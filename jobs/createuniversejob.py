import common
import jobs
import multiverse
import typing

class CreateUniverseJob(jobs.ProgressJob):
    def __init__(
            self,
            name: str,
            milieu: str,
            description: str,
            importTravellerMap: bool,
            reporter: typing.Optional[common.Reporter] = None
            ) -> None:
        super().__init__()
        self._name = name
        self._milieu = milieu
        self._description = description
        self._importTravellerMap = importTravellerMap
        self._reporter = reporter
        self._universeId = None

    def universeId(self) -> typing.Optional[str]:
        return self._universeId

    def errorMessage(self) -> typing.Optional[str]:
        if not self.exception():
            return None
        return 'Failed to create universe.'

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        progressMessage = f'Creating Universe {self._name}'
        progressSteps = 1000
        progressWrapper = lambda p: progressCallback(progressMessage, int(p * progressSteps), progressSteps)
        progress = common.ProgressTracker(weight=1, updateCallback=progressWrapper)

        self._universeId = multiverse.UniverseManager.instance().createUniverse(
            name=self._name,
            milieu=self._milieu,
            description=self._description,
            importTravellerMap=self._importTravellerMap,
            progress=progress,
            reporter=self._reporter)
