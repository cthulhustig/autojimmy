import azathoth
import common
import typing

class ImportSectorCommand(azathoth.EditCommandInterface):
    def __init__(
            self,
            universe: azathoth.EditableUniverse,
            sector: azathoth.EditableSector,
            worlds: typing.Optional[typing.Collection[azathoth.EditableWorld]]
            ) -> None:
        super().__init__()

        common.validateObject(name='universe', value=universe, objectType=azathoth.EditableUniverse, allowNone=False)
        common.validateObject(name='sector', value=sector, objectType=azathoth.EditableSector, allowNone=False)
        common.validateCollection(name='worlds', value=worlds, elementType=azathoth.EditableWorld, allowNone=True)

        self._universe = universe
        self._newSector = sector
        self._newWorlds = worlds

        self._oldSector = self._universe.sectorByPosition(self._newSector.position())
        self._oldWorlds = self._universe.worldsInSector(self._newSector.position())

    def applyEvent(self) -> azathoth.ChangeEvent:
        return self._createEvent(
            oldSector=self._oldSector,
            oldWorlds=self._oldWorlds,
            newSector=self._newSector,
            newWorlds=self._newWorlds)

    def applyChanges(self) -> None:
        self._universe.insertSector(
            sector=self._newSector,
            worlds=self._newWorlds)

    def revertEvent(self) -> azathoth.ChangeEvent:
        return self._createEvent(
            oldSector=self._newSector,
            oldWorlds=self._newWorlds,
            newSector=self._oldSector,
            newWorlds=self._oldWorlds)

    def revertChanges(self) -> None:
        self._universe.insertSector(
            sector=self._oldSector,
            worlds=self._oldWorlds)

    @staticmethod
    def _createEvent(
            oldSector: typing.Optional[azathoth.EditableSector],
            oldWorlds: typing.Optional[typing.Collection[azathoth.EditableWorld]],
            newSector: typing.Optional[azathoth.EditableSector],
            newWorlds: typing.Optional[typing.Collection[azathoth.EditableWorld]],
            ) -> azathoth.ChangeEvent:
        added = []
        if newSector:
            added.append(newSector)
            added.extend(newSector.entities())

        if newWorlds:
            added.extend(newWorlds)

        deleted = []
        if oldSector:
            deleted.append(oldSector)
            deleted.extend(oldSector.entities())

        if oldWorlds:
            deleted.extend(oldWorlds)

        return azathoth.ChangeEvent(added=added, deleted=deleted)
