import astronomer
import common
import survey

class Sophont(astronomer.Entity):
    def __init__(
            self,
            entityId: str,
            name: str,
            code: str,
            isMajor: bool
            ) -> None:
        super().__init__(entityId=entityId)

        survey.validateSophontName(name='name', value=name)
        survey.validateSophontCode(name='code', value=code)
        common.validateBool(name='isMajor', value=isMajor)

        self._name = name
        self._code = code
        self._isMajor = isMajor

    def name(self) -> str:
        return self._name

    def code(self) -> str:
        return self._code

    def isMajor(self) -> bool:
        return self._isMajor
