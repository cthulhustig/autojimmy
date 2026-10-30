import astronomer
import common
import typing

class EditableBorder(astronomer.Border):
    def __init__(
            self,
            entityId: str,
            hexes: typing.Iterable[astronomer.HexPosition],
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            style: typing.Optional[astronomer.LineStyle] = None,
            colour: typing.Optional[str] = None,
            labels: typing.Optional[typing.Collection[astronomer.BorderLabel]] = None
            ) -> None:
        super().__init__(
            entityId=entityId,
            hexes=hexes,
            allegiance=allegiance,
            style=style,
            colour=colour,
            labels=labels)
        self._sectorId = None

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        common.validateStr(name='sectorId', value=sectorId, allowEmpty=False)
        self._sectorId = sectorId