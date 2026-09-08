import astronomer
import common
import typing

class Main(object):
    def __init__(
            self,
            hexes: typing.Iterable[astronomer.HexPosition]
            ) -> None:
        self._hexes = list(hexes)

    def hexCount(self) -> int:
        return len(self._hexes)

    def hexes(self) -> typing.Collection[astronomer.HexPosition]:
        return common.ConstCollectionRef(self._hexes)
