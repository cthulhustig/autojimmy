import astronomer
import enum
import typing

class Border(astronomer.Region):
    class Style(enum.Enum):
        Solid = 0
        Dashed = 1
        Dotted = 2

    def __init__(
            self,
            hexList: typing.Iterable[astronomer.HexPosition],
            allegiance: typing.Optional[astronomer.Allegiance],
            style: typing.Optional[Style],
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

    def style(self) -> typing.Optional[Style]:
        return self._style
