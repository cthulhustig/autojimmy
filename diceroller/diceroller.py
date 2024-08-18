import common
import random
import typing
import uuid

def _makeScalarValue(
        value: typing.Union[common.ScalarCalculation, int],
        name: str
        ) -> common.ScalarCalculation:
    if isinstance(value, common.ScalarCalculation):
        return common.Calculator.equals(value=value, name=name)
    else:
        return common.ScalarCalculation(value=value, name=name)

class UuidObject(object):
    def __init__(self) -> None:
        self._uuid = str(uuid.uuid4())

    def uuid(self) -> str:
        return self._uuid

class DiceModifier(UuidObject):
    def __init__(
            self,
            name: str = '',
            enabled: bool = True,
            value: int = 0
            ) -> None:
        self._name = name
        self._enabled = enabled
        self._value = value

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> str:
        self._name = name

    def enabled(self) -> bool:
        return self._enabled

    def setEnabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def value(self) -> int:
        return self._value

    def setValue(self, value: int)-> None:
        self._value = value

class DiceRollResult(UuidObject):
    def __init__(
            self,
            total: common.ScalarCalculation,
            effect: typing.Optional[common.ScalarCalculation],
            rolls: typing.Iterable[common.ScalarCalculation]
            ) -> None:
        self._total = total
        self._effect = effect
        self._rolls = rolls

    def total(self) -> common.ScalarCalculation:
        return self._total

    # The effect will only be set if a target number was specified and that
    # target number was met
    def effect(self) -> typing.Optional[common.ScalarCalculation]:
        return self._effect

    def yieldRolls(self) -> typing.Generator[common.ScalarCalculation, None, None]:
        for roll in self._rolls:
            yield roll

class DiceRoller(UuidObject):
    def __init__(
            self,
            name: str,
            dieCount: int,
            dieType: common.DieType,
            constantDM: int = 0,
            boonCount: int = 0,
            baneCount: int = 0,
            randomGenerator: typing.Optional[random.Random] = None
            ) -> None:
        self._name = name
        self._dieCount = dieCount
        self._dieType = dieType
        self._constantDM = constantDM
        self._boonCount = boonCount
        self._baneCount = baneCount
        self._dynamicDMs: typing.List[DiceModifier] = []
        self._randomGenerator = randomGenerator if randomGenerator else random

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> str:
        self._name = name

    def dieCount(self) -> int:
        return self._dieCount

    def setDieCount(self, dieCount: int) -> None:
        self._dieCount = dieCount

    def dieType(self) -> int:
        return self._dieType

    def setDieType(self, dieType: common.DieType) -> None:
        self._dieType = dieType

    def constantDM(self) -> int:
        return self._constantDM

    def setConstantDM(self, modifier: int) -> None:
        self._constantDM = modifier

    def boonCount(self) -> int:
        return self._boonCount

    def setBoonCount(self, count: int) -> None:
        self._boonCount = count

    def baneCount(self) -> int:
        return self._baneCount

    def setBaneCount(self, count: int) -> None:
        self._baneCount = count

    def addDynamicDM(self, modifier: DiceModifier) -> None:
        if modifier not in self._dynamicDMs:
            self._dynamicDMs.append(modifier)

    def removeDynamicDM(self, modifier: DiceModifier) -> None:
        self._dynamicDMs.remove(modifier)

    def findDynamicDM(self, uuid: str) -> typing.Optional[DiceModifier]:
        for modifier in self._dynamicDMs:
            if uuid == modifier.uuid():
                return modifier
        return None

    def yieldDynamicDMs(self) -> typing.Generator[DiceModifier, None, None]:
        for modifier in self._dynamicDMs:
            yield modifier

    def roll(
            self,
            targetNumber: typing.Optional[int] = None
            ) -> DiceRollResult:
        originalRolls: typing.List[common.ScalarCalculation] = []
        boonBaneCount = self._boonCount - self._baneCount
        totalDieCount = self._dieCount + abs(boonBaneCount)
        dieSides = 3 if self._dieType == common.DieType.D3 else 6
        for index in range(0, totalDieCount):
            roll = self._randomGenerator.randint(1, dieSides)
            if self._dieType == common.DieType.DD:
                roll * 10
            originalRolls.append(common.ScalarCalculation(
                value=roll,
                name=f'{self._name} {self._dieType.value} Roll {index + 1}/{totalDieCount}'))

        # TODO: Need to double check this logic is right
        if boonBaneCount != 0:
            usedRolls = list(originalRolls)
            usedRolls.sort(
                key=lambda x: x.value(),
                reverse=boonBaneCount > 0)
            usedRolls = usedRolls[:self._dieCount]
        else:
            usedRolls = originalRolls

        modifiers = []
        if self._constantDM != 0:
            modifiers.append(_makeScalarValue(
                value=self._constantDM,
                name=f'{self._name} Constant DM'))
        for modifier in self._dynamicDMs:
            if modifier.enabled() and (modifier.value() != 0):
                modifiers.append(_makeScalarValue(
                    value=modifier.value(),
                    name=f'{self._name} DM'))

        total = common.Calculator.sum(
            values=usedRolls + modifiers,
            name=f'{self._name} Modified Roll')

        effect = None
        if targetNumber != None:
            targetNumber = _makeScalarValue(
                value=targetNumber,
                name=f'{self._name} Target Number')
            if total.value() >= targetNumber:
                effect = common.Calculator.subtract(
                    lhs=total,
                    rhs=targetNumber,
                    name=f'{self._name} Roll Effect')

        return DiceRollResult(
            total=total,
            effect=effect,
            rolls=originalRolls)

class DiceRollerGroup(UuidObject):
    def __init__(
            self,
            name: str,
            ) -> None:
        self._name = name
        self._rollers: typing.List[DiceRoller] = []

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> str:
        self._name = name

    def addRoller(
            self,
            roller: DiceRoller
            ) -> None:
        if roller not in self._rollers:
            self._rollers.append(roller)

    def removeRoller(
            self,
            roller: DiceRoller
            ) -> None:
        self._rollers.remove(roller)

    def findRoller(self, uuid) -> typing.Optional[DiceRoller]:
        for roller in self._rollers:
            if uuid == roller.uuid():
                return roller
        return None

    def yieldRollers(self) -> typing.Generator[DiceRoller, None, None]:
        for roller in self._rollers:
            yield roller
