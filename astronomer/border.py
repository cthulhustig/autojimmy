import astronomer
import typing

class Border(astronomer.Region):
    def __init__(
            self,
            hexList: typing.Iterable[astronomer.HexPosition],
            allegiance: typing.Optional[astronomer.Allegiance],
            style: typing.Optional[astronomer.LineStyle],
            colour: typing.Optional[str],
            label: typing.Optional[str],
            labelWorldX: typing.Optional[float],
            labelWorldY: typing.Optional[float],
            showLabel: bool,
            ) -> None:
        super().__init__(
            hexList=hexList,
            colour=colour,
            label=label,
            labelWorldX=labelWorldX,
            labelWorldY=labelWorldY,
            showLabel=showLabel)
        self._allegiance = allegiance
        self._style = style

    def allegiance(self) -> typing.Optional[astronomer.Allegiance]:
        return self._allegiance

    def style(self) -> typing.Optional[astronomer.LineStyle]:
        return self._style
