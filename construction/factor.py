import common
import enum
import construction
import typing

class FactorInterface(object):
    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        raise RuntimeError('The calculations method must be implemented by the class derived from FactorInterface')

    def displayString(self) -> str:
        raise RuntimeError('The displayString method must be implemented by the class derived from FactorInterface')

class StringFactor(FactorInterface):
    def __init__(
            self,
            string: str
            ) -> None:
        super().__init__()
        self._string = string

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return []

    def displayString(self) -> str:
        return self._string

# The NonModifyingFactor is used when we want the factor details to be displayed in the manifest but not
# applied to the weapon (e.g. secondary weapon factors or munitions quantities).
class NonModifyingFactor(FactorInterface):
    def __init__(
            self,
            factor: FactorInterface,
            prefix: typing.Optional[str] = None
            ) -> None:
        super().__init__()
        self._factor = factor
        self._prefix = prefix

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return self._factor.calculations()

    def displayString(self) -> str:
        if self._prefix:
            return self._prefix + self._factor.displayString()
        return self._factor.displayString()

class AttributeFactor(FactorInterface):
    def applyTo(
            self,
            attributeGroup: construction.AttributesGroup
            ) -> None:
        raise RuntimeError('The applyTo method must be implemented by the class derived from TraitFactor')

class SetAttributeFactor(AttributeFactor):
    def __init__(
            self,
            attributeId: construction.ConstructionAttributeId,
            value: typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]] = None
            ) -> None:
        super().__init__()
        assert(isinstance(attributeId, construction.ConstructionAttributeId))
        self._attributeId = attributeId
        self._value = value

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        if isinstance(self._value, common.ScalarCalculation):
            return [self._value]
        elif isinstance(self._value, common.DiceRoll):
            return [self._value.dieCount(), self._value.constant()]
        return []

    def displayString(self) -> str:
        displayString = self._attributeId.value

        if isinstance(self._value, common.ScalarCalculation):
            displayString += ' = ' + common.formatNumber(
                number=self._value.value(),
                alwaysIncludeSign=False)
        elif isinstance(self._value, common.DiceRoll):
            displayString += ' = ' + str(self._value)
        elif isinstance(self._value, enum.Enum):
            displayString += ' = ' + str(self._value.value)

        return displayString

    def applyTo(
            self,
            attributeGroup: construction.AttributesGroup
            ) -> None:
        attributeGroup.setAttribute(
            attributeId=self._attributeId,
            value=self._value)

class ModifyAttributeFactor(AttributeFactor):
    def __init__(
            self,
            attributeId: construction.ConstructionAttributeId,
            modifier: construction.ModifierInterface
            ) -> None:
        super().__init__()
        assert(isinstance(attributeId, construction.ConstructionAttributeId))
        assert(isinstance(modifier, construction.ModifierInterface))
        self._attributeId = attributeId
        self._modifier = modifier

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return self._modifier.calculations()

    def displayString(self) -> str:
        return self._attributeId.value + ' ' + \
            self._modifier.displayString()

    def applyTo(
            self,
            attributeGroup: construction.AttributesGroup
            ) -> None:
        attributeGroup.modifyAttribute(
            attributeId=self._attributeId,
            modifier=self._modifier)

class DeleteAttributeFactor(AttributeFactor):
    def __init__(
            self,
            attributeId: construction.ConstructionAttributeId
            ) -> None:
        super().__init__()
        assert(isinstance(attributeId, construction.ConstructionAttributeId))
        self._attributeId = attributeId

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return []

    def displayString(self) -> str:
        return 'Removes ' + self._attributeId.value

    def applyTo(
            self,
            attributeGroup: construction.AttributesGroup
            ) -> None:
        attributeGroup.deleteAttribute(attributeId=self._attributeId)
