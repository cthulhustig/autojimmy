import construction
import enum
import gunsmith
import logging
import json
import typing

def serialiseOptions(
        component: gunsmith.WeaponComponentInterface
        ) -> typing.Iterable[typing.Mapping[str, typing.Any]]:
    options = []
    for option in component.options():
        value = option.value()
        if isinstance(option, construction.BooleanOption):
            assert(isinstance(value, bool))
            options.append({
                'id': option.id(),
                'value': value
            })
        elif isinstance(option, construction.StringOption):
            assert(isinstance(value, str))
            options.append({
                'id': option.id(),
                'value': value
            })            
        elif isinstance(option, construction.IntegerOption):
            assert(isinstance(value, int))
            options.append({
                'id': option.id(),
                'value': value
            })
        elif isinstance(option, construction.FloatOption):
            assert(isinstance(value, float) or isinstance(value, int))
            options.append({
                'id': option.id(),
                'value': value
            })
        elif isinstance(option, construction.EnumOption):
            assert(value == None or isinstance(value, enum.Enum))
            options.append({
                'id': option.id(),
                'value': value.name if value else None
            })
        elif isinstance(option, construction.MultiSelectOption):
            # TODO: This hasn't been tested
            assert(isinstance(value, list))
            options.append({
                'id': option.id(),
                'value': value
            })            

    return options

def deserialiseOptions(
        componentType: str,
        dataList: typing.Iterable[typing.Mapping[str, typing.Any]]
        ) -> typing.Dict[str, typing.Any]:
    options: typing.Mapping[str, typing.Any] = {}
    for optionData in dataList:
        optionId = optionData.get('id')
        if optionId == None:
            raise RuntimeError(f'Option for component type {componentType} is missing the ID element')
        optionValue = optionData.get('value') # No checking of value as it can be None
        options[optionId] = optionValue
    return options

def serialiseComponentList(
        components: typing.Iterable[gunsmith.WeaponComponentInterface]
        ) -> typing.Iterable[typing.Mapping[str, typing.Any]]:
    serialised = []
    for component in components:
        serialised.append({
            'type': type(component).__name__,
            'options': serialiseOptions(component=component)
        })
    return serialised

def serialiseComponents(
        weapon: gunsmith.Weapon
        ) -> typing.Mapping[str, typing.Any]:
    sequenceComponents: typing.Dict[str, typing.List[gunsmith.WeaponComponentInterface]] = {}
    commonComponents: typing.List[gunsmith.WeaponComponentInterface] = []
    for stage in weapon.stages():
        if stage.phase() in gunsmith.InternalConstructionPhases:
            continue # Don't write internal phases

        sequence = stage.sequence()
        if sequence:
            componentList = sequenceComponents.get(sequence)
            if not componentList:
                componentList = []
                sequenceComponents[sequence] = componentList
            componentList.extend(stage.components())
        else:
            commonComponents.extend(stage.components())

    # It's important this is done in standard sequence order
    sequenceList = []
    for sequence in weapon.sequences():
        weaponType = weapon.weaponType(sequence=sequence)
        componentList = sequenceComponents.get(sequence, [])
        sequenceList.append({
            'type': weaponType.name,
            'components': serialiseComponentList(components=componentList)
        })

    return {
        'sequences': sequenceList,
        'common': serialiseComponentList(components=commonComponents)
    }

def deserialiseComponentList(
    components: typing.Iterable[typing.Mapping[str, typing.Any]]
    ) -> typing.List[typing.Tuple[
        str,
        typing.Optional[typing.Mapping[str, typing.Any]]
        ]]:
    deserialised = []
    for componentData in components:
        componentType = componentData.get('type')
        if componentType == None:
            raise RuntimeError('Component list entry is missing the type element')

        optionList: typing.Iterable[typing.Mapping[str, typing.Any]] = \
            componentData.get('options')
        options = None
        if optionList:
            options = deserialiseOptions(
                componentType=componentType,
                dataList=optionList)

        deserialised.append((componentType, options))
    return deserialised

def deserialiseComponents(
        weapon: gunsmith.Weapon,
        componentData: typing.Mapping[str, typing.Any]
        ) -> typing.Mapping[str, typing.Any]:
    sequenceDataList: typing.Iterable[typing.Mapping[str, typing.Any]] = \
        componentData.get('sequences')
    if sequenceDataList == None:
        raise RuntimeError('Component data is missing the sequences element')

    commonDataList = componentData.get('common')
    if commonDataList == None:
        raise RuntimeError('Component data is missing the common element')

    # Create each of the sequences and generate a per sequence lists of
    # components and their options. Options aren't applied to the component
    # until after its been added to the weapon
    sequenceComponentMap = {}
    for sequenceData in sequenceDataList:
        weaponType = sequenceData.get('type')
        if weaponType == None:
            raise RuntimeError('Sequence data is missing the type element')
        weaponType = gunsmith.WeaponType[weaponType]

        componentDataList = sequenceData.get('components')
        if componentDataList == None:
            raise RuntimeError('Sequence data is missing the type components')

        sequence = weapon.addSequence(
            weaponType=weaponType,
            regenerate=False) # Loading components will regenerate

        sequenceComponentMap[sequence] = deserialiseComponentList(
            components=componentDataList)

    # Create a list of common components and their options.
    commonComponents = deserialiseComponentList(
        components=commonDataList)
    
    weapon.loadComponents(
        sequenceComponents=sequenceComponentMap,
        commonComponents=commonComponents)

def serialiseRules(
        weapon: gunsmith.Weapon
        ) -> typing.Iterable[str]:
    rules = []
    for rule in weapon.rules():
        rules.append(rule.name)
    return rules

def deserialiseRules(
        weapon: gunsmith.Weapon,
        rulesData: typing.Iterable[str]
        ) -> None:
    rules = []
    for ruleString in rulesData:
        try:
            rule = gunsmith.RuleId[ruleString]
        except Exception:
            logging.warning(f'Ignoring unknown rule \'{ruleString}\' when loading weapon \'{weapon.weaponName()}\'')
            continue
        rules.append(rule)

    weapon.setRules(rules=rules)

def serialiseWeapon(
        weapon: gunsmith.Weapon
        ) -> typing.Mapping[str, typing.Any]:
    return {
        'name': weapon.weaponName(),
        'techLevel': weapon.techLevel(),
        'rules': serialiseRules(weapon),
        'components': serialiseComponents(weapon=weapon),
        'notes': json.dumps(weapon.userNotes()) # This is user entered content so use dumps to escape it
    }

def deserialiseWeapon(
        data: typing.Mapping[str, typing.Any],
        inPlace: typing.Optional[gunsmith.Weapon] = None,
        ) -> gunsmith.Weapon:
    weaponName = data.get('name')
    if weaponName == None:
        raise RuntimeError('Weapon data is missing the name element')

    techLevel = data.get('techLevel')
    if techLevel == None:
        raise RuntimeError('Weapon data is missing the techLevel element')
    techLevel = int(techLevel)

    if inPlace:
        inPlace.clearRules()
        inPlace.clearSequences()
        inPlace.setWeaponName(name=weaponName)
        inPlace.setTechLevel(techLevel=techLevel, regenerate=True) # Only regenerate on last step
        weapon = inPlace
    else:
        weapon = gunsmith.Weapon(
            weaponName=weaponName,
            techLevel=techLevel)

    rules = data.get('rules', [])
    if rules:
        deserialiseRules(
            weapon=weapon,
            rulesData=rules)

    components = data.get('components')
    if components:
        deserialiseComponents(
            weapon=weapon,
            componentData=components)

    notes = data.get('notes')
    if notes:
        weapon.setUserNotes(notes=json.loads(notes)) # Unescape string when loading

    return weapon

def writeWeapon(
        weapon: gunsmith.Weapon,
        filePath: str
        ) -> None:
    data = serialiseWeapon(weapon=weapon)
    with open(filePath, 'w', encoding='UTF8') as file:
        json.dump(data, file, indent=4)

def readWeapon(
        filePath: str,
        inPlace: typing.Optional[gunsmith.Weapon] = None
        ) -> gunsmith.Weapon:
    with open(filePath, 'r') as file:
        return deserialiseWeapon(
            data=json.load(file),
            inPlace=inPlace)
