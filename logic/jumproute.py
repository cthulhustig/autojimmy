import enum
import multiverse
import typing

class JumpRoute(object):
    class NodeFlags(enum.IntFlag):
        Waypoint = 1
        MandatoryBerthing = 2

    def __init__(
            self,
            nodes: typing.Sequence[typing.Tuple[
                multiverse.HexPosition,
                NodeFlags]]
            ) -> None:
        if not nodes:
            raise ValueError('A jump route can\'t have an empty nodes list')
        self._hexes: typing.List[multiverse.HexPosition] = []
        self._flags: typing.List[JumpRoute.NodeFlags] = []
        for hex, flags in nodes:
            self._hexes.append(hex)
            self._flags.append(flags)

        self._totalParsecs = 0
        self._minJumpRating = 0

        if len(self._hexes) > 1:
            fromHex = self._hexes[0]
            for index in range(1, len(self._hexes)):
                toHex = self._hexes[index]
                parsecs = fromHex.parsecsTo(toHex)

                self._totalParsecs += parsecs
                if parsecs > self._minJumpRating:
                    self._minJumpRating = parsecs
                fromHex = toHex

    def jumpCount(self) -> int:
        return len(self._hexes) - 1

    def nodeCount(self) -> int:
        return len(self._hexes)

    def nodeAt(self, index: int) -> multiverse.HexPosition:
        return self._hexes[index]

    def nodes(self) -> typing.List[multiverse.HexPosition]:
        return list(self._hexes)

    def startNode(self) -> multiverse.HexPosition:
        return self._hexes[0]

    def finishNode(self) -> multiverse.HexPosition:
        return self._hexes[-1]

    def flagsAt(self, index: int) -> NodeFlags:
        return self._flags[index]

    def isWaypoint(self, index: int) -> bool:
        return self._flags[index] & JumpRoute.NodeFlags.Waypoint

    def mandatoryBerthing(self, index: int) -> bool:
        return self._flags[index] & JumpRoute.NodeFlags.MandatoryBerthing

    def minJumpRating(self) -> int:
        return self._minJumpRating

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
        return self._totalParsecs

    def __getitem__(self, index: int) -> multiverse.HexPosition:
        return self.nodeAt(index)

    def __iter__(self) -> typing.Iterator[multiverse.HexPosition]:
        return self._hexes.__iter__()

    def __next__(self) -> typing.Any:
        return self._hexes.__next__()

    def __len__(self) -> int:
        return self._hexes.__len__()
