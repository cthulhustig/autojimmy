import travellermap
import typing

class Main(object):
    def __init__(
            self,
            worlds: typing.Iterable[travellermap.World]
            ) -> None:
        self._worlds = list(worlds)

    def worldCount(self) -> int:
        return len(self._worlds)

    def worlds(self) -> typing.Iterable[travellermap.World]:
        return list(self._worlds)

    def __getitem__(self, index: int) -> travellermap.World:
        return self._worlds.__getitem__(index)

    def __iter__(self) -> typing.Iterator[travellermap.World]:
        return self._worlds.__iter__()

    def __next__(self) -> typing.Any:
        return self._worlds.__next__()

    def __len__(self) -> int:
        return self._worlds.__len__()
