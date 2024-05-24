import construction
import gunsmith
import logging
import json
import typing

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
            'components': construction.serialiseComponentList(components=componentList)
        })

    return {
        'sequences': sequenceList,
        'common': construction.serialiseComponentList(components=commonComponents)
    }

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

        sequenceComponentMap[sequence] = construction.deserialiseComponentList(
            components=componentDataList)

    # Create a list of common components and their options.
    commonComponents = construction.deserialiseComponentList(
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
            logging.warning(f'Ignoring unknown rule \'{ruleString}\' when loading weapon \'{weapon.name()}\'')
            continue
        rules.append(rule)

    weapon.setRules(rules=rules)

def serialiseWeapon(
        weapon: gunsmith.Weapon
        ) -> typing.Mapping[str, typing.Any]:
    return {
        'name': weapon.name(),
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
        inPlace.setName(name=weaponName)
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
