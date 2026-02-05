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