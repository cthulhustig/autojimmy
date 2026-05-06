import astronomer
import typing

class EditableRegion(astronomer.Region):
    def __init__(
            self,
            id: str,
            hexList: typing.Iterable[astronomer.HexPosition],
            colour: typing.Optional[str] = None,
            label: typing.Optional[str] = None,
            labelWorldX: typing.Optional[float] = None,
            labelWorldY: typing.Optional[float] = None,
            showLabel: bool = True,
            wrapLabel: bool = False
            ) -> None:
        super().__init__(
            id=id,
            hexList=hexList,
            colour=colour,
            label=label,
            labelWorldX=labelWorldX,
            labelWorldY=labelWorldY,
            showLabel=showLabel,
            wrapLabel=wrapLabel)