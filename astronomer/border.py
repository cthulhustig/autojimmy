import astronomer
import typing

class Border(astronomer.Region):
    def __init__(
            self,
            entityId: str,
            hexList: typing.Iterable[astronomer.HexPosition],
            allegiance: typing.Optional[astronomer.Allegiance] = None,
            style: typing.Optional[astronomer.LineStyle] = None,
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> None:
        super().__init__(
            entityId=entityId,
            hexList=hexList,
            colour=colour,
            label=label,
            labelWorldX=labelWorldX,
            labelWorldY=labelWorldY,
            showLabel=showLabel,
            wrapLabel=wrapLabel)
        self._allegiance = allegiance
        self._style = style

    def allegiance(self) -> typing.Optional[astronomer.Allegiance]:
        return self._allegiance

    def style(self) -> typing.Optional[astronomer.LineStyle]:
        return self._style
