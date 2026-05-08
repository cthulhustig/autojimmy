import azathoth

class ReplaceSectorCommand(azathoth.EditCommandInterface):
    def __init__(
            self,
            oldSector: azathoth.EditableSector,
            newSector: azathoth.EditableSector
            ) -> None:
        super().__init__()
        if oldSector.milieu() != newSector.milieu():
            raise ValueError(f'Sectors have different milieu ({oldSector.milieu().value} vs {newSector.milieu().value})')
        if oldSector.position() != newSector.position():
            raise ValueError(f'Sectors have different milieu ({oldSector.position().elements()} vs {newSector.position().elements()})')

        self._oldSector = oldSector
        self._newSector = newSector

    def applyEvent(self) -> azathoth.ChangeEvent:
        return self._createEvent(
            oldSector=self._oldSector,
            newSector=self._newSector)

    def applyChanges(
            self,
            universe: azathoth.EditableUniverse
            ) -> None:
        self._makeChanges(
            universe=universe,
            oldSector=self._oldSector,
            newSector=self._newSector)

    def revertEvent(self) -> azathoth.ChangeEvent:
        return self._createEvent(
            oldSector=self._newSector,
            newSector=self._oldSector)

    def revertChanges(
            self,
            universe: azathoth.EditableUniverse
            ) -> None:
        self._makeChanges(
            universe=universe,
            oldSector=self._newSector,
            newSector=self._oldSector)

    @staticmethod
    def _createEvent(
            oldSector: azathoth.EditableSector,
            newSector: azathoth.EditableSector
            ) -> azathoth.ChangeEvent:
        added = [newSector]
        added.extend(newSector.entities())

        deleted = [oldSector]
        deleted.extend(oldSector.entities())

        return azathoth.ChangeEvent(added=added, deleted=deleted)

    @staticmethod
    def _makeChanges(
            universe: azathoth.EditableUniverse,
            oldSector: azathoth.EditableSector,
            newSector: azathoth.EditableSector
            ) -> None:
        universe.replaceSector(oldSector=oldSector, newSector=newSector)