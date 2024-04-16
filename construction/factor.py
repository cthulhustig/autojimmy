import common
import enum
import construction
import traveller
import typing

class FactorInterface(object):
    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        raise RuntimeError(f'{type(self)} is derived from FactorInterface so must implement calculations')

    def displayString(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from FactorInterface so must implement displayString')

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

# The NonModifyingFactor is used when we want the factor details to be displayed
# in the manifest but not applied to the context (e.g. secondary weapon factors
# or munitions quantities).
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
    def attributeId(self) -> construction.ConstructionAttributeId:
        raise RuntimeError(f'{type(self)} is derived from AttributeFactor so must implement attributeId') 

    def applyTo(
            self,
            attributeGroup: construction.AttributesGroup
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from AttributeFactor so must implement applyTo')

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

    def attributeId(self) -> construction.ConstructionAttributeId:
        return self._attributeId

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

    def attributeId(self) -> construction.ConstructionAttributeId:
        return self._attributeId

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

    def attributeId(self) -> construction.ConstructionAttributeId:
        return self._attributeId

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return []

    def displayString(self) -> str:
        return 'Removes ' + self._attributeId.value

    def applyTo(
            self,
            attributeGroup: construction.AttributesGroup
            ) -> None:
        attributeGroup.deleteAttribute(attributeId=self._attributeId)

class SkillFactor(FactorInterface):
    def skillDef(self) -> traveller.SkillDefinition:
        raise RuntimeError(f'{type(self)} is derived from SkillFactor so must implement skillDef') 

    def applyTo(
            self,
            skillGroup: construction.SkillGroup
            ) -> None:
        raise RuntimeError(f'{type(self)} is derived from SkillFactor so must implement applyTo')
    
class SetSkillFactor(SkillFactor):
    def __init__(
            self,
            skillDef: traveller.SkillDefinition,
            level: common.ScalarCalculation,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None,
            keepGreatest: bool = True
            ) -> None:
        super().__init__()
        assert(isinstance(skillDef, traveller.SkillDefinition))
        self._skillDef = skillDef
        self._speciality = speciality
        self._level = level
        self._keepGreatest = keepGreatest

    def skillDef(self) -> construction.ConstructionAttributeId:
        return self._skillDef

    def calculations(self) -> typing.Collection[common.ScalarCalculation]:
        return [self._level]

    def displayString(self) -> str:
        string = self._skillDef.name()
        if isinstance(self._speciality, enum.Enum):
            string += f' ({self._speciality.value})'
        elif isinstance(self._speciality, str):
            string += f' ({self._speciality})'
        string += f' {self._level.value()}'
        return string

    def applyTo(
            self,
            skillGroup: construction.SkillGroup
            ) -> None:
        skillGroup.setLevel(
            skillDef=self._skillDef,
            level=self._level,
            speciality=self._speciality,
            keepGreatest=self._keepGreatest)