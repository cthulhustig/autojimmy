import common
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
        if isinstance(option, construction.BooleanComponentOption):
            assert(isinstance(value, bool))
            options.append({
                'id': option.id(),
                'value': value
            })
        elif isinstance(option, construction.IntegerComponentOption):
            assert(isinstance(value, int))
            options.append({
                'id': option.id(),
                'value': value
            })
        elif isinstance(option, construction.FloatComponentOption):
            assert(isinstance(value, float) or isinstance(value, int))
            options.append({
                'id': option.id(),
                'value': value
            })
        elif isinstance(option, construction.EnumComponentOption):
            assert(value == None or isinstance(value, enum.Enum))
            options.append({
                'id': option.id(),
                'value': value.name if value else None
            })

    return options

def deserialiseOptions(
        weapon: gunsmith.Weapon,
        component: gunsmith.WeaponComponentInterface,
        dataList: typing.Iterable[typing.Mapping[str, typing.Any]]
        ) -> None:
    # Note that this code is more complicated than you might expect as it has to cope with the fact
    # setting one option may change what options are available. Rather than require that the options
    # are specified in the correct logical order in the file, the code makes multiple passes at
    # setting the options. It maintains a list of options specified in the file that still haven't been
    # set. Each pass it retrieves the current list of options from the component (based on the weapon
    # and any any options that have previously been set) and sets any that are still on the list of
    # options that need set. After an option has been set it's removed from the list. This process
    # repeats until there are no more options needing set _OR_ we have a pass where no options were
    # removed from the list of options waiting to be set (the later avoids an infinite loop if there
    # is an invalid option)
    pendingOptions: typing.Mapping[str, typing.Any] = {}
    for optionData in dataList:
        optionId = optionData.get('id')
        if optionId == None:
            raise RuntimeError(f'Option for component type {type(component).__name__} is missing the ID element')
        optionValue = optionData.get('value') # No checking of value as it can be None
        pendingOptions[optionId] = optionValue

    while pendingOptions:
        componentOptions = {}
        for option in component.options():
            componentOptions[option.id()] = option

        optionFound = False
        for optionId in list(pendingOptions.keys()): # Copy keys so found entries can be removed while iterating
            option = componentOptions.get(optionId)
            if not option:
                continue
            optionValue = pendingOptions[optionId]

            if isinstance(option, construction.BooleanComponentOption):
                option.setValue(value=optionValue)
            elif isinstance(option, construction.IntegerComponentOption):
                option.setValue(value=optionValue)
            elif isinstance(option, construction.FloatComponentOption):
                option.setValue(value=optionValue)
            elif isinstance(option, construction.EnumComponentOption):
                enumValue = None
                if optionValue != None:
                    enumType = option.type()
                    enumValue = enumType.__members__.get(optionValue)
                    if not enumValue:
                        raise RuntimeError(f'Option {option.id()} for component type {type(component).__name__} has unknown value "{optionValue}"')
                elif not option.isOptional():
                    raise RuntimeError(f'Option {option.id()} for component type {type(component).__name__} must have a value')

                option.setValue(value=enumValue)

            # The option has been set so remove it from the pending options and record
            # the fact we've found at least one option this time round the loop
            del pendingOptions[optionId]
            optionFound = True

        if not optionFound:
            break # No pending options are found so no reason to think another iteration will help

    for optionId in pendingOptions:
        logging.warning(f'Ignoring unknown option {optionId} for component type {type(component).__name__} when loading \'{weapon.weaponName()}\'')

    weapon.regenerate()

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

# Note that this function doesn't deserialise options as that can't be done until the component has
# been added to the weapon. It returns a list of component instances and their (still serialised)
# option data
def deserialiseComponentList(
    weapon: gunsmith.Weapon,
    components: typing.Iterable[typing.Mapping[str, typing.Any]],
    componentTypeMap: typing.Mapping[str, typing.Type[gunsmith.WeaponComponentInterface]]
    ) -> typing.List[typing.Tuple[
        gunsmith.WeaponComponentInterface,
        typing.Optional[typing.Iterable[typing.Mapping[str, typing.Any]]] # This is still serialised
        ]]:
    deserialised = []
    for componentData in components:
        componentType = componentData.get('type')
        if componentType == None:
            raise RuntimeError('Component list entry is missing the type element')

        componentClass = componentTypeMap.get(componentType)
        if not componentClass:
            logging.warning(f'Ignoring unknown component type \'{componentType}\' when loading weapon \'{weapon.weaponName()}\'')
            continue

        component = componentClass()

        optionData = componentData.get('options') # Treat options as optional

        deserialised.append((component, optionData))
    return deserialised

def deserialiseComponents(
        weapon: gunsmith.Weapon,
        componentData: typing.Mapping[str, typing.Any]
        ) -> typing.Mapping[str, typing.Any]:
    sequenceDataList: typing.Iterable[typing.Mapping[str, typing.Any]] = componentData.get('sequences')
    if sequenceDataList == None:
        raise RuntimeError('Component data is missing the sequences element')

    commonDataList = componentData.get('common')
    if commonDataList == None:
        raise RuntimeError('Component data is missing the common element')

    componentClasses = common.getSubclasses(
        classType=gunsmith.WeaponComponentInterface,
        topLevelOnly=True)
    componentTypeMap = {}
    for componentClass in componentClasses:
        componentTypeMap[componentClass.__name__] = componentClass

    # Create each of the sequences and generate a per sequence lists of components and their options.
    # Options aren't applied to the component until after its been added to the weapon
    sequenceComponentMap: typing.Dict[
        str,
        typing.List[typing.Tuple[
            gunsmith.WeaponComponentInterface,
            typing.Optional[typing.Iterable[typing.Mapping[str, typing.Any]]]
            ]]] = {}
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
            regenerate=False) # Hold off regenerating until we start adding components

        sequenceComponentMap[sequence] = deserialiseComponentList(
            weapon=weapon,
            components=componentDataList,
            componentTypeMap=componentTypeMap)

    # Create a list of common components and their options.
    commonComponents = deserialiseComponentList(
        weapon=weapon,
        components=commonDataList,
        componentTypeMap=componentTypeMap)

    # Iterate over all the weapon stages in construction order adding the components
    # for that stage, applying options to the component as we go. This works on the
    # assumption the weapon always returns stages in construction order
    for stage in weapon.stages():
        sequence = stage.sequence()
        if sequence:
            # This is a sequence specific stage so check the components for that sequence
            componentList = sequenceComponentMap.get(sequence)
        else:
            # This is a common stage so check the common components
            componentList = commonComponents
        assert(componentList != None)

        # Iterate over the relevant components to see if they match this stage. A copy of the list
        # is used so that component that match can be removed to avoid them being re-checked in the
        # future
        for component, optionData in list(componentList):
            if stage.matchesComponent(component=component):
                # Add the component to the weapon, regenerating the weapon as each component
                # is added so compatibility can be checked when further components are added
                componentList.remove((component, optionData))

                try:
                    weapon.addComponent(
                        stage=stage,
                        component=component,
                        regenerate=True)
                except gunsmith.CompatibilityException:
                    logging.warning(f'Ignoring incompatible component type \'{type(component).__name__}\' when loading weapon \'{weapon.weaponName()}\'')
                    continue

                if optionData:
                    deserialiseOptions(
                        weapon=weapon,
                        component=component,
                        dataList=optionData)

    for sequence, components in sequenceComponentMap.items():
        for component, _ in components:
            logging.warning(f'Ignoring unmatched component type \'{type(component).__name__}\' when loading weapon \'{weapon.weaponName()}\' sequence {sequence}')

    for component, _ in commonComponents:
        logging.warning(f'Ignoring unmatched component type \'{type(component).__name__}\' when loading weapon \'{weapon.weaponName()}\' common components')

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
