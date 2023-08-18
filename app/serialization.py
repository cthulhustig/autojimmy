import app
import common
import pickle
import typing

class CalculationArchive(object):
    def __init__(
            self,
            calculations: typing.Iterable[common.Calculation]
            ) -> None:
        self._appVersion = app.AppVersion
        self._calculations = list(calculations)

    def appVersion(self) -> str:
        return self._appVersion

    def calculations(self) -> typing.Collection[common.Calculation]:
        return self._calculations

def writeCalculations(
        calculations: typing.Iterable[common.Calculation],
        filePath: str
        ) -> None:
    archive = CalculationArchive(calculations=calculations)
    with open(filePath, 'wb') as f:
        pickle.dump(archive, f)

def readCalculations(filePath: str) -> CalculationArchive:
    with open(filePath, 'rb') as f:
        return pickle.load(f)
