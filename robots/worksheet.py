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
        # Characteristics isn't one of the fields in the standard worksheet. I
        # added it to support robot as player character and brain in a jar
        Characteristics = 'Characteristics'

    def __init__(self) -> None:
        super().__init__()
        self._values: typing.Dict[Worksheet.Field, str] = {}
        self._calculations: typing.Dict[Worksheet.Field, typing.List[common.ScalarCalculation]] = {}

    def hasField(
            self,
            field: Field
            ) -> bool:
        return field in self._values

    def setField(
            self,
            field: Field,
            value: typing.Optional[str],
            calculations: typing.Optional[typing.Iterable[common.ScalarCalculation]] = None
            ) -> None:
        self._values[field] = value
        if value != None and calculations:
            self._calculations[field] = list(calculations)
        elif field in self._calculations:
            del self._calculations[field]

    def value(self, field: Field) -> typing.Optional[str]:
        return self._values.get(field)

    def calculations(self, field: Field) -> typing.Iterable[common.ScalarCalculation]:
        return self._calculations.get(field, [])
