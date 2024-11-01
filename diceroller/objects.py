import common
import datetime
import enum
import objectdb
import typing

class DiceModifier(objectdb.DatabaseObject):
    def __init__(
            self,
            name: str,
            value: int,
            enabled: bool,
            id: typing.Optional[str] = None,
            parent: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, parent=parent)
        self._name = name
        self._value = value
        self._enabled = enabled

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DiceModifier):
            return super().__eq__(other) and \
                self._name == other._name and \
                self._value == other._value and \
                self._enabled == other._enabled
        return False

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

    def value(self) -> int:
        return self._value

    def setValue(self, value: int) -> None:
        self._value = value

    def enabled(self) -> bool:
        return self._enabled

    def setEnabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def copyConfig(
            self,
            copyIds: bool = False
            ) -> 'DiceModifier':
        return DiceModifier(
            id=self._id if copyIds else None,
            name=self._name,
            value=self._value,
            enabled=self._enabled)

    def data(self) -> typing.Mapping[
            str,
            typing.Optional[typing.Union[bool, int, float, str, objectdb.DatabaseEntity]]]:
        return {
            'name': self._name,
            'value': self._value,
            'enabled': self._enabled}

    @staticmethod
    def defineObject() -> objectdb.ObjectDef:
        return objectdb.ObjectDef(
            tableName='dice_modifiers',
            tableSchema=1,
            classType=DiceModifier,
            paramDefs=[
                objectdb.ParamDef(columnName='name', columnType=str),
                objectdb.ParamDef(columnName='value', columnType=int),
                objectdb.ParamDef(columnName='enabled', columnType=bool)
            ])

    @staticmethod
    def createObject(
        id: str,
        parent: typing.Optional[str],
        data: typing.Mapping[
            str,
            typing.Optional[typing.Union[bool, int, float, str, objectdb.DatabaseEntity]]]
        ) -> 'DiceRoller':
        name = data.get('name')
        if not isinstance(name, str):
            raise ValueError('DiceModifier construction parameter "name" is not a str')

        value = data.get('value')
        if not isinstance(value, int):
            raise ValueError('DiceModifier construction parameter "value" is not a int')

        enabled = data.get('enabled')
        if not isinstance(enabled, bool):
            raise ValueError('DiceModifier construction parameter "enabled" is not a bool')

        return DiceModifier(
            id=id,
            parent=parent,
            name=name,
            value=value,
            enabled=enabled)

class DiceRoller(objectdb.DatabaseObject):
    def __init__(
            self,
            name: str,
            dieCount: int = 1,
            dieType: common.DieType = common.DieType.D6,
            constant: int = 0,
            hasBoon: bool = False,
            hasBane: bool = False,
            modifiers: typing.Optional[typing.Union[
                typing.Iterable[DiceModifier],
                objectdb.DatabaseList]] = None,
            targetType: typing.Optional[common.ComparisonType] = None,
            targetNumber: typing.Optional[int] = None, # Must be supplied if targetType is supplied
            id: typing.Optional[str] = None,
            parent: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, parent=parent)
        self._name = name
        self._dieCount = dieCount
        self._dieType = dieType
        self._constant = constant
        self._hasBoon = hasBoon
        self._hasBane = hasBane
        self._targetType = targetType if targetType != None and targetNumber != None else None
        self._targetNumber = targetNumber if targetType != None and targetNumber != None else None

        self._modifiers = objectdb.DatabaseList(
            parent=self.id(),
            id=modifiers.id() if isinstance(modifiers, objectdb.DatabaseList) else None)
        if modifiers:
            self.setModifiers(modifiers=modifiers)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DiceRoller):
            return super().__eq__(other) and \
                self._name == other._name and \
                self._dieCount == other._dieCount and \
                self._dieType == other._dieType and \
                self._constant == other._constant and \
                self._hasBoon == other._hasBoon and \
                self._hasBane == other._hasBane and \
                self._modifiers == other._modifiers and \
                self._targetType == other._targetType and \
                self._targetNumber == other._targetNumber
        return False

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

    def dieCount(self) -> int:
        return self._dieCount

    def setDieCount(self, dieCount: int) -> None:
        self._dieCount = dieCount

    def dieType(self) -> common.DieType:
        return self._dieType

    def setDieType(self, dieType: common.DieType) -> None:
        self._dieType = dieType

    def constant(self) -> int:
        return self._constant

    def setConstant(self, constant: int) -> None:
        self._constant = constant

    def hasBoon(self) -> bool:
        return self._hasBoon

    def setHasBoon(self, hasBoon: bool) -> None:
        self._hasBoon = hasBoon

    def hasBane(self) -> bool:
        return self._hasBane

    def setHasBane(self, hasBane: bool) -> None:
        self._hasBane = hasBane

    def modifiers(self) -> typing.Iterable[DiceModifier]:
        return self._modifiers

    def modifierCount(self) -> int:
        return len(self._modifiers)

    def setModifiers(
            self,
            modifiers: typing.Union[
                typing.Iterable[DiceModifier],
                objectdb.DatabaseList]
            ) -> None:
        for modifier in modifiers:
            if not isinstance(modifier, DiceModifier):
                raise ValueError(f'Modifier is not a {DiceModifier}')

        if isinstance(modifiers, objectdb.DatabaseList):
            if modifiers.parent() != None:
                raise ValueError(f'List {modifiers.id()} already has parent {modifiers.parent()}')

            self._modifiers.setParent(None)
            self._modifiers = modifiers
            self._modifiers.setParent(self.id())
        else:
            for modifier in modifiers:
                if modifier.parent() != None:
                    raise ValueError(f'Modifier {modifier.id()} already has parent {modifier.parent()}')
            self._modifiers.init(content=modifiers)

    def addModifier(self, modifier: DiceModifier) -> None:
        if not isinstance(modifier, DiceModifier):
            raise ValueError(f'Modifier is not a {DiceModifier}')
        self._modifiers.add(item=modifier)

    def insertModifier(self, index: int, modifier: DiceModifier) -> None:
        if not isinstance(modifier, DiceModifier):
            raise ValueError(f'Modifier is not a {DiceModifier}')
        self._modifiers.insert(index=index, item=modifier)

    def removeModifier(self, id: str) -> DiceModifier:
        return self._modifiers.removeById(id=id)

    def clearModifiers(self) -> None:
        self._modifiers.clear()

    def targetType(self) -> typing.Optional[common.ComparisonType]:
        return self._targetType

    def setTargetType(self, targetType: typing.Optional[common.ComparisonType]) -> None:
        self._targetType = targetType
        if self._targetType == None:
            self._targetNumber = None

    def targetNumber(self) -> typing.Optional[int]:
        return self._targetNumber

    def setTargetNumber(self, targetNumber: typing.Optional[int]) -> None:
        self._targetNumber = targetNumber
        if self._targetNumber == None:
            self._targetType = None

    def hasTarget(self) -> bool:
        return self._targetType != None and self._targetNumber != None

    def setTarget(
            self,
            targetType: typing.Optional[common.ComparisonType],
            targetNumber: typing.Optional[int]
            ) -> None:
        self._targetType = targetType if targetType != None and targetNumber != None else None
        self._targetNumber = targetNumber if targetType != None and targetNumber != None else None

    def copyConfig(
            self,
            copyIds: bool = False
            ) -> 'DiceRoller':
        modifiers = objectdb.DatabaseList()
        for modifier in self._modifiers:
            assert(isinstance(modifier, DiceModifier))
            modifiers.add(modifier.copyConfig(copyIds=copyIds))
        return DiceRoller(
            id=self._id if copyIds else None,
            name=self._name,
            dieCount=self._dieCount,
            dieType=self._dieType,
            constant=self._constant,
            hasBoon=self._hasBoon,
            hasBane=self._hasBane,
            modifiers=modifiers,
            targetType=self._targetType,
            targetNumber=self._targetNumber)

    def data(self) -> typing.Mapping[
            str,
            typing.Optional[typing.Union[bool, int, float, str, objectdb.DatabaseEntity]]]:
        return {
            'name': self._name,
            'die_count': self._dieCount,
            'die_type': self._dieType.name,
            'constant': self._constant,
            'has_boon': self._hasBoon,
            'has_bane': self._hasBane,
            'modifiers': self._modifiers,
            'target_type': self._targetType.name if self._targetType != None else None,
            'target_number': self._targetNumber}

    @staticmethod
    def defineObject() -> objectdb.ObjectDef:
        return objectdb.ObjectDef(
            tableName='dice_rollers',
            tableSchema=1,
            classType=DiceRoller,
            paramDefs=[
                objectdb.ParamDef(columnName='name', columnType=str),
                objectdb.ParamDef(columnName='die_count', columnType=int),
                objectdb.ParamDef(columnName='die_type', columnType=str),
                objectdb.ParamDef(columnName='constant', columnType=int),
                objectdb.ParamDef(columnName='has_boon', columnType=bool),
                objectdb.ParamDef(columnName='has_bane', columnType=bool),
                objectdb.ParamDef(columnName='modifiers', columnType=objectdb.DatabaseList),
                objectdb.ParamDef(columnName='target_type', columnType=str, isOptional=True),
                objectdb.ParamDef(columnName='target_number', columnType=int, isOptional=True),
            ])

    @staticmethod
    def createObject(
        id: str,
        parent: typing.Optional[str],
        data: typing.Mapping[
            str,
            typing.Optional[typing.Union[bool, int, float, str, objectdb.DatabaseEntity]]]
        ) -> 'DiceRoller':
        name = data.get('name')
        if not isinstance(name, str):
            raise ValueError('DiceRoller construction parameter "name" is not a str')

        dieCount = data.get('die_count')
        if not isinstance(dieCount, int):
            raise ValueError('DiceRoller construction parameter "die_count" is not an int')

        dieType = data.get('die_type')
        if not isinstance(dieType, str):
            raise ValueError('DiceRoller construction parameter "die_type" is not a str')
        if dieType not in common.DieType.__members__:
            raise ValueError(f'DiceRoller construction parameter "die_type" has unexpected value "{dieType}"')
        dieType = common.DieType.__members__[dieType]

        constant = data.get('constant')
        if not isinstance(constant, int):
            raise ValueError('DiceRoller construction parameter "constant" is not an int')

        hasBoon = data.get('has_boon')
        if not isinstance(hasBoon, bool):
            raise ValueError('DiceRoller construction parameter "has_boon" is not a bool')

        hasBane = data.get('has_bane')
        if not isinstance(hasBane, bool):
            raise ValueError('DiceRoller construction parameter "has_bane" is not a bool')

        modifiers = data.get('modifiers')
        if not isinstance(modifiers, objectdb.DatabaseList):
            raise ValueError('DiceRoller construction parameter "modifiers" is not a DatabaseList')

        targetType = data.get('target_type')
        if targetType != None:
            if not isinstance(targetType, str):
                raise ValueError('DiceRoller construction parameter "target_type" is not a str or None')
            if targetType not in common.ComparisonType.__members__:
                raise ValueError(f'DiceRoller construction parameter "target_type" has unexpected value "{targetType}"')
            targetType = common.ComparisonType.__members__[targetType]

        targetNumber = data.get('target_number')
        if targetNumber != None and not isinstance(targetNumber, int):
            raise ValueError('DiceRoller construction parameter "target_number" is not an int or None')

        return DiceRoller(
            id=id,
            parent=parent,
            name=name,
            dieCount=dieCount,
            dieType=dieType,
            constant=constant,
            hasBoon=hasBoon,
            hasBane=hasBane,
            modifiers=modifiers,
            targetType=targetType,
            targetNumber=targetNumber)

class DiceRollerGroup(objectdb.DatabaseObject):
    def __init__(
            self,
            name: str,
            rollers: typing.Optional[typing.Union[
                typing.Iterable[DiceRoller],
                objectdb.DatabaseList]] = None,
            id: typing.Optional[str] = None,
            parent: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, parent=parent)
        self._name = name

        self._rollers = objectdb.DatabaseList(
            parent=self.id(),
            id=rollers.id() if isinstance(rollers, objectdb.DatabaseList) else None)
        if rollers:
            self.setRollers(rollers=rollers)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DiceRollerGroup):
            return super().__eq__(other) and \
                self._name == other._name and \
                self._rollers == other._rollers
        return False

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

    def rollers(self) -> typing.Iterable[DiceRoller]:
        return self._rollers

    def rollerCount(self) -> int:
        return len(self._rollers)

    def setRollers(
            self,
            rollers: typing.Union[
                typing.Iterable[DiceRoller],
                objectdb.DatabaseList]
            ) -> None:
        for roller in rollers:
            if not isinstance(roller, DiceRoller):
                raise ValueError(f'Roller is not a {DiceRoller})')

        if isinstance(rollers, objectdb.DatabaseList):
            if rollers.parent() != None:
                raise ValueError(f'List {rollers.id()} already has parent {rollers.parent()}')

            self._rollers.setParent(None)
            self._rollers = rollers
            self._rollers.setParent(self.id())
        else:
            for roller in rollers:
                if roller.parent() != None:
                    raise ValueError(f'Roller {roller.id()} already has parent {roller.parent()}')
            self._rollers.init(content=rollers)

    def addRoller(self, roller: DiceRoller) -> None:
        if not isinstance(roller, DiceRoller):
            raise ValueError(f'Roller is not a {DiceRoller}')
        if roller.parent() != None:
            raise ValueError(f'Roller {roller.id()} already has parent {roller.parent()}')

        self._rollers.add(roller)

    def insertRoller(self, index: int, roller: DiceRoller) -> None:
        if not isinstance(roller, DiceRoller):
            raise ValueError(f'Roller is not a {DiceRoller}')
        if roller.parent() != None:
            raise ValueError(f'Roller {roller.id()} already has parent {roller.parent()}')
        self._rollers.insert(index=index, item=roller)

    def removeRoller(self, id: str) -> DiceRoller:
        return self._rollers.removeById(id=id)

    def clearRollers(self) -> None:
        self._rollers.clear()

    def copyConfig(
            self,
            copyIds: bool = False
            ) -> 'DiceRollerGroup':
        rollers = objectdb.DatabaseList()
        for roller in self._rollers:
            assert(isinstance(roller, DiceRoller))
            rollers.add(roller.copyConfig(copyIds=copyIds))
        return DiceRollerGroup(
            id=self._id if copyIds else None,
            name=self._name,
            rollers=rollers)

    def data(self) -> typing.Mapping[
            str,
            typing.Optional[typing.Union[bool, int, float, str, objectdb.DatabaseEntity]]]:
        return {
            'name': self._name,
            'rollers': self._rollers}

    @staticmethod
    def defineObject() -> objectdb.ObjectDef:
        return objectdb.ObjectDef(
            tableName='dice_roller_groups',
            tableSchema=1,
            classType=DiceRollerGroup,
            paramDefs=[
                objectdb.ParamDef(columnName='name', columnType=str),
                objectdb.ParamDef(columnName='rollers', columnType=objectdb.DatabaseList),
            ])

    @staticmethod
    def createObject(
        id: str,
        parent: typing.Optional[str],
        data: typing.Mapping[
            str,
            typing.Optional[typing.Union[bool, int, float, str, objectdb.DatabaseEntity]]]
        ) -> 'DiceRollerGroup':
        name = data.get('name')
        if not isinstance(name, str):
            raise ValueError('DiceRollerGroup construction parameter "name" is not a str')

        rollers = data.get('rollers')
        if not isinstance(rollers, objectdb.DatabaseList):
            raise ValueError('DiceRollerGroup construction parameter "rollers" is not a DatabaseList')

        return DiceRollerGroup(
            id=id,
            parent=parent,
            name=name,
            rollers=rollers)

# IMPORTANT: If I ever change the names of the enum definitions (not their value
# string) then I need to add some kind of value mapping to objectdb as the name
# of the enum is stored in the database for dice roller db objects. I will also
# need some kind of mapping in dice roller serialisation as the names are also
# used in serialised data
class DiceRollEffectType(enum.Enum):
    ExceptionalFailure = 'Exceptional Failure'
    AverageFailure = 'Average Failure'
    MarginalFailure = 'Marginal Failure'
    MarginalSuccess = 'Marginal Success'
    AverageSuccess = 'Average Success'
    ExceptionalSuccess = 'Exceptional Success'

    @staticmethod
    def effectValueToType(value: int) -> 'DiceRollEffectType':
        if isinstance(value, common.ScalarCalculation):
            value = value.value()
        if value <= -6:
            return DiceRollEffectType.ExceptionalFailure
        elif value <= -2:
            return DiceRollEffectType.AverageFailure
        elif value == -1:
            return DiceRollEffectType.MarginalFailure
        elif value == 0:
            return DiceRollEffectType.MarginalSuccess
        elif value <= 5:
            return DiceRollEffectType.AverageSuccess
        else:
            return DiceRollEffectType.ExceptionalSuccess

class DiceRollResult(objectdb.DatabaseObject):
    def __init__(
            self,
            timestamp: datetime.datetime,
            label: str,
            die: common.DieType,
            rolls: typing.Union[
                typing.Iterable[int],
                objectdb.DatabaseList],
            ignored: typing.Optional[int] = None, # Index of ignored roll in rolls list
            modifiers: typing.Optional[typing.Union[
                typing.Iterable[typing.Tuple[
                    str, # Modifier name
                    int]], # Modifier value
                objectdb.DatabaseList]] = None,
            targetType: typing.Optional[common.ComparisonType] = None,
            targetNumber: typing.Optional[int] = None,
            id: typing.Optional[str] = None,
            parent: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, parent=parent)
        self._timestamp = timestamp
        self._label = label
        self._die = die
        self._ignored = ignored
        self._targetType = targetType
        self._targetNumber = targetNumber

        self._rolls = objectdb.DatabaseList(
            parent=self.id(),
            id=rolls.id() if isinstance(rolls, objectdb.DatabaseList) else None)
        if rolls != None:
            for roll in rolls:
                self._rolls.add(roll)

        self._modifiers = objectdb.DatabaseList(
            parent=self.id(),
            id=modifiers.id() if isinstance(modifiers, objectdb.DatabaseList) else None)
        if modifiers != None:
            for name, value in modifiers:
                tupleList = objectdb.DatabaseList()
                tupleList.add(name)
                tupleList.add(value)
                self._modifiers.add(tupleList)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DiceRollResult):
            return super().__eq__(other) and \
                self._timestamp == other._timestamp and \
                self._label == other._label and \
                self._die == other._die and \
                self._rolls == other._rolls and \
                self._ignored == other._ignored and \
                self._modifiers == other._modifiers and \
                self._targetType == other._targetType and \
                self._targetNumber == other._targetNumber
        return False

    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    def label(self) -> str:
        return self._label

    def die(self) -> common.DieType:
        return self._die

    def total(self) -> int:
        return self.rolledTotal() + self.modifiersTotal()

    def rolls(self) -> typing.Iterable[typing.Tuple[
            int, # Rolled value
            bool # Is roll ignored due to boon/bane
            ]]:
        return [(roll, index == self._ignored) for index, roll in enumerate(self._rolls)]

    def rollCount(self) -> int:
        return len(self._rolls)

    def rolledTotal(self) -> int:
        total = 0
        for index, roll in enumerate(self._rolls):
            if index != self._ignored:
                total += roll
        return total

    def modifiers(self) -> typing.Iterable[typing.Tuple[str, int]]:
        return [(modifier[0], modifier[1]) for modifier in self._modifiers]

    def modifiersTotal(self) -> int:
        total = 0
        for modifier in self._modifiers:
            total += modifier[1]
        return total

    def modifierCount(self) -> int:
        return len(self._modifiers)

    def targetType(self) -> typing.Optional[common.ComparisonType]:
        return self._targetType

    def targetNumber(self) -> typing.Optional[int]:
        return self._targetNumber

    def hasTarget(self) -> bool:
        return self._targetType != None and self._targetNumber != None

    def isSuccess(self) -> bool:
        if self._targetType == None or self._targetNumber == None:
            return False # No target means no pass
        return common.ComparisonType.compareValues(
            lhs=self.total(),
            rhs=self._targetNumber,
            comparison=self._targetType)

    # The effect will only be set if a target number was specified and that
    # target number was met
    def effectType(self) -> typing.Optional[DiceRollEffectType]:
        effectValue = self.effectValue()
        if effectValue == None:
            return None
        return DiceRollEffectType.effectValueToType(value=effectValue)

    def effectValue(self) -> typing.Optional[int]:
        if self._targetNumber != None:
            if self._targetType == common.ComparisonType.EqualTo:
                return -abs(self._targetNumber - self.total())
            elif self._targetType == common.ComparisonType.GreaterThan:
                return self.total() - (self._targetNumber + 1)
            elif self._targetType == common.ComparisonType.GreaterOrEqualTo:
                return self.total() - self._targetNumber
            elif self._targetType == common.ComparisonType.LessThan:
                return (self._targetNumber - 1) - self.total()
            elif self._targetType == common.ComparisonType.LessThanOrEqualTo:
                return self._targetNumber - self.total()
        return None

    def data(self) -> typing.Mapping[
            str,
            typing.Optional[typing.Union[bool, int, float, str, objectdb.DatabaseEntity]]]:
        return {
            'timestamp': self._timestamp.isoformat(),
            'label': self._label,
            'die': self._die.name,
            'rolls': self._rolls,
            'ignored': self._ignored,
            'modifiers': self._modifiers,
            'target_type': self._targetType.name if self._targetType != None else None,
            'target_number': self._targetNumber
            }

    @staticmethod
    def defineObject() -> objectdb.ObjectDef:
        return objectdb.ObjectDef(
            tableName='dice_roll_results',
            tableSchema=1,
            classType=DiceRollResult,
            paramDefs=[
                objectdb.ParamDef(columnName='timestamp', columnType=str),
                objectdb.ParamDef(columnName='label', columnType=str),
                objectdb.ParamDef(columnName='die', columnType=str),
                objectdb.ParamDef(columnName='rolls', columnType=objectdb.DatabaseList),
                objectdb.ParamDef(columnName='ignored', columnType=int, isOptional=True),
                objectdb.ParamDef(columnName='modifiers', columnType=objectdb.DatabaseList),
                objectdb.ParamDef(columnName='target_type', columnType=str, isOptional=True),
                objectdb.ParamDef(columnName='target_number', columnType=int, isOptional=True)
            ])

    @staticmethod
    def createObject(
        id: str,
        parent: typing.Optional[str],
        data: typing.Mapping[
            str,
            typing.Optional[typing.Union[bool, int, float, str, objectdb.DatabaseEntity]]]
        ) -> 'DiceRollerGroup':
        timestamp = data.get('timestamp')
        if not isinstance(timestamp, str):
            raise ValueError('RollResult construction parameter "timestamp" is not a str')
        try:
            timestamp = datetime.datetime.fromisoformat(timestamp)
        except Exception as ex:
            raise ValueError(f'RollResult construction parameter "timestamp" has unexpected value "{timestamp}"')

        label = data.get('label')
        if not isinstance(label, str):
            raise ValueError('RollResult construction parameter "label" is not a str')

        die = data.get('die')
        if not isinstance(die, str):
            raise ValueError('RollResult construction parameter "die" is not a str')
        if die not in common.DieType.__members__:
            raise ValueError(f'RollResult construction parameter "die" has unexpected value "{die}"')
        die = common.DieType.__members__[die]

        rolls = data.get('rolls')
        if not isinstance(rolls, objectdb.DatabaseList):
            raise ValueError('RollResult construction parameter "rolls" is not a DatabaseList')

        ignored = data.get('ignored')
        if ignored != None and not isinstance(ignored, int):
            raise ValueError('RollResult construction parameter "ignored" is not an int or None')

        modifiers = data.get('modifiers')
        if not isinstance(modifiers, objectdb.DatabaseList):
            raise ValueError('RollResult construction parameter "modifiers" is not a DatabaseList')

        targetType = data.get('target_type')
        if targetType != None:
            if not isinstance(targetType, str):
                raise ValueError('RollResult construction parameter "target_type" is not a str or None')
            if targetType not in common.ComparisonType.__members__:
                raise ValueError(f'RollResult construction parameter "target_type" has unexpected value "{targetType}"')
            targetType = common.ComparisonType.__members__[targetType]

        targetNumber = data.get('target_number')
        if targetNumber != None and not isinstance(targetNumber, int):
            raise ValueError('RollResult construction parameter "target_number" is not an int or None')

        return DiceRollResult(
            id=id,
            parent=parent,
            timestamp=timestamp,
            label=label,
            die=die,
            rolls=rolls,
            ignored=ignored,
            modifiers=modifiers,
            targetType=targetType,
            targetNumber=targetNumber)