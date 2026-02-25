import typing

def validateMandatoryBool(
        name: str,
        value: bool,
        validationFn: typing.Optional[typing.Callable[[str, bool], typing.Any]] = None
        ) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f'{name} must be an bool')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateOptionalBool(
        name: str,
        value: typing.Optional[bool],
        validationFn: typing.Optional[typing.Callable[[str, typing.Optional[bool]], typing.Any]] = None
        ) -> typing.Optional[bool]:
    if value is not None and not isinstance(value, bool):
        raise TypeError(f'{name} must be an bool or None')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateMandatoryInt(
        name: str,
        value: int,
        min: typing.Optional[int] = None,
        max: typing.Optional[int] = None,
        allowed: typing.Optional[typing.Collection[int]] = None,
        validationFn: typing.Optional[typing.Callable[[str, int], typing.Any]] = None
        ) -> int:
    if not isinstance(value, int):
        raise TypeError(f'{name} must be an int')

    if min is not None and max is not None and (value < min or value > max):
        raise ValueError(f'{name} must be in the range {min} to {max}')
    elif min is not None and value < min:
        raise ValueError(f'{name} must be >= {min}')
    elif max is not None and value > max:
        raise ValueError(f'{name} must be <= {max}')

    if allowed is not None and value not in allowed:
        raise ValueError(f'{name} must be one of [{",".join(allowed)}]')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateOptionalInt(
        name: str,
        value: typing.Optional[int],
        min: typing.Optional[int] = None,
        max: typing.Optional[int] = None,
        allowed: typing.Optional[typing.Collection[int]] = None,
        validationFn: typing.Optional[typing.Callable[[str, typing.Optional[int]], typing.Any]] = None
        ) -> typing.Optional[int]:
    if value is not None:
        if not isinstance(value, int):
            raise TypeError(f'{name} must be an int or None')

        if min is not None and max is not None and (value < min or value > max):
            raise ValueError(f'{name} must be in the range {min} to {max} or None')
        elif min is not None and value < min:
            raise ValueError(f'{name} must be >= {min} or None')
        elif max is not None and value > max:
            raise ValueError(f'{name} must be <= {max} or None')

        if allowed is not None and value not in allowed:
            raise ValueError(f'{name} must be one of [{",".join(allowed)}] or None')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateMandatoryFloat(
        name: str,
        value: typing.Union[int, float],
        min: typing.Optional[typing.Union[int, float]] = None,
        max: typing.Optional[typing.Union[int, float]] = None,
        allowed: typing.Optional[typing.Collection[typing.Union[int, float]]] = None,
        validationFn: typing.Optional[typing.Callable[[str, typing.Union[int, float]], typing.Any]] = None
        ) -> typing.Union[int, float]:
    if not isinstance(value, (int, float)):
        raise TypeError(f'{name} must be an int or float')

    if min is not None and max is not None and (value < min or value > max):
        raise ValueError(f'{name} must be in the range {min} to {max}')
    elif min is not None and value < min:
        raise ValueError(f'{name} must be >= {min}')
    elif max is not None and value > max:
        raise ValueError(f'{name} must be <= {max}')

    if allowed is not None and value not in allowed:
        raise ValueError(f'{name} must be one of [{",".join(allowed)}]')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateOptionalFloat(
        name: str,
        value: typing.Optional[typing.Union[int, float]],
        min: typing.Optional[typing.Union[int, float]] = None,
        max: typing.Optional[typing.Union[int, float]] = None,
        allowed: typing.Optional[typing.Collection[typing.Union[int, float]]] = None,
        validationFn: typing.Optional[typing.Callable[[str, typing.Optional[typing.Union[int, float]]], typing.Any]] = None
        ) -> typing.Optional[typing.Union[int, float]]:
    if value is not None:
        if not isinstance(value, (int, float)):
            raise TypeError(f'{name} must be an int, float or None')

        if min is not None and max is not None and (value < min or value > max):
            raise ValueError(f'{name} must be in the range {min} to {max} or None')
        elif min is not None and value < min:
            raise ValueError(f'{name} must be >= {min} or None')
        elif max is not None and value > max:
            raise ValueError(f'{name} must be <= {max} or None')

        if allowed is not None and value not in allowed:
            raise ValueError(f'{name} must be one of [{",".join(allowed)}] or None')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateMandatoryStr(
        name: str,
        value: str,
        allowed: typing.Optional[typing.Collection[str]] = None,
        allowEmpty = True,
        validationFn: typing.Optional[typing.Callable[[str, str], typing.Any]] = None
        ) -> str:
    if not isinstance(value, str):
        raise TypeError(f'{name} must be an str')

    if not allowEmpty and not len(value):
        raise ValueError(f'{name} can\'t be empty')

    if allowed is not None and value not in allowed:
        raise ValueError(f'{name} must be one of [{",".join(allowed)}]')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateOptionalStr(
        name: str,
        value: typing.Optional[str],
        allowed: typing.Optional[typing.Collection[str]] = None,
        allowEmpty = True,
        validationFn: typing.Optional[typing.Callable[[str, typing.Optional[str]], typing.Any]] = None
        ) -> typing.Optional[str]:
    if value is not None:
        if not isinstance(value, str):
            raise TypeError(f'{name} must be an str or None')

        if not allowEmpty and not len(value):
            raise ValueError(f'{name} can\'t be empty or must be None')

        if allowed is not None and value not in allowed:
            raise ValueError(f'{name} must be one of [{",".join(allowed)}] or None')

    if validationFn is not None:
        validationFn(name, value)

    return value

T = typing.TypeVar("T")
def validateMandatoryObject(
        name: str,
        value: T,
        type: typing.Union[typing.Type[T], typing.Tuple[typing.Type[T], ...]],
        validationFn: typing.Optional[typing.Callable[[str, T], typing.Any]] = None
        ) -> T:
    if not isinstance(value, type):
        raise TypeError(f"{name} must be of type {type}")

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateOptionalObject(
        name: str,
        value: typing.Optional[T],
        type: typing.Union[typing.Type[T], typing.Tuple[typing.Type[T], ...]],
        validationFn: typing.Optional[typing.Callable[[str, typing.Optional[T]], typing.Any]] = None
        ) -> typing.Optional[T]:
    if value is not None and not isinstance(value, type):
        raise TypeError(f'{name} must be of type {type} or None')

    if validationFn is not None:
        validationFn(name, value)

    return value

def validateMandatoryCollection(
        name: str,
        value: typing.Collection[T],
        type: typing.Optional[typing.Union[typing.Type[T], typing.Tuple[typing.Type[T], ...]]] = None,
        allowEmpty: bool = True,
        allowNone: bool = False,
        validationFn: typing.Optional[typing.Callable[[str, typing.Optional[T]], typing.Any]] = None
        ) -> typing.Collection[T]:
    if not allowEmpty and not len(value):
        raise ValueError(f'{name} can\'t be empty')

    for obj in value:
        if obj is not None:
            if type is not None and not isinstance(obj, type):
                raise TypeError(f'{name} must contain objects of type {type}')
        elif not allowNone:
            raise ValueError(f'{name} can\'t contain None')

        if validationFn is not None:
            validationFn(name, obj)

    return value

def validateOptionalCollection(
        name: str,
        value: typing.Optional[typing.Collection[T]],
        type: typing.Optional[typing.Union[typing.Type[T], typing.Tuple[typing.Type[T], ...]]] = None,
        allowEmpty: bool = True,
        allowNone: bool = False,
        validationFn: typing.Optional[typing.Callable[[str, typing.Optional[T]], typing.Any]] = None
        ) -> typing.Optional[typing.Collection[T]]:
    if value is None:
        return value

    if not allowEmpty and not len(value):
        raise ValueError(f'{name} can\'t be empty or must be None')

    for obj in value:
        if obj is not None:
            if type is not None and not isinstance(obj, type):
                raise TypeError(f'{name} must contain objects of type {type} or be None')
        elif not allowNone:
            raise ValueError(f'{name} can\'t contain None')

        if validationFn is not None:
            validationFn(name, obj)

    return value