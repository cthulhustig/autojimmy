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

class DieType(enum.Enum):
    # IMPORTANT: If I ever change the name of the enum (not that value string) then I need
    # to add some kind of value mapping to objectdb as the name of the enum is stored in
    # the database for dice roller db objects
    D6 = 'D'
    D3 = 'D3'
    DD = 'DD' # Roll XD6 and multiply the result by 10 (any constant is added after multiplication)


_LowestD6Roll = common.ScalarCalculation(
    value=1,
    name='Lowest Roll With One D6')
_HighestD6Roll = common.ScalarCalculation(
    value=6,
    name='Highest Roll With One D6')
_AverageD6Roll = common.Calculator.average(
    lhs=_LowestD6Roll,
    rhs=_HighestD6Roll,
    name='Average Roll With One D6')

_LowestD3Roll = common.ScalarCalculation(
    value=1,
    name='Lowest Roll With One D3')
_HighestD3Roll = common.ScalarCalculation(
    value=3,
    name='Highest Roll With One D3')
_AverageD3Roll = common.Calculator.average(
    lhs=_LowestD3Roll,
    rhs=_HighestD3Roll,
    name='Average Roll With One D3')

_DDRollMultiplier = common.ScalarCalculation(
    value=10,
    name='DD Roll Multiplier')

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

    if dieType == DieType.D3:
        lowestRoll = _LowestD3Roll
        highestRoll = _HighestD3Roll
        averageRoll = _AverageD3Roll
    else:
        lowestRoll = _LowestD6Roll
        highestRoll = _HighestD6Roll
        averageRoll = _AverageD6Roll

    if dieType == DieType.DD:
        lowestRoll = common.Calculator.multiply(
            lhs=lowestRoll,
            rhs=_DDRollMultiplier)
        highestRoll = common.Calculator.multiply(
            lhs=highestRoll,
            rhs=_DDRollMultiplier)
        averageRoll = common.Calculator.multiply(
            lhs=averageRoll,
            rhs=_DDRollMultiplier)

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
        for count_showing_max in range(dieCount + 1):  # 0..count
            subResults = _calculateRollProbabilities(
                dieCount=dieCount - count_showing_max,
                dieSides=dieSides - 1,
                ignoreHighest=max(ignoreHighest - count_showing_max, 0),
                ignoreLowest=ignoreLowest)
            count_showing_max_not_dropped = max(
                min(count_showing_max - ignoreHighest,
                    dieCount - ignoreHighest - ignoreLowest),
                0)
            sum_showing_max = count_showing_max_not_dropped * dieSides

            multiplier = _calculateBinomial(dieCount, count_showing_max)

            for k, v in subResults.items():
                masterResults[sum_showing_max + k] += multiplier * v
    return masterResults

class ProbabilityType(enum.Enum):
    EqualTo = 'Equal To'
    GreaterThan = 'Greater Than'
    GreaterOrEqualTo = 'Greater Or Equal To'
    LessThan = 'Less Than'
    LessThanOrEqualTo = 'Less Or Equal To'

def calculateRollProbabilities(
        dieCount: typing.Union[int, common.ScalarCalculation],
        dieType: DieType = DieType.D6,
        hasBoon: bool = False,
        hasBane: bool = False,
        modifier: typing.Union[int, common.ScalarCalculation] = 0,
        probability: ProbabilityType = ProbabilityType.EqualTo
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
        dieSides=3 if dieType == DieType.D3 else 6,
        ignoreHighest=1 if hasBane else 0,
        ignoreLowest=1 if hasBoon else 0)

    denominator = sum(results.values())
    probabilities = {}
    accumulate = 0
    for value, combinations in results.items():
        if dieType == DieType.DD:
            value *= _DDRollMultiplier.value()

        if probability == ProbabilityType.EqualTo:
            enumerator = combinations
        elif probability == ProbabilityType.LessThan:
            enumerator = accumulate
        elif probability == ProbabilityType.LessThanOrEqualTo:
            enumerator = accumulate + combinations
        elif probability == ProbabilityType.GreaterOrEqualTo:
            enumerator = denominator - accumulate
        elif probability == ProbabilityType.GreaterThan:
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
        probability: ProbabilityType = ProbabilityType.GreaterOrEqualTo,
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
        hasBane=hasBane)
    assert(probabilities)

    minValue = min(probabilities.keys())
    maxValue = max(probabilities.keys())

    if probability == ProbabilityType.EqualTo:
        return probabilities[targetValue - modifier]
    elif probability == ProbabilityType.GreaterThan:
        startValue = max((targetValue + 1) - modifier, minValue)
        stopValue = maxValue
        typeString = 'Greater Than'
    elif probability == ProbabilityType.GreaterOrEqualTo:
        startValue = max(targetValue - modifier, minValue)
        stopValue = maxValue
        typeString = 'Greater Than Or Equal To'
    elif probability == ProbabilityType.LessThan:
        startValue = minValue
        stopValue = min((targetValue - 1) - modifier, maxValue)
        typeString = 'Less Than'
    elif probability == ProbabilityType.LessThanOrEqualTo:
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
        hasBane=hasBane)
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
            if self._type == DieType.D3:
                displayString += '3'
            elif self._type == DieType.DD:
                displayString += 'D'

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
