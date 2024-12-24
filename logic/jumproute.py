import traveller
import travellermap
import typing

# TODO: This will need updated to deal with nodes rather than worlds
class JumpRoute(object):
    def __init__(
            self,
            worldList: typing.List[traveller.World]
            ) -> None:
        if not worldList:
            raise ValueError('A jump route can\'t have an empty world list')
        self._worldList = worldList

        # The total parsecs calculation is done on demand as it's not often used and is relatively
        # expensive to calculate
        self._totalParsecs = None

    def worldCount(self) -> int:
        return len(self._worldList)

    def worlds(self) -> typing.List[traveller.World]:
        return self._worldList

    def jumpCount(self) -> int:
        return len(self._worldList) - 1

    def startWorld(self) -> traveller.World:
        return self._worldList[0]

    def finishWorld(self) -> traveller.World:
        return self._worldList[-1]

    def nodeParsecs(self, node: int) -> int:
        parsecs = 0
        for index in range(0, self.jumpCount()):
            if index >= node:
                break
            fromWorld = self._worldList[index]
            toWorld = self._worldList[index + 1]
            parsecs += fromWorld.parsecsTo(toWorld)
        return parsecs

    def totalParsecs(self) -> int:
        if not self._totalParsecs:
            self._totalParsecs = self.nodeParsecs(
                node=len(self._worldList) - 1)
        return self._totalParsecs

    def __getitem__(self, index: int) -> traveller.World:
        return self._worldList.__getitem__(index)

    def __iter__(self) -> typing.Iterator[traveller.World]:
        return self._worldList.__iter__()

    def __next__(self) -> typing.Any:
        return self._worldList.__next__()

    def __len__(self) -> int:
        return self._worldList.__len__()
