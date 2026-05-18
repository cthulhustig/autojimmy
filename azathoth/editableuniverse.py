import astronomer
import azathoth
import typing

class EditableUniverse(astronomer.Universe):
    def __init__(
            self,
            universeId: str,
            sectors: typing.Collection[astronomer.Sector], # Sectors for all milieu
            placeholderMilieu: typing.Optional[astronomer.Milieu] = None
            ) -> None:
        super().__init__(
            universeId=universeId,
            sectors=sectors,
            placeholderMilieu=placeholderMilieu)

    def replaceSector(
            self,
            oldSector: typing.Optional[azathoth.EditableSector],
            newSector: typing.Optional[azathoth.EditableSector]
            ) -> None:
        if oldSector and newSector:
            if oldSector.milieu() != newSector.milieu():
                raise ValueError(f'Sectors have different milieu ({oldSector.milieu().value} vs {newSector.milieu().value})')
            if oldSector.position() != newSector.position():
                raise ValueError(f'Sectors have different milieu ({oldSector.position().elements()} vs {newSector.position().elements()})')

        if oldSector and oldSector.entityId() not in self._idToEntityMap:
            raise ValueError(f'Sectors {oldSector.entityId()} is not in universe {self.universeId()}')

        if newSector and newSector.entityId() in self._idToEntityMap:
            raise ValueError(f'Sectors {newSector.entityId()} is already in universe {self.universeId()}')

        if oldSector:
            self._removeSector(oldSector)
        if newSector:
            self._addSector(newSector)