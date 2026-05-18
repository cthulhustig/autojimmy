import astronomer
import typing

class EditableLabel(astronomer.Label):
    def __init__(
            self,
            entityId: str,
            text: str,
            worldX: float,
            worldY: float,
            colour: typing.Optional[str] = None,
            size: typing.Optional[astronomer.Label.Size] = None,
            wrap: bool = False
            ) -> None:
        super().__init__(
            entityId=entityId,
            text=text,
            worldX=worldX,
            worldY=worldY,
            colour=colour,
            size=size,
            wrap=wrap)
        self._sectorId = None

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId