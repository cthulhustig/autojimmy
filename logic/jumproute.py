import logic
import json
import packaging
import packaging.version
import traveller
import travellermap
import typing

class JumpRoute(object):
    def __init__(
            self,
            nodes: typing.Sequence[typing.Tuple[
                travellermap.HexPosition,
                typing.Optional[traveller.World]]]
            ) -> None:
        if not nodes:
            raise ValueError('A jump route can\'t have an empty nodes list')
        self._nodes = list(nodes)

        # The total parsecs calculation is done on demand as it's not often used and is relatively
        # expensive to calculate
        self._totalParsecs = None

    def jumpCount(self) -> int:
        return len(self._nodes) - 1

    def nodeCount(self) -> int:
        return len(self._nodes)

    def node(self, index) -> typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]:
        return self._nodes[index]

    def startNode(self) -> typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]:
        return self._nodes[0]

    def finishNode(self) -> typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]:
        return self._nodes[-1]

    def hex(self, index: int) -> travellermap.HexPosition:
        return self._nodes[index][0]

    def startHex(self) -> travellermap.HexPosition:
        return self._nodes[0][0]

    def finishHex(self) -> travellermap.HexPosition:
        return self._nodes[-1][0]

    def world(self, index: int) -> typing.Optional[traveller.World]:
        return self._nodes[index][1]

    def startWorld(self) -> typing.Optional[traveller.World]:
        return self._nodes[0][1]

    def finishWorld(self) -> typing.Optional[traveller.World]:
        return self._nodes[-1][1]

    def nodeParsecs(self, index: int) -> int:
        parsecs = 0
        for current in range(0, self.jumpCount()):
            if current >= index:
                break
            fromHex = self._nodes[current][0]
            toHex = self._nodes[current + 1][0]
            parsecs += fromHex.parsecsTo(toHex)
        return parsecs

    def totalParsecs(self) -> int:
        if self._totalParsecs == None:
            self._totalParsecs = self.nodeParsecs(index=len(self._nodes) - 1)
        return self._totalParsecs

    def __getitem__(self, index: int) -> typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]:
        return self._nodes.__getitem__(index)

    def __iter__(self) -> typing.Iterator[typing.Tuple[
            travellermap.HexPosition,
            typing.Optional[traveller.World]]]:
        return self._nodes.__iter__()

    def __next__(self) -> typing.Any:
        return self._nodes.__next__()

    def __len__(self) -> int:
        return self._nodes.__len__()
