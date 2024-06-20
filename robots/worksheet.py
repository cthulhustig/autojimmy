import common
import enum
import typing

class Worksheet(object):
    class Field(enum.Enum):
        Robot = 'Robot'
        Hits = 'Hits'
        Locomotion = 'Locomotion'
        Speed = 'Speed'
        TL = 'TL'
        Cost = 'Cost'
        Skills = 'Skills'
        Attacks = 'Attacks'
        Manipulators = 'Manipulators'
        Endurance = 'Endurance'
        Traits = 'Traits'
        Programming = 'Programming'
        Options = 'Options'

    def __init__(self) -> None:
        super().__init__()
        self._values: typing.Dict[Worksheet.Field, str] = {}
        self._calculations: typing.Dict[Worksheet.Field, typing.List[common.ScalarCalculation]] = {}

    def setField(
            self,
            field: Field,
            value: str,
            calculations: typing.Optional[typing.Iterable[common.ScalarCalculation]] = None
            ) -> None:
        self._values[field] = value
        if calculations:
            self._calculations[field] = list(calculations)

    def value(self, field: Field) -> str:
        return self._values.get(field, '')
    
    def calculations(self, field: Field) -> typing.Iterable[common.ScalarCalculation]:
        return self._calculations.get(field, [])
