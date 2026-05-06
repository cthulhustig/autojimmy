import astronomer
import typing

class EditableLabel(astronomer.Label):
    def __init__(
            self,
            id: str,
            text: str,
            worldX: float,
            worldY: float,
            colour: typing.Optional[str] = None,
            size: typing.Optional[astronomer.Label.Size] = None,
            wrap: bool = False
            ) -> None:
        super().__init__(
            id=id,
            text=text,
            worldX=worldX,
            worldY=worldY,
            colour=colour,
            size=size,
            wrap=wrap)