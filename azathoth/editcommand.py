import azathoth

class EditCommandInterface(object):
    def applyEvent(self) -> azathoth.ChangeEvent:
        raise NotImplementedError(f'{type(self)} is derived from CommandInterface so must implement applyEvent')

    def applyChanges(
            self,
            universe: azathoth.EditableUniverse
            ) -> None:
        raise NotImplementedError(f'{type(self)} is derived from CommandInterface so must implement applyChanges')

    def revertEvent(self) -> azathoth.ChangeEvent:
        raise NotImplementedError(f'{type(self)} is derived from CommandInterface so must implement revertEvent')

    def revertChanges(
            self,
            universe: azathoth.EditableUniverse
            ) -> None:
        raise NotImplementedError(f'{type(self)} is derived from CommandInterface so must implement revertChanges')