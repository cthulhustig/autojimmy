import travellermap
import typing

class PlaceholderWorld(object):
    def __init__(
            self,
            hex: travellermap.HexPosition
            ) -> None:
        self._hex = hex

    def hex(self) -> travellermap.HexPosition:
        return self._hex

class PlaceholderSector(object):
    def __init__(
            self,
            x: int,
            y: int,
            placeholders: typing.Iterable[PlaceholderWorld]
            ):
        self._x = x
        self._y = y
        self._placeholders = list(placeholders)

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def placeholders(self) -> typing.Iterable[PlaceholderWorld]:
        return list(self._placeholders)

    def __getitem__(self, index: int) -> PlaceholderWorld:
        return self._placeholders.__getitem__(index)

    def __iter__(self) -> typing.Iterator[PlaceholderWorld]:
        return self._placeholders.__iter__()

    def __next__(self) -> typing.Any:
        return self._placeholders.__next__()

    def __len__(self) -> int:
        return self._placeholders.__len__()