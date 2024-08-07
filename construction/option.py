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
            choices: typing.Optional[typing.Iterable[str]] = None,
            isEditable: bool = True,
            isOptional: bool = False,
            description: str = '',
            enabled: bool = True
            ) -> None:
        if value == None and not isOptional:
            if isEditable:
                value = ''
            elif choices:
                value = choices[0]

        super().__init__(
            id=id,
            name=name,
            value=value,
            description=description,
            enabled=enabled)
        self._choices = list(choices) if choices != None else []
        self._isEditable = isEditable
        self._isOptional = isOptional
        self._checkAndUpdateValue(value=self._value)

    def setValue(
            self,
            value: typing.Optional[str]
            ) -> None:
        self._checkAndUpdateValue(value=value)

    def choices(self) -> typing.Iterable[str]:
        return self._choices

    def setChoices(
            self,
            choices: typing.Iterable[str] = None
            ) -> None:
        self._choices = list(choices) if choices != None else []
        if self._isEditable:
            return # Nothing more to check

        if self._isOptional:
            if (self._value != None) and (self._value not in choices):
                self._value = None
        else:
            if self._value not in self._choices:
                self._value = self._choices[0] if len(self._choices) > 0 else None

    def isEditable(self) -> bool:
        return self._isEditable

    def setEditable(
            self,
            editable: bool
            ) -> None:
        self._isEditable = editable
        if self._value != None and not self._isEditable and self._value not in self._choices:
            self._value = self._choices[0] if len(self._choices) > 0 else None

    def isOptional(self) -> bool:
        return self._isOptional

    def setOptional(self, optional: bool) -> None:
        self._isOptional = optional
        if not self._isOptional and self._value == None:
            if self._isEditable:
                self._value = ''
            elif self._choices:
                self._value = self._choices[0]

    def _checkAndUpdateValue(
            self,
            value: typing.Optional[str]
            ) -> None:
        if value == None and not self._isOptional:
            raise ValueError(f'The value can\'t be None')

        if value != None and not self._isEditable and value not in self._choices:
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
        self._minValue = min(minValue, maxValue) if minValue != None and maxValue != None else minValue
        self._maxValue = max(maxValue, minValue) if minValue != None and maxValue != None else maxValue
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

    def setOptional(self, isOptional: bool) -> None:
        self._isOptional = isOptional
        if not self._isOptional and self._value == None:
            self._value = 0
            if self._minValue != None and self._value < self._minValue:
                self._value = self._minValue
            if self._maxValue != None and self._value > self._maxValue:
                self._value = self._maxValue

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
        self._minValue = min(minValue, maxValue) if minValue != None and maxValue != None else minValue
        self._maxValue = max(maxValue, minValue) if minValue != None and maxValue != None else maxValue
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

    def setOptional(self, isOptional: bool) -> None:
        self._isOptional = isOptional
        if not self._isOptional and self._value == None:
            self._value = 0
            if self._minValue != None and self._value < self._minValue:
                self._value = self._minValue
            if self._maxValue != None and self._value > self._maxValue:
                self._value = self._maxValue

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
            choices: typing.Iterable[enum.Enum] = None,
            isOptional: bool = False,
            description: str = '',
            enabled: bool = True
            ) -> None:
        choices = list(choices) if choices != None else [e for e in type]
        if value == None and not isOptional and choices:
            value = choices[0]

        super().__init__(
            id=id,
            name=name,
            value=value,
            description=description,
            enabled=enabled)
        self._type = type
        self._choices = choices
        self._isOptional = isOptional
        self._checkAndUpdateValue(value=self._value)

    def type(self) -> typing.Type[enum.Enum]:
        return self._type

    def setValue(
            self,
            value: typing.Optional[enum.Enum]
            ) -> None:
        self._checkAndUpdateValue(value=value)

    def choices(self) -> typing.Iterable[enum.Enum]:
        return self._choices

    def setChoices(
            self,
            choices: typing.Iterable[enum.Enum] = None
            ) -> None:
        self._choices = list(choices) if choices != None else [e for e in self._type]
        if self._isOptional:
            if (self._value != None) and (self._value not in choices):
                self._value = None
        else:
            if self._value not in choices:
                self._value = choices[0] if len(choices) > 0 else None

    def isOptional(self) -> bool:
        return self._isOptional

    def setOptional(self, isOptional: bool) -> None:
        self._isOptional = isOptional
        if not self._isOptional and self._value == None:
            options = self._choices if self._choices != None else [e for e in self._type]
            if options:
                self._value = options[0]

    def _checkAndUpdateValue(
            self,
            value: typing.Optional[enum.Enum]
            ) -> None:
        if value == None and not self._isOptional:
            raise ValueError(f'The value can\'t be None')

        if value != None and value not in self._choices:
            raise ValueError(f'The value {value} is not a valid option')

        self._value = value

class MultiSelectOption(ComponentOption):
    def __init__(
            self,
            id: str,
            name: str,
            choices: typing.Iterable[str],
            value: typing.Optional[typing.Iterable[str]] = None,
            unselectable: typing.Optional[typing.Iterable[str]] = None,
            description: str = '',
            enabled: bool = True
            ) -> None:
        super().__init__(
            id=id,
            name=name,
            value=list(value) if value else [],
            description=description,
            enabled=enabled)
        self._choices = list(choices)
        self._unselectable = list(unselectable) if unselectable else []
        self._checkAndUpdateValue(value=self._value)

    def setValue(
            self,
            value: typing.Iterable[str]
            ) -> None:
        self._checkAndUpdateValue(value=value)

    def choices(self) -> typing.Iterable[str]:
        return self._choices

    def setChoices(
            self,
            choices: typing.Iterable[str]
            ) -> None:
        self._choices = list(choices)

        for item in list(self._value):
            if item not in self._choices:
                self._value.remove(item)

    def unselectable(self) -> typing.Iterable[str]:
        return self._unselectable

    def setUnselectable(
            self,
            unselectable: typing.Optional[typing.Iterable[str]]
            ) -> None:
        if not unselectable:
            self._unselectable.clear()
            return

        self._unselectable = list(unselectable)
        for selected in list(self._value):
            if selected in self._unselectable:
                self._value.remove(selected)

    def _checkAndUpdateValue(
            self,
            value: typing.Iterable[str]
            ) -> None:
        for item in value:
            if item not in self._choices:
                raise ValueError(f'The value {value} is not a valid selection for')

        self._value = list(value)
