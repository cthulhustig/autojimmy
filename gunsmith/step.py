import common
import enum
import gunsmith
import typing

class FactorInterface(object):
    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        raise RuntimeError('The calculations method must be implemented by the class derived from Factor')

    def displayString(self) -> str:
        raise RuntimeError('The displayString method must be implemented by the class derived from Factor')

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
            factor: 'gunsmith.FactorInterface',
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
            attributeGroup: gunsmith.AttributesGroup
            ) -> None:
        raise RuntimeError('The applyTo method must be implemented by the class derived from TraitFactor')

class SetAttributeFactor(AttributeFactor):
    def __init__(
            self,
            attributeId: gunsmith.AttributeId,
            value: typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, gunsmith.Signature]] = None
            ) -> None:
        super().__init__()
        assert(isinstance(attributeId, gunsmith.AttributeId))
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
            attributeGroup: gunsmith.AttributesGroup
            ) -> None:
        attributeGroup.setAttribute(
            attributeId=self._attributeId,
            value=self._value)

class ModifyAttributeFactor(AttributeFactor):
    def __init__(
            self,
            attributeId: gunsmith.AttributeId,
            modifier: gunsmith.ModifierInterface
            ) -> None:
        super().__init__()
        assert(isinstance(attributeId, gunsmith.AttributeId))
        assert(isinstance(modifier, gunsmith.ModifierInterface))
        self._attributeId = attributeId
        self._modifier = modifier

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return self._modifier.calculations()

    def displayString(self) -> str:
        return self._attributeId.value + ' ' + \
            self._modifier.displayString()

    def applyTo(
            self,
            attributeGroup: gunsmith.AttributesGroup
            ) -> None:
        attributeGroup.modifyAttribute(
            attributeId=self._attributeId,
            modifier=self._modifier)

class DeleteAttributeFactor(AttributeFactor):
    def __init__(
            self,
            attributeId: gunsmith.AttributeId
            ) -> None:
        super().__init__()
        assert(isinstance(attributeId, gunsmith.AttributeId))
        self._attributeId = attributeId

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return []

    def displayString(self) -> str:
        return 'Removes ' + self._attributeId.value

    def applyTo(
            self,
            attributeGroup: gunsmith.AttributesGroup
            ) -> None:
        attributeGroup.deleteAttribute(attributeId=self._attributeId)

class ConstructionStep(object):
    def __init__(
            self,
            name: str,
            type: str,
            cost: typing.Optional[gunsmith.NumericModifierInterface] = None,
            weight: typing.Optional[gunsmith.NumericModifierInterface] = None,
            factors: typing.Optional[typing.Iterable[FactorInterface]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        self._name = name
        self._type = type
        self._cost = cost
        self._weight = weight
        self._factors = list(factors) if factors != None else []
        self._notes = list(notes) if notes != None else []

    def name(self) -> str:
        return self._name

    def type(self) -> str:
        return self._type

    def cost(self) -> typing.Optional[gunsmith.NumericModifierInterface]:
        return self._cost

    def setCost(
            self,
            cost: gunsmith.NumericModifierInterface
            ) -> None:
        self._cost = cost

    def weight(self) -> typing.Optional[gunsmith.NumericModifierInterface]:
        return self._weight

    def setWeight(
            self,
            weight: gunsmith.NumericModifierInterface
            ) -> None:
        self._weight = weight

    def factors(self) -> typing.Iterable[FactorInterface]:
        return self._factors

    def addFactor(
            self,
            factor: FactorInterface
            ) -> None:
        self._factors.append(factor)

    def notes(self) -> typing.Iterable[str]:
        return self._notes

    def addNote(
            self,
            note: str
            ) -> None:
        self._notes.append(note)

    @staticmethod
    def calculateSequenceCost(
            steps: typing.Iterable['ConstructionStep']
            ) -> typing.Optional[common.ScalarCalculation]:
        total = gunsmith.calculateNumericModifierSequence(
            modifiers=[step.cost() for step in steps if step.cost()])
        if not total:
            return None
        return common.Calculator.equals(
            value=total,
            name='Total Cost')

    @staticmethod
    def calculateSequenceWeight(
            steps: typing.Iterable['ConstructionStep']
            ) -> typing.Optional[common.ScalarCalculation]:
        total = gunsmith.calculateNumericModifierSequence(
            modifiers=[step.weight() for step in steps if step.weight()])
        if not total:
            return None
        return common.Calculator.equals(
            value=total,
            name='Total Weight')
