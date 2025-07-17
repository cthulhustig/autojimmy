import common
import enum
import json
import logging
import packaging
import packaging.version
import threading
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

    @staticmethod
    def serialisationType() -> str:
        raise RuntimeError('The static serialisationType method should be overridden by derived classes')

    def toJson(self) -> typing.Mapping[str, typing.Any]:
        raise RuntimeError('The toJson method should be overridden by derived classes')

    @staticmethod
    def fromJson(jsonData: typing.Mapping[str, typing.Any]) -> 'CalculatorFunction':
        raise RuntimeError('The static fromJson method should be overridden by derived classes')

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
            assert(isinstance(value, (int, float)))
            self._value = value
            self._function = None
        self._name = name

    def value(self) -> typing.Union[int, float]:
        return self._value

    def function(self) -> typing.Optional[CalculatorFunction]:
        return self._function

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

    def name(self, forCalculation=False) -> typing.Optional[str]:
        if not self._name:
            return None

        if forCalculation:
            return '<' + self._name + '>'

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

        @staticmethod
        def serialisationType() -> str:
            return 'rename'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {'value': serialiseCalculation(self._value, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.RenameFunction':
            value = jsonData.get('value')
            if value is None:
                raise RuntimeError('Rename function is missing the value property')
            value = deserialiseCalculation(jsonData=value)
            return Calculator.RenameFunction(value=value)

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

        @staticmethod
        def serialisationType() -> str:
            return 'equals'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {'value': serialiseCalculation(self._value, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.EqualsFunction':
            value = jsonData.get('value')
            if value is None:
                raise RuntimeError('Equals function is missing the value property')
            value = deserialiseCalculation(jsonData=value)
            return Calculator.EqualsFunction(value=value)

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

        @staticmethod
        def serialisationType() -> str:
            return 'add'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'lhs': serialiseCalculation(self._lhs, includeVersion=False),
                'rhs': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.AddFunction':
            lhs = jsonData.get('lhs')
            if lhs is None:
                raise RuntimeError('Add function is missing the lhs property')
            lhs = deserialiseCalculation(jsonData=lhs)

            rhs = jsonData.get('rhs')
            if rhs is None:
                raise RuntimeError('Add function is missing the rhs property')
            rhs = deserialiseCalculation(jsonData=rhs)

            return Calculator.AddFunction(lhs=lhs, rhs=rhs)

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

        @staticmethod
        def serialisationType() -> str:
            return 'subtract'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'lhs': serialiseCalculation(self._lhs, includeVersion=False),
                'rhs': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.SubtractFunction':
            lhs = jsonData.get('lhs')
            if lhs is None:
                raise RuntimeError('Subtract function is missing the lhs property')
            lhs = deserialiseCalculation(jsonData=lhs)

            rhs = jsonData.get('rhs')
            if rhs is None:
                raise RuntimeError('Subtract function is missing the rhs property')
            rhs = deserialiseCalculation(jsonData=rhs)

            return Calculator.SubtractFunction(lhs=lhs, rhs=rhs)

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

        @staticmethod
        def serialisationType() -> str:
            return 'multiply'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'lhs': serialiseCalculation(self._lhs, includeVersion=False),
                'rhs': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.MultiplyFunction':
            lhs = jsonData.get('lhs')
            if lhs is None:
                raise RuntimeError('Multiply function is missing the lhs property')
            lhs = deserialiseCalculation(jsonData=lhs)

            rhs = jsonData.get('rhs')
            if rhs is None:
                raise RuntimeError('Multiply function is missing the rhs property')
            rhs = deserialiseCalculation(jsonData=rhs)

            return Calculator.MultiplyFunction(lhs=lhs, rhs=rhs)

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

        @staticmethod
        def serialisationType() -> str:
            return 'dividef'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'lhs': serialiseCalculation(self._lhs, includeVersion=False),
                'rhs': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.DivideFloatFunction':
            lhs = jsonData.get('lhs')
            if lhs is None:
                raise RuntimeError('Divide float function is missing the lhs property')
            lhs = deserialiseCalculation(jsonData=lhs)

            rhs = jsonData.get('rhs')
            if rhs is None:
                raise RuntimeError('Divide float function is missing the rhs property')
            rhs = deserialiseCalculation(jsonData=rhs)

            return Calculator.DivideFloatFunction(lhs=lhs, rhs=rhs)

    class DivideIntegerFunction(TwoParameterFunction):
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

        def copy(self) -> 'Calculator.DivideIntegerFunction':
            return Calculator.DivideIntegerFunction(self._lhs.copy(), self._rhs.copy())

        @staticmethod
        def serialisationType() -> str:
            return 'dividei'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'lhs': serialiseCalculation(self._lhs, includeVersion=False),
                'rhs': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.DivideIntegerFunction':
            lhs = jsonData.get('lhs')
            if lhs is None:
                raise RuntimeError('Divide integer function is missing the lhs property')
            lhs = deserialiseCalculation(jsonData=lhs)

            rhs = jsonData.get('rhs')
            if rhs is None:
                raise RuntimeError('Divide integer function is missing the rhs property')
            rhs = deserialiseCalculation(jsonData=rhs)

            return Calculator.DivideIntegerFunction(lhs=lhs, rhs=rhs)

    class SumFunction(CalculatorFunction):
        def __init__(
                self,
                values: typing.Sequence[ScalarCalculation]
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
            return Calculator.SumFunction(values=[v.copy() for v in self._values])

        @staticmethod
        def serialisationType() -> str:
            return 'sum'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {'values': serialiseCalculationList(self._values, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.SumFunction':
            jsonValues = jsonData.get('values')
            if jsonValues is None:
                raise RuntimeError('Sum function is missing the values property')
            if not isinstance(jsonValues, list):
                raise RuntimeError('Sum function values property is not a list')

            values = []
            for jsonValue in jsonValues:
                values.append(deserialiseCalculation(jsonData=jsonValue))

            return Calculator.SumFunction(values=values)

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

        @staticmethod
        def serialisationType() -> str:
            return 'average'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'lhs': serialiseCalculation(self._lhs, includeVersion=False),
                'rhs': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.AverageFunction':
            lhs = jsonData.get('lhs')
            if lhs is None:
                raise RuntimeError('Average function is missing the lhs property')
            lhs = deserialiseCalculation(jsonData=lhs)

            rhs = jsonData.get('rhs')
            if rhs is None:
                raise RuntimeError('Average function is missing the rhs property')
            rhs = deserialiseCalculation(jsonData=rhs)

            return Calculator.AverageFunction(lhs=lhs, rhs=rhs)

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

        @staticmethod
        def serialisationType() -> str:
            return 'floor'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {'value': serialiseCalculation(self._value, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.FloorFunction':
            value = jsonData.get('value')
            if value is None:
                raise RuntimeError('Floor function is missing the value property')
            value = deserialiseCalculation(jsonData=value)
            return Calculator.FloorFunction(value=value)

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

        @staticmethod
        def serialisationType() -> str:
            return 'ceil'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {'value': serialiseCalculation(self._value, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.CeilFunction':
            value = jsonData.get('value')
            if value is None:
                raise RuntimeError('Ceil function is missing the value property')
            value = deserialiseCalculation(jsonData=value)
            return Calculator.CeilFunction(value=value)

    # https://stackoverflow.com/questions/3410976/how-to-round-a-number-to-significant-figures-in-python
    class SignificantDigitsFunction(TwoParameterFunction):
        # NOTE: If the values of this enum change I'll need to add some kind
        # of mapping for serialisation
        class Rounding(enum.Enum):
            Nearest = 'Nearest'
            Floor = 'Floor'
            Ceil = 'Ceil'
        _RoundingSerialisationTypeToStr = {e: e.value.lower() for e in Rounding}
        _RoundingSerialisationStrToType = {v: k for k, v in _RoundingSerialisationTypeToStr.items()}

        def __init__(
                self,
                value: ScalarCalculation,
                digits: ScalarCalculation,
                rounding: Rounding = Rounding.Nearest
                ) -> None:
            super().__init__(lhs=value, rhs=digits)
            self._rounding = rounding

        def value(self) -> typing.Union[int, float]:
            value = self._lhs.value()
            if value == 0:
                return 0
            absValue = abs(value)
            if absValue < 1:
                return 0
            digits = int(self._rhs.value() - int(math.floor(math.log10(absValue))) - 1)

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
                value=self._lhs.copy(),
                digits=self._rhs.copy(),
                rounding=self._rounding)

        @staticmethod
        def serialisationType() -> str:
            return 'sigdigs'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'value': serialiseCalculation(self._lhs, includeVersion=False),
                'digits': serialiseCalculation(self._rhs, includeVersion=False),
                'rounding': Calculator.SignificantDigitsFunction._RoundingSerialisationTypeToStr[self._rounding]}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.SignificantDigitsFunction':
            value = jsonData.get('value')
            if value is None:
                raise RuntimeError('Significant digits function is missing the value property')
            value = deserialiseCalculation(jsonData=value)

            digits = jsonData.get('digits')
            if digits is None:
                raise RuntimeError('Significant digits function is missing the digits property')
            digits = deserialiseCalculation(jsonData=digits)

            rounding = jsonData.get('rounding')
            if rounding is None:
                raise RuntimeError('Significant digits function is missing the rounding property')
            if not isinstance(rounding, str):
                raise RuntimeError('Significant digits function rounding property is not a string')
            rounding = rounding.lower()
            if rounding not in Calculator.SignificantDigitsFunction._RoundingSerialisationStrToType:
                raise RuntimeError(f'Significant digits function has invalid rounding property {rounding}')
            rounding = Calculator.SignificantDigitsFunction._RoundingSerialisationStrToType[rounding]

            return Calculator.SignificantDigitsFunction(value=value, digits=digits, rounding=rounding)

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

        @staticmethod
        def serialisationType() -> str:
            return 'min'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'lhs': serialiseCalculation(self._lhs, includeVersion=False),
                'rhs': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.MinFunction':
            lhs = jsonData.get('lhs')
            if lhs is None:
                raise RuntimeError('Min function is missing the lhs property')
            lhs = deserialiseCalculation(jsonData=lhs)

            rhs = jsonData.get('rhs')
            if rhs is None:
                raise RuntimeError('Min function is missing the rhs property')
            rhs = deserialiseCalculation(jsonData=rhs)

            return Calculator.MinFunction(lhs=lhs, rhs=rhs)

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

        @staticmethod
        def serialisationType() -> str:
            return 'max'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'lhs': serialiseCalculation(self._lhs, includeVersion=False),
                'rhs': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.MaxFunction':
            lhs = jsonData.get('lhs')
            if lhs is None:
                raise RuntimeError('Max function is missing the lhs property')
            lhs = deserialiseCalculation(jsonData=lhs)

            rhs = jsonData.get('rhs')
            if rhs is None:
                raise RuntimeError('Max function is missing the rhs property')
            rhs = deserialiseCalculation(jsonData=rhs)

            return Calculator.MaxFunction(lhs=lhs, rhs=rhs)

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

        @staticmethod
        def serialisationType() -> str:
            return 'negate'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {'value': serialiseCalculation(self._value, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.NegateFunction':
            value = jsonData.get('value')
            if value is None:
                raise RuntimeError('Negate function is missing the value property')
            value = deserialiseCalculation(jsonData=value)
            return Calculator.NegateFunction(value=value)

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

        @staticmethod
        def serialisationType() -> str:
            return 'abs'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {'value': serialiseCalculation(self._value, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.AbsoluteFunction':
            value = jsonData.get('value')
            if value is None:
                raise RuntimeError('Absolute function is missing the value property')
            value = deserialiseCalculation(jsonData=value)
            return Calculator.AbsoluteFunction(value=value)

    # This can be used to capture calculation logic when overriding (i.e. replacing) one
    # value with another
    class OverrideFunction(TwoParameterFunction):
        def __init__(
                self,
                old: ScalarCalculation,
                new: ScalarCalculation
                ) -> None:
            super().__init__(lhs=old, rhs=new)

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

        @staticmethod
        def serialisationType() -> str:
            return 'override'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'old': serialiseCalculation(self._lhs, includeVersion=False),
                'new': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.OverrideFunction':
            old = jsonData.get('old')
            if old is None:
                raise RuntimeError('Override function is missing the old property')
            old = deserialiseCalculation(jsonData=old)

            new = jsonData.get('new')
            if new is None:
                raise RuntimeError('Override function is missing the new property')
            new = deserialiseCalculation(jsonData=new)

            return Calculator.OverrideFunction(old=old, new=new)

    class TakePercentageFunction(TwoParameterFunction):
        def __init__(
                self,
                value: ScalarCalculation,
                percentage: ScalarCalculation
                ) -> None:
            super().__init__(lhs=value, rhs=percentage)

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

        # TODO: I don't like this name (maybe jsonType???)
        @staticmethod
        def serialisationType() -> str:
            return 'takepercent'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'value': serialiseCalculation(self._lhs, includeVersion=False),
                'percentage': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.TakePercentageFunction':
            value = jsonData.get('value')
            if value is None:
                raise RuntimeError('Take percentage function is missing the value property')
            value = deserialiseCalculation(jsonData=value)

            percentage = jsonData.get('percentage')
            if percentage is None:
                raise RuntimeError('Take percentage function is missing the percentage property')
            percentage = deserialiseCalculation(jsonData=percentage)

            return Calculator.TakePercentageFunction(value=value, percentage=percentage)

    class ApplyPercentageFunction(TwoParameterFunction):
        def __init__(
                self,
                value: ScalarCalculation,
                percentage: ScalarCalculation
                ) -> None:
            super().__init__(lhs=value, rhs=percentage)

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

        # TODO: I don't like this name
        @staticmethod
        def serialisationType() -> str:
            return 'applypercent'

        def toJson(self) -> typing.Mapping[str, typing.Any]:
            return {
                'value': serialiseCalculation(self._lhs, includeVersion=False),
                'percentage': serialiseCalculation(self._rhs, includeVersion=False)}

        @staticmethod
        def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'Calculator.ApplyPercentageFunction':
            value = jsonData.get('value')
            if value is None:
                raise RuntimeError('Apply percentage function is missing the value property')
            value = deserialiseCalculation(jsonData=value)

            percentage = jsonData.get('percentage')
            if percentage is None:
                raise RuntimeError('Apply percentage function is missing the percentage property')
            percentage = deserialiseCalculation(jsonData=percentage)

            return Calculator.ApplyPercentageFunction(value=value, percentage=percentage)

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
        name: typing.Optional[str] = None
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def equals(
        value: RangeCalculation,
        name: typing.Optional[str] = None
        ) -> RangeCalculation: ...

    @staticmethod
    def equals(
            value: typing.Union[ScalarCalculation, RangeCalculation],
            name: typing.Optional[str] = None
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
                value=Calculator.DivideIntegerFunction(lhs, rhs),
                name=name)
        assert(isinstance(lhs, ScalarCalculation) or isinstance(lhs, RangeCalculation))
        assert(isinstance(rhs, ScalarCalculation) or isinstance(rhs, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.DivideIntegerFunction(lhs.worstCaseCalculation(), rhs.worstCaseCalculation()),
            bestCase=Calculator.DivideIntegerFunction(lhs.bestCaseCalculation(), rhs.bestCaseCalculation()),
            averageCase=Calculator.DivideIntegerFunction(lhs.averageCaseCalculation(), rhs.averageCaseCalculation()),
            name=name)

    @staticmethod
    def sum(
            values: typing.Sequence[typing.Union[ScalarCalculation, RangeCalculation]],
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
                    value=value,
                    digits=digits,
                    rounding=Calculator.SignificantDigitsFunction.Rounding.Floor),
                name=name)
        assert(isinstance(value, ScalarCalculation) or isinstance(value, RangeCalculation))
        assert(isinstance(digits, ScalarCalculation) or isinstance(digits, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.SignificantDigitsFunction(
                value=value.worstCaseCalculation(),
                digits=digits.worstCaseCalculation(),
                rounding=Calculator.SignificantDigitsFunction.Rounding.Floor),
            bestCase=Calculator.SignificantDigitsFunction(
                value=value.bestCaseCalculation(),
                digits=digits.bestCaseCalculation(),
                rounding=Calculator.SignificantDigitsFunction.Rounding.Floor),
            averageCase=Calculator.SignificantDigitsFunction(
                value=value.averageCaseCalculation(),
                digits=digits.averageCaseCalculation(),
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
                    value=value,
                    digits=digits,
                    rounding=Calculator.SignificantDigitsFunction.Rounding.Ceil),
                name=name)
        assert(isinstance(value, ScalarCalculation) or isinstance(value, RangeCalculation))
        assert(isinstance(digits, ScalarCalculation) or isinstance(digits, RangeCalculation))

        return RangeCalculation(
            worstCase=Calculator.SignificantDigitsFunction(
                value=value.worstCaseCalculation(),
                digits=digits.worstCaseCalculation(),
                rounding=Calculator.SignificantDigitsFunction.Rounding.Ceil),
            bestCase=Calculator.SignificantDigitsFunction(
                value=value.bestCaseCalculation(),
                digits=digits.bestCaseCalculation(),
                rounding=Calculator.SignificantDigitsFunction.Rounding.Ceil),
            averageCase=Calculator.SignificantDigitsFunction(
                value=value.averageCaseCalculation(),
                digits=digits.averageCaseCalculation(),
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
    @staticmethod
    def negate(
        value: ScalarCalculation,
        name: typing.Optional[str] = None
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def negate(
        value: RangeCalculation,
        name: typing.Optional[str] = None
        ) -> RangeCalculation: ...

    @staticmethod
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
    @staticmethod
    def absolute(
        value: ScalarCalculation,
        name: typing.Optional[str] = None
        ) -> ScalarCalculation: ...

    @typing.overload
    @staticmethod
    def absolute(
        value: RangeCalculation,
        name: typing.Optional[str] = None
        ) -> RangeCalculation: ...

    @staticmethod
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

#
# Serialisation
#
class _FunctionSerialiser(object):
    _instance = None # Singleton instance
    _lock = threading.Lock()
    _FunctionTypeMap: typing.Optional[typing.Dict[str, typing.Type[CalculatorFunction]]] = None

    def __init__(self) -> None:
        raise RuntimeError('Call instance() instead')

    @classmethod
    def instance(cls):
        if not cls._instance:
            with cls._lock:
                # Recheck instance as another thread could have created it between the
                # first check adn the lock
                if not cls._instance:
                    cls._instance = cls.__new__(cls)
                    cls._instance._findFunctions()
        return cls._instance

    def serialise(
            self,
            function: CalculatorFunction
            ) -> typing.Mapping[str, typing.Any]:
        return {
            'type': function.serialisationType(),
            'values': function.toJson()}

    def deserialise(
            self,
            jsonData: typing.Mapping[str, typing.Any]
            ) -> CalculatorFunction:
        type = jsonData.get('type')
        if type is None:
            raise RuntimeError('Calculation function is missing the type property')
        values = jsonData.get('values')
        if values is None:
            raise RuntimeError('Calculation function is missing the values property')

        cls = None
        if _FunctionSerialiser._FunctionTypeMap:
            cls = _FunctionSerialiser._FunctionTypeMap.get(type)
        if cls is None:
            raise RuntimeError(f'Calculation function has unknown type {type}')

        return cls.fromJson(jsonData=values)

    def _findFunctions(self) -> None:
        if _FunctionSerialiser._FunctionTypeMap is None:
            _FunctionSerialiser._FunctionTypeMap = {}
            for cls in common.getSubclasses(classType=CalculatorFunction):
                _FunctionSerialiser._FunctionTypeMap[cls.serialisationType()] = cls

_CalculationVersion = packaging.version.Version('1.0')

def serialiseCalculation(
        calculation: Calculation,
        includeVersion: bool = True,
        includeHierarchy: bool = True
        ) -> typing.Mapping[str, typing.Any]:
    # TODO: The way this is done isn't ideal for 2 reasons
    # - The fact it's added means every calculation saved in something like
    # the jump route gets it's own version. Again not a real problem but looks
    # ugly. It does server a purpose though as, if the calculation format ever
    # changes we need to know which calculation format to use when reading it
    # back in
    jsonData = {}
    if includeVersion:
        jsonData['version'] = str(_CalculationVersion)

    if isinstance(calculation, ScalarCalculation):
        jsonData['type'] = 'scalar'

        if calculation.name():
            jsonData['name'] = calculation.name()

        jsonData['value'] = calculation.value()

        if includeHierarchy and calculation.function():
            jsonData['valueFunc'] = _FunctionSerialiser.instance().serialise(
                function=calculation.function())
    elif isinstance(calculation, RangeCalculation):
        jsonData['type'] = 'range'

        if calculation.name():
            jsonData['name'] = calculation.name()

        worst = calculation.worstCaseCalculation()
        jsonData['worst'] = worst.value()
        if includeHierarchy and worst.function():
            jsonData['worstFunc'] = _FunctionSerialiser.instance().serialise(
                function=worst.function())

        best = calculation.bestCaseCalculation()
        jsonData['best'] = best.value()
        if includeHierarchy and best.function():
            jsonData['bestFunc'] = _FunctionSerialiser.instance().serialise(
                function=best.function())

        average = calculation.averageCaseCalculation()
        jsonData['average'] = average.value()
        if includeHierarchy and average.function():
            jsonData['averageFunc'] = _FunctionSerialiser.instance().serialise(
                function=average.function())
    else:
        raise ValueError(f'Unable to serialise unknown calculation type {type(calculation)}')

    return jsonData

def serialiseCalculationList(
        calculations: typing.Iterable[Calculation],
        includeVersion: bool = True,
        includeHierarchy: bool = True
        ) -> typing.Mapping[str, typing.Any]:
    jsonData = {}
    if includeVersion:
        jsonData['version'] = str(_CalculationVersion)

    jsonList = []
    for calculation in calculations:
        jsonList.append(serialiseCalculation(
            calculation=calculation,
            includeVersion=False,
            includeHierarchy=includeHierarchy))
    jsonData['list'] = jsonList

    return jsonData

def deserialiseCalculation(
        jsonData: typing.Mapping[str, typing.Any],
        ) -> Calculation:
    version = jsonData.get('version')
    if version is not None:
        if not isinstance(version, str):
            raise RuntimeError('Calculation version property is not a string')
        try:
            version = packaging.version.Version(version)
        except Exception:
            raise RuntimeError(f'Calculation version property has invalid value {version}')
        if version.major != _CalculationVersion.major:
            raise RuntimeError(f'Calculation version property has unsupported version {version}')

    type = jsonData.get('type')
    if type is None:
        raise RuntimeError('Calculation is missing the type property')

    name = jsonData.get('name')
    if name is not None and not isinstance(name, str):
        raise RuntimeError('Scalar calculation name property is not a string')

    if type == 'scalar':
        value = jsonData.get('value')
        if value is None:
            raise RuntimeError('Calculation is missing the value property')
        if not isinstance(value, (int, float)):
            raise RuntimeError('Scalar calculation value property is not a number')

        function = jsonData.get('valueFunc')
        if function is not None:
            if not isinstance(function, dict):
                raise RuntimeError('Scalar calculation valueFunc property is not a dictionary')
            try:
                function = _FunctionSerialiser.instance().deserialise(jsonData=function)
            except Exception as ex:
                message = \
                    'Failed to deserialise valueFunc property for scalar calculation with name "{name}"'.format(name=name) \
                    if name else \
                    'Failed to deserialise valueFunc property for unnamed scalar calculation'
                logging.warning(message, exc_info=ex)

        return ScalarCalculation(value=function if function else value, name=name)
    elif type == 'range':
        worstValue = jsonData.get('worst')
        if worstValue is None:
            raise RuntimeError('Calculation is missing the worst property')
        if not isinstance(worstValue, (int, float)):
            raise RuntimeError('Scalar calculation worst property is not a number')

        worstFunction = jsonData.get('worstFunc')
        if worstFunction is not None:
            if not isinstance(worstFunction, dict):
                raise RuntimeError('Scalar calculation worstFunc property is not a dictionary')
            try:
                worstFunction = _FunctionSerialiser.instance().deserialise(jsonData=worstFunction)
            except Exception as ex:
                message = \
                    'Failed to deserialise worstFunc property for range calculation with name "{name}"'.format(name=name) \
                    if name else \
                    'Failed to deserialise worstFunc property for unnamed range calculation'
                logging.warning(message, exc_info=ex)


        bestValue = jsonData.get('best')
        if bestValue is None:
            raise RuntimeError('Calculation is missing the best property')
        if not isinstance(bestValue, (int, float)):
            raise RuntimeError('Scalar calculation best property is not a number')

        bestFunction = jsonData.get('bestFunc')
        if bestFunction is not None:
            if not isinstance(bestFunction, dict):
                raise RuntimeError('Scalar calculation bestFunc property is not a dictionary')
            try:
                bestFunction = _FunctionSerialiser.instance().deserialise(jsonData=bestFunction)
            except Exception as ex:
                message = \
                    'Failed to deserialise bestFunc property for range calculation with name "{name}"'.format(name=name) \
                    if name else \
                    'Failed to deserialise bestFunc property for unnamed range calculation'
                logging.warning(message, exc_info=ex)

        averageValue = jsonData.get('average')
        if averageValue is None:
            raise RuntimeError('Calculation is missing the average property')
        if not isinstance(averageValue, (int, float)):
            raise RuntimeError('Scalar calculation average property is not a number')

        averageFunction = jsonData.get('averageFunc')
        if averageFunction is not None:
            if not isinstance(averageFunction, dict):
                raise RuntimeError('Scalar calculation averageFunc property is not a dictionary')
            try:
                averageFunction = _FunctionSerialiser.instance().deserialise(jsonData=averageFunction)
            except Exception as ex:
                message = \
                    'Failed to deserialise averageFunc property for range calculation with name "{name}"'.format(name=name) \
                    if name else \
                    'Failed to deserialise averageFunc property for unnamed range calculation'
                logging.warning(message, exc_info=ex)

        return RangeCalculation(
            worstCase=worstFunction if worstFunction else worstValue,
            bestCase=bestFunction if bestFunction else bestValue,
            averageCase=averageFunction if averageFunction else averageValue,
            name=name)
    else:
        raise RuntimeError(f'Unable to deserialise unknown calculation type {type}')

def deserialiseCalculationList(
        jsonData: typing.Mapping[str, typing.Any]
        ) -> typing.List[Calculation]:
    version = jsonData.get('version')
    if version is not None:
        if not isinstance(version, str):
            raise RuntimeError('Calculation list version property is not a string')
        try:
            version = packaging.version.Version(version)
        except Exception:
            raise RuntimeError(f'Calculation list version property has invalid value {version}')
        if version.major != _CalculationVersion.major:
            raise RuntimeError(f'Calculation list version property has unsupported version {version}')

        jsonList = jsonData.get('list')
        if jsonList is None:
            raise RuntimeError('Calculation list is missing the list property')
        if not isinstance(jsonList, list):
            raise RuntimeError('Calculation list list property is not a list')

    calculations = []
    for jsonCalculation in jsonList:
        calculations.append(deserialiseCalculation(jsonData=jsonCalculation))
    if not calculations:
        raise RuntimeError('Calculation list is empty')
    return calculations

def writeCalculation(
        calculation: Calculation,
        path: str,
        includeHierarchy: bool = True
        ) -> None:
    jsonData = serialiseCalculation(
        calculation=calculation,
        includeVersion=True,
        includeHierarchy=includeHierarchy)
    with open(path, 'w', encoding='UTF8') as file:
        json.dump(jsonData, file, indent=4)

def writeCalculationList(
        calculations: typing.Iterable[Calculation],
        path: str,
        includeHierarchy: bool = True
        ) -> None:
    jsonData = serialiseCalculationList(
        calculations=calculations,
        includeVersion=True,
        includeHierarchy=includeHierarchy)
    with open(path, 'w', encoding='UTF8') as file:
        json.dump(jsonData, file, indent=4)

def readCalculation(path: str) -> Calculation:
    with open(path, 'r') as file:
        return deserialiseCalculation(jsonData=json.load(file))

def readCalculationList(path: str) -> typing.List[Calculation]:
    with open(path, 'r') as file:
        return deserialiseCalculationList(jsonData=json.load(file))