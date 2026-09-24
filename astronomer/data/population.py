
import astronomer
import common
import survey
import typing

class SophontPopulation(object):
    def __init__(
            self,
            sophont: 'astronomer.Sophont',
            percentage: typing.Optional[int], # None means unknown percentage
            isHomeWorld: bool,
            isDieBack: bool
            ) -> None:
        common.validateObject(name='sophont', value=sophont, objectType=astronomer.Sophont)
        survey.validateSophontPercentage(name='percentage', value=percentage, allowNone=True)
        common.validateBool(name='isHomeWorld', value=isHomeWorld)
        common.validateBool(name='isDieBack', value=isDieBack)

        self._sophont = sophont
        self._percentage = percentage
        self._isHomeWorld = isHomeWorld
        self._isDieBack = isDieBack

    def sophont(self) -> 'astronomer.Sophont':
        return self._sophont

    def code(self) -> str:
        return self._sophont.code()

    def name(self) -> str:
        return self._sophont.name()

    def isMajorRace(self) -> bool:
        return self._sophont.isMajor()

    def percentage(self) -> typing.Optional[int]:
        return self._percentage

    def isHomeWorld(self) -> bool:
        return self._isHomeWorld

    def isDieBack(self) -> bool:
        return self._isDieBack