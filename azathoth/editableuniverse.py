import astronomer
import azathoth
import common
import typing

class EditableUniverse(astronomer.Universe):
    def __init__(
            self,
            universeId: str,
            milieu: astronomer.Milieu,
            sectors: typing.Collection[astronomer.Sector],
            labels: typing.Collection[astronomer.MapLabel],
            vectors: typing.Collection[astronomer.MapVector]
            ) -> None:
        super().__init__(
            universeId=universeId,
            milieu=milieu,
            sectors=sectors,
            labels=labels,
            vectors=vectors)

    def replaceSector(
            self,
            oldSector: typing.Optional[azathoth.EditableSector],
            newSector: typing.Optional[azathoth.EditableSector]
            ) -> None:
        common.validateObject(name='oldSector', value=oldSector, objectType=azathoth.EditableSector, allowNone=True)
        common.validateObject(name='newSector', value=newSector, objectType=azathoth.EditableSector, allowNone=True)

        if oldSector and newSector:
            if oldSector.position() != newSector.position():
                raise ValueError(f'Sectors have different position ({oldSector.position().elements()} vs {newSector.position().elements()})')

        if oldSector and oldSector.entityId() not in self._idToEntityMap:
            raise ValueError(f'Sectors {oldSector.entityId()} is not in universe {self.id()}')

        if newSector and newSector.entityId() in self._idToEntityMap:
            raise ValueError(f'Sectors {newSector.entityId()} is already in universe {self.id()}')

        if oldSector:
            self._removeSector(oldSector)
        if newSector:
            self._addSector(newSector)