import travellermap
import typing

class MainGenerator(object):
     # This is the value used by Traveller Map (tools\mains.js)
    _MinMainWorlds = 5

    def __init__(self) -> None:
        self._worlds:typing.Set[typing.Tuple[int, int, int, int]] = set()

    def addWorld(
            self,
            sectorX,
            sectorY,
            hexX,
            hexY
            ) -> None:
        self._worlds.add((sectorX, sectorY, hexX, hexY))

    # Based on the algorithm used by Traveller Map (tools\mains.js)
    def generate(self) -> typing.Iterable[typing.Iterable[typing.Tuple[int, int, int, int]]]:
        mainIndex = 0
        seenPositions = {}

        for world in self._worlds:
            if world in seenPositions:
                continue
            mainIndex += 1

            stack = [world]
            while stack:
                check = stack.pop() # TODO: Not sure if this is removing from correct end (does it matter???)
                seenPositions[check] = mainIndex
                for neighbour in self._neighbours(world=check):
                    if neighbour not in seenPositions:
                         stack.append(neighbour)

        mains = [[] for _ in range(0, mainIndex + 1)]
        for world, mainIndex in seenPositions.items():
            mains[mainIndex].append(world)
        mains = [main for main in mains if len(main) > MainGenerator._MinMainWorlds]
        mains = sorted(mains, key=lambda element: -len(element))
        return mains

    def _neighbours(
            self,
            world: typing.Tuple[int, int, int, int]
            ) -> typing.Iterable[typing.Tuple[int, int, int, int]]:
        neighbours = []
        for direction in travellermap.NeighbourDirs:
            neighbour = travellermap.neighbourRelativeHex(origin=world, direction=direction)
            if neighbour in self._worlds:
                neighbours.append(neighbour)
        return neighbours