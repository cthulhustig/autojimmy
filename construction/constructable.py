import typing

class ConstructableInterface(object):
    def name(self) -> typing.Optional[str]:
        raise RuntimeError(f'{type(self)} is derived from ConstructableInterface so must implement constructableName')
    
    def setName(self, str) -> None:
        raise RuntimeError(f'{type(self)} is derived from ConstructableInterface so must implement setConstructableName')