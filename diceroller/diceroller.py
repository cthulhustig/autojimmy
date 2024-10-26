import common
import diceroller
import enum
import random
import typing

class DiceRollEffectType(enum.Enum):
    ExceptionalFailure = 'Exceptional Failure'
    AverageFailure = 'Average Failure'
    MarginalFailure = 'Marginal Failure'
    MarginalSuccess = 'Marginal Success'
    AverageSuccess = 'Average Success'
    ExceptionalSuccess = 'Exceptional Success'

def _makeScalarValue(
        value: typing.Union[common.ScalarCalculation, int],
        name: str
        ) -> common.ScalarCalculation:
    if isinstance(value, common.ScalarCalculation):
        return common.Calculator.equals(value=value, name=name)
    else:
        return common.ScalarCalculation(value=int(value), name=name)

def _effectValueToType(
        value: typing.Union[common.ScalarCalculation, int],
        ) -> DiceRollEffectType:
    if isinstance(value, common.ScalarCalculation):
        value = value.value()
    if value <= -6:
        return DiceRollEffectType.ExceptionalFailure
    elif value <= -2:
        return DiceRollEffectType.AverageFailure
    elif value == -1:
        return DiceRollEffectType.MarginalFailure
    elif value == 0:
        return DiceRollEffectType.MarginalSuccess
    elif value <= 5:
        return DiceRollEffectType.AverageSuccess
    else:
        return DiceRollEffectType.ExceptionalSuccess

class DiceRollResult(object):
    def __init__(
            self,
            die: common.DieType,
            total: common.ScalarCalculation,
            rolls: typing.Iterable[common.ScalarCalculation],
            ignored: typing.Optional[common.ScalarCalculation], # The same instance MUST appear in rolls
            modifiers: typing.Mapping[
                common.ScalarCalculation, # Modifier name
                str], # Modifier value
            targetNumber: typing.Optional[common.ScalarCalculation],
            effectType: typing.Optional[DiceRollEffectType],
            effectValue: typing.Optional[common.ScalarCalculation]
            ) -> None:
        super().__init__()
        self._die = die
        self._total = total
        self._rolls = list(rolls) if rolls else []
        self._ignored = ignored
        self._modifiers = dict(modifiers) if modifiers else {}
        self._targetNumber = targetNumber
        self._effectType = effectType
        self._effectValue = effectValue

    def die(self) -> common.DieType:
        return self._die

    def total(self) -> common.ScalarCalculation:
        return self._total

    def rolledTotal(self) -> common.ScalarCalculation:
        rolls = [roll for roll in self._rolls if roll is not self._ignored]
        return common.Calculator.sum(values=rolls)

    def rollCount(self) -> int:
        return len(self._rolls)

    def yieldRolls(self) -> typing.Generator[typing.Tuple[common.ScalarCalculation, bool], None, None]:
        for roll in self._rolls:
            yield (roll, roll is self._ignored)

    def ignored(self) -> typing.Optional[common.ScalarCalculation]:
        return self._ignored

    def modifiersTotal(self) -> common.ScalarCalculation:
        modifiers = [modifier for modifier in self._modifiers.keys()]
        return common.Calculator.sum(values=modifiers)

    def modifierCount(self) -> int:
        return len(self._modifiers)

    def yieldModifiers(self) -> typing.Generator[typing.Tuple[common.ScalarCalculation, str], None, None]:
        for pair in self._modifiers.items():
            yield pair

    def targetNumber(self) -> typing.Optional[common.ScalarCalculation]:
        return self._targetNumber

    # The effect will only be set if a target number was specified and that
    # target number was met
    def effectType(self) -> typing.Optional[DiceRollEffectType]:
        return self._effectType

    def effectValue(self) -> typing.Optional[common.ScalarCalculation]:
        return self._effectValue

def calculateProbabilities(
        roller: diceroller.DiceRoller,
        probability: common.ProbabilityType = common.ProbabilityType.EqualTo,
        ) -> typing.Mapping[int, common.ScalarCalculation]:
    # NOTE: Modifiers with a value of 0 are included even though they have no
    # effect on the roll so that they are still included in results
    modifiers = [_makeScalarValue(
        value=roller.constant(),
        name='Constant DM')]
    for modifier in roller.modifiers():
        if modifier.enabled():
            modifiers.append(_makeScalarValue(
                value=modifier.value(),
                name=modifier.name()))
    modifiers = common.Calculator.sum(
        values=modifiers,
        name='Total DM')

    return common.calculateRollProbabilities(
        dieCount=roller.dieCount(),
        dieType=roller.dieType(),
        hasBoon=roller.hasBoon(),
        hasBane=roller.hasBane(),
        modifier=modifiers,
        probability=probability)

def rollDice(
        roller: diceroller.DiceRoller,
        randomGenerator: typing.Optional[random.Random] = None,
        ) -> DiceRollResult:
    dieCount = _makeScalarValue(
        value=roller.dieCount(),
        name='Die Count')
    constant = _makeScalarValue(
        value=roller.constant(),
        name='Constant DM')
    targetNumber = None
    if roller.targetNumber() != None:
        targetNumber = _makeScalarValue(
            value=roller.targetNumber(),
            name='Target Number')
    if randomGenerator == None:
        randomGenerator = random

    originalRolls: typing.List[common.ScalarCalculation] = []
    boonBaneCount = 0
    if roller.hasBoon() and not roller.hasBane():
        boonBaneCount = 1
    elif roller.hasBane() and not roller.hasBoon():
        boonBaneCount = -1
    totalDieCount = dieCount.value() + abs(boonBaneCount)
    dieType = roller.dieType()
    dieSides = common.dieSides(dieType=dieType)
    for index in range(0, totalDieCount):
        roll = randomGenerator.randint(1, dieSides)
        if dieType == common.DieType.DD:
            roll *= 10
        originalRolls.append(_makeScalarValue(
            value=roll,
            name=f'{dieType.value} Roll {index + 1}/{totalDieCount}'))

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

    # NOTE: Modifiers with a value of 0 are included even though they have no
    # effect on the roll so that they are still included in results
    modifiers = {constant: constant.name()}
    for modifier in roller.modifiers():
        if modifier.enabled():
            value = _makeScalarValue(
                value=modifier.value(),
                name=modifier.name())
            modifiers[value] = modifier.name()

    total = common.Calculator.sum(
        values=usedRolls + list(modifiers.keys()),
        name='Modified Roll')

    effectValue = None
    effectType = None
    if targetNumber != None:
        effectValue = common.Calculator.subtract(
            lhs=total,
            rhs=targetNumber,
            name='Roll Effect')
        effectType = _effectValueToType(value=effectValue)

    return DiceRollResult(
        die=dieType,
        total=total,
        rolls=originalRolls,
        ignored=ignoredRoll,
        modifiers=modifiers,
        targetNumber=targetNumber,
        effectType=effectType,
        effectValue=effectValue)
