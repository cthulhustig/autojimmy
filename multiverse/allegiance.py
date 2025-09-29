import typing

class Allegiance(object):
    def __init__(
            self,
            code: str,
            name: typing.Optional[str],
            legacyCode: typing.Optional[str],
            baseCode: typing.Optional[str],
            uniqueCode: typing.Optional[str]
            ) -> None:
        self._code = code
        self._name = name
        self._legacyCode = legacyCode
        self._baseCode = baseCode
        self._uniqueCode = uniqueCode

    def code(self) -> str:
        return self._code

    def name(self) -> typing.Optional[str]:
        return self._name

    def legacyCode(self) -> typing.Optional[str]:
        return self._legacyCode

    # The base code is used in cases where a region has an allegiance that's a
    # subgroup of a larger allegiance. For example the Sylean Worlds in Core
    # have the allegiance ImSy but are still part of the Imperium so those
    # worlds have the base allegiance Im
    def baseCode(self) -> typing.Optional[str]:
        return self._baseCode

    def uniqueCode(self) -> str:
        return self._uniqueCode if self._uniqueCode else self._code
