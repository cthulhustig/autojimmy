import typing

def validateBool(
        name: str,
        value: typing.Optional[bool],
        allowNone: bool = False,
        validationFn: typing.Optional[typing.Callable[[str, bool], typing.Any]] = None
        ) -> typing.Optional[bool]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None:
        if not isinstance(value, bool):
            raise TypeError(f'{name} must be an bool')

        if validationFn is not None:
            validationFn(name, value)

    return value

def validateInt(
        name: str,
        value: typing.Optional[int],
        min: typing.Optional[int] = None,
        max: typing.Optional[int] = None,
        allowNone: bool = False,
        allowedValues: typing.Optional[typing.Collection[int]] = None,
        validationFn: typing.Optional[typing.Callable[[str, int], typing.Any]] = None
        ) -> typing.Optional[int]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None:
        if not isinstance(value, int):
            raise TypeError(f'{name} must be an int')

        if min is not None and max is not None and (value < min or value > max):
            raise ValueError(f'{name} must be in the range {min} to {max}')
        elif min is not None and value < min:
            raise ValueError(f'{name} must be >= {min}')
        elif max is not None and value > max:
            raise ValueError(f'{name} must be <= {max}')

        if allowedValues is not None and value not in allowedValues:
            raise ValueError(f'{name} must be one of [{",".join(allowedValues)}]')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateFloat(
        name: str,
        value: typing.Optional[typing.Union[int, float]],
        min: typing.Optional[typing.Union[int, float]] = None,
        max: typing.Optional[typing.Union[int, float]] = None,
        allowNone: bool = False,
        allowedValues: typing.Optional[typing.Collection[typing.Union[int, float]]] = None,
        validationFn: typing.Optional[typing.Callable[[str, typing.Optional[typing.Union[int, float]]], typing.Any]] = None
        ) -> typing.Optional[typing.Union[int, float]]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None:
        if not isinstance(value, (int, float)):
            raise TypeError(f'{name} must be an int or float')

        if min is not None and max is not None and (value < min or value > max):
            raise ValueError(f'{name} must be in the range {min} to {max}')
        elif min is not None and value < min:
            raise ValueError(f'{name} must be >= {min}')
        elif max is not None and value > max:
            raise ValueError(f'{name} must be <= {max}')

        if allowedValues is not None and value not in allowedValues:
            raise ValueError(f'{name} must be one of [{",".join(allowedValues)}]')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateStr(
        name: str,
        value: typing.Optional[str],
        allowNone: bool = False,
        allowEmpty: bool = True,
        allowedValues: typing.Optional[typing.Collection[str]] = None,
        validationFn: typing.Optional[typing.Callable[[str, str], typing.Any]] = None
        ) -> typing.Optional[str]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None:
        if not isinstance(value, str):
            raise TypeError(f'{name} must be an str')

        if not allowEmpty and not len(value):
            raise ValueError(f'{name} can\'t be empty')

        if allowedValues is not None and value not in allowedValues:
            raise ValueError(f'{name} must be one of [{",".join(allowedValues)}]')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateBytes(
        name: str,
        value: typing.Optional[bytes],
        allowNone: bool = False,
        allowEmpty: bool = True,
        validationFn: typing.Optional[typing.Callable[[str, bytes], typing.Any]] = None
        ) -> typing.Optional[str]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None:
        if not isinstance(value, bytes):
            raise TypeError(f'{name} must be a bytes')

        if not allowEmpty and not len(value):
            raise ValueError(f'{name} can\'t be empty')

    if validationFn is not None:
        validationFn(name, value)

    return value

T = typing.TypeVar("T")
def validateObject(
        name: str,
        value: typing.Optional[T],
        objectType: typing.Union[typing.Type[T], typing.Tuple[typing.Type[T], ...]],
        allowNone: bool = False,
        validationFn: typing.Optional[typing.Callable[[str, typing.Optional[T]], typing.Any]] = None
        ) -> typing.Optional[T]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None and not isinstance(value, objectType):
        raise TypeError(f"{name} must be of type {objectType}")

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateCollection(
        name: str,
        value: typing.Optional[typing.Collection[T]],
        elementType: typing.Optional[typing.Union[typing.Type[T], typing.Tuple[typing.Type[T], ...]]] = None,
        allowNone: bool = False,
        allowEmpty: bool = True,
        validationFn: typing.Optional[typing.Callable[[str, int, typing.Optional[T]], typing.Any]] = None
        ) -> typing.Optional[typing.Collection[T]]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None:
        if not allowEmpty and not len(value):
            raise ValueError(f'{name} can\'t be empty')

        for index, obj in enumerate(value):
            if elementType is not None and not isinstance(obj, elementType):
                raise TypeError(f'{name}[{index}] must be an object of type {elementType}')

            if validationFn is not None:
                validationFn(name, index, obj)

    return value

def validateSequence(
        name: str,
        value: typing.Optional[typing.Sequence[T]],
        elementType: typing.Optional[typing.Union[typing.Type[T], typing.Tuple[typing.Type[T], ...]]] = None,
        allowNone: bool = False,
        allowEmpty: bool = True,
        validationFn: typing.Optional[typing.Callable[[str, int, typing.Optional[T]], typing.Any]] = None
        ) -> typing.Optional[typing.Sequence[T]]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None:
        if not allowEmpty and not len(value):
            raise ValueError(f'{name} can\'t be empty')

        for index in range(len(value)):
            try:
                obj = value[index]
            except Exception:
                raise TypeError(f'{name} must be a sequence of {elementType} elements')

            if elementType is not None and not isinstance(obj, elementType):
                raise TypeError(f'{name}[{index}] must be an object of type {elementType}')

            if validationFn is not None:
                validationFn(name, index, obj)

    return value

K = typing.TypeVar("K")
V = typing.TypeVar("V")
def validateMapping(
        name: str,
        value: typing.Optional[typing.Mapping[K, V]],
        keyType: typing.Optional[typing.Union[typing.Type[K], typing.Tuple[typing.Type[K], ...]]] = None,
        valueType: typing.Optional[typing.Union[typing.Type[V], typing.Tuple[typing.Type[V], ...]]] = None,
        allowNone: bool = False,
        allowEmpty: bool = True,
        validationFn: typing.Optional[typing.Callable[[str, K, V], typing.Any]] = None
        ) -> typing.Optional[typing.Mapping[K, V]]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None:
        if not allowEmpty and not len(value):
            raise ValueError(f'{name} can\'t be empty')

        for k, v in value.items():
            if keyType is not None and not isinstance(k, keyType):
                raise TypeError(f'{name} keys must be objects of type {keyType}')
            if valueType is not None and not isinstance(v, valueType):
                raise TypeError(f'{name} values must be objects of type {valueType}')

            if validationFn is not None:
                validationFn(name, k, v)

    return value

def validateStrCollection(
        name: str,
        value: typing.Optional[typing.Collection[str]],
        allowNone: bool = False,
        allowEmpty: bool = True,
        allowNoneValues: bool = False,
        allowEmptyValues: bool = True,
        allowedValues: typing.Optional[typing.Collection[str]] = None,
        validationFn: typing.Optional[typing.Callable[[str, int, typing.Optional[str]], typing.Any]] = None
        ) -> typing.Optional[typing.Collection[str]]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None:
        if not allowEmpty and not len(value):
            raise ValueError(f'{name} can\'t be empty')

        for index, element in enumerate(value):
            if not allowNoneValues and element is None:
                raise TypeError(f'{name}[{index}] can\'t be None')

            if element is not None:
                if not isinstance(element, str):
                    raise TypeError(f'{name}[{index}] must be an object of type str')

                if not allowEmptyValues and not len(element):
                    raise ValueError(f'{name}[{index}] can\'t be empty')

                if allowedValues is not None and element not in allowedValues:
                    raise ValueError(f'{name}[{index}] must be one of [{",".join(allowedValues)}]')

            if validationFn is not None:
                validationFn(name, index, element)

    return value

def validateStrMapping(
        name: str,
        value: typing.Optional[typing.Mapping[str, str]],
        allowNone: bool = False,
        allowEmpty: bool = True,
        allowNoneKeys: bool = False,
        allowEmptyKeys: bool = True,
        allowNoneValues: bool = False,
        allowEmptyValues: bool = True,
        validationFn: typing.Optional[typing.Callable[[str, str, str], typing.Any]] = None
        ) -> typing.Optional[typing.Mapping[str, str]]:
    if not allowNone and value is None:
        raise ValueError(f'{name} can\'t be None')

    if value is not None:
        if not allowEmpty and not len(value):
            raise ValueError(f'{name} can\'t be empty')

        for k, v in value.items():
            if not allowNoneKeys and k is None:
                raise TypeError(f'{name} values can\'t be None')

            if k is not None:
                if not isinstance(k, str):
                    raise TypeError(f'{name} keys must be objects of type str')

                if not allowEmptyKeys and not len(k):
                    raise TypeError(f'{name} keys can\'t be empty')

            if not allowNoneValues and v is None:
                raise TypeError(f'{name} values can\'t be None')

            if v is not None:
                if not isinstance(v, str):
                    raise TypeError(f'{name} values must be objects of type str')

                if not allowEmptyValues and not len(v):
                    raise TypeError(f'{name} values can\'t be empty')

            if validationFn is not None:
                validationFn(name, k, v)

    return value