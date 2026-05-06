import astronomer
import typing

class EditableUniverse(astronomer.Universe):
    def __init__(
            self,
            id: str,
            sectors: typing.Collection[astronomer.Sector], # Sectors for all milieu
            placeholderMilieu: typing.Optional[astronomer.Milieu] = None
            ) -> None:
        super().__init__(
            id=id,
            sectors=sectors,
            placeholderMilieu=placeholderMilieu)