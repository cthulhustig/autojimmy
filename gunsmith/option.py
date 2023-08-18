import enum
import gunsmith
import typing

class ComponentOption(object):
    def __init__(
            self,
            id: str,
            name: str,
            value: typing.Any,
            description: str = '',
            enabled: bool = True
            ) -> None:
        self._id = id
        self._name = name
        self._value = value
        self._description = description
        self._enabled = enabled

    def id(self) -> str:
        return self._id

    def name(self) -> str:
        return self._name

    def value(self) -> typing.Any:
        return self._value

    def description(self) -> str:
        return self._description

    def isEnabled(self) -> bool:
        return self._enabled

    def setEnabled(
            self,
            enabled: bool
            ) -> None:
        self._enabled = enabled

    def reset(self) -> None:
        raise RuntimeError('The reset method must be implemented by classes derived from ComponentOption')

class BooleanComponentOption(ComponentOption):
    def __init__(
            self,
            id: str,
            name: str,
            value: bool,
            description: str = '',
            enabled: bool = True
            ) -> None:
        super().__init__(
            id=id,
            name=name,
            value=value,
            description=description,
            enabled=enabled)
        self._default = value

    def setValue(
            self,
            value: bool
            ) -> None:
        self._value = value

    def setDefault(
            self,
            default: bool
            ) -> None:
        self._default = default

    def reset(self) -> None:
        self._value = self._default

class StringComponentOption(ComponentOption):
    def __init__(
            self,
            id: str,
            name: str,
            value: str,
            description: str = '',
            enabled: bool = True
            ) -> None:
        super().__init__(
            id=id,
            name=name,
            value=value,
            description=description,
            enabled=enabled)
        self._default = value

    def setValue(
            self,
            value: str,
            ) -> None:
        self._value = value

    def setDefault(
            self,
            default: str
            ) -> None:
        self._default = default

    def reset(self) -> None:
        self._value = self._default

class IntegerComponentOption(ComponentOption):
    def __init__(
            self,
            id: str,
            name: str,
            value: int,
            minValue: typing.Optional[int] = None,
            maxValue: typing.Optional[int] = None,
            isOptional: bool = False,
            description: str = '',
            enabled: bool = True
            ) -> None:
        super().__init__(
            id=id,
            name=name,
            value=value,
            description=description,
            enabled=enabled)
        self._default = value
        self._minValue = minValue
        self._maxValue = maxValue
        self._isOptional = isOptional
        self._checkAndUpdateValue(value=self._value)

    def setValue(
            self,
            value: typing.Optional[int],
            ) -> None:
        self._checkAndUpdateValue(value=value)

    def min(self) -> typing.Optional[int]:
        return self._minValue

    def setMin(self, value: typing.Optional[int]) -> None:
        self._minValue = value
        if self._minValue == None:
            return # Nothing more to do
        if self._value != None and self._value < self._minValue:
            self._value = self._minValue
        if self._maxValue != None and self._maxValue < self._minValue:
            self._maxValue = self._minValue

    def max(self) -> typing.Optional[int]:
        return self._maxValue

    def setMax(self, value: typing.Optional[int]) -> None:
        self._maxValue = value
        if self._maxValue == None:
            return # Nothing more to do
        if self._value != None and self._value > self._maxValue:
            self._value = self._maxValue
        if self._minValue != None and self._minValue > self._maxValue:
            self._minValue = self._maxValue

    def isOptional(self) -> bool:
        return self._isOptional

    def setDefault(
            self,
            default: typing.Optional[int]
            ) -> None:
        self._default = default

    def reset(self) -> None:
        self._value = self._default

    def _checkAndUpdateValue(
            self,
            value: typing.Optional[int]
            ) -> None:
        if value == None and not self._isOptional:
            raise ValueError(f'The specified value can\'t be None')

        if self._minValue != None and value < self._minValue:
            raise ValueError(f'The specified value must be greater than or equal to {self._minValue}')

        if self._maxValue != None and value > self._maxValue:
            raise ValueError(f'The specified value must be less than or equal to {self._maxValue}')

        self._value = value

class FloatComponentOption(ComponentOption):
    def __init__(
            self,
            id: str,
            name: str,
            value: typing.Optional[float] = None,
            minValue: typing.Optional[float] = None,
            maxValue: typing.Optional[float] = None,
            isOptional: bool = False,
            description: str = '',
            enabled: bool = True
            ) -> None:
        super().__init__(
            id=id,
            name=name,
            value=value,
            description=description,
            enabled=enabled)
        self._default = value
        self._minValue = minValue
        self._maxValue = maxValue
        self._isOptional = isOptional
        self._checkAndUpdateValue(value=self._value)

    def setValue(
            self,
            value: float
            ) -> None:
        self._checkAndUpdateValue(value=value)

    def min(self) -> typing.Optional[float]:
        return self._minValue

    def setMin(self, value: typing.Optional[int]) -> None:
        self._minValue = value
        if self._minValue == None:
            return # Nothing more to do
        if self._value != None and self._value < self._minValue:
            self._value = self._minValue
        if self._maxValue != None and self._maxValue < self._minValue:
            self._maxValue = self._minValue

    def max(self) -> typing.Optional[float]:
        return self._maxValue

    def setMax(self, value: typing.Optional[int]) -> None:
        self._maxValue = value
        if self._maxValue == None:
            return # Nothing more to do
        if self._value != None and self._value > self._maxValue:
            self._value = self._maxValue
        if self._minValue != None and self._minValue > self._maxValue:
            self._minValue = self._maxValue

    def isOptional(self) -> bool:
        return self._isOptional

    def setDefault(
            self,
            default: typing.Optional[float]
            ) -> None:
        self._default = default

    def reset(self) -> None:
        self._value = self._default

    def _checkAndUpdateValue(
            self,
            value: typing.Optional[float]
            ) -> None:
        if value == None and not self._isOptional:
            raise ValueError(f'The specified value can\'t be None')

        if self._minValue != None and value < self._minValue:
            raise ValueError(f'The specified value must be less than or equal to {self._minValue}')

        if self._maxValue != None and value > self._maxValue:
            raise ValueError(f'The specified value must be greater than or equal to {self._maxValue}')

        self._value = value

class EnumComponentOption(ComponentOption):
    def __init__(
            self,
            id: str,
            name: str,
            type: typing.Type[enum.Enum],
            value: enum.Enum,
            options: typing.Iterable[enum.Enum] = None,
            isOptional: bool = False,
            description: str = '',
            enabled: bool = True
            ) -> None:
        super().__init__(
            id=id,
            name=name,
            value=value,
            description=description,
            enabled=enabled)
        self._default = value
        self._type = type
        self._options = list(options) if options != None else [e for e in self._type]
        self._isOptional = isOptional
        self._checkAndUpdateValue(value=self._value)

    def type(self) -> typing.Type[enum.Enum]:
        return self._type

    def setValue(
            self,
            value: typing.Optional[enum.Enum]
            ) -> None:
        self._checkAndUpdateValue(value=value)

    def options(self) -> typing.Iterable[enum.Enum]:
        return self._options

    def setOptions(
            self,
            options: typing.Iterable[enum.Enum] = None
            ) -> None:
        self._options = list(options) if options != None else [e for e in self._type]
        if self._isOptional:
            if (self._value != None) and (self._value not in options):
                self._value = None
        else:
            if self._value not in options:
                self._value = options[0] if len(options) > 0 else None

    def isOptional(self) -> bool:
        return self._isOptional

    def setDefault(
            self,
            default: typing.Type[enum.Enum]
            ) -> None:
        self._default = default

    def reset(self) -> None:
        self._value = self._default

    def _checkAndUpdateValue(
            self,
            value: typing.Type[enum.Enum]
            ) -> None:
        if value == None and not self._isOptional:
            raise ValueError(f'The specified value can\'t be None')

        if value != None and value not in self._options:
            raise ValueError(f'The specified value is not a valid option')

        self._value = value
