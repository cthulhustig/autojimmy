import common
import enum
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
            rolls: typing.Iterable[common.ScalarCalculation],
            ignored: typing.Optional[common.ScalarCalculation],
            modifiers: typing.Mapping[
                common.ScalarCalculation, # Modifier name
                str], # Modifier value
            target: typing.Optional[common.ScalarCalculation],
            effect: typing.Optional[common.ScalarCalculation],
            ) -> None:
        self._total = total
        self._rolls = list(rolls) if rolls else []
        self._ignored = ignored
        self._modifiers = dict(modifiers) if modifiers else {}
        self._target = target
        self._effect = effect

    def total(self) -> common.ScalarCalculation:
        return self._total

    def yieldRolls(self) -> typing.Generator[typing.Tuple[common.ScalarCalculation, bool], None, None]:
        for roll in self._rolls:
            yield (roll, roll is self._ignored)

    def ignored(self) -> typing.Optional[common.ScalarCalculation]:
        return self._ignored

    def yieldModifiers(self) -> typing.Generator[typing.Tuple[common.ScalarCalculation, str], None, None]:
        for pair in self._modifiers.items():
            yield pair

    def target(self) -> typing.Optional[common.ScalarCalculation]:
        return self._target

    # The effect will only be set if a target number was specified and that
    # target number was met
    def effect(self) -> typing.Optional[common.ScalarCalculation]:
        return self._effect

class DiceRoller(UuidObject):
    class Flags(enum.IntFlag):
        HasBoonDice = 1
        HasBaneDice = 2

    def __init__(
            self,
            name: str,
            dieCount: int,
            dieType: common.DieType,
            constantDM: int = 0,
            flags: Flags = 0,
            dynamicDMs: typing.Optional[typing.Iterable[DiceModifier]] = None,
            targetNumber: typing.Optional[int] = None,
            randomGenerator: typing.Optional[random.Random] = None
            ) -> None:
        self._name = name
        self._dieCount = dieCount
        self._dieType = dieType
        self._constantDM = constantDM
        self._flags = flags
        self._dynamicDMs: typing.List[DiceModifier] = list(dynamicDMs) if dynamicDMs else []
        self._targetNumber = targetNumber
        self._randomGenerator = randomGenerator if randomGenerator else random

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> str:
        self._name = name

    def dieCount(self) -> int:
        return self._dieCount

    def setDieCount(self, dieCount: int) -> None:
        self._dieCount = dieCount

    def dieType(self) -> common.DieType:
        return self._dieType

    def setDieType(self, dieType: common.DieType) -> None:
        self._dieType = dieType

    def constantDM(self) -> int:
        return self._constantDM

    def setConstantDM(self, modifier: int) -> None:
        self._constantDM = modifier

    def flags(self) -> Flags:
        return self._flags

    def setFlags(self, flags: Flags) -> None:
        self._flags = flags

    def hasBoon(self) -> bool:
        return (self._flags & DiceRoller.Flags.HasBoonDice) != 0

    def setHasBoon(self, enabled: bool) -> None:
        if enabled:
            self._flags |= DiceRoller.Flags.HasBoonDice
        else:
            self._flags &= ~DiceRoller.Flags.HasBoonDice

    def hasBane(self) -> bool:
        return (self._flags & DiceRoller.Flags.HasBaneDice) != 0

    def setHasBane(self, enabled: bool) -> None:
        if enabled:
            self._flags |= DiceRoller.Flags.HasBaneDice
        else:
            self._flags &= ~DiceRoller.Flags.HasBaneDice

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

    def targetNumber(self) -> typing.Optional[int]:
        return self._targetNumber

    def setTargetNumber(
            self,
            targetNumber: typing.Optional[int]
            ) -> None:
        self._targetNumber = targetNumber

    def roll(self) -> DiceRollResult:
        originalRolls: typing.List[common.ScalarCalculation] = []
        boonBaneCount = 0
        if self.hasBoon() and not self.hasBane():
            boonBaneCount = 1
        elif self.hasBane() and not self.hasBoon():
            boonBaneCount = -1
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
        usedRolls = originalRolls
        ignoredRoll = None
        if boonBaneCount > 0:
            # The roll has a boon so remove the lowest value
            usedRolls = list(originalRolls)
            ignoredRoll = min(usedRolls, key=lambda x: x.value())
            usedRolls.remove(ignoredRoll)
        elif boonBaneCount < 0:
            # The roll has a bane so remove the largest value
            usedRolls = list(originalRolls)
            ignoredRoll = max(usedRolls, key=lambda x: x.value())
            usedRolls.remove(ignoredRoll)

        modifiers = {}
        if self._constantDM != 0:
            modifiers['Constant Roll Modifier'] = _makeScalarValue(
                value=self._constantDM,
                name=f'{self._name} Constant DM')
        for modifier in self._dynamicDMs:
            if modifier.enabled():
                # NOTE: Dynamic modifiers with a value of 0 are intentionally
                # included so they show up in the detailed report view
                modifierName = modifier.name()
                modifier = _makeScalarValue(
                    value=modifier.value(),
                    name=f'{self._name} DM')
                modifiers[modifier] = modifierName

        total = common.Calculator.sum(
            values=usedRolls + list(modifiers.keys()),
            name=f'{self._name} Modified Roll')

        targetNumber = None
        effect = None
        if self._targetNumber != None:
            targetNumber = _makeScalarValue(
                value=self._targetNumber,
                name=f'{self._name} Target Number')
            if total.value() >= targetNumber.value():
                effect = common.Calculator.subtract(
                    lhs=total,
                    rhs=targetNumber,
                    name=f'{self._name} Roll Effect')

        return DiceRollResult(
            total=total,
            rolls=originalRolls,
            ignored=ignoredRoll,
            modifiers=modifiers,
            target=targetNumber,
            effect=effect)

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
