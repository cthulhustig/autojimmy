import traveller
import travellermap
import typing

# TODO: Better jump routes
# - Drop milieu and worlds from jump route, they should be independent of
# the milieu
# - Hexes in the route need to have a flag to say berthing is required
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

    def nodeAt(self, index: int) -> travellermap.HexPosition:
        return self._nodes[index][0]

    def nodes(self) -> typing.List[travellermap.HexPosition]:
        return [node[0] for node in self._nodes]

    def startNode(self) -> travellermap.HexPosition:
        return self._nodes[0][0]

    def finishNode(self) -> travellermap.HexPosition:
        return self._nodes[-1][0]

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

    # TODO: I either need to get rid of these methods or switch them to return
    # just the hex. I think I've marked all the places that will need updated
    # with either option. I'm currently thinking to keep them as it means it's
    # consistent with things like refuelling plans
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
