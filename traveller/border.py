import enum
import travellermap
import typing

class Border(object):
    class Style(enum.Enum):
        Solid = 0
        Dashed = 1
        Dotted = 2

    def __init__(
            self,
            hexList: typing.Iterable[travellermap.HexPosition],
            allegiance: typing.Optional[str],
            showLabel: typing.Optional[bool],
            wrapLabel: typing.Optional[bool],
            labelHex: typing.Optional[travellermap.HexPosition],
            labelOffsetX: typing.Optional[float],
            labelOffsetY: typing.Optional[float],
            label: typing.Optional[str],
            style: typing.Optional[str],
            colour: typing.Optional[str]
            ) -> None:
        self._hexList = list(hexList)
        self._allegiance = allegiance
        self._showLabel = showLabel
        self._wrapLabel = wrapLabel
        self._labelHex = labelHex
        self._labelOffsetX = labelOffsetX
        self._labelOffsetY = labelOffsetY
        self._label = label
        self._style = style
        self._colour = colour

    def hexList(self) -> typing.Iterable[travellermap.HexPosition]:
        return self._hexList

    def allegiance(self) -> typing.Optional[str]:
        return self._allegiance

    def showLabel(self) -> typing.Optional[bool]:
        return self._showLabel

    def wrapLabel(self) -> typing.Optional[bool]:
        return self._wrapLabel

    def labelHex(self) -> typing.Optional[travellermap.HexPosition]:
        return self._labelHex

    # TODO: Make it clear what units these are in
    def labelOffsetX(self) -> typing.Optional[float]:
        return self._labelOffsetX

    def labelOffsetY(self) -> typing.Optional[float]:
        return self._labelOffsetY

    def label(self) -> typing.Optional[str]:
        return self._label

    def style(self) -> typing.Optional[str]:
        return self._style

    def colour(self) -> typing.Optional[str]:
        return self._colour
