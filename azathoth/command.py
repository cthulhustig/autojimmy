import typing

import azathoth

class CommandInterface(object):
    def changeEvent(self) -> azathoth.ChangeEvent:
        raise RuntimeError(f'{type(self)} is derived from CommandInterface so must implement changeEvent')

    def execute(self) -> None:
        raise RuntimeError(f'{type(self)} is derived from CommandInterface so must implement execute')