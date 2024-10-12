import common
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
        self._total = total
        self._rolls = list(rolls) if rolls else []
        self._ignored = ignored
        self._modifiers = dict(modifiers) if modifiers else {}
        self._targetNumber = targetNumber
        self._effectType = effectType
        self._effectValue = effectValue

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

    def modifiersTotal(self)-> common.ScalarCalculation:
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
        dieCount: typing.Union[int, common.ScalarCalculation],
        dieType: common.DieType,
        constantDM: typing.Union[int, common.ScalarCalculation] = 0,
        hasBoon: bool = False,
        hasBane: bool = False,
        dynamicDMs: typing.Optional[typing.Iterable[typing.Tuple[
            str, # Modifier name
            typing.Union[int, common.ScalarCalculation], # Modifier value
            ]]] = None,
        probability: common.ProbabilityType = common.ProbabilityType.EqualTo,
        ) -> typing.Mapping[int, common.ScalarCalculation]:
    modifiers = [_makeScalarValue(
        value=constantDM,
        name='Constant DM')]
    if dynamicDMs:
        for modifierName, modifierValue in dynamicDMs:
            # NOTE: Dynamic modifiers with a value of 0 are intentionally
            # included so they show up in the detailed report view
            modifiers.append(_makeScalarValue(
                value=modifierValue,
                name=f'{modifierName} Dynamic DM'))
    modifiers = common.Calculator.sum(
        values=modifiers,
        name='Total DM')

    return common.calculateRollProbabilities(
        dieCount=dieCount,
        dieType=dieType,
        hasBoon=hasBoon,
        hasBane=hasBane,
        modifier=modifiers,
        probability=probability)

def rollDice(
        dieCount: typing.Union[int, common.ScalarCalculation],
        dieType: common.DieType,
        constantDM: typing.Union[int, common.ScalarCalculation] = 0,
        hasBoon: bool = False,
        hasBane: bool = False,
        dynamicDMs: typing.Optional[typing.Iterable[typing.Tuple[
            str, # Modifier name
            typing.Union[int, common.ScalarCalculation], # Modifier value
            ]]] = None,
        targetNumber: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
        randomGenerator: typing.Optional[random.Random] = None,
        ) -> DiceRollResult:
    dieCount = _makeScalarValue(
        value=dieCount,
        name='Die Count')
    constantDM = _makeScalarValue(
        value=constantDM,
        name='Constant DM')
    if targetNumber != None:
        targetNumber = _makeScalarValue(
            value=targetNumber,
            name='Target Number')
    if randomGenerator == None:
        randomGenerator = random

    originalRolls: typing.List[common.ScalarCalculation] = []
    boonBaneCount = 0
    if hasBoon and not hasBane:
        boonBaneCount = 1
    elif hasBane and not hasBoon:
        boonBaneCount = -1
    totalDieCount = dieCount.value() + abs(boonBaneCount)
    dieSides = 3 if dieType == common.DieType.D3 else 6
    for index in range(0, totalDieCount):
        roll = randomGenerator.randint(1, dieSides)
        if dieType == common.DieType.DD:
            roll * 10
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

    modifiers = {}
    if constantDM.value() != 0:
        modifiers[constantDM] = 'Constant DM'
    if dynamicDMs:
        for modifierName, modifierValue in dynamicDMs:
            # NOTE: Dynamic modifiers with a value of 0 are intentionally
            # included so they show up in the detailed report view
            modifierValue = _makeScalarValue(
                value=modifierValue,
                name=f'{modifierName} Dynamic DM')
            modifiers[modifierValue] = modifierName

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
        total=total,
        rolls=originalRolls,
        ignored=ignoredRoll,
        modifiers=modifiers,
        targetNumber=targetNumber,
        effectType=effectType,
        effectValue=effectValue)
