import astronomer
import azathoth
import common
import typing

class DeleteSectorCommand(azathoth.EditCommandInterface):
    def __init__(
            self,
            universe: azathoth.EditableUniverse,
            sectorPos: astronomer.SectorPosition
            ) -> None:
        super().__init__()

        common.validateObject(name='universe', value=universe, objectType=azathoth.EditableUniverse, allowNone=False)
        common.validateObject(name='sectorPos', value=sectorPos, objectType=astronomer.SectorPosition, allowNone=False)

        self._universe = universe
        self._sectorPos = sectorPos

        # TODO: I'll need to update this as I move stuff from the sector to the universe
        self._removeSector = self._universe.sectorByPosition(self._sectorPos)
        self._removeWorlds = self._universe.worldsInSector(self._sectorPos)

    def applyEvent(self) -> azathoth.ChangeEvent:
        deleted = []
        if self._removeSector:
            deleted.append(self._removeSector)
            deleted.extend(self._removeSector.entities())

        if self._removeWorlds:
            deleted.extend(self._removeWorlds)

        return azathoth.ChangeEvent(deleted=deleted)

    def applyChanges(self) -> None:
        self._universe.deleteSector(self._sectorPos)

    def revertEvent(self) -> azathoth.ChangeEvent:
        added = []
        if self._removeSector:
            added.append(self._removeSector)
            added.extend(self._removeSector.entities())

        if self._removeWorlds:
            added.extend(self._removeWorlds)

        return azathoth.ChangeEvent(added=added)

    def revertChanges(self) -> None:
        self._universe.insertSector(
            sector=self._removeSector,
            worlds=self._removeWorlds)
