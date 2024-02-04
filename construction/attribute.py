import common
import construction
import enum
import typing

# Construction implementations should create an enum derived from this class
# with entries for each of the attributes that can be used during construction.
# The value of the entry should be the human readable name of the attribute to
# be displayed to the user
class ConstructionAttributeId(enum.Enum):
    pass

class AttributeInterface(object):
    def __init__(self) -> None:
        pass

    def id(self) -> ConstructionAttributeId:
        raise RuntimeError('The attribute method must be implemented by classes derived from AttributeInterface')

    def name(self) -> str:
        raise RuntimeError('The name method must be implemented by classes derived from AttributeInterface')

    def value(self) -> typing.Any:
        raise RuntimeError('The value method must be implemented by classes derived from AttributeInterface')

    def calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        raise RuntimeError('The calculations method must be implemented by classes derived from AttributeInterface')

    def applyModifier(
            self,
            modifier: construction.ModifierInterface
            ) -> None:
        raise RuntimeError('The applyModifier method must be implemented by classes derived from AttributeInterface')

class FlagAttribute(AttributeInterface):
    def __init__(
            self,
            attributeId: ConstructionAttributeId
            ) -> None:
        super().__init__()
        self._attributeId = attributeId

    def id(self) -> ConstructionAttributeId:
        return self._attributeId

    def name(self) -> str:
        return self._attributeId.value

    def value(self) -> common.ScalarCalculation:
        return None

    def calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        return None

    def applyModifier(
            self,
            modifier: construction.ModifierInterface
            ) -> None:
        # Applying a modifier to a flag has no effect
        pass

class NumericAttribute(AttributeInterface):
    def __init__(
            self,
            attributeId: ConstructionAttributeId,
            value: common.ScalarCalculation
            ) -> None:
        super().__init__()
        self._attributeId = attributeId
        self._value = common.Calculator.equals(
            value=value,
            name=f'{self._attributeId.value} Value')

    def id(self) -> ConstructionAttributeId:
        return self._attributeId

    def name(self) -> str:
        return self._attributeId.value

    def value(self) -> common.ScalarCalculation:
        return self._value

    def calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        return [self._value]

    def applyModifier(
            self,
            modifier: construction.ModifierInterface
            ) -> None:
        self._value = common.Calculator.rename(
            value=modifier.applyTo(baseValue=self._value),
            name=f'{self._attributeId.value} Value')

class EnumAttribute(AttributeInterface):
    def __init__(
            self,
            attributeId: ConstructionAttributeId,
            value: enum.Enum
            ) -> None:
        super().__init__()

        self._attributeId = attributeId

        # Create a list of enums in definition order that can be used when modifying the attribute
        # by an integer amount. This assumes that iterating the enum type gives you the elements in
        # definition order (https://docs.python.org/3/library/enum.html)
        self._order = [e for e in type(value)]

        # Store the value as an integer value that is mapped back to an enum when required. This is
        # done to prevent clamping of modifier values. For example, a light handgun calibre pistol
        # (base signature Low) with the an extreme stealth receiver (signature -3) and a handgun
        # barrel (signature +1) should have Minimal signature not a Small signature as you would get
        # if the signature value was clamped to the available enums when the extreme stealth modifier
        # was applied.
        valueIndex = self._order.index(value)
        self._numericValue = common.ScalarCalculation(
            value=valueIndex,
            name=f'{attributeId.value} Value')

    def id(self) -> ConstructionAttributeId:
        return self._attributeId

    def name(self) -> str:
        return self._attributeId.value

    def value(self) -> enum.Enum:
        valueIndex = common.clamp(
            value=self._numericValue.value(),
            minValue=0,
            maxValue=len(self._order) - 1)
        return self._order[valueIndex]

    def calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        return [self._numericValue]

    def applyModifier(
            self,
            modifier: construction.ModifierInterface
            ) -> None:
        if isinstance(modifier, construction.ConstantModifier):
            self._numericValue = common.Calculator.rename(
                value=modifier.applyTo(baseValue=self._numericValue),
                name=f'{self._attributeId.value} Value')
        elif isinstance(modifier, construction.PercentageModifier):
            raise RuntimeError(f'Unable to add percentage modifier to Enum attribute {self._attributeId.name}')
        elif isinstance(modifier, construction.MultiplierModifier):
            raise RuntimeError(f'Unable to apply multiplier modifier to Enum attribute {self._attributeId.name}')
        elif isinstance(modifier, construction.DiceRollModifier):
            raise RuntimeError(f'Unable to apply dice roll modifier to Enum attribute {self._attributeId.name}')
        else:
            raise RuntimeError(f'Unable to apply unknown modifier type {type(modifier)} to Enum attribute {self._attributeId.name}' )

class DiceRollAttribute(AttributeInterface):
    def __init__(
            self,
            attributeId: ConstructionAttributeId,
            roll: common.DiceRoll
            ) -> None:
        super().__init__()
        self._attributeId = attributeId
        self._roll = common.DiceRoll(
            count=common.Calculator.equals(
                value=roll.dieCount(),
                name=f'{attributeId.value} Die Count'),
            type=roll.dieType(),
            constant=common.Calculator.equals(
                value=roll.constant(),
                name=f'{attributeId.value} Constant'))

    def id(self) -> ConstructionAttributeId:
        return self._attributeId

    def name(self) -> str:
        return self._attributeId.value

    def value(self) -> common.DiceRoll:
        return self._roll

    def calculations(self) -> typing.Iterable[common.ScalarCalculation]:
        return [self._roll.dieCount(), self._roll.constant()]

    def applyModifier(
            self,
            modifier: construction.ModifierInterface
            ) -> None:
        if isinstance(modifier, construction.ConstantModifier):
            raise RuntimeError(f'Unable to apply constant modifier to Dice Roll attribute {self._attributeId.name}')
        elif isinstance(modifier, construction.PercentageModifier):
            raise RuntimeError(f'Unable to apply percentage modifier to Dice Roll attribute {self._attributeId.name}')
        elif isinstance(modifier, construction.MultiplierModifier):
            raise RuntimeError(f'Unable to apply multiplier modifier to Dice Roll attribute {self._attributeId.name}')
        elif isinstance(modifier, construction.DiceRollModifier):
            self._roll = modifier.applyTo(baseValue=self._roll)
        else:
            raise RuntimeError(f'Unable to apply unknown modifier type {type(modifier)} to Dice Roll attribute {self._attributeId.name}' )

class AttributesGroup(object):
    def __init__(self) -> None:
        self._attributes: typing.Dict[ConstructionAttributeId, AttributeInterface] = {}

    def attributes(
            self
            ) -> typing.Iterable[AttributeInterface]:
        return self._attributes.values()

    def attribute(
            self,
            attributeId: ConstructionAttributeId
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        assert(isinstance(attributeId, ConstructionAttributeId))
        return self._attributes.get(attributeId)

    def attributeValue(
            self,
            attributeId: ConstructionAttributeId
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        assert(isinstance(attributeId, ConstructionAttributeId))
        value = self._attributes.get(attributeId)
        if not value:
            return None
        return value.value()

    def hasAttribute(
            self,
            attributeId: ConstructionAttributeId
            ) -> bool:
        assert(isinstance(attributeId, ConstructionAttributeId))
        return attributeId in self._attributes

    def setAttribute(
            self,
            attributeId: ConstructionAttributeId,
            value: typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]] = None
            ) -> None:
        assert(isinstance(attributeId, ConstructionAttributeId))
        if value == None:
            self._attributes[attributeId] = FlagAttribute(
                attributeId=attributeId)
        elif isinstance(value, common.ScalarCalculation):
            self._attributes[attributeId] = NumericAttribute(
                attributeId=attributeId,
                value=value)
        elif isinstance(value, common.DiceRoll):
            self._attributes[attributeId] = DiceRollAttribute(
                attributeId=attributeId,
                roll=value)
        elif isinstance(value, enum.Enum):
            self._attributes[attributeId] = EnumAttribute(
                attributeId=attributeId,
                value=value)
        else:
            raise RuntimeError(f'Unknown type {type(value)} when setting attribute {attributeId.name}' )

    def modifyAttribute(
            self,
            attributeId: ConstructionAttributeId,
            modifier: construction.ModifierInterface
            ) -> None:
        assert(isinstance(attributeId, ConstructionAttributeId))
        assert(isinstance(modifier, construction.ModifierInterface))
        attribute = self._attributes.get(attributeId)
        if attribute:
            attribute.applyModifier(modifier=modifier)
        else:
            # This attribute is currently uninitialised
            if isinstance(modifier, construction.ConstantModifier):
                # An absolute value is being applied to the attribute so just initialise a new numeric
                # attribute with the modifier value
                self._attributes[attributeId] = NumericAttribute(
                    attributeId=attributeId,
                    value=modifier.numericModifier())
            elif isinstance(modifier, construction.PercentageModifier):
                raise RuntimeError(f'Unable to use percentage modifier to initialise attribute {attributeId.name}')
            elif isinstance(modifier, construction.MultiplierModifier):
                raise RuntimeError(f'Unable to use multiplier modifier to initialise attribute {attributeId.name}')
            elif isinstance(modifier, construction.DiceRollModifier):
                raise RuntimeError(f'Unable to use dice roll modifier to initialise attribute {attributeId.name}')

    def deleteAttribute(
            self,
            attributeId: ConstructionAttributeId
            ) -> None:
        if attributeId in self._attributes:
            del self._attributes[attributeId]

    def clear(self) -> None:
        self._attributes.clear()
