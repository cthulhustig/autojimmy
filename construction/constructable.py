import typing

class ConstructableInterface(object):
    def name(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from ConstructableInterface so must implement constructableName')

    def setName(self, name: str) -> None:
        raise RuntimeError(f'{type(self)} is derived from ConstructableInterface so must implement setConstructableName')
