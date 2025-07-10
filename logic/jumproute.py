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

    # TODO: Need to drop term node and just use hexes. All calls
    # to these methods should be replaced with calls to the hex
    # equivalent
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

    def hexes(self) -> typing.List[travellermap.HexPosition]:
        return [node[0] for node in self._nodes]

    def startHex(self) -> travellermap.HexPosition:
        return self._nodes[0][0]

    def finishHex(self) -> travellermap.HexPosition:
        return self._nodes[-1][0]

    # TODO: Need to remove worlds from jump routes to make them independent
    # of milieu. All calls to world functions should be replaced with calls
    # to the hex equivalent
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
