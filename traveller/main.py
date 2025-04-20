import traveller
import typing

class Main(object):
    def __init__(
            self,
            worlds: typing.Iterable[traveller.World]
            ) -> None:
        self._worlds = set(worlds)

    def worlds(self) -> str:
        return self._worlds

    def __getitem__(self, index: int) -> traveller.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[traveller.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()
