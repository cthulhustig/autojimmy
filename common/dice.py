import collections
import common
import enum
import functools
import math
import random
import re
import typing

# Useful die probability related stuff
# https://grognardgravitywell.wordpress.com/2020/07/22/boons-banes/
# https://www.lookwhattheshoggothdraggedin.com/post/dice-rolls-in-traveller.html
# https://anydice.com/

# IMPORTANT: If I ever change the names of the enum definitions (not their value
# string) then I need to add some kind of value mapping to objectdb as the name
# of the enum is stored in the database for dice roller db objects. I will also
# need some kind of mapping in dice roller serialisation as the names are also
# used in serialised data
class DieType(enum.Enum):
    D6 = 'D'
    D3 = 'D3'
    DD = 'DD' # Roll XD6 and multiply the result by 10 (any constant is added after multiplication)
    D10 = 'D10'
    D20 = 'D20'

_DieSidesMap = {
    DieType.D6: 6,
    DieType.D3: 3,
    DieType.DD: 6, # Result is multiplied by 10
    DieType.D10: 10,
    DieType.D20: 20
}

def dieSides(dieType: DieType) -> int:
    return _DieSidesMap[dieType]

def calculateValueRangeForDice(
        dieCount: typing.Union[int, common.ScalarCalculation],
        higherIsBetter: bool,
        dieType: DieType = DieType.D6
        ) -> common.RangeCalculation:
    if not isinstance(dieCount, common.ScalarCalculation):
        assert(isinstance(dieCount, int))
        dieCount = common.ScalarCalculation(
            value=dieCount,
            name='Die Count')

    lowestRoll = common.ScalarCalculation(
        value=1,
        name=f'Lowest {dieType.value} Roll')
    highestRoll = common.ScalarCalculation(
        value=dieSides(dieType=dieType),
        name=f'Highest {dieType.value} Roll')
    averageRoll = common.Calculator.average(
        lhs=lowestRoll,
        rhs=highestRoll,
        name=f'Average {dieType.value} Roll')

    if dieType == DieType.DD:
        multiplier = common.ScalarCalculation(value=10)
        lowestRoll = common.Calculator.multiply(
            lhs=lowestRoll,
            rhs=multiplier)
        highestRoll = common.Calculator.multiply(
            lhs=highestRoll,
            rhs=multiplier)
        averageRoll = common.Calculator.multiply(
            lhs=averageRoll,
            rhs=multiplier)

    if dieCount.value() > 1:
        lowestRoll = common.Calculator.multiply(
            lhs=lowestRoll,
            rhs=dieCount)
        highestRoll = common.Calculator.multiply(
            lhs=highestRoll,
            rhs=dieCount)
        averageRoll = common.Calculator.multiply(
            lhs=averageRoll,
            rhs=dieCount)

    lowestRoll = common.Calculator.equals(
        value=lowestRoll,
        name=f'Lowest Roll With {dieCount.value()}{dieType.value}')
    highestRoll = common.Calculator.equals(
        value=highestRoll,
        name=f'Highest Roll With {dieCount.value()}{dieType.value}')
    averageRoll = common.Calculator.equals(
        value=averageRoll,
        name=f'Average Roll With {dieCount.value()}{dieType.value}')

    range = common.RangeCalculation(
        worstCase=lowestRoll if higherIsBetter else highestRoll,
        bestCase=highestRoll if higherIsBetter else lowestRoll,
        averageCase=averageRoll,
        name=f'Roll With {dieCount.value()}{dieType.value}')
    assert(isinstance(range, common.RangeCalculation))
    return range

@functools.lru_cache(maxsize=None)
def _calculateBinomial(n: int, k: int) -> int:
    return math.factorial(n) // (math.factorial(k) * math.factorial(n - k))

# https://stackoverflow.com/questions/50690348/calculate-probability-of-a-fair-dice-roll-in-non-exponential-time
# NOTE: Having this function modifier seems to prevent debugging into this function
# I could see it only happening once (as the result in the cached) but I was never
# seeing it hit
@functools.lru_cache(maxsize=None)
def _calculateRollProbabilities(
        dieCount: int,
        dieSides: int,
        ignoreHighest: int = 0,
        ignoreLowest: int = 0,
        ) -> typing.Mapping[int, int]:
    masterResults = collections.Counter()
    if dieCount == 0:
        masterResults[0] = 1
    elif dieSides == 0:
        pass
    else:
        for countShowingMax in range(dieCount + 1):  # 0..count
            subResults = _calculateRollProbabilities(
                dieCount=dieCount - countShowingMax,
                dieSides=dieSides - 1,
                ignoreHighest=max(ignoreHighest - countShowingMax, 0),
                ignoreLowest=ignoreLowest)
            countShowingMaxNotDropped = max(
                min(countShowingMax - ignoreHighest,
                    dieCount - ignoreHighest - ignoreLowest),
                0)
            sumShowingMax = countShowingMaxNotDropped * dieSides

            multiplier = _calculateBinomial(dieCount, countShowingMax)

            for k, v in subResults.items():
                masterResults[sumShowingMax + k] += multiplier * v
    return masterResults

# IMPORTANT: If I ever change the names of the enum definitions (not their value
# string) then I need to add some kind of value mapping to objectdb as the name
# of the enum is stored in the database for dice roller db objects. I will also
# need some kind of mapping in dice roller serialisation as the names are also
# used in serialised data
class ComparisonType(enum.Enum):
    EqualTo = 'Equal To'
    GreaterThan = 'Greater Than'
    GreaterOrEqualTo = 'Greater Or Equal To'
    LessThan = 'Less Than'
    LessThanOrEqualTo = 'Less Or Equal To'

    @staticmethod
    def compareValues(
            lhs: int,
            rhs: int,
            comparison: 'ComparisonType'
            ) -> bool:
        if comparison == ComparisonType.EqualTo:
            return lhs == rhs
        elif comparison == ComparisonType.GreaterThan:
            return lhs > rhs
        elif comparison == ComparisonType.GreaterOrEqualTo:
            return lhs >= rhs
        elif comparison == ComparisonType.LessThan:
            return lhs < rhs
        elif comparison == ComparisonType.LessThanOrEqualTo:
            return lhs <= rhs

        raise ValueError(f'Invalid comparison type {comparison}')

def calculateRollProbabilities(
        dieCount: typing.Union[int, common.ScalarCalculation],
        dieType: DieType = DieType.D6,
        hasBoon: bool = False,
        hasBane: bool = False,
        modifier: typing.Union[int, common.ScalarCalculation] = 0,
        probability: ComparisonType = ComparisonType.EqualTo
        ) -> typing.Mapping[int, common.ScalarCalculation]:
    if isinstance(dieCount, common.ScalarCalculation):
        dieCount = dieCount.value()
    dieCount = int(dieCount)

    if isinstance(modifier, common.ScalarCalculation):
        modifier = modifier.value()
    modifier = int(modifier)

    if hasBoon and hasBane:
        hasBoon = hasBane = False

    results = _calculateRollProbabilities(
        dieCount=dieCount + 1 if hasBoon or hasBane else dieCount,
        dieSides=dieSides(dieType=dieType),
        ignoreHighest=1 if hasBane else 0,
        ignoreLowest=1 if hasBoon else 0)

    denominator = sum(results.values())
    probabilities = {}
    accumulate = 0
    for value, combinations in results.items():
        if dieType == DieType.DD:
            value *= 10

        if probability == ComparisonType.EqualTo:
            enumerator = combinations
        elif probability == ComparisonType.LessThan:
            enumerator = accumulate
        elif probability == ComparisonType.LessThanOrEqualTo:
            enumerator = accumulate + combinations
        elif probability == ComparisonType.GreaterOrEqualTo:
            enumerator = denominator - accumulate
        elif probability == ComparisonType.GreaterThan:
            enumerator = denominator - (accumulate + combinations)

        probabilities[value + modifier] = common.ScalarCalculation(
            value=enumerator / denominator,
            name=f'Normalised Percentage Probability Of Rolling {probability.value} {value}')
        accumulate += combinations

    return probabilities

# NOTE: This function returns a normalised percentage in the range (0->1.0)
def calculateRollProbability(
        dieCount: typing.Union[int, common.ScalarCalculation],
        targetValue: typing.Union[int, common.ScalarCalculation],
        hasBoon: bool = False,
        hasBane: bool = False,
        modifier: typing.Union[int, common.ScalarCalculation] = 0,
        dieType: DieType = DieType.D6,
        probability: ComparisonType = ComparisonType.GreaterOrEqualTo,
        ) -> common.ScalarCalculation:
    if isinstance(dieCount, common.ScalarCalculation):
        dieCount = dieCount.value()
    dieCount = int(dieCount)

    if isinstance(targetValue, common.ScalarCalculation):
        targetValue = targetValue.value()
    targetValue = int(targetValue)

    if isinstance(modifier, common.ScalarCalculation):
        modifier = modifier.value()
    modifier = int(modifier)

    probabilities = calculateRollProbabilities(
        dieCount=dieCount,
        dieType=dieType,
        hasBoon=hasBoon,
        hasBane=hasBane,
        probability=probability)
    assert(probabilities)

    minValue = min(probabilities.keys())
    maxValue = max(probabilities.keys())

    if probability == ComparisonType.EqualTo:
        return probabilities[targetValue - modifier]
    elif probability == ComparisonType.GreaterThan:
        startValue = max((targetValue + 1) - modifier, minValue)
        stopValue = maxValue
        typeString = 'Greater Than'
    elif probability == ComparisonType.GreaterOrEqualTo:
        startValue = max(targetValue - modifier, minValue)
        stopValue = maxValue
        typeString = 'Greater Than Or Equal To'
    elif probability == ComparisonType.LessThan:
        startValue = minValue
        stopValue = min((targetValue - 1) - modifier, maxValue)
        typeString = 'Less Than'
    elif probability == ComparisonType.LessThanOrEqualTo:
        startValue = minValue
        stopValue = min(targetValue - modifier, maxValue)
        typeString = 'Less Than Or Equal To'
    else:
        raise ValueError('Invalid roll target type')

    values = []
    for value in range(startValue, stopValue + 1):
        values.append(probabilities[value])

    probabilityString = f'Percentage Probability Of Rolling {typeString} {targetValue}'
    if modifier:
        probabilityString += f' {modifier:+}'

    if not values:
        return common.ScalarCalculation(
            value=0,
            name=probabilityString)

    return common.Calculator.sum(
        values=values,
        name=probabilityString)

# NOTE: This function returns a normalised percentage in the range (0->1.0)
def calculateRollRangeProbability(
        dieCount: typing.Union[int, common.ScalarCalculation],
        lowValue: typing.Union[int, common.ScalarCalculation],
        highValue: typing.Union[int, common.ScalarCalculation],
        hasBoon: bool = False,
        hasBane: bool = False,
        modifier: typing.Union[int, common.ScalarCalculation] = 0,
        dieType: DieType = DieType.D6
        ) -> common.ScalarCalculation:
    if isinstance(dieCount, common.ScalarCalculation):
        dieCount = dieCount.value()
    dieCount = int(dieCount)

    if isinstance(lowValue, common.ScalarCalculation):
        lowValue = lowValue.value()
    lowValue = int(lowValue)

    if isinstance(highValue, common.ScalarCalculation):
        highValue = highValue.value()
    highValue = int(highValue)

    if isinstance(modifier, common.ScalarCalculation):
        modifier = modifier.value()
    modifier = int(modifier)

    probabilities = calculateRollProbabilities(
        dieCount=dieCount,
        dieType=dieType,
        hasBoon=hasBoon,
        hasBane=hasBane,
        probability=ComparisonType.EqualTo)
    assert(probabilities)

    probabilityString = f'Percentage Probability Of Rolling Between {lowValue} and {highValue}'
    if modifier:
        probabilityString += f' {modifier:+}'

    minValue = min(probabilities.keys())
    maxValue = max(probabilities.keys())

    lowValue = max(lowValue - modifier, minValue)
    highValue = min(highValue - modifier, maxValue)

    values = []
    for value in range(lowValue, highValue + 1):
        values.append(probabilities[value])

    if not values:
        return common.ScalarCalculation(
            value=0,
            name=probabilityString)

    return common.Calculator.sum(
        values=values,
        name=probabilityString)

def randomRollDice(
        dieCount: typing.Union[int, common.ScalarCalculation],
        randomGenerator: typing.Optional[random.Random] = None
        ) -> common.ScalarCalculation:
    if randomGenerator == None:
        randomGenerator = random

    if not isinstance(dieCount, common.ScalarCalculation):
        assert(isinstance(dieCount, int))
        dieCount = common.ScalarCalculation(
            value=dieCount,
            name='Die Count')

    rolls = []
    for _ in range(0, dieCount.value()):
        roll = randomGenerator.randint(1, 6)
        rolls.append(common.ScalarCalculation(roll))
    total = common.Calculator.sum(
        values=rolls,
        name=f'Random Roll With {dieCount.value()}D')
    assert(isinstance(total, common.ScalarCalculation))
    return total

class DiceRollResult(object):
    def __init__(
            self,
            dieCount: common.ScalarCalculation,
            result: common.ScalarCalculation
            ) -> None:
        self._dieCount = dieCount
        self._result = result

    def dieCount(self) -> common.ScalarCalculation:
        return self._dieCount

    def result(self) -> common.ScalarCalculation:
        return self._result

    def name(self) -> str:
        return self._result.name()

class DiceRoller(object):
    def __init__(
            self,
            randomGenerator: typing.Optional[random.Random] = None
            ) -> None:
        self._randomGenerator = randomGenerator
        self._rolls = []

    def makeRoll(
            self,
            dieCount: typing.Union[int, common.ScalarCalculation],
            name: str
            ) -> common.ScalarCalculation:
        if not isinstance(dieCount, common.ScalarCalculation):
            assert(isinstance(dieCount, int))
            dieCount = common.ScalarCalculation(
                value=dieCount,
                name='Die Count')

        result = common.ScalarCalculation(
            value=randomRollDice(
                dieCount=dieCount,
                randomGenerator=self._randomGenerator),
            name=name)

        self._rolls.append(DiceRollResult(
            dieCount=dieCount,
            result=result))

        return result

    def rolls(self) -> typing.Iterable[DiceRollResult]:
        return self._rolls

class DiceRoll(object):
    # This matches <OptionalDiceCount><DiceType><OptionalConstantModifier>
    # NOTE: The OptionalConstantModifier may contain a space between the sign
    # and numeric value which should be removed before converting to an int
    # NOTE: Even though DiceRoll supports it, this pattern doesn't match
    # 'dice rolls' that are just a constant value (i.e. no actual rolling).
    _DiceRollPattern = re.compile(r'^\s*((?:[+-]?\d+)?)([Dd][36Dd]*)\s*((?:[+-]\s*\d+)?)\s*$')

    def __init__(
            self,
            count: typing.Union[common.ScalarCalculation, int] = 0,
            type: DieType = DieType.D6,
            constant: typing.Union[common.ScalarCalculation, int] = 0,
            ) -> None:
        super().__init__()
        if not isinstance(count, common.ScalarCalculation):
            count = common.ScalarCalculation(
                value=count,
                name='Die Count')
        if not isinstance(constant, common.ScalarCalculation):
            constant = common.ScalarCalculation(
                value=constant,
                name='Constant DM')

        self._count = count
        self._type = type
        self._constant = constant

    def dieCount(self) -> common.ScalarCalculation:
        return self._count

    def dieType(self) -> DieType:
        return self._type

    def constant(self) -> common.ScalarCalculation:
        return self._constant

    def __str__(self) -> str:
        displayString = ''

        count = self._count.value() if self._count else 0
        if count != 0:
            displayString = f'{count}D'
            if self._type == DieType.DD:
                displayString += 'D'
            elif self._type != DieType.D6:
                displayString += str(dieSides(dieType=self._type))

        constant = self._constant.value() if self._constant else 0
        if constant > 0:
            displayString += ' + ' if displayString else '+'
            displayString += str(constant)
        elif constant < 0:
            displayString += ' - ' if displayString else '-'
            displayString += str(abs(constant))

        return displayString if displayString else '0'

    @staticmethod
    def fromString(string: str) -> typing.Optional['DiceRoll']:
        match = DiceRoll._DiceRollPattern.match(string)
        if not match:
            return None
        try:
            count = match.group(1)
            count = common.ScalarCalculation(
                value=int(count) if count else 1, # If no value assume 1D
                name='Parsed Dice Roll Dice Count')

            type = match.group(2)
            type = type.upper()
            if type == 'D3':
                type = DieType.D3
            elif type == 'DD':
                type = DieType.DD
            elif type =='D10':
                type = DieType.D10
            elif type =='D20':
                type = DieType.D20
            else:
                type = DieType.D6

            constant = match.group(3)
            if constant:
                constant = ''.join(constant.split())
            constant = common.ScalarCalculation(
                value=int(constant) if constant else 0,
                name='Parsed Dice Roll Constant Modifier')

            return DiceRoll(
                count=count,
                type=type,
                constant=constant)
        except:
            return None
