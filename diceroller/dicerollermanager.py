import copy
import diceroller
import common
import diceroller
import threading
import typing

class _DiceRollerGroup(common.UuidObject):
    def __init__(
            self,
            name: str,
            ) -> None:
        super().__init__()
        self._name = name
        self._rollers: typing.List[diceroller.DiceRoller] = []

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> str:
        self._name = name

    def addRoller(
            self,
            roller: diceroller.DiceRoller
            ) -> None:
        if roller not in self._rollers:
            self._rollers.append(roller)

    def removeRoller(
            self,
            roller: diceroller.DiceRoller
            ) -> None:
        self._rollers.remove(roller)

    def yieldRollers(self) -> typing.Generator[diceroller.DiceRoller, None, None]:
        for roller in self._rollers:
            yield roller


class DiceRollerManager(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()
    _groups: typing.Dict[str, _DiceRollerGroup] = {}
    _rollers: typing.Dict[str, diceroller.DiceRoller] = {}

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check and the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
        return cls._instance

    def createGroup(
            self,
            name: str,
            ) -> str:
        group = _DiceRollerGroup(name=name)
        self._groups[group.uuid()] = group
        return group.uuid()

    def removeGroup(self, groupId: str) -> None:
        group = self._lookupGroup(groupId)
        del self._groups[group.uuid()]
        for roller in group.yieldRollers():
            del self._rollers[roller.uuid()]

    def groupName(self, groupId: str) -> str:
        group = self._lookupGroup(groupId)
        return group.name()

    def renameGroup(
            self,
            groupId: str,
            newName: str
            ) -> None:
        group = self._lookupGroup(groupId)
        group.setName(newName)

    def yieldGroups(self) -> typing.Generator[str, None, None]:
        # Use a copy of the list to allow for callers manipulating the
        # list as we go
        for group in list(self._groups.values()):
            yield group.uuid()

    def createRoller(
            self,
            name: str,
            groupId: str,
            dieCount: int,
            dieType: common.DieType,
            constantDM: int = 0,
            flags: diceroller.DiceRoller.Flags = 0,
            dynamicDMs: typing.Optional[typing.Iterable[diceroller.DiceModifier]] = None,
            targetNumber: typing.Optional[int] = None
            ) -> diceroller.DiceRoller:
        group = self._lookupGroup(groupId)

        roller = diceroller.DiceRoller(
            name=name,
            group=group.uuid(),
            dieCount=dieCount,
            dieType=dieType,
            constantDM=constantDM,
            flags=flags,
            dynamicDMs=dynamicDMs,
            targetNumber=targetNumber)
        self._rollers[roller.uuid()] = roller
        group.addRoller(roller)
        return roller

    def removeRoller(
            self,
            roller: diceroller.DiceRoller
            ) -> None:
        roller = self._lookupRoller(roller.uuid())
        del self._rollers[roller.uuid()]

    def yieldRollers(self) -> typing.Generator[diceroller.DiceRoller, None, None]:
        # Use a copy of the list to allow for callers manipulating the
        # list as we go
        for roller in list(self._rollers.values()):
            yield roller

    def _lookupGroup(self, groupId: str) -> _DiceRollerGroup:
        group = self._groups.get(groupId)
        if group == None:
            raise ValueError(f'Unknown dice roller group {groupId}')
        return group

    def _lookupRoller(self, rollerId: str) -> diceroller.DiceRoller:
        roller = self._rollers.get(rollerId)
        if roller == None:
            raise ValueError(f'Unknown dice roller {rollerId}')
        return roller