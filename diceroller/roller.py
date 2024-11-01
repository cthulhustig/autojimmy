import common
import diceroller
import random
import typing

def _makeScalarValue(
        value: typing.Union[common.ScalarCalculation, int],
        name: str
        ) -> common.ScalarCalculation:
    if isinstance(value, common.ScalarCalculation):
        return common.Calculator.equals(value=value, name=name)
    else:
        return common.ScalarCalculation(value=int(value), name=name)

def calculateProbabilities(
        roller: diceroller.DiceRoller,
        probability: common.ComparisonType = common.ComparisonType.EqualTo,
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
        label: str,
        roller: diceroller.DiceRoller,
        randomGenerator: typing.Optional[random.Random] = None,
        ) -> diceroller.DiceRollResult:
    if randomGenerator == None:
        randomGenerator = random

    rolls: typing.List[int] = []
    boonBaneCount = 0
    if roller.hasBoon() and not roller.hasBane():
        boonBaneCount = 1
    elif roller.hasBane() and not roller.hasBoon():
        boonBaneCount = -1
    totalDieCount = roller.dieCount() + abs(boonBaneCount)
    dieType = roller.dieType()
    dieSides = common.dieSides(dieType=dieType)
    for index in range(0, totalDieCount):
        roll = randomGenerator.randint(1, dieSides)
        if dieType == common.DieType.DD:
            roll *= 10
        rolls.append(roll)

    calculationValues = list(rolls)
    ignoredRollIndex = None
    if boonBaneCount != 0:
        # If the boon/bane count count is positive it means the roll has
        # a boon and the lowest roll should be removed. If the count is
        # negative it means the roll has a bane and the largest value should
        # be removed
        bestValue = None
        for index, roll in enumerate(calculationValues):
            isBetter = (bestValue == None) or \
                ((roll < bestValue) if (boonBaneCount > 0) else (roll > bestValue))
            if isBetter:
                bestValue = roll
                ignoredRollIndex = index
        del calculationValues[ignoredRollIndex]

    # NOTE: Modifiers with a value of 0 are included even though they have no
    # effect on the roll so that they are still included in results
    modifiers = [('Constant DM', roller.constant())]
    for modifier in roller.modifiers():
        if modifier.enabled():
            modifiers.append((modifier.name(), modifier.value()))

    return diceroller.DiceRollResult(
        timestamp=common.utcnow(),
        label=label,
        die=dieType,
        rolls=rolls,
        ignored=ignoredRollIndex,
        modifiers=modifiers,
        targetType=roller.targetType(),
        targetNumber=roller.targetNumber())
