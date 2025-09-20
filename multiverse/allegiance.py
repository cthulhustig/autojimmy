import logging
import threading
import multiverse
import typing

class Allegiance(object):
    def __init__(
            self,
            code: str,
            name: typing.Optional[str],
            legacyCode: typing.Optional[str],
            basesCode: typing.Optional[str],
            uniqueCode: typing.Optional[str]
            ) -> None:
        self._code = code
        self._name = name
        self._legacyCode = legacyCode
        self._basesCode = basesCode
        self._uniqueCode = uniqueCode

    def code(self) -> str:
        return self._code

    def name(self) -> typing.Optional[str]:
        return self._name

    def legacyCode(self) -> typing.Optional[str]:
        return self._legacyCode

    def basesCode(self) -> typing.Optional[str]:
        return self._basesCode

    def uniqueCode(self) -> str:
        return self._uniqueCode if self._uniqueCode else self._code
