import collections
import common
import diceroller
import random
import typing

def calculateProbabilities(
        roller: diceroller.DiceRoller,
        probability: common.ComparisonType = common.ComparisonType.EqualTo,
        ) -> typing.Mapping[int, int]:
    dieCount = roller.dieCount()
    dieType = roller.dieType()

    # NOTE: Modifiers with a value of 0 are included even though they have no
    # effect on the roll so that they are still included in results
    modifierTotal = roller.constant()
    for modifier in roller.modifiers():
        if modifier.enabled():
            modifierTotal += modifier.value()

    rollCombinations = common.calculateRollCombinations(
        dieCount=dieCount,
        dieType=dieType,
        hasBoon=roller.hasBoon(),
        hasBane=roller.hasBane(),
        modifier=modifierTotal)

    fluxType = roller.fluxType()
    if fluxType:
        baseCombinations = common.calculateRollCombinations(
            dieCount=2,
            dieType=dieType)
        rollOffset = common.dieSides(dieType) + 1
        if dieType == common.DieType.DD:
            rollOffset *= 10

        fluxCombinations = collections.defaultdict(int)
        if fluxType == diceroller.FluxType.Neutral:
            for roll, count in baseCombinations.items():
                fluxCombinations[roll - rollOffset] = count
        elif fluxType == diceroller.FluxType.Good:
            for roll, count in baseCombinations.items():
                fluxCombinations[abs(roll - rollOffset)] += count
        elif fluxType == diceroller.FluxType.Bad:
            for roll, count in baseCombinations.items():
                fluxCombinations[-abs(roll - rollOffset)] += count

        combinedCombinations: typing.Dict[int, int] = collections.defaultdict(int)
        for rollResult, rollCount in rollCombinations.items():
            for fluxResult, fluxCount in fluxCombinations.items():
                totalResult = rollResult + fluxResult
                totalCount = rollCount * fluxCount
                combinedCombinations[totalResult] += totalCount
    else:
        combinedCombinations = rollCombinations

    denominator = sum(combinedCombinations.values())
    probabilities = {}
    accumulatedCount = 0
    for result, count in combinedCombinations.items():
        if probability == common.ComparisonType.EqualTo:
            numerator = count
        elif probability == common.ComparisonType.LessThan:
            numerator = accumulatedCount
        elif probability == common.ComparisonType.LessThanOrEqualTo:
            numerator = accumulatedCount + count
        elif probability == common.ComparisonType.GreaterOrEqualTo:
            numerator = denominator - accumulatedCount
        elif probability == common.ComparisonType.GreaterThan:
            numerator = denominator - (accumulatedCount + count)

        probabilities[result] = numerator / denominator
        accumulatedCount += count

    return probabilities

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
    dieCount = roller.dieCount() + abs(boonBaneCount)
    dieType = roller.dieType()
    dieSides = common.dieSides(dieType=dieType)
    for index in range(0, dieCount):
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

    fluxType = roller.fluxType()
    fluxRolls = None
    if fluxType:
        fluxRolls = []
        for _ in range(2):
            roll = randomGenerator.randint(1, dieSides)
            if dieType == common.DieType.DD:
                roll *= 10
            fluxRolls.append(roll)

    # NOTE: Modifiers with a value of 0 are included even though they have no
    # effect on the roll so that they are still included in results
    modifiers = [('Constant DM', roller.constant())]
    for modifier in roller.modifiers():
        if modifier.enabled():
            modifiers.append((modifier.name(), modifier.value()))

    return diceroller.DiceRollResult(
        timestamp=common.utcnow(),
        label=label,
        dieType=dieType,
        rolls=rolls,
        ignored=ignoredRollIndex,
        fluxType=fluxType,
        fluxRolls=fluxRolls,
        modifiers=modifiers,
        targetType=roller.targetType(),
        targetNumber=roller.targetNumber())
