import enum
import traveller
import travellermap
import typing

class Border(traveller.Region):
    class Style(enum.Enum):
        Solid = 0
        Dashed = 1
        Dotted = 2

    def __init__(
            self,
            hexList: typing.Iterable[travellermap.HexPosition],
            allegiance: typing.Optional[str],
            showLabel: bool,
            wrapLabel: bool,
            labelHex: typing.Optional[travellermap.HexPosition],
            labelOffsetX: typing.Optional[float],
            labelOffsetY: typing.Optional[float],
            label: typing.Optional[str],
            style: typing.Optional[Style],
            colour: typing.Optional[str]
            ) -> None:
        super().__init__(
            hexList=hexList,
            showLabel=showLabel,
            wrapLabel=wrapLabel,
            labelHex=labelHex,
            labelOffsetX=labelOffsetX,
            labelOffsetY=labelOffsetY,
            label=label,
            colour=colour)
        self._allegiance = allegiance
        self._style = style

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

    def style(self) -> typing.Optional[Style]:
        return self._style
