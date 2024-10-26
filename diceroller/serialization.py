import common
import diceroller
import json
import typing

def serialiseGroups(
        groups: typing.Iterable[diceroller.DiceRollerGroup]
        ) -> str: # Returns json representation
    data = []
    for group in groups:
        data.append(_serialiseGroup(group=group))
    return json.dumps(data, indent=4)

def deserialiseGroups(
        serialData: str
        ) -> typing.Iterable[diceroller.DiceRollerGroup]:
    data = json.loads(serialData)
    if not isinstance(data, list):
        raise RuntimeError('Invalid data, expected list of DiceRollerGroup')
    groups = []
    for groupData in data:
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

    return diceroller.DiceRollerGroup(
        name=name,
        rollers=rollers)

def _serialiseRoller(
        roller: diceroller.DiceRoller,
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
    if dieType not in common.DieType.__members__:
        raise RuntimeError('Dice Roller data dieType attribute must be one of {valid}'.format(
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
        raise RuntimeError('Dice Roller data constant attribute must be a integer')

    hasBoon = rollerData.get('hasBoon', False)
    if not isinstance(hasBoon, bool):
        raise RuntimeError('Dice Roller data hasBoon attribute must be true or false')

    hasBane = rollerData.get('hasBane', False)
    if not isinstance(hasBane, bool):
        raise RuntimeError('Dice Roller data hasBane attribute must be true or false')

    targetType = rollerData.get('targetType')
    if targetType != None:
        if targetType not in common.ComparisonType.__members__:
            raise RuntimeError('Dice Roller data targetType attribute must be null or one of {valid}'.format(
                valid=common.humanFriendlyListString(
                    strings=list(common.ComparisonType.__members__.keys()))))
        targetType = common.ComparisonType.__members__[targetType]

    targetNumber = rollerData.get('targetNumber')
    if targetNumber != None and not isinstance(targetNumber, int):
        raise RuntimeError('Dice Roller data targetNumber attribute must be an integer')

    return diceroller.DiceRoller(
        name=name,
        dieCount=dieCount,
        dieType=dieType,
        constant=constant,
        hasBoon=hasBoon,
        hasBane=hasBane,
        modifiers=modifiers,
        targetType=targetType,
        targetNumber=targetNumber)

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

    return diceroller.DiceModifier(
        name=name,
        value=value,
        enabled=enabled)
