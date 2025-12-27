import typing

class StartupJob(object):
    def __init__(self) -> None:
        super().__init__()
        self._exception = None

    def run(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        try:
            self.execute(progressCallback=progressCallback)
        except Exception as ex:
            self._exception = ex

    # Return true if startup should continue, false if it should
    # abort
    def shouldContinue(self) -> bool:
        return self._exception is None

    def errorMessage(self) -> typing.Optional[str]:
        return 'Startup Failed' if self._exception else None

    def exception(self) -> typing.Optional[Exception]:
        return self._exception

    def execute(
            self,
            progressCallback: typing.Callable[[str, int, int], typing.Any]
            ) -> None:
        raise RuntimeError('The run method must be implemented by classes derived from StartupJob')