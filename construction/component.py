import common
import enum
import construction
import typing

# TODO: This should probably be moved into it's own file. It will need to
# be before component.py in the init file
# TODO: I suspect this interface might be pointless after the refactor and
# the base ConstructionContext will just be used
class ConstructionContextInterface(object):
    def techLevel(self) -> int:
        raise RuntimeError('The techLevel method must be implemented by classes derived from ConstructionContextInterface')

    def isPrimary(
            self,
            sequence: str
            ) -> bool:
        raise RuntimeError('The techLevel method must be implemented by classes derived from ConstructionContextInterface')

    def findFirstComponent(
            self,
            componentType: typing.Type['ComponentInterface'],
            sequence: typing.Optional[str]
            ) -> typing.Optional['ComponentInterface']:
        raise RuntimeError('The findFirstComponent method must be implemented by classes derived from ConstructionContextInterface')

    def findComponents(
            self,
            componentType: typing.Type['ComponentInterface'],
            sequence: typing.Optional[str]
            ) -> typing.Iterable['ComponentInterface']:
        raise RuntimeError('The findComponents method must be implemented by classes derived from ConstructionContextInterface')

    def hasComponent(
            self,
            componentType: typing.Type['ComponentInterface'],
            sequence: typing.Optional[str]
            ) -> bool:
        raise RuntimeError('The hasComponent method must be implemented by classes derived from ConstructionContextInterface')

    def attributeValue(
            self,
            attributeId: construction.ConstructionAttribute,
            sequence: str
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        raise RuntimeError('The attributeValue method must be implemented by classes derived from ConstructionContextInterface')

    def hasAttribute(
            self,
            attributeId: construction.ConstructionAttribute,
            sequence: str
            ) -> bool:
        raise RuntimeError('The hasAttribute method must be implemented by classes derived from ConstructionContextInterface')

    def applyStep(
            self,
            sequence: str,
            step: construction.ConstructionStep
            ) -> None:
        raise RuntimeError('The addStep method must be implemented by classes derived from ConstructionContextInterface')
    
class ComponentInterface(object):
    def componentString(self) -> str:
        raise RuntimeError('The componentString method must be implemented by classes derived from ComponentInterface')

    def instanceString(self) -> str:
        # Use component string for instance string by default
        return self.componentString()

    def typeString(self) -> str:
        raise RuntimeError('The typeString method must be implemented by classes derived from ComponentInterface')

    def isCompatible(
            self,
            sequence: str,
            context: ConstructionContextInterface
            ) -> bool:
        raise RuntimeError('The isCompatible method must be implemented by classes derived from ComponentInterface')

    def options(self) -> typing.List[construction.ComponentOption]:
        raise RuntimeError('The options method must be implemented by classes derived from ComponentInterface')

    def updateOptions(
            self,
            sequence: str,
            context: ConstructionContextInterface
            ) -> None:
        raise RuntimeError('The updateOptions method must be implemented by classes derived from ComponentInterface')

    def createSteps(
            self,
            sequence: str,
            context: ConstructionContextInterface
            ) -> None:
        raise RuntimeError('The createSteps method must be implemented by classes derived from ComponentInterface')
