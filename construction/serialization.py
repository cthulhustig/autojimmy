import construction
import enum
import typing

def serialiseOptions(
        component: construction.ComponentInterface
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
            assert(value == None or isinstance(value, str))
            options.append({
                'id': option.id(),
                'value': value
            })            
        elif isinstance(option, construction.IntegerOption):
            assert(value == None or isinstance(value, int))
            options.append({
                'id': option.id(),
                'value': value
            })
        elif isinstance(option, construction.FloatOption):
            assert(value == None or isinstance(value, float) or isinstance(value, int))
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
            assert(value == None or isinstance(value, list))
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
        components: typing.Iterable[construction.ComponentInterface]
        ) -> typing.Iterable[typing.Mapping[str, typing.Any]]:
    serialised = []
    for component in components:
        serialised.append({
            'type': type(component).__name__,
            'options': serialiseOptions(component=component)
        })
    return serialised

def deserialiseComponentList(
    components: typing.Iterable[typing.Mapping[str, typing.Any]]
    ) -> typing.List[typing.Tuple[ # List of components
        str, # Component type
        typing.Optional[typing.Mapping[ # Options for this component
            str, # Option ID
            typing.Any # Option value
            ]]
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