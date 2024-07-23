import common
import enum
import typing
import math

class Calculation(object):
    def name(self, forCalculation=False) -> typing.Optional[str]:
        raise RuntimeError('The name method should be overridden by derived classes')

    def calculationString(self, outerBrackets: bool, decimalPlaces: int = 2) -> str:
        raise RuntimeError('The calculationString method should be overridden by derived classes')

    def subCalculations(self) -> typing.List['ScalarCalculation']:
        raise RuntimeError('The subCalculations method should be overridden by derived classes')

    def worstCaseValue(self) -> typing.Union[int, float]:
        raise RuntimeError('The worstCaseValue method should be overridden by derived classes')

    def bestCaseValue(self) -> typing.Union[int, float]:
        raise RuntimeError('The bestCaseValue method should be overridden by derived classes')

    def averageCaseValue(self) -> typing.Union[int, float]:
        raise RuntimeError('The averageCaseValue method should be overridden by derived classes')

    def worstCaseCalculation(self) -> 'ScalarCalculation':
        raise RuntimeError('The worstCaseCalculation method should be overridden by derived classes')

    def bestCaseCalculation(self) -> 'ScalarCalculation':
        raise RuntimeError('The bestCalculation method should be overridden by derived classes')

    def averageCaseCalculation(self) -> 'ScalarCalculation':
        raise RuntimeError('The averageCaseCalculation method should be overridden by derived classes')

    def copy(self) -> typing.Any:
        raise RuntimeError('The copy method should be overridden by derived classes')

class CalculatorFunction(object):
    def value(self) -> typing.Union[int, float]:
        raise RuntimeError('The execute method should be overridden by derived classes')

    def calculationString(self, outerBrackets: bool, decimalPlaces: int = 2) -> str:
        raise RuntimeError('The getCalculationString method should be overridden by derived classes')

    def calculations(self) -> typing.List['ScalarCalculation']:
        raise RuntimeError('The getCalculations method should be overridden by derived classes')

    def copy(self) -> typing.Any:
        raise RuntimeError('The copy method should be overridden by derived classes')

# IMPORTANT: To avoid weird bugs the value of a ScalarValue should never be allowed to change
# after it's constructed
class ScalarCalculation(Calculation):
    def __init__(
            self,
            value: typing.Union[int, float, CalculatorFunction, 'ScalarCalculation'],
            name: typing.Optional[str] = None
            ) -> None:
        if isinstance(value, ScalarCalculation):
            self._value = value._value
            self._function = value._function
        elif isinstance(value, CalculatorFunction):
            self._value = value.value()
            self._function = value
        else:
            assert(isinstance(value, int) or isinstance(value, float))
            self._value = value
            self._function = None
        self._name = name

    def value(self) -> typing.Union[int, float]:
        return self._value

    def name(self, forCalculation=False) -> typing.Optional[str]:
        if not self._name:
            return None

        if forCalculation:
            return '<' + self._name + '>'

        return self._name

    def calculationString(
            self,
            outerBrackets: bool,
            decimalPlaces: int = 2
            ) -> str:
        if not self._function:
            return common.formatNumber(
                number=self._value,
                thousandsSeparator=False,
                decimalPlaces=decimalPlaces)

        return self._function.calculationString(
            outerBrackets=outerBrackets,
            decimalPlaces=decimalPlaces)

    def subCalculations(self) -> typing.List['ScalarCalculation']:
        if not self._function:
            return []
        return self._function.calculations()

    def worstCaseValue(self) -> typing.Union[int, float]:
        return self._value

    def bestCaseValue(self) -> typing.Union[int, float]:
        return self._value

    def averageCaseValue(self) -> typing.Union[int, float]:
        return self._value

    def worstCaseCalculation(self) -> 'ScalarCalculation':
        return self

    def bestCaseCalculation(self) -> 'ScalarCalculation':
        return self

    def averageCaseCalculation(self) -> 'ScalarCalculation':
        return self

    def copy(self) -> 'ScalarCalculation':
        return ScalarCalculation(
            value=self._function.copy() if self._function else self._value,
            name=self._name)

# IMPORTANT: To avoid weird bugs the min, max & avg values of a RangeValue should never be
# allowed to change after it's constructed
class RangeCalculation(Calculation):
    def __init__(
            self,
            worstCase: typing.Union[int, float, CalculatorFunction, ScalarCalculation],
            bestCase: typing.Union[int, float, CalculatorFunction, ScalarCalculation],
            averageCase: typing.Union[int, float, CalculatorFunction, ScalarCalculation],
            name: typing.Optional[str] = None
            ) -> None:
        worstCaseName = bestCaseName = averageCaseName = None
        if name:
            worstCaseName = 'Worst Case ' + name
            bestCaseName = 'Best Case ' + name
            averageCaseName = 'Average Case ' + name
        self._worstCaseCalculation = ScalarCalculation(value=worstCase, name=worstCaseName)
        self._bestCaseCalculation = ScalarCalculation(value=bestCase, name=bestCaseName)
        self._averageCaseCalculation = ScalarCalculation(value=averageCase, name=averageCaseName)
        self._name = name

    def worstCaseValue(self) -> typing.Union[int, float]:
        return self._worstCaseCalculation.value()

    def bestCaseValue(self) -> typing.Union[int, float]:
        return self._bestCaseCalculation.value()

    def averageCaseValue(self) -> typing.Union[int, float]:
        return self._averageCaseCalculation.value()

    def name(self) -> typing.Optional[str]:
        return self._name

    def worstCaseCalculation(self) -> ScalarCalculation:
        return self._worstCaseCalculation

    def bestCaseCalculation(self) -> ScalarCalculation:
        return self._bestCaseCalculation

    def averageCaseCalculation(self) -> ScalarCalculation:
        return self._averageCaseCalculation

    def copy(self) -> 'RangeCalculation':
        return RangeCalculation(
            worstCase=self._worstCaseCalculation.copy(),
            bestCase=self._bestCaseCalculation.copy(),
            averageCase=self._averageCaseCalculation.copy(),
            name=self._name)

class Calculator(object):
    class SingleParameterFunction(CalculatorFunction):
        def __init__(
                self,
                value: ScalarCalculation
                ) -> None:
            self._value = value

        def calculations(self) -> typing.List[ScalarCalculation]:
            if self._value.name():
                return [self._value]
            return self._value.subCalculations()

    class TwoParameterFunction(CalculatorFunction):
        def __init__(
                self,
                lhs: ScalarCalculation,
                rhs: ScalarCalculation
                ) -> None:
            self._lhs = lhs
            self._rhs = rhs

        def calculations(self) -> typing.List[ScalarCalculation]:
            calculations = []

            if self._lhs.name():
                calculations.append(self._lhs)
            else:
                calculations.extend(self._lhs.subCalculations())

            if self._rhs.name():
                calculations.append(self._rhs)
            else:
                calculations.extend(self._rhs.subCalculations())

            return calculations

    class RenameFunction(CalculatorFunction):
        def __init__(
                self,
                value: ScalarCalculation
                ) -> None:
            self._value = value

        def value(self) -> typing.Union[int, float]:
            return self._value.value()

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            return self._value.calculationString(
                outerBrackets=outerBrackets,
                decimalPlaces=decimalPlaces)

        def calculations(self) -> typing.List[ScalarCalculation]:
            return self._value.subCalculations()

        def copy(self) -> 'Calculator.RenameFunction':
            return Calculator.RenameFunction(self._value.copy())

    class EqualsFunction(SingleParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return self._value.value()

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            valueString = self._value.name(forCalculation=True)
            if not valueString:
                valueString = self._value.calculationString(
                    outerBrackets=outerBrackets,
                    decimalPlaces=decimalPlaces)
            return valueString

        def copy(self) -> 'Calculator.EqualsFunction':
            return Calculator.EqualsFunction(self._value.copy())

    class AddFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return self._lhs.value() + self._rhs.value()

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)
            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)

            calculationString = ''
            if outerBrackets:
                calculationString += '('
            calculationString += f'{lhsString} + {rhsString}'
            if outerBrackets:
                calculationString += ')'
            return calculationString

        def copy(self) -> 'Calculator.AddFunction':
            return Calculator.AddFunction(self._lhs.copy(), self._rhs.copy())

    class SubtractFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return self._lhs.value() - self._rhs.value()

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)
            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)

            calculationString = ''
            if outerBrackets:
                calculationString += '('
            calculationString += f'{lhsString} - {rhsString}'
            if outerBrackets:
                calculationString += ')'
            return calculationString

        def copy(self) -> 'Calculator.SubtractFunction':
            return Calculator.SubtractFunction(self._lhs.copy(), self._rhs.copy())

    class MultiplyFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return self._lhs.value() * self._rhs.value()

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)
            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)

            calculationString = ''
            if outerBrackets:
                calculationString += '('
            calculationString += f'{lhsString} * {rhsString}'
            if outerBrackets:
                calculationString += ')'
            return calculationString

        def copy(self) -> 'Calculator.MultiplyFunction':
            return Calculator.MultiplyFunction(self._lhs.copy(), self._rhs.copy())

    class DivideFloatFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            try:
                return self._lhs.value() / self._rhs.value()
            except ZeroDivisionError:
                lhs = self._lhs.value()
                if lhs > 0:
                    return float('inf')
                if lhs < 0:
                    return float('-inf')
                assert(lhs == 0)
                return 0.0

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)
            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)

            calculationString = ''
            if outerBrackets:
                calculationString += '('
            calculationString += f'{lhsString} / {rhsString}'
            if outerBrackets:
                calculationString += ')'
            return calculationString

        def copy(self) -> 'Calculator.DivideFloatFunction':
            return Calculator.DivideFloatFunction(self._lhs.copy(), self._rhs.copy())

    class DivideFloorFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            # I swapped out the old implementation after I found some odd behaviour
            # with // compared to dividing and flooring. An example of this would be
            # math.floor(26/2.6) == 10 however 26//2.6 == 9.0. I could imagine there
            # being some floating point rounding error but I don't understand why
            # floor and // wouldn't both show the same rounding errors.
            #return int(self._lhs.value() // self._rhs.value())
            return math.floor(self._lhs.value() / self._rhs.value())

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)
            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)

            if (self._lhs.value() % self._rhs.value()) == 0:
                # No rounding required so just use the values to simplify the string
                calculationString = ''
                if outerBrackets:
                    calculationString += '('
                calculationString += f'{lhsString} / {rhsString}'
                if outerBrackets:
                    calculationString += ')'
                return calculationString

            return f'RoundedDown({lhsString} / {rhsString})'

        def copy(self) -> 'Calculator.DivideFloorFunction':
            return Calculator.DivideFloorFunction(self._lhs.copy(), self._rhs.copy())

    class SumFunction(CalculatorFunction):
        def __init__(
                self,
                values: typing.List[ScalarCalculation]
                ) -> None:
            self._values = values

        def value(self) -> typing.Union[int, float]:
            sum = 0
            for value in self._values:
                sum += value.value()
            return sum

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            if not self._values:
                return common.formatNumber(
                    number=0,
                    decimalPlaces=decimalPlaces)

            resultString = ''

            if outerBrackets and len(self._values) > 1:
                resultString += '('

            isFirst = True
            for value in self._values:
                if not isFirst:
                    resultString += ' + '
                isFirst = False

                valueString = value.name(forCalculation=True)
                if not valueString:
                    valueString = value.calculationString(
                        outerBrackets=True if len(self._values) > 1 else outerBrackets,
                        decimalPlaces=decimalPlaces)

                resultString += valueString

            if outerBrackets and len(self._values) > 1:
                resultString += ')'

            return resultString

        def calculations(self) -> typing.List[ScalarCalculation]:
            calculations = []
            for value in self._values:
                if value.name():
                    calculations.append(value)
                else:
                    calculations.extend(value.subCalculations())
            return calculations

        def copy(self) -> 'Calculator.SumFunction':
            return Calculator.SumFunction(self._values.copy())

    class AverageFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return (self._lhs.value() + self._rhs.value()) / 2

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=False,
                    decimalPlaces=decimalPlaces)
            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=False,
                    decimalPlaces=decimalPlaces)
            return f'Average({lhsString}, {rhsString})'

        def copy(self) -> 'Calculator.AverageFunction':
            return Calculator.AverageFunction(self._lhs.copy(), self._rhs.copy())

    class FloorFunction(SingleParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return math.floor(self._value.value())

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            numericValue = self._value.value()
            noRoundingRequired = isinstance(numericValue, int) or numericValue.is_integer()

            valueString = self._value.name(forCalculation=True)
            if not valueString:
                valueString = self._value.calculationString(
                    outerBrackets=outerBrackets if noRoundingRequired else False,
                    decimalPlaces=decimalPlaces)

            if noRoundingRequired:
                # No rounding needed so just use the value string to simplify the string
                return valueString

            return f'RoundedDown({valueString})'

        def copy(self) -> 'Calculator.FloorFunction':
            return Calculator.FloorFunction(self._value.copy())

    class CeilFunction(SingleParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return math.ceil(self._value.value())

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            numericValue = self._value.value()
            noRoundingRequired = isinstance(numericValue, int) or numericValue.is_integer()

            valueString = self._value.name(forCalculation=True)
            if not valueString:
                valueString = self._value.calculationString(
                    outerBrackets=outerBrackets if noRoundingRequired else False,
                    decimalPlaces=decimalPlaces)

            if noRoundingRequired:
                # No rounding needed so just use the value string to simplify the string
                return valueString

            return f'RoundedUp({valueString})'

        def copy(self) -> 'Calculator.CeilFunction':
            return Calculator.CeilFunction(self._value.copy())

    # https://stackoverflow.com/questions/3410976/how-to-round-a-number-to-significant-figures-in-python
    class SignificantDigitsFunction(TwoParameterFunction):
        class Rounding(enum.Enum):
            Nearest = 'Nearest'
            Floor = 'Floor'
            Ceil = 'Ceil'

        def __init__(
                self,
                lhs: ScalarCalculation,
                rhs: ScalarCalculation,
                rounding: Rounding = Rounding.Nearest
                ) -> None:
            self._lhs = lhs
            self._rhs = rhs
            self._rounding = rounding

        def value(self) -> typing.Union[int, float]:
            value = self._lhs.value()
            if value == 0:
                return 0
            absValue = abs(value)
            if absValue < 1:
                return 0
            digits = self._rhs.value() - int(math.floor(math.log10(absValue))) - 1

            if self._rounding != Calculator.SignificantDigitsFunction.Rounding.Nearest:
                fudge = math.pow(10, -digits) / 2
                if self._rounding == Calculator.SignificantDigitsFunction.Rounding.Floor:
                    value -= fudge
                elif self._rounding == Calculator.SignificantDigitsFunction.Rounding.Ceil:
                    value += fudge

            return round(value, digits)

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            numberString = self._lhs.name(forCalculation=True)
            if not numberString:
                numberString = self._lhs.calculationString(
                    outerBrackets=False,
                    decimalPlaces=decimalPlaces)

            digitsString = self._rhs.name(forCalculation=True)
            if not digitsString:
                digitsString = self._rhs.calculationString(
                    outerBrackets=False,
                    decimalPlaces=decimalPlaces)

            return f'{self._rounding.value}SignificantDigits({numberString}, {digitsString})'

        def copy(self) -> 'Calculator.SignificantDigitsFunction':
            return Calculator.SignificantDigitsFunction(
                lhs=self._lhs.copy(),
                rhs=self._rhs.copy(),
                rounding=self._rounding)

    class MinFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return min(self._lhs.value(), self._rhs.value())

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=False,
                    decimalPlaces=decimalPlaces)

            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=False,
                    decimalPlaces=decimalPlaces)

            return f'Minimum({lhsString}, {rhsString})'

        def copy(self) -> 'Calculator.MinFunction':
            return Calculator.MinFunction(self._lhs.copy(), self._rhs.copy())

    class MaxFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return max(self._lhs.value(), self._rhs.value())

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=False,
                    decimalPlaces=decimalPlaces)

            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=False,
                    decimalPlaces=decimalPlaces)

            return f'Maximum({lhsString}, {rhsString})'

        def copy(self) -> 'Calculator.MaxFunction':
            return Calculator.MaxFunction(self._lhs.copy(), self._rhs.copy())

    class NegateFunction(SingleParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return -self._value.value()

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            valueString = self._value.name(forCalculation=True)
            if not valueString:
                valueString = self._value.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)

            calculationString = ''
            if outerBrackets:
                calculationString += '('
            calculationString += f'Negate({valueString})'
            if outerBrackets:
                calculationString += ')'
            return calculationString

        def copy(self) -> 'Calculator.NegateFunction':
            return Calculator.NegateFunction(self._value.copy())

    class AbsoluteFunction(SingleParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return abs(self._value.value())

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            valueString = self._value.name(forCalculation=True)
            if not valueString:
                valueString = self._value.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)

            calculationString = ''
            if outerBrackets:
                calculationString += '('
            calculationString += f'Absolute({valueString})'
            if outerBrackets:
                calculationString += ')'
            return calculationString

        def copy(self) -> 'Calculator.AbsoluteFunction':
            return Calculator.AbsoluteFunction(self._value.copy())

    # This can be used to capture calculation logic when overriding (i.e. replacing) one
    # value with another
    class OverrideFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return self._rhs.value()

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=False,
                    decimalPlaces=decimalPlaces)

            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=False,
                    decimalPlaces=decimalPlaces)

            return f'Override(old={lhsString}, new={rhsString})'

        def copy(self) -> 'Calculator.OverrideFunction':
            return Calculator.OverrideFunction(self._lhs.copy(), self._rhs.copy())

    class TakePercentageFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return self._lhs.value() * (self._rhs.value() / 100)

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)
            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)

            calculationString = ''
            if outerBrackets:
                calculationString += '('
            calculationString += f'{rhsString}% of {lhsString}'
            if outerBrackets:
                calculationString += ')'
            return calculationString

        def copy(self) -> 'Calculator.TakePercentageFunction':
            return Calculator.TakePercentageFunction(self._lhs.copy(), self._rhs.copy())

    class ApplyPercentageFunction(TwoParameterFunction):
        def value(self) -> typing.Union[int, float]:
            return self._lhs.value() * (1.0 + (self._rhs.value() / 100))

        def calculationString(
                self,
                outerBrackets: bool,
                decimalPlaces: int = 2
                ) -> str:
            lhsString = self._lhs.name(forCalculation=True)
            if not lhsString:
                lhsString = self._lhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)
            rhsString = self._rhs.name(forCalculation=True)
            if not rhsString:
                rhsString = self._rhs.calculationString(
                    outerBrackets=True,
                    decimalPlaces=decimalPlaces)

            calculationString = ''
            if outerBrackets:
                calculationString += '('
            calculationString += f'{lhsString} + {rhsString}%'
            if outerBrackets:
                calculationString += ')'
            return calculationString

        def copy(self) -> 'Calculator.ApplyPercentageFunction':
            return Calculator.ApplyPercentageFunction(self._lhs.copy(), self._rhs.copy())

    @typing.overload
    @staticmethod
    def rename(
        value: ScalarCalculation,
        name: str # Unlike other functions name is mandatory for alias
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def rename(
        value: RangeCalculation,
        name: str # Unlike other functions name is mandatory for alias
        ) -> RangeCalculation: ...

    @staticmethod
    def rename(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            name: str # Unlike most other functions name is mandatory for rename
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.RenameFunction(value),
                name=name)

        assert(isinstance(value, RangeCalculation))
        return RangeCalculation(
            worstCase=Calculator.RenameFunction(value.worstCaseCalculation()),
            bestCase=Calculator.RenameFunction(value.bestCaseCalculation()),
            averageCase=Calculator.RenameFunction(value.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def equals(
        value: ScalarCalculation,
        name: str = None
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def equals(
        value: RangeCalculation,
        name: str = None
        ) -> RangeCalculation: ...

    @staticmethod
    def equals(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            name: str = None
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.EqualsFunction(value),
                name=name)

        assert(isinstance(value, RangeCalculation))
        return RangeCalculation(
            worstCase=Calculator.EqualsFunction(value.worstCaseCalculation()),
            bestCase=Calculator.EqualsFunction(value.bestCaseCalculation()),
            averageCase=Calculator.EqualsFunction(value.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def add(
        lhs: ScalarCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def add(
        lhs: ScalarCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def add(
        lhs: RangeCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def add(
        lhs: RangeCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def add(
            lhs: typing.Union[ScalarCalculation, RangeCalculation],
            rhs: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(lhs, ScalarCalculation) and isinstance(rhs, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.AddFunction(lhs, rhs),
                name=name)
        assert(isinstance(lhs, ScalarCalculation) or isinstance(lhs, RangeCalculation))
        assert(isinstance(rhs, ScalarCalculation) or isinstance(rhs, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.AddFunction(lhs.worstCaseCalculation(), rhs.worstCaseCalculation()),
            bestCase=Calculator.AddFunction(lhs.bestCaseCalculation(), rhs.bestCaseCalculation()),
            averageCase=Calculator.AddFunction(lhs.averageCaseCalculation(), rhs.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def subtract(
        lhs: ScalarCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def subtract(
        lhs: ScalarCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def subtract(
        lhs: RangeCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def subtract(
        lhs: RangeCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def subtract(
            lhs: typing.Union[ScalarCalculation, RangeCalculation],
            rhs: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(lhs, ScalarCalculation) and isinstance(rhs, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.SubtractFunction(lhs, rhs),
                name=name)
        assert(isinstance(lhs, ScalarCalculation) or isinstance(lhs, RangeCalculation))
        assert(isinstance(rhs, ScalarCalculation) or isinstance(rhs, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.SubtractFunction(lhs.worstCaseCalculation(), rhs.worstCaseCalculation()),
            bestCase=Calculator.SubtractFunction(lhs.bestCaseCalculation(), rhs.bestCaseCalculation()),
            averageCase=Calculator.SubtractFunction(lhs.averageCaseCalculation(), rhs.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def multiply(
        lhs: ScalarCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def multiply(
        lhs: ScalarCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def multiply(
        lhs: RangeCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def multiply(
        lhs: RangeCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def multiply(
            lhs: typing.Union[ScalarCalculation, RangeCalculation],
            rhs: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(lhs, ScalarCalculation) and isinstance(rhs, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.MultiplyFunction(lhs, rhs),
                name=name)
        assert(isinstance(lhs, ScalarCalculation) or isinstance(lhs, RangeCalculation))
        assert(isinstance(rhs, ScalarCalculation) or isinstance(rhs, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.MultiplyFunction(lhs.worstCaseCalculation(), rhs.worstCaseCalculation()),
            bestCase=Calculator.MultiplyFunction(lhs.bestCaseCalculation(), rhs.bestCaseCalculation()),
            averageCase=Calculator.MultiplyFunction(lhs.averageCaseCalculation(), rhs.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def divideFloat(
        lhs: ScalarCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def divideFloat(
        lhs: ScalarCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def divideFloat(
        lhs: RangeCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def divideFloat(
        lhs: RangeCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def divideFloat(
            lhs: typing.Union[ScalarCalculation, RangeCalculation],
            rhs: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(lhs, ScalarCalculation) and isinstance(rhs, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.DivideFloatFunction(lhs, rhs),
                name=name)
        assert(isinstance(lhs, ScalarCalculation) or isinstance(lhs, RangeCalculation))
        assert(isinstance(rhs, ScalarCalculation) or isinstance(rhs, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.DivideFloatFunction(lhs.worstCaseCalculation(), rhs.worstCaseCalculation()),
            bestCase=Calculator.DivideFloatFunction(lhs.bestCaseCalculation(), rhs.bestCaseCalculation()),
            averageCase=Calculator.DivideFloatFunction(lhs.averageCaseCalculation(), rhs.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def divideFloor(
        lhs: ScalarCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def divideFloor(
        lhs: ScalarCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def divideFloor(
        lhs: RangeCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def divideFloor(
        lhs: RangeCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def divideFloor(
            lhs: typing.Union[ScalarCalculation, RangeCalculation],
            rhs: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(lhs, ScalarCalculation) and isinstance(rhs, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.DivideFloorFunction(lhs, rhs),
                name=name)
        assert(isinstance(lhs, ScalarCalculation) or isinstance(lhs, RangeCalculation))
        assert(isinstance(rhs, ScalarCalculation) or isinstance(rhs, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.DivideFloorFunction(lhs.worstCaseCalculation(), rhs.worstCaseCalculation()),
            bestCase=Calculator.DivideFloorFunction(lhs.bestCaseCalculation(), rhs.bestCaseCalculation()),
            averageCase=Calculator.DivideFloorFunction(lhs.averageCaseCalculation(), rhs.averageCaseCalculation()),
            name=name)

    @staticmethod
    def sum(
            values: typing.Iterable[typing.Union[ScalarCalculation, RangeCalculation]],
            name: typing.Optional[str] = None
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        hasRange = False
        for value in values:
            if isinstance(value, RangeCalculation):
                hasRange = True
                break

        if not hasRange:
            return ScalarCalculation(
                value=Calculator.SumFunction(values),
                name=name)

        worstCaseValues = []
        bestCaseValues = []
        averageCaseValues = []

        for value in values:
            worstCaseValues.append(value.worstCaseCalculation())
            bestCaseValues.append(value.bestCaseCalculation())
            averageCaseValues.append(value.averageCaseCalculation())

        return RangeCalculation(
            worstCase=Calculator.SumFunction(worstCaseValues),
            bestCase=Calculator.SumFunction(bestCaseValues),
            averageCase=Calculator.SumFunction(averageCaseValues),
            name=name)

    @typing.overload
    @staticmethod
    def average(
        lhs: ScalarCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def average(
        lhs: ScalarCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def average(
        lhs: RangeCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def average(
        lhs: RangeCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None
        ) -> RangeCalculation: ...

    @staticmethod
    def average(
            lhs: typing.Union[ScalarCalculation, RangeCalculation],
            rhs: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(lhs, ScalarCalculation) and isinstance(rhs, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.AverageFunction(lhs, rhs),
                name=name)
        assert(isinstance(lhs, ScalarCalculation) or isinstance(lhs, RangeCalculation))
        assert(isinstance(rhs, ScalarCalculation) or isinstance(rhs, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.AverageFunction(lhs.worstCaseCalculation(), rhs.worstCaseCalculation()),
            bestCase=Calculator.AverageFunction(lhs.bestCaseCalculation(), rhs.bestCaseCalculation()),
            averageCase=Calculator.AverageFunction(lhs.averageCaseCalculation(), rhs.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def floor(
        value: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def floor(
        value: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def floor(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.FloorFunction(value),
                name=name)
        assert(isinstance(value, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.FloorFunction(value.worstCaseCalculation()),
            bestCase=Calculator.FloorFunction(value.bestCaseCalculation()),
            averageCase=Calculator.FloorFunction(value.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def ceil(
        value: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def ceil(
        value: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def ceil(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.CeilFunction(value),
                name=name)
        assert(isinstance(value, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.CeilFunction(value.worstCaseCalculation()),
            bestCase=Calculator.CeilFunction(value.bestCaseCalculation()),
            averageCase=Calculator.CeilFunction(value.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def significantDigits(
        value: ScalarCalculation,
        digits: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def significantDigits(
        value: RangeCalculation,
        digits: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def significantDigits(
        value: RangeCalculation,
        digits: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def significantDigits(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            digits: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation) and isinstance(digits, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.SignificantDigitsFunction(value, digits),
                name=name)
        assert(isinstance(value, ScalarCalculation) or isinstance(value, RangeCalculation))
        assert(isinstance(digits, ScalarCalculation) or isinstance(digits, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.SignificantDigitsFunction(value.worstCaseCalculation(), digits.worstCaseCalculation()),
            bestCase=Calculator.SignificantDigitsFunction(value.bestCaseCalculation(), digits.bestCaseCalculation()),
            averageCase=Calculator.SignificantDigitsFunction(value.averageCaseCalculation(), digits.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def floorDigits(
        value: ScalarCalculation,
        digits: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def floorDigits(
        value: RangeCalculation,
        digits: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def floorDigits(
        value: RangeCalculation,
        digits: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def floorDigits(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            digits: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation) and isinstance(digits, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.SignificantDigitsFunction(
                    lhs=value,
                    rhs=digits,
                    rounding=Calculator.SignificantDigitsFunction.Rounding.Floor),
                name=name)
        assert(isinstance(value, ScalarCalculation) or isinstance(value, RangeCalculation))
        assert(isinstance(digits, ScalarCalculation) or isinstance(digits, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.SignificantDigitsFunction(
                lhs=value.worstCaseCalculation(),
                rhs=digits.worstCaseCalculation(),
                rounding=Calculator.SignificantDigitsFunction.Rounding.Floor),
            bestCase=Calculator.SignificantDigitsFunction(
                lhs=value.bestCaseCalculation(),
                rhs=digits.bestCaseCalculation(),
                rounding=Calculator.SignificantDigitsFunction.Rounding.Floor),
            averageCase=Calculator.SignificantDigitsFunction(
                lhs=value.averageCaseCalculation(),
                rhs=digits.averageCaseCalculation(),
                rounding=Calculator.SignificantDigitsFunction.Rounding.Floor),
            name=name)

    @typing.overload
    @staticmethod
    def ceilDigits(
        value: ScalarCalculation,
        digits: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def ceilDigits(
        value: RangeCalculation,
        digits: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def ceilDigits(
        value: RangeCalculation,
        digits: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def ceilDigits(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            digits: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation) and isinstance(digits, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.SignificantDigitsFunction(
                    lhs=value,
                    rhs=digits,
                    rounding=Calculator.SignificantDigitsFunction.Rounding.Ceil),
                name=name)
        assert(isinstance(value, ScalarCalculation) or isinstance(value, RangeCalculation))
        assert(isinstance(digits, ScalarCalculation) or isinstance(digits, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.SignificantDigitsFunction(
                lhs=value.worstCaseCalculation(),
                rhs=digits.worstCaseCalculation(),
                rounding=Calculator.SignificantDigitsFunction.Rounding.Ceil),
            bestCase=Calculator.SignificantDigitsFunction(
                lhs=value.bestCaseCalculation(),
                rhs=digits.bestCaseCalculation(),
                rounding=Calculator.SignificantDigitsFunction.Rounding.Ceil),
            averageCase=Calculator.SignificantDigitsFunction(
                lhs=value.averageCaseCalculation(),
                rhs=digits.averageCaseCalculation(),
                rounding=Calculator.SignificantDigitsFunction.Rounding.Ceil),
            name=name)

    @typing.overload
    @staticmethod
    def min(
        lhs: ScalarCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def min(
        lhs: ScalarCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def min(
        lhs: RangeCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def min(
        lhs: RangeCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def min(
            lhs: typing.Union[ScalarCalculation, RangeCalculation],
            rhs: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(lhs, ScalarCalculation) and isinstance(rhs, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.MinFunction(lhs, rhs),
                name=name)
        assert(isinstance(lhs, ScalarCalculation) or isinstance(lhs, RangeCalculation))
        assert(isinstance(rhs, ScalarCalculation) or isinstance(rhs, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.MinFunction(lhs.worstCaseCalculation(), rhs.worstCaseCalculation()),
            bestCase=Calculator.MinFunction(lhs.bestCaseCalculation(), rhs.bestCaseCalculation()),
            averageCase=Calculator.MinFunction(lhs.averageCaseCalculation(), rhs.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def max(
        lhs: ScalarCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def max(
        lhs: ScalarCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def max(
        lhs: RangeCalculation,
        rhs: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def max(
        lhs: RangeCalculation,
        rhs: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def max(
            lhs: typing.Union[ScalarCalculation, RangeCalculation],
            rhs: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(lhs, ScalarCalculation) and isinstance(rhs, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.MaxFunction(lhs, rhs),
                name=name)
        assert(isinstance(lhs, ScalarCalculation) or isinstance(lhs, RangeCalculation))
        assert(isinstance(rhs, ScalarCalculation) or isinstance(rhs, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.MaxFunction(lhs.worstCaseCalculation(), rhs.worstCaseCalculation()),
            bestCase=Calculator.MaxFunction(lhs.bestCaseCalculation(), rhs.bestCaseCalculation()),
            averageCase=Calculator.MaxFunction(lhs.averageCaseCalculation(), rhs.averageCaseCalculation()),
            name=name)

    @typing.overload
    def negate(
        value: ScalarCalculation,
        name: typing.Optional[str] = None
        ) -> ScalarCalculation: ...

    @typing.overload
    def negate(
        value: RangeCalculation,
        name: typing.Optional[str] = None
        ) -> RangeCalculation: ...

    def negate(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.NegateFunction(value),
                name=name)

        assert(isinstance(value, RangeCalculation))
        return RangeCalculation(
            worstCase=Calculator.NegateFunction(value.worstCaseCalculation()),
            bestCase=Calculator.NegateFunction(value.bestCaseCalculation()),
            averageCase=Calculator.NegateFunction(value.averageCaseCalculation()),
            name=name)

    @typing.overload
    def absolute(
        value: ScalarCalculation,
        name: typing.Optional[str] = None
        ) -> ScalarCalculation: ...

    @typing.overload
    def absolute(
        value: RangeCalculation,
        name: typing.Optional[str] = None
        ) -> RangeCalculation: ...

    def absolute(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.AbsoluteFunction(value),
                name=name)

        assert(isinstance(value, RangeCalculation))
        return RangeCalculation(
            worstCase=Calculator.AbsoluteFunction(value.worstCaseCalculation()),
            bestCase=Calculator.AbsoluteFunction(value.bestCaseCalculation()),
            averageCase=Calculator.AbsoluteFunction(value.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def override(
        old: ScalarCalculation,
        new: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def override(
        old: ScalarCalculation,
        new: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def override(
        old: RangeCalculation,
        new: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def override(
        old: RangeCalculation,
        new: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def override(
            old: typing.Union[ScalarCalculation, RangeCalculation],
            new: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(old, ScalarCalculation) and isinstance(new, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.OverrideFunction(old, new),
                name=name)
        assert(isinstance(old, ScalarCalculation) or isinstance(old, RangeCalculation))
        assert(isinstance(new, ScalarCalculation) or isinstance(new, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.OverrideFunction(old.worstCaseCalculation(), new.worstCaseCalculation()),
            bestCase=Calculator.OverrideFunction(old.bestCaseCalculation(), new.bestCaseCalculation()),
            averageCase=Calculator.OverrideFunction(old.averageCaseCalculation(), new.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def takePercentage(
        value: ScalarCalculation,
        percentage: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def takePercentage(
        value: ScalarCalculation,
        percentage: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def takePercentage(
        value: RangeCalculation,
        percentage: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def takePercentage(
        value: RangeCalculation,
        percentage: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def takePercentage(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            percentage: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation) and isinstance(percentage, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.TakePercentageFunction(value, percentage),
                name=name)
        assert(isinstance(value, ScalarCalculation) or isinstance(value, RangeCalculation))
        assert(isinstance(percentage, ScalarCalculation) or isinstance(percentage, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.TakePercentageFunction(value.worstCaseCalculation(), percentage.worstCaseCalculation()),
            bestCase=Calculator.TakePercentageFunction(value.bestCaseCalculation(), percentage.bestCaseCalculation()),
            averageCase=Calculator.TakePercentageFunction(value.averageCaseCalculation(), percentage.averageCaseCalculation()),
            name=name)

    @typing.overload
    @staticmethod
    def applyPercentage(
        value: ScalarCalculation,
        percentage: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def applyPercentage(
        value: ScalarCalculation,
        percentage: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def applyPercentage(
        value: RangeCalculation,
        percentage: ScalarCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @typing.overload
    @staticmethod
    def applyPercentage(
        value: RangeCalculation,
        percentage: RangeCalculation,
        name: typing.Optional[str] = None,
        ) -> RangeCalculation: ...

    @staticmethod
    def applyPercentage(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            percentage: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None,
            ) -> typing.Union[ScalarCalculation, RangeCalculation]:
        if isinstance(value, ScalarCalculation) and isinstance(percentage, ScalarCalculation):
            return ScalarCalculation(
                value=Calculator.ApplyPercentageFunction(value, percentage),
                name=name)
        assert(isinstance(value, ScalarCalculation) or isinstance(value, RangeCalculation))
        assert(isinstance(percentage, ScalarCalculation) or isinstance(percentage, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.ApplyPercentageFunction(value.worstCaseCalculation(), percentage.worstCaseCalculation()),
            bestCase=Calculator.ApplyPercentageFunction(value.bestCaseCalculation(), percentage.bestCaseCalculation()),
            averageCase=Calculator.ApplyPercentageFunction(value.averageCaseCalculation(), percentage.averageCaseCalculation()),
            name=name)
