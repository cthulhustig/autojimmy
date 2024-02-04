import common
import enum
import construction
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
            attributeId: construction.ConstructionAttribute,
            value: typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]] = None
            ) -> None:
        super().__init__()
        assert(isinstance(attributeId, construction.ConstructionAttribute))
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
            attributeId: construction.ConstructionAttribute,
            modifier: construction.ModifierInterface
            ) -> None:
        super().__init__()
        assert(isinstance(attributeId, construction.ConstructionAttribute))
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
            attributeId: construction.ConstructionAttribute
            ) -> None:
        super().__init__()
        assert(isinstance(attributeId, construction.ConstructionAttribute))
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

class ConstructionCost(enum.Enum):
    pass

class ConstructionStep(object):
    def __init__(
            self,
            name: str,
            type: str,
            costs: typing.Optional[typing.Mapping[ConstructionCost, construction.NumericModifierInterface]] = None,
            factors: typing.Optional[typing.Iterable[FactorInterface]] = None,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        self._name = name
        self._type = type
        self._costs = dict(costs) if costs != None else {}
        self._factors = list(factors) if factors != None else []
        self._notes = list(notes) if notes != None else []

    def name(self) -> str:
        return self._name

    def type(self) -> str:
        return self._type

    def cost(
            self,
            costId: ConstructionCost
            ) -> typing.Optional[construction.NumericModifierInterface]:
        return self._costs.get(costId)

    def setCost(
            self,
            costId: ConstructionCost,
            value: construction.NumericModifierInterface
            ) -> None:
        self._costs[costId] = value

    def costs(self) -> typing.Mapping[ConstructionCost, construction.NumericModifierInterface]:
        return self._costs

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
            costId: ConstructionCost,
            steps: typing.Iterable['ConstructionStep']
            ) -> typing.Optional[common.ScalarCalculation]:
        total = construction.calculateNumericModifierSequence(
            modifiers=[step.cost(costId=costId) for step in steps if step.cost(costId=costId)])
        if not total:
            return None
        return common.Calculator.equals(
            value=total,
            name=f'Total {costId.value}')
