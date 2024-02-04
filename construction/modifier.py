import common
import typing

class ModifierInterface(object):
    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        raise RuntimeError('The calculations method must be implemented by the class derived from ModifierInterface')

    def displayString(
            self,
            decimalPlaces: int = 2
            ) -> str:
        raise RuntimeError('The displayString method must be implemented by classes derived from ModifierInterface')

    def applyTo(
            self,
            baseValue: common.ScalarCalculation,
            ) -> common.ScalarCalculation:
        raise RuntimeError('The applyTo method must be implemented by classes derived from ModifierInterface')

class NumericModifierInterface(ModifierInterface):
    def numericModifier(self) -> common.ScalarCalculation:
        raise RuntimeError('The calculation method must be implemented by classes derived from NumericModifierInterface')

    def isAbsolute(self) -> bool:
        raise RuntimeError('The isAbsolute method must be implemented by classes derived from NumericModifierInterface')

class ConstantModifier(NumericModifierInterface):
    def __init__(
            self,
            value: common.ScalarCalculation
            ) -> None:
        super().__init__()
        self._value = value

    def numeric(self) -> typing.Union[int, float]:
        return self._value.value()

    def numericModifier(self) -> common.ScalarCalculation:
        return self._value

    def isAbsolute(self) -> bool:
        return True

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return [self._value]

    def displayString(
            self,
            decimalPlaces: int = 2
            ) -> str:
        return common.formatNumber(
            number=self._value.value(),
            decimalPlaces=decimalPlaces,
            alwaysIncludeSign=True)

    def applyTo(
            self,
            baseValue: common.ScalarCalculation
            ) -> common.ScalarCalculation:
        return common.Calculator.add(
            lhs=baseValue,
            rhs=self._value)

class PercentageModifier(NumericModifierInterface):
    def __init__(
            self,
            value: common.ScalarCalculation,
            roundDown: bool = False
            ) -> None:
        super().__init__()
        self._value = value
        self._roundDown = roundDown

    def numeric(self) -> typing.Union[int, float]:
        return self._value.value()

    def numericModifier(self) -> common.ScalarCalculation:
        return self._value

    def isAbsolute(self) -> bool:
        return False

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return [self._value]

    def displayString(
            self,
            decimalPlaces: int = 2
            ) -> str:
        return common.formatNumber(
            number=self._value.value(),
            decimalPlaces=decimalPlaces,
            alwaysIncludeSign=True) + '%'

    def applyTo(
            self,
            baseValue: common.ScalarCalculation
            ) -> common.ScalarCalculation:
        result = common.Calculator.applyPercentage(
            value=baseValue,
            percentage=self._value)
        if self._roundDown:
            result = common.Calculator.floor(value=result)
        return result

class MultiplierModifier(NumericModifierInterface):
    def __init__(
            self,
            value: common.ScalarCalculation,
            roundDown: bool = False
            ) -> None:
        super().__init__()
        self._value = value
        self._roundDown = roundDown

    def numeric(self) -> typing.Union[int, float]:
        return self._value.value()

    def numericModifier(self) -> common.ScalarCalculation:
        return self._value

    def isAbsolute(self) -> bool:
        return False

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return [self._value]

    def displayString(
            self,
            decimalPlaces: int = 2
            ) -> str:
        value = self._value.value()
        if value >= 0:
            return 'x' + common.formatNumber(
                number=value,
                decimalPlaces=decimalPlaces)
        else:
            return 'x(' + common.formatNumber(
                number=value,
                decimalPlaces=decimalPlaces) + ')'

    def applyTo(
            self,
            baseValue: common.ScalarCalculation
            ) -> common.ScalarCalculation:
        result = common.Calculator.multiply(
            lhs=baseValue,
            rhs=self._value)
        if self._roundDown:
            result = common.Calculator.floor(value=result)
        return result

class DiceRollModifier(ModifierInterface):
    def __init__(
            self,
            countModifier: typing.Optional[common.ScalarCalculation] = None,
            constantModifier: typing.Optional[common.ScalarCalculation] = None
            ) -> None:
        super().__init__()
        self._countModifier = countModifier
        self._constantModifier = constantModifier

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        calculations = []
        if self._countModifier:
            calculations.append(self._countModifier)
        if self._constantModifier:
            calculations.append(self._constantModifier)
        return calculations

    def displayString(
            self,
            decimalPlaces: int = 2 # Not used for dice rolls as they're always integers
            ) -> str:
        displayString = ''

        if self._countModifier and self._countModifier.value() != 0:
            displayString += common.formatNumber(
                number=int(self._countModifier.value()),
                alwaysIncludeSign=True) + 'D'

        if self._constantModifier and self._constantModifier.value() != 0:
            if self._constantModifier.value() > 0:
                displayString += ' + ' if displayString else '+'
            else:
                displayString += ' - ' if displayString else '-'
            displayString += common.formatNumber(
                number=int(abs(self._constantModifier.value())))

        return displayString

    def applyTo(
            self,
            baseValue: common.DiceRoll
            ) -> common.DiceRoll:
        dieCount = baseValue.dieCount()
        constant = baseValue.constant()

        if self._countModifier:
            dieCount = common.Calculator.add(
                lhs=dieCount,
                rhs=self._countModifier,
                name=dieCount.name())

        if self._constantModifier:
            constant = common.Calculator.add(
                lhs=constant,
                rhs=self._constantModifier,
                name=constant.name())

        return common.DiceRoll(
            count=dieCount,
            type=baseValue.dieType(),
            constant=constant)

def calculateNumericModifierSequence(
        modifiers: typing.Iterable[NumericModifierInterface]
        ) -> typing.Optional[common.ScalarCalculation]:
    total = None
    for modifier in modifiers:
        if not total:
            if modifier.isAbsolute():
                total = modifier.numericModifier()
                continue
            total = common.ScalarCalculation(value=0)

        total = modifier.applyTo(baseValue=total)
    if not total:
        return common.ScalarCalculation(
            value=0,
            name=f'Modifier Sequence Total')
    if len(modifiers) == 1:
        return common.Calculator.equals(
            value=total,
            name=f'Modifier Sequence Total')
    return common.Calculator.rename(
        value=total,
        name=f'Modifier Sequence Total')
