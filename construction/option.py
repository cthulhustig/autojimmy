import enum
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

class BooleanOption(ComponentOption):
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

    def setValue(
            self,
            value: bool
            ) -> None:
        self._value = value

class StringOption(ComponentOption):
    def __init__(
            self,
            id: str,
            name: str,
            value: typing.Optional[str] = None,
            options: typing.Optional[typing.Iterable[str]] = None,
            isEditable: bool = True,
            isOptional: bool = False,
            description: str = '',
            enabled: bool = True
            ) -> None:
        if value == None and not isOptional:
            if isEditable:
                value = ''
            elif options:
                value = options[0]

        super().__init__(
            id=id,
            name=name,
            value=value,
            description=description,
            enabled=enabled)
        self._options = list(options) if options != None else []
        self._isEditable = isEditable
        self._isOptional = isOptional
        self._checkAndUpdateValue(value=self._value)        

    def setValue(
            self,
            value: typing.Optional[str]
            ) -> None:
        self._checkAndUpdateValue(value=value)   

    def options(self) -> typing.Iterable[str]:
        return self._options

    def setOptions(
            self,
            options: typing.Iterable[str] = None
            ) -> None:
        self._options = list(options) if options != None else []
        if self._isEditable:
            return # Nothing more to check
        
        if self._isOptional:
            if (self._value != None) and (self._value not in options):
                self._value = None
        else:
            if self._value not in options:
                self._value = options[0] if len(options) > 0 else None

    def isEditable(self) -> bool:
        return self._isEditable
    
    def setIsEditable(self) -> None:
        self._isEditable = False

    def isOptional(self) -> bool:
        return self._isOptional

    def _checkAndUpdateValue(
            self,
            value: typing.Optional[str]
            ) -> None:
        if value == None and not self._isOptional:
            raise ValueError(f'The value can\'t be None')

        if value != None and not self._isEditable and value not in self._options:
            raise ValueError(f'The value {value} is not a valid option')

        self._value = value

class IntegerOption(ComponentOption):
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

    def _checkAndUpdateValue(
            self,
            value: typing.Optional[int]
            ) -> None:
        if value == None and not self._isOptional:
            raise ValueError(f'The value can\'t be None')

        if value != None:
            if self._minValue != None and value < self._minValue:
                raise ValueError(
                    f'The value {value} is not greater than or equal to {self._minValue}')

            if self._maxValue != None and value > self._maxValue:
                raise ValueError(
                    f'The value {value} is not less than or equal to {self._maxValue}')

        self._value = value

class FloatOption(ComponentOption):
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

    def _checkAndUpdateValue(
            self,
            value: typing.Optional[float]
            ) -> None:
        if value == None and not self._isOptional:
            raise ValueError(f'The specified value can\'t be None')

        if value != None:
            if self._minValue != None and value < self._minValue:
                raise ValueError(
                    f'The value {value} is not less than or equal to {self._minValue}')

            if self._maxValue != None and value > self._maxValue:
                raise ValueError(
                    f'The value {value} is not greater than or equal to {self._maxValue}')

        self._value = value

class EnumOption(ComponentOption):
    def __init__(
            self,
            id: str,
            name: str,
            type: typing.Type[enum.Enum],
            value: typing.Optional[enum.Enum] = None,
            options: typing.Iterable[enum.Enum] = None,
            isOptional: bool = False,
            description: str = '',
            enabled: bool = True
            ) -> None:
        options = list(options) if options != None else [e for e in type]
        if value == None and not isOptional and options:
            value = options[0]

        super().__init__(
            id=id,
            name=name,
            value=value,
            description=description,
            enabled=enabled)
        self._type = type
        self._options = options
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

    def _checkAndUpdateValue(
            self,
            value: typing.Optional[enum.Enum]
            ) -> None:
        if value == None and not self._isOptional:
            raise ValueError(f'The value can\'t be None')

        if value != None and value not in self._options:
            raise ValueError(f'The value {value} is not a valid option')

        self._value = value
