import typing

class Sophont(object):
    def __init__(
            self,
            code: str,
            name: str,
            isMajor: bool
            ) -> None:
        self._code = code
        self._name = name
        self._isMajor = isMajor

    def code(self) -> str:
        return self._code

    def name(self) -> str:
        return self._name

    def isMajor(self) -> bool:
        return self._isMajor

class SophontPopulation(object):
    def __init__(
            self,
            sophont: Sophont,
            percentage: typing.Optional[int], # None means unknown percentage
            isHomeWorld: bool,
            isDieBack: bool
            ) -> None:
        self._sophont = sophont
        self._percentage = percentage
        self._isHomeWorld = isHomeWorld
        self._isDieBack = isDieBack

    def sophont(self) -> Sophont:
        return self._sophont

    def code(self) -> int:
        return self._sophont.code()

    def name(self) -> int:
        return self._sophont.name()

    def isMajorRace(self) -> bool:
        return self._sophont.isMajor()

    def percentage(self) -> typing.Optional[int]:
        return self._percentage

    def isHomeWorld(self) -> bool:
        return self._isHomeWorld

    def isDieBack(self) -> bool:
        return self._isDieBack