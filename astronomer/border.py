import astronomer
import common
import typing

class Border(astronomer.Region):
    def __init__(
            self,
            entityId: str,
            hexes: typing.Iterable[astronomer.HexPosition],
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
            hexes=hexes,
            colour=colour,
            label=label,
            labelWorldX=labelWorldX,
            labelWorldY=labelWorldY,
            showLabel=showLabel,
            wrapLabel=wrapLabel)

        common.validateObject(name='allegiance', value=allegiance, objectType=astronomer.Allegiance, allowNone=True)
        common.validateObject(name='style', value=style, objectType=astronomer.LineStyle, allowNone=True)

        self._allegiance = allegiance
        self._style = style

    def allegiance(self) -> typing.Optional[astronomer.Allegiance]:
        return self._allegiance

    def style(self) -> typing.Optional[astronomer.LineStyle]:
        return self._style
