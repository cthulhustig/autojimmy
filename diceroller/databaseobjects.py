import common
import enum
import objectdb
import typing

class DiceModifierDatabaseObject(objectdb.DatabaseObject):
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
        if isinstance(other, DiceModifierDatabaseObject):
            return super().__eq__(other) and \
                self._name == other._name and \
                self._value ==  other._value and \
                self._enabled == other._enabled
        return False

    def __hash__(self) -> int:
        return hash((
            super().__hash__(),
            self._name,
            self._value,
            self._enabled))

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

    @staticmethod
    def defineObject() -> objectdb.ObjectDef:
        return objectdb.ObjectDef(
            classType=DiceModifierDatabaseObject,
            paramDefs=[
                objectdb.ParamDef(paramName='name', paramType=objectdb.ParamDef.ParamType.Text),
                objectdb.ParamDef(paramName='value', paramType=objectdb.ParamDef.ParamType.Integer),
                objectdb.ParamDef(paramName='enabled', paramType=objectdb.ParamDef.ParamType.Boolean)
            ],
            tableName='dice_modifiers')

class DiceRollerDatabaseObject(objectdb.DatabaseObject):
    def __init__(
            self,
            name: str,
            dieCount: int = 1,
            dieType: common.DieType = common.DieType.D6,
            constantDM: int = 0,
            hasBoon: bool = False,
            hasBane: bool = False,
            dynamicDMs: typing.Optional[typing.Union[
                typing.Iterable[DiceModifierDatabaseObject],
                objectdb.DatabaseList]] = None,
            targetNumber: typing.Optional[int] = None,
            id: typing.Optional[str] = None,
            parent: typing.Optional[str] = None
            ) -> None:
        super().__init__(id=id, parent=parent)
        self._name = name
        self._dieCount = dieCount
        self._dieType = dieType
        self._constantDM = constantDM
        self._hasBoon = hasBoon
        self._hasBane = hasBane
        self._targetNumber = targetNumber

        self._dynamicDMs = objectdb.DatabaseList(
            parent=self.id(),
            id=dynamicDMs.id() if isinstance(dynamicDMs, objectdb.DatabaseList) else None)
        if dynamicDMs:
            self.setDynamicDMs(dynamicDMs=dynamicDMs)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DiceRollerDatabaseObject):
            return super().__eq__(other) and \
                self._name == other._name and \
                self._dieCount ==  other._dieCount and \
                self._dieType == other._dieType and \
                self._constantDM == other._constantDM and \
                self._hasBoon == other._hasBoon and \
                self._hasBane == other._hasBane and \
                self._dynamicDMs == other._dynamicDMs and \
                self._targetNumber == other._targetNumber
        return False

    def __hash__(self) -> int:
        return hash((
            super().__hash__(),
            self._name,
            self._dieCount,
            self._dieType,
            self._constantDM,
            self._hasBoon,
            self._hasBane,
            self._dynamicDMs,
            self._targetNumber))

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

    def dieCount(self) -> int:
        return self._dieCount

    def setDieCount(self, dieCount: int) -> None:
        self._dieCount = dieCount

    def dieType(self) -> str:
        return self._dieType

    def setDieType(self, dieType: str) -> None:
        self._dieType = dieType

    def constantDM(self) -> int:
        return self._constantDM

    def setConstantDM(self, constantDM: int) -> None:
        self._constantDM = constantDM

    def hasBoon(self) -> bool:
        return self._hasBoon

    def setHasBoon(self, hasBoon: bool) -> None:
        self._hasBoon = hasBoon

    def hasBane(self) -> bool:
        return self._hasBane

    def setHasBane(self, hasBane: bool) -> None:
        self._hasBane = hasBane

    def dynamicDMs(self) -> objectdb.DatabaseList:
        return self._dynamicDMs

    def setDynamicDMs(
            self,
            dynamicDMs: typing.Union[
                typing.Iterable[DiceModifierDatabaseObject],
                objectdb.DatabaseList]
            ) -> None:
        for dynamicDM in dynamicDMs:
            if not isinstance(dynamicDM, DiceModifierDatabaseObject):
                raise ValueError(f'Dynamic DM is not a {DiceModifierDatabaseObject}')

        if isinstance(dynamicDMs, objectdb.DatabaseList):
            if dynamicDMs.parent() != None:
                raise ValueError(f'List {dynamicDMs.id()} already has parent {dynamicDMs.parent()}')

            self._dynamicDMs.setParent(None)
            self._dynamicDMs = dynamicDMs
            self._dynamicDMs.setParent(self.id())
        else:
            for dynamicDM in dynamicDMs:
                if dynamicDM.parent() != None:
                    raise ValueError(f'Dynamic DM {dynamicDM.id()} already has parent {dynamicDM.parent()}')
            self._dynamicDMs.init(objects=dynamicDMs)

    def addDynamicDM(self, dynamicDM: DiceModifierDatabaseObject) -> None:
        if not isinstance(dynamicDM, DiceModifierDatabaseObject):
            raise ValueError(f'Dynamic DM is not a {DiceModifierDatabaseObject}')
        self._dynamicDMs.add(object=dynamicDM)

    def removeDynamicDM(self, dynamicDM: DiceModifierDatabaseObject) -> None:
        self._dynamicDMs.remove(object=dynamicDM)

    def targetNumber(self) -> typing.Optional[int]:
        return self._targetNumber

    def setTargetNumber(self, targetNumber: typing.Optional[int]) -> None:
        self._targetNumber = targetNumber

    @staticmethod
    def defineObject() -> objectdb.ObjectDef:
        return objectdb.ObjectDef(
            classType=DiceRollerDatabaseObject,
            paramDefs=[
                objectdb.ParamDef(paramName='name', paramType=objectdb.ParamDef.ParamType.Text),
                objectdb.ParamDef(paramName='dieCount', columnName='die_count', paramType=objectdb.ParamDef.ParamType.Integer),
                objectdb.ParamDef(paramName='dieType', columnName='die_type', paramType=objectdb.ParamDef.ParamType.Enum, enumType=common.DieType),
                objectdb.ParamDef(paramName='constantDM', columnName='constant_dm', paramType=objectdb.ParamDef.ParamType.Integer),
                objectdb.ParamDef(paramName='hasBoon', columnName='has_boon', paramType=objectdb.ParamDef.ParamType.Integer),
                objectdb.ParamDef(paramName='hasBane', columnName='has_bane', paramType=objectdb.ParamDef.ParamType.Integer),
                objectdb.ParamDef(paramName='dynamicDMs', columnName='dynamic_dms', paramType=objectdb.ParamDef.ParamType.List),
                objectdb.ParamDef(paramName='targetNumber', columnName='target_number', paramType=objectdb.ParamDef.ParamType.Integer, isOptional=True),
            ],
            tableName='dice_rollers')

class DiceRollerGroupDatabaseObject(objectdb.DatabaseObject):
    def __init__(
            self,
            name: str,
            rollers: typing.Union[
                typing.Iterable[DiceRollerDatabaseObject],
                objectdb.DatabaseList],
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
        if isinstance(other, DiceRollerGroupDatabaseObject):
            return super().__eq__(other) and \
                self._name == other._name and \
                self._rollers ==  other._rollers
        return False

    def __hash__(self) -> int:
        return hash((
            super().__hash__(),
            self._name,
            self._rollers))

    def name(self) -> str:
        return self._name

    def setName(self, name: str) -> None:
        self._name = name

    def rollers(self) -> objectdb.DatabaseList:
        return self._rollers

    def setRollers(
            self,
            rollers: typing.Union[
                typing.Iterable[DiceRollerDatabaseObject],
                objectdb.DatabaseList]
            ) -> None:
        for roller in rollers:
            if not isinstance(roller, DiceRollerDatabaseObject):
                raise ValueError(f'Roller is not a {DiceRollerDatabaseObject})')

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
            self._rollers.init(objects=rollers)

    def addRoller(self, roller: DiceRollerDatabaseObject) -> None:
        if not isinstance(roller, DiceRollerDatabaseObject):
            raise ValueError(f'Roller is not a {DiceRollerDatabaseObject}')
        if roller.parent() != None:
            raise ValueError(f'Roller {roller.id()} already has parent {roller.parent()}')

        self._rollers.add(roller)

    def removeRoller(self, roller: DiceRollerDatabaseObject) -> None:
        self._rollers.remove(roller)

    @staticmethod
    def defineObject() -> objectdb.ObjectDef:
        return objectdb.ObjectDef(
            classType=DiceRollerGroupDatabaseObject,
            paramDefs=[
                objectdb.ParamDef(paramName='name', paramType=objectdb.ParamDef.ParamType.Text),
                objectdb.ParamDef(paramName='rollers', paramType=objectdb.ParamDef.ParamType.List),
            ],
            tableName='dice_groups')
