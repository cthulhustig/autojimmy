import common
import json
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

    def data(self) -> typing.Mapping[str, typing.Any]:
        return {
            'name': self._name,
            'value': self._value,
            'enabled': self._enabled}

    @staticmethod
    def defineObject() -> objectdb.ObjectDef:
        return objectdb.ObjectDef(
            tableName='dice_modifiers',
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
        data: typing.Mapping[str, typing.Any]
        ) -> 'DiceRoller':
        name = data.get('name')
        if not isinstance(name, str):
            raise ValueError(f'Constructing a DiceModifierDatabaseObject requires a name parameter of type str')
        value = data.get('value')
        if not isinstance(value, int):
            raise ValueError(f'Constructing a DiceModifierDatabaseObject requires a value parameter of type int')
        enabled = data.get('enabled')
        if not isinstance(enabled, bool):
            raise ValueError(f'Constructing a DiceModifierDatabaseObject requires a enabled parameter of type bool')

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
            targetNumber: typing.Optional[int] = None,
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
        self._targetNumber = targetNumber

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
            self._modifiers.init(objects=modifiers)

    def addModifier(self, modifier: DiceModifier) -> None:
        if not isinstance(modifier, DiceModifier):
            raise ValueError(f'Modifier is not a {DiceModifier}')
        self._modifiers.add(object=modifier)

    def insertModifier(self, index: int, modifier: DiceModifier) -> None:
        if not isinstance(modifier, DiceModifier):
            raise ValueError(f'Modifier is not a {DiceModifier}')
        self._modifiers.insert(index=index, object=modifier)

    def removeModifier(self, id: str) -> DiceModifier:
        return self._modifiers.remove(id=id)

    def clearModifiers(self) -> None:
        self._modifiers.clear()

    def targetNumber(self) -> typing.Optional[int]:
        return self._targetNumber

    def setTargetNumber(self, targetNumber: typing.Optional[int]) -> None:
        self._targetNumber = targetNumber

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
            targetNumber=self._targetNumber)

    def data(self) -> typing.Mapping[str, typing.Any]:
        return {
            'name': self._name,
            'die_count': self._dieCount,
            'die_type': self._dieType,
            'constant': self._constant,
            'has_boon': self._hasBoon,
            'has_bane': self._hasBane,
            'modifiers': self._modifiers,
            'target_number': self._targetNumber}

    @staticmethod
    def defineObject() -> objectdb.ObjectDef:
        return objectdb.ObjectDef(
            tableName='dice_rollers',
            classType=DiceRoller,
            paramDefs=[
                objectdb.ParamDef(columnName='name', columnType=str),
                objectdb.ParamDef(columnName='die_count', columnType=int),
                objectdb.ParamDef(columnName='die_type', columnType=common.DieType),
                objectdb.ParamDef(columnName='constant', columnType=int),
                objectdb.ParamDef(columnName='has_boon', columnType=bool),
                objectdb.ParamDef(columnName='has_bane', columnType=bool),
                objectdb.ParamDef(columnName='modifiers', columnType=objectdb.DatabaseList),
                objectdb.ParamDef(columnName='target_number', columnType=int, isOptional=True),
            ])

    @staticmethod
    def createObject(
        id: str,
        parent: typing.Optional[str],
        data: typing.Mapping[str, typing.Any]
        ) -> 'DiceRoller':
        name = data.get('name')
        if not isinstance(name, str):
            raise ValueError(f'Constructing a DiceRollerDatabaseObject requires a name parameter of type str')
        dieCount = data.get('die_count')
        if not isinstance(dieCount, int):
            raise ValueError(f'Constructing a DiceRollerDatabaseObject requires a die_count parameter of type int')
        dieType = data.get('die_type')
        if not isinstance(dieType, common.DieType):
            raise ValueError(f'Constructing a DiceRollerDatabaseObject requires a die_count parameter of type DieType')
        constant = data.get('constant')
        if not isinstance(constant, int):
            raise ValueError(f'Constructing a DiceRollerDatabaseObject requires a constant parameter of type int')
        hasBoon = data.get('has_boon')
        if not isinstance(hasBoon, bool):
            raise ValueError(f'Constructing a DiceRollerDatabaseObject requires a has_boon parameter of type bool')
        hasBane = data.get('has_bane')
        if not isinstance(hasBane, bool):
            raise ValueError(f'Constructing a DiceRollerDatabaseObject requires a has_bane parameter of type bool')
        modifiers = data.get('modifiers')
        if not isinstance(modifiers, objectdb.DatabaseList):
            raise ValueError(f'Constructing a DiceRollerDatabaseObject requires a modifiers parameter of type DatabaseList')
        targetNumber = data.get('target_number')
        if targetNumber != None and not isinstance(targetNumber, int):
            raise ValueError(f'Constructing a DiceRollerDatabaseObject requires a target_number parameter of type int or None')

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
            self._rollers.init(objects=rollers)

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
        self._rollers.insert(index=index, object=roller)

    def removeRoller(self, id: str) -> DiceRoller:
        return self._rollers.remove(id=id)

    def clearRollers(self) -> None:
        self._rollers.clear()

    def findRoller(self, id: str) -> typing.Optional[DiceRoller]:
        return self._rollers.find(id=id)

    def containsRoller(self, id: str) -> bool:
        return self._rollers.contains(id=id)

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

    def data(self) -> typing.Mapping[str, typing.Any]:
        return {
            'name': self._name,
            'rollers': self._rollers}

    @staticmethod
    def defineObject() -> objectdb.ObjectDef:
        return objectdb.ObjectDef(
            tableName='dice_groups',
            classType=DiceRollerGroup,
            paramDefs=[
                objectdb.ParamDef(columnName='name', columnType=str),
                objectdb.ParamDef(columnName='rollers', columnType=objectdb.DatabaseList),
            ])

    @staticmethod
    def createObject(
        id: str,
        parent: typing.Optional[str],
        data: typing.Mapping[str, typing.Any]
        ) -> 'DiceRollerGroup':
        name = data.get('name')
        if not isinstance(name, str):
            raise ValueError(f'Constructing a DiceRollerGroupDatabaseObject requires a name parameter of type str')
        rollers = data.get('rollers')
        if not isinstance(rollers, objectdb.DatabaseList):
            raise ValueError(f'Constructing a DiceRollerGroupDatabaseObject requires a rollers parameter of type DatabaseList')

        return DiceRollerGroup(
            id=id,
            parent=parent,
            name=name,
            rollers=rollers)

def serialiseGroups(
        groups: typing.Iterable[DiceRollerGroup]
        ) -> str: # Returns json representation
    data = []
    for group in groups:
        data.append(_serialiseGroup(group=group))
    return json.dumps(data, indent=4)

def deserialiseGroups(
        serialData: str
        ) -> typing.Iterable[DiceRollerGroup]:
    data = json.loads(serialData)
    if not isinstance(data, list):
        raise RuntimeError('Invalid data, expected list of DiceRollerGroup')
    groups = []
    for groupData in data:
        groups.append(_deserialiseGroup(groupData=groupData))
    return groups

def _serialiseGroup(
        group: DiceRollerGroup,
        ) -> typing.Mapping[str, typing.Any]:
    rollers = []
    for roller in group.rollers():
        rollers.append(_serialiseRoller(roller=roller))

    return {
        'name': group.name(),
        'rollers': rollers}

def _deserialiseGroup(
        groupData: typing.Mapping[str, typing.Any]
        ) -> DiceRollerGroup:
    name = groupData.get('name')
    if name == None:
        raise RuntimeError('Dice Roller Group data must have a name attribute')
    if not isinstance(name, str):
        raise RuntimeError('Dice Roller Group data name attribute must be a string')

    rollerDataList = groupData.get('rollers')
    rollers = []
    if rollerDataList != None:
        if not isinstance(rollerDataList, list):
            raise RuntimeError('Dice Roller Group data list attribute must be a list')
        for rollerData in rollerDataList:
            rollers.append(_deserialiseRoller(
                rollerData=rollerData))

    return DiceRollerGroup(
        name=name,
        rollers=rollers)

def _serialiseRoller(
        roller: DiceRoller,
        ) -> typing.Mapping[str, typing.Any]:
    modifierDataList = []
    for modifier in roller.modifiers():
        modifierDataList.append(_serialiseModifier(modifier=modifier))
    rollerData = {
        'name': roller.name(),
        'dieCount': roller.dieCount(),
        'dieType': roller.dieType().name,
        'constant': roller.constant(),
        'hasBoon': roller.hasBoon(),
        'hasBane': roller.hasBane(),
        'modifiers': modifierDataList}

    if roller.targetNumber() != None:
        rollerData['targetNumber'] = roller.targetNumber()

    return rollerData

def _deserialiseRoller(
        rollerData: typing.Mapping[str, typing.Any],
        ) -> DiceRoller:
    name = rollerData.get('name')
    if name == None:
        raise RuntimeError('Dice Roller data must have a name attribute')
    if not isinstance(name, str):
        raise RuntimeError('Dice Roller data name attribute must be a string')

    dieCount = rollerData.get('dieCount')
    if dieCount == None:
        raise RuntimeError('Dice Roller data must have a dieCount attribute')
    if not isinstance(dieCount, int):
        raise RuntimeError('Dice Roller data dieCount attribute must be a integer')

    dieType = rollerData.get('dieType')
    if dieType == None:
        raise RuntimeError('Dice Roller data must have a dieType attribute')
    if not isinstance(dieType, str) or \
        dieType not in common.DieType.__members__:
        raise RuntimeError('Dice Roller data dieType attribute must be one of {valid}'.format(
            value=common.humanFriendlyListString(strings=common.DieType.__members__.keys())))
    if dieType not in common.DieType.__members__:
        raise RuntimeError('Dice Roller data dieType attribute must ')
    dieType = common.DieType.__members__[dieType]

    modifierDataList = rollerData.get('modifiers')
    modifiers = []
    if modifierDataList != None:
        for modifierData in modifierDataList:
            modifiers.append(_deserialiseModifier(
                modifierData=modifierData))

    constant = rollerData.get('constant', 0)
    if not isinstance(constant, int):
        raise RuntimeError('Dice Roller data constant attribute must be a integer')

    hasBoon = rollerData.get('hasBoon', False)
    if not isinstance(hasBoon, bool):
        raise RuntimeError('Dice Roller data hasBoon attribute must be true or false')

    hasBane = rollerData.get('hasBane', False)
    if not isinstance(hasBane, bool):
        raise RuntimeError('Dice Roller data hasBane attribute must be true or false')

    targetNumber = rollerData.get('targetNumber')
    if targetNumber != None and not isinstance(targetNumber, int):
        raise RuntimeError('Dice Roller data targetNumber attribute must be an integer')

    return DiceRoller(
        name=name,
        dieCount=dieCount,
        dieType=dieType,
        constant=constant,
        hasBoon=hasBoon,
        hasBane=hasBane,
        modifiers=modifiers,
        targetNumber=targetNumber)

def _serialiseModifier(
        modifier: DiceModifier,
        ) -> typing.Mapping[str, typing.Any]:
    return {
        'name': modifier.name(),
        'value': modifier.value(),
        'enabled': modifier.enabled()}

def _deserialiseModifier(
        modifierData: typing.Mapping[str, typing.Any]
        ) -> DiceModifier:
    name = modifierData.get('name')
    if name == None:
        raise RuntimeError('Dice Modifier data must have a name attribute')
    if not isinstance(name, str):
        raise RuntimeError('Dice Modifier data name attribute must be a string')

    value = modifierData.get('value')
    if value == None:
        raise RuntimeError('Dice Modifier data must have a value attribute')
    if not isinstance(value, int):
        raise RuntimeError('Dice Modifier data value attribute must be a integer')

    enabled = modifierData.get('enabled', True)
    if not isinstance(enabled, bool):
        raise RuntimeError('Dice Modifier data enabled attribute must be true or false')

    return DiceModifier(
        name=name,
        value=value,
        enabled=enabled)