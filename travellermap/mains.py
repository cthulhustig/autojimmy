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

    # Optimised version of algorithm used by Traveller Map (tools\mains.js)
    def generate(self) -> typing.Iterable[typing.Iterable[typing.Tuple[int, int, int, int]]]:
        seen = set()
        mains = []

        for world in self._worlds:
            if world in seen:
                continue

            main = [world]
            mains.append(main)

            index = 0
            while index < len(main):
                world = main[index]
                seen.add(world)
                index += 1

                for direction in travellermap.NeighbourDirs:
                    neighbour = travellermap.neighbourRelativeHex(origin=world, direction=direction)
                    if (neighbour in self._worlds) and (neighbour not in seen):
                        main.append(neighbour)
                        seen.add(neighbour)

        # Drop mains that are under the required size
        mains = [main for main in mains if len(main) > MainGenerator._MinMainWorlds]

        # Sort mains from largest to smallest for consistency with how Traveller Map generates them
        mains = sorted(mains, key=lambda element: -len(element))
        return mains
