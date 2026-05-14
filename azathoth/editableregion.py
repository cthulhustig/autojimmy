import astronomer
import typing

class EditableRegion(astronomer.Region):
    def __init__(
            self,
            entityId: str,
            hexes: typing.Iterable[astronomer.HexPosition],
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> None:
        super().__init__(
            entityId=entityId,
            hexes=hexes,
            colour=colour,
            label=label,
            labelWorldX=labelWorldX,
            labelWorldY=labelWorldY,
            showLabel=showLabel,
            wrapLabel=wrapLabel)
        self._sectorId = None

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId