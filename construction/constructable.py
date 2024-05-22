import typing

class ConstructableInterface(object):
    def constructableName(self) -> typing.Optional[str]:
        raise RuntimeError(f'{type(self)} is derived from ConstructableInterface so must implement constructableName')
    
    def setConstructableName(self, str) -> None:
        raise RuntimeError(f'{type(self)} is derived from ConstructableInterface so must implement setConstructableName')