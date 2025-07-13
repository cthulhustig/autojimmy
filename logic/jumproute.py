import travellermap
import typing

class JumpRoute(object):
    def __init__(
            self,
            nodes: typing.Sequence[typing.Tuple[
                travellermap.HexPosition,
                bool]] # True if berthing is mandatory at this hex (i.e. regardless of if it's required for fuel)
            ) -> None:
        if not nodes:
            raise ValueError('A jump route can\'t have an empty nodes list')
        self._hexes: typing.List[travellermap.HexPosition] = []
        self._berthing: typing.Set[int] = set()
        for index, (hex, berthing) in enumerate(nodes):
            self._hexes.append(hex)
            if berthing:
                self._berthing.add(index)

        # The total parsecs calculation is done on demand as it's not often used and is relatively
        # expensive to calculate
        self._totalParsecs = None

    def jumpCount(self) -> int:
        return len(self._hexes) - 1

    def nodeCount(self) -> int:
        return len(self._hexes)

    def nodeAt(self, index: int) -> travellermap.HexPosition:
        return self._hexes[index]

    def nodes(self) -> typing.List[travellermap.HexPosition]:
        return list(self._hexes)

    def startNode(self) -> travellermap.HexPosition:
        return self._hexes[0]

    def finishNode(self) -> travellermap.HexPosition:
        return self._hexes[-1]

    def mandatoryBerthing(self, index: int) -> bool:
        return index in self._berthing

    def nodeParsecs(self, index: int) -> int:
        parsecs = 0
        for current in range(0, self.jumpCount()):
            if current >= index:
                break
            fromHex = self._hexes[current]
            toHex = self._hexes[current + 1]
            parsecs += fromHex.parsecsTo(toHex)
        return parsecs

    def totalParsecs(self) -> int:
        if self._totalParsecs == None:
            self._totalParsecs = self.nodeParsecs(index=len(self._hexes) - 1)
        return self._totalParsecs

    def __getitem__(self, index: int) -> travellermap.HexPosition:
        return self.nodeAt(index)

    def __iter__(self) -> typing.Iterator[travellermap.HexPosition]:
        return self._hexes.__iter__()

    def __next__(self) -> typing.Any:
        return self._hexes.__next__()

    def __len__(self) -> int:
        return self._hexes.__len__()
