import common
import enum
import typing

class Characteristic(enum.Enum):
    Strength = 'STR'
    Dexterity = 'DEX'
    Endurance = 'END'
    Intellect = 'INT'
    Education = 'EDU'
    Social = 'SOC'
    Psionic = 'PSI'
    Luck = 'LCK'
    Wealth = 'WLT'
    Moral = 'MRL'
    Sanity = 'STY'

def characteristicDM(level: int) -> int:
    if level <= 0:
        return -3
    elif level <= 2:
        return -2
    elif level <= 5:
        return -1
    elif level <= 8:
        return 0
    elif level <= 11:
        return +1
    elif level <= 14:
        return +2
    else: # 15+
        return +3

class CharacteristicDMFunction(common.CalculatorFunction):
    def __init__(
            self,
            characteristic: Characteristic,
            level: common.ScalarCalculation
            ) -> None:
        self._characteristic = characteristic
        self._level = level
        self._modifier = common.ScalarCalculation(
            value=characteristicDM(self._level.value()),
            name=f'{self._characteristic.value} Characteristic Modifier')

    def value(self) -> typing.Union[int, float]:
        return self._modifier.value()

    def calculationString(
            self,
            outerBrackets: bool,
            decimalPlaces: int = 2
            ) -> str:
        valueString = self._level.name(forCalculation=True)
        if not valueString:
            valueString = self._level.calculationString(
                outerBrackets=False,
                decimalPlaces=decimalPlaces)
        return f'CharacteristicDM({valueString})'

    def calculations(self) -> typing.List[common.ScalarCalculation]:
        if self._level.name():
            return [self._level]
        return self._level.subCalculations()

    def copy(self) -> 'CharacteristicDMFunction':
        return CharacteristicDMFunction(
            level=self._level.copy())
