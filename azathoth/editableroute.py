import astronomer
import typing

class EditableRoute(astronomer.Route):
    def __init__(
            self,
            entityId: str,
            startHex: astronomer.HexPosition,
            endHex: astronomer.HexPosition,
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            routeType: typing.Optional[str] = None,
            style: typing.Optional[astronomer.LineStyle] = None,
            colour: typing.Optional[str] = None,
            width: typing.Optional[float] = None
            ) -> None:
        super().__init__(
            entityId=entityId,
            startHex=startHex,
            endHex=endHex,
            allegiance=allegiance,
            routeType=routeType,
            style=style,
            colour=colour,
            width=width)
        self._sectorId = None

    def sectorId(self) -> typing.Optional[str]:
        return self._sectorId

    def setSectorId(self, sectorId: str) -> None:
        self._sectorId = sectorId
