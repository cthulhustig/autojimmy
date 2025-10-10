import common
import enum
import typing

# NOTE: If I ever update the value of these enums I'll need to do something
# for backward compatibility with serialisation
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


_CharacteristicSerialisationTypeToStr = {e: e.value.lower() for e in Characteristic}
_CharacteristicSerialisationStrToType = {v: k for k, v in _CharacteristicSerialisationTypeToStr.items()}

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

    @staticmethod
    def serialisationType() -> str:
        return 'chardm'

    def toJson(self) -> typing.Mapping[str, typing.Any]:
        return {
            'characteristic': _CharacteristicSerialisationTypeToStr[self._characteristic],
            'level': common.serialiseCalculation(self._level, includeVersion=False)}

    @staticmethod
    def fromJson(
            jsonData: typing.Mapping[str, typing.Any]
            ) -> 'CharacteristicDMFunction':
        characteristic = jsonData.get('characteristic')
        if characteristic is None:
            raise RuntimeError('Characteristic DM function is missing the characteristic property')
        if not isinstance(characteristic, str):
            raise RuntimeError('Characteristic DM function characteristic property is not a string')
        characteristic = characteristic.lower()
        if characteristic not in _CharacteristicSerialisationStrToType:
            raise RuntimeError(f'Characteristic DM function has invalid characteristic property {characteristic}')
        characteristic = _CharacteristicSerialisationStrToType[characteristic]

        level = jsonData.get('level')
        if level is None:
            raise RuntimeError('Characteristic DM function is missing the level property')
        level = common.deserialiseCalculation(jsonData=level)

        return CharacteristicDMFunction(characteristic=characteristic, level=level)
