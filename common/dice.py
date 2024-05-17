import common
import enum
import random
import re
import typing

_Lowest1DRoll = common.ScalarCalculation(
    value=1,
    name='Lowest Roll With 1D')
_Highest1DRoll = common.ScalarCalculation(
    value=6,
    name='Highest Roll With 1D')
_Average1DRoll = common.Calculator.average(
    lhs=_Lowest1DRoll,
    rhs=_Highest1DRoll,
    name='Average Roll With 1D')

def calculateValueRangeForDice(
        dieCount: typing.Union[int, common.ScalarCalculation],
        higherIsBetter: bool
        ) -> common.RangeCalculation:
    if not isinstance(dieCount, common.ScalarCalculation):
        assert(isinstance(dieCount, int))
        dieCount = common.ScalarCalculation(
            value=dieCount,
            name='Die Count')

    numericDieCount = dieCount.value()
    if numericDieCount > 1:
        lowestRoll = common.Calculator.multiply(
            lhs=_Lowest1DRoll,
            rhs=dieCount,
            name=f'Lowest Roll With {numericDieCount}D')
        highestRoll = common.Calculator.multiply(
            lhs=_Highest1DRoll,
            rhs=dieCount,
            name=f'Highest Roll With {numericDieCount}D')
        averageRoll = common.Calculator.multiply(
            lhs=_Average1DRoll,
            rhs=dieCount,
            name=f'Average Roll With {numericDieCount}D')
    else:
        lowestRoll = _Lowest1DRoll
        highestRoll = _Highest1DRoll
        averageRoll = _Average1DRoll

    range = common.RangeCalculation(
        worstCase=lowestRoll if higherIsBetter else highestRoll,
        bestCase=highestRoll if higherIsBetter else lowestRoll,
        averageCase=averageRoll,
        name=f'Roll With {numericDieCount}D')
    assert(isinstance(range, common.RangeCalculation))
    return range

# Recursive function for calculating percentage of rolling different values with different
# numbers of dice
# https://stackoverflow.com/questions/58405377/a-c-question-about-dice-probability-calculation
def _calculateRollProbabilities(
        checkValue: int,
        diceIndex: int,
        diceTypes: typing.Iterable[int],
        valueCombinations: typing.Iterable[int]
        ) -> int:
    if (diceIndex == len(diceTypes)):
        # No more dices -> save result and stop recursion
        if checkValue in valueCombinations:
            valueCombinations[checkValue] += 1
        else:
            valueCombinations[checkValue] = 1
        return 1

    # Iterate over all dice values
    totalCombinations = 0
    for i in range(diceTypes[diceIndex]):
        totalCombinations += _calculateRollProbabilities(
            checkValue=checkValue + i + 1,
            diceIndex=diceIndex + 1,
            diceTypes=diceTypes,
            valueCombinations=valueCombinations)
    return totalCombinations


_ProbabilityCache: typing.Dict[int, typing.Mapping[int, common.ScalarCalculation]] = {}

def _cacheRollProbabilities(
        dieCount: int,
        ) -> typing.Mapping[int, common.ScalarCalculation]:
    probabilities = _ProbabilityCache.get(dieCount)
    if probabilities:
        return probabilities

    diceTypes = [6] * dieCount
    valueCombinations = {}
    totalCombinations = _calculateRollProbabilities(
        diceIndex=0,
        checkValue=0,
        diceTypes=diceTypes,
        valueCombinations=valueCombinations)
    totalCombinations = common.ScalarCalculation(
        value=totalCombinations,
        name=f'Number Of Combinations Of {dieCount}D')

    probabilities = {}
    for value, combinations in valueCombinations.items():
        combinations = common.ScalarCalculation(
            value=combinations,
            name=f'Number Of Ways To Roll {value} with {dieCount}D')
        probabilities[value] = common.Calculator.divideFloat(
            lhs=combinations,
            rhs=totalCombinations,
            name=f'Normalised Percentage Probability Of Rolling {value} With {dieCount}D')
    _ProbabilityCache[dieCount] = probabilities
    return probabilities

class RollTargetType(enum.Enum):
    EqualTo = 0
    GreaterThan = 1
    GreaterOrEqualTo = 2
    LessThan = 3
    LessThanOrEqualTo = 4

# NOTE: This function returns a normalised percentage in the range (0->1.0)
def calculateRollProbability(
        dieCount: typing.Union[int, common.ScalarCalculation],
        targetType: RollTargetType,
        targetValue: typing.Union[int, common.ScalarCalculation],
        modifier: typing.Union[int, common.ScalarCalculation] = 0
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

    probabilities = _cacheRollProbabilities(dieCount=dieCount)
    assert(probabilities)

    minValue = min(probabilities.keys())
    maxValue = max(probabilities.keys())

    if targetType == RollTargetType.EqualTo:
        return probabilities[targetValue - modifier]
    elif targetType == RollTargetType.GreaterThan:
        startValue = max((targetValue + 1) - modifier, minValue)
        stopValue = maxValue
        typeString = 'Greater Than'
    elif targetType == RollTargetType.GreaterOrEqualTo:
        startValue = max(targetValue - modifier, minValue)
        stopValue = maxValue
        typeString = 'Greater Than Or Equal To'
    elif targetType == RollTargetType.LessThan:
        startValue = minValue
        stopValue = min((targetValue - 1) - modifier, maxValue)
        typeString = 'Less Than'
    elif targetType == RollTargetType.LessThanOrEqualTo:
        startValue = minValue
        stopValue = min(targetValue - modifier, maxValue)
        typeString = 'Less Than Or Equal To'
    else:
        raise ValueError('Invalid roll target type')

    values = []
    for value in range(startValue, stopValue + 1):
        values.append(probabilities[value])

    probabilityString = f'Percentage Probability Of Rolling {typeString} {targetValue} With {dieCount}D'
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
        modifier: typing.Union[int, common.ScalarCalculation] = 0
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

    probabilities = _cacheRollProbabilities(dieCount=dieCount)
    assert(probabilities)

    probabilityString = f'Percentage Probability Of Rolling Between {lowValue} and {highValue} With {dieCount}D'
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

class DieType(enum.Enum):
    D6 = 0
    D3 = 1
    DD = 2 # Roll XD6 and multiply the result by 10 (any constant is added after multiplication)

class DiceRoll(object):
    # This matches <OptionalDiceCount><DiceType><OptionalConstantModifier>
    # NOTE: The OptionalConstantModifier may contain a space between the sign
    # and numeric value which should be removed before converting to an int
    # NOTE: Even though DiceRoll supports it, this pattern doesn't match
    # 'dice rolls' that are just a constant value (i.e. no actual rolling).
    _DiceRollPattern = re.compile(r'^\s*((?:[+-]?\d+)?)([Dd][36Dd]*)\s*((?:[+-]\s*\d+)?)\s*$')

    def __init__(
            self,
            count: common.ScalarCalculation = common.ScalarCalculation(value=0),
            type: DieType = DieType.D6,
            constant: common.ScalarCalculation = common.ScalarCalculation(value=0),
            ) -> None:
        super().__init__()
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
