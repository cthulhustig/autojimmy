import packaging.version
import common
import diceroller
import packaging
import json
import typing

# Major version changes indicate breaking changes
# Minor version changes should be backwards compatible with older
# versions (but new functionality is ignored)
_FormatVersion = packaging.version.Version('1.0')

def serialiseGroups(
        groups: typing.Iterable[diceroller.DiceRollerGroup]
        ) -> str: # Returns json representation
    groupListData = []
    for group in groups:
        groupListData.append(_serialiseGroup(group=group))
    data = {
        'version': str(_FormatVersion),
        'groups': groupListData}
    return json.dumps(data, indent=4)

def deserialiseGroups(
        serialData: str
        ) -> typing.Iterable[diceroller.DiceRollerGroup]:
    data = json.loads(serialData)
    if not isinstance(data, dict):
        raise RuntimeError('File has no root object')

    version = data.get('version')
    if version == None:
        raise RuntimeError('File has no version property')
    if not isinstance(version, str):
        raise RuntimeError('File version property is not a string')
    try:
        version = packaging.version.Version(version)
    except Exception as ex:
        raise RuntimeError(f'File version property has invalid format ({ex})')
    if version.major > _FormatVersion.major:
        raise RuntimeError(f'Unsupported file format {version}')

    groupDataList = data.get('groups')
    if groupDataList == None:
        raise RuntimeError('File has no groups property')
    if not isinstance(groupDataList, list):
        raise RuntimeError('File groups property is not a list')

    groups = []
    for groupData in groupDataList:
        groups.append(_deserialiseGroup(groupData=groupData))
    return groups

def _serialiseGroup(
        group: diceroller.DiceRollerGroup,
        ) -> typing.Mapping[str, typing.Any]:
    rollers = []
    for roller in group.rollers():
        rollers.append(_serialiseRoller(roller=roller))

    return {
        'name': group.name(),
        'rollers': rollers}

def _deserialiseGroup(
        groupData: typing.Mapping[str, typing.Any]
        ) -> diceroller.DiceRollerGroup:
    name = groupData.get('name')
    if name == None:
        raise RuntimeError('Dice Roller Group has no name property')
    if not isinstance(name, str):
        raise RuntimeError('Dice Roller Group name property is not a string')

    rollerDataList = groupData.get('rollers')
    rollers = []
    if rollerDataList != None:
        if not isinstance(rollerDataList, list):
            raise RuntimeError('Dice Roller Group rollers property is not a list')
        for rollerData in rollerDataList:
            rollers.append(_deserialiseRoller(
                rollerData=rollerData))

    return diceroller.DiceRollerGroup(
        name=name,
        rollers=rollers)

def _serialiseRoller(
        roller: diceroller.DiceRoller,
        ) -> typing.Mapping[str, typing.Any]:
    rollerData = {
        'name': roller.name(),
        'dieCount': roller.dieCount(),
        'dieType': roller.dieType().name,
        'constant': roller.constant(),
        'snakeEyesRule': roller.snakeEyesRule()}

    if roller.extraDie() != None:
        rollerData['extraDie'] = roller.extraDie().name

    if roller.fluxType() != None:
        rollerData['fluxType'] = roller.fluxType().name

    modifierDataList = []
    for modifier in roller.modifiers():
        modifierDataList.append(_serialiseModifier(modifier=modifier))
    if modifierDataList:
        rollerData['modifiers'] = modifierDataList

    if roller.targetType() != None:
        rollerData['targetType'] = roller.targetType().name

    if roller.targetNumber() != None:
        rollerData['targetNumber'] = roller.targetNumber()

    return rollerData

def _deserialiseRoller(
        rollerData: typing.Mapping[str, typing.Any],
        ) -> diceroller.DiceRoller:
    name = rollerData.get('name')
    if name == None:
        raise RuntimeError('Dice Roller has no name property')
    if not isinstance(name, str):
        raise RuntimeError('Dice Roller name property is not a string')

    dieCount = rollerData.get('dieCount')
    if dieCount == None:
        raise RuntimeError('Dice Roller has no dieCount property')
    if not isinstance(dieCount, int):
        raise RuntimeError('Dice Roller dieCount property is not a integer')

    dieType = rollerData.get('dieType')
    if dieType == None:
        raise RuntimeError('Dice Roller has no dieType property')
    if dieType not in common.DieType.__members__:
        raise RuntimeError('Dice Roller dieType property is not one of {valid}'.format(
            valid=common.humanFriendlyListString(
                strings=list(common.DieType.__members__.keys()))))
    dieType = common.DieType.__members__[dieType]

    modifierDataList = rollerData.get('modifiers')
    modifiers = []
    if modifierDataList != None:
        for modifierData in modifierDataList:
            modifiers.append(_deserialiseModifier(
                modifierData=modifierData))

    constant = rollerData.get('constant', 0)
    if not isinstance(constant, int):
        raise RuntimeError('Dice Roller constant property is not an integer')

    extraDie = rollerData.get('extraDie')
    if extraDie != None:
        if extraDie not in common.ExtraDie.__members__:
            raise RuntimeError('Dice Roller extraDie property is not null or one of {valid}'.format(
                valid=common.humanFriendlyListString(
                    strings=list(common.ExtraDie.__members__.keys()))))
        extraDie = common.ExtraDie.__members__[extraDie]

    fluxType = rollerData.get('fluxType')
    if fluxType != None:
        if fluxType not in diceroller.FluxType.__members__:
            raise RuntimeError('Dice Roller fluxType property is not null or one of {valid}'.format(
                valid=common.humanFriendlyListString(
                    strings=list(diceroller.FluxType.__members__.keys()))))
        fluxType = diceroller.FluxType.__members__[fluxType]

    targetType = rollerData.get('targetType')
    if targetType != None:
        if targetType not in common.ComparisonType.__members__:
            raise RuntimeError('Dice Roller targetType property is not null or one of {valid}'.format(
                valid=common.humanFriendlyListString(
                    strings=list(common.ComparisonType.__members__.keys()))))
        targetType = common.ComparisonType.__members__[targetType]

    targetNumber = rollerData.get('targetNumber')
    if targetNumber != None and not isinstance(targetNumber, int):
        raise RuntimeError('Dice Roller targetNumber property is not null or an integer')

    snakeEyesRule = rollerData.get('snakeEyesRule', False)
    if not isinstance(snakeEyesRule, bool):
        raise RuntimeError('Dice Roller snakeEyesRule property is not a boolean')

    return diceroller.DiceRoller(
        name=name,
        dieCount=dieCount,
        dieType=dieType,
        constant=constant,
        extraDie=extraDie,
        fluxType=fluxType,
        modifiers=modifiers,
        targetType=targetType,
        targetNumber=targetNumber,
        snakeEyesRule=snakeEyesRule)

def _serialiseModifier(
        modifier: diceroller.DiceModifier,
        ) -> typing.Mapping[str, typing.Any]:
    return {
        'name': modifier.name(),
        'value': modifier.value(),
        'enabled': modifier.enabled()}

def _deserialiseModifier(
        modifierData: typing.Mapping[str, typing.Any]
        ) -> diceroller.DiceModifier:
    name = modifierData.get('name')
    if name == None:
        raise RuntimeError('Dice Modifier has no name property')
    if not isinstance(name, str):
        raise RuntimeError('Dice Modifier name property is not an string')

    value = modifierData.get('value')
    if value == None:
        raise RuntimeError('Dice Modifier has no value property')
    if not isinstance(value, int):
        raise RuntimeError('Dice Modifier value property is not an integer')

    enabled = modifierData.get('enabled', True)
    if not isinstance(enabled, bool):
        raise RuntimeError('Dice Modifier enabled property is not true or false')

    return diceroller.DiceModifier(
        name=name,
        value=value,
        enabled=enabled)
