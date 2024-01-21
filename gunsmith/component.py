import common
import enum
import gunsmith
import typing

class ConstructionContextInterface(object):
    def isRuleEnabled(self, rule: gunsmith.RuleId) -> bool:
        raise RuntimeError('The isRuleEnabled method must be implemented by classes derived from ConstructionContextInterface')

    def techLevel(self) -> int:
        raise RuntimeError('The techLevel method must be implemented by classes derived from ConstructionContextInterface')

    def weaponType(
            self,
            sequence: str
            ) -> gunsmith.WeaponType:
        raise RuntimeError('The weaponType method must be implemented by classes derived from ConstructionContextInterface')

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
            attributeId: gunsmith.AttributeId,
            sequence: str
            ) -> typing.Optional[typing.Union[common.ScalarCalculation, common.DiceRoll, enum.Enum]]:
        raise RuntimeError('The attributeValue method must be implemented by classes derived from ConstructionContextInterface')

    def hasAttribute(
            self,
            attributeId: gunsmith.AttributeId,
            sequence: str
            ) -> bool:
        raise RuntimeError('The hasAttribute method must be implemented by classes derived from ConstructionContextInterface')

    def phaseWeight(
            self,
            phase: gunsmith.ConstructionPhase,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        raise RuntimeError('The phaseWeight method must be implemented by classes derived from ConstructionContextInterface')

    def phaseCredits(
            self,
            phase: gunsmith.ConstructionPhase,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        raise RuntimeError('The phaseCredits method must be implemented by classes derived from ConstructionContextInterface')

    def receiverWeight(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        raise RuntimeError('The receiverWeight method must be implemented by classes derived from ConstructionContextInterface')

    def receiverCredits(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        raise RuntimeError('The receiverCredits method must be implemented by classes derived from ConstructionContextInterface')

    # Basic weapon weight (doesn't include accessories or ammo)
    def baseWeight(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        raise RuntimeError('The baseWeight method must be implemented by classes derived from ConstructionContextInterface')

    # Basic weapon cost (doesn't include accessories or ammo)
    def baseCredits(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        raise RuntimeError('The baseCredits method must be implemented by classes derived from ConstructionContextInterface')

    def totalWeight(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        raise RuntimeError('The totalWeight method must be implemented by classes derived from ConstructionContextInterface')

    def totalCredits(
            self,
            sequence: typing.Optional[str]
            ) -> common.ScalarCalculation:
        raise RuntimeError('The totalCredits method must be implemented by classes derived from ConstructionContextInterface')

    def applyStep(
            self,
            sequence: str,
            step: gunsmith.ConstructionStep
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

    def options(self) -> typing.List[gunsmith.ComponentOption]:
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

class ReceiverInterface(ComponentInterface):
    pass

class CalibreInterface(ComponentInterface):
    def isRocket(self) -> bool:
        raise RuntimeError('The isRocket method must be implemented by classes derived from CalibreInterface')

    def isHighVelocity(self) -> bool:
        raise RuntimeError('The isHighVelocity method must be implemented by classes derived from CalibreInterface')

class PropellantTypeInterface(ComponentInterface):
    pass

class FeedInterface(ComponentInterface):
    pass

class MultiBarrelInterface(ComponentInterface):
    pass

class MechanismInterface(ComponentInterface):
    pass

class ReceiverFeatureInterface(ComponentInterface):
    pass

class CapacityModificationInterface(ComponentInterface):
    pass

class FireRateInterface(ComponentInterface):
    pass

class BarrelInterface(ComponentInterface):
    pass

class MultiMountInterface(ComponentInterface):
    def weaponCount(self) -> int:
        raise RuntimeError('The weaponCount method must be implemented by classes derived from MultiMountInterface')

class StockInterface(ComponentInterface):
    pass

class WeaponFeatureInterface(ComponentInterface):
    pass

class SecondaryMountInterface(ComponentInterface):
    def weapon(self) -> typing.Optional['gunsmith.Weapon']:
        raise RuntimeError('The weapon method must be implemented by classes derived from SecondaryMountInterface')

class AccessoryInterface(ComponentInterface):
    def isDetachable(self) -> bool:
        raise RuntimeError('The isDetachable method must be implemented by classes derived from AccessoryInterface')

    def isAttached(self) -> bool:
        raise RuntimeError('The isAttached method must be implemented by classes derived from AccessoryInterface')

    def setAttached(self, attached: bool) -> None:
        raise RuntimeError('The setAttached method must be implemented by classes derived from AccessoryInterface')

class BarrelAccessoryInterface(AccessoryInterface):
    pass

class WeaponAccessoryInterface(AccessoryInterface):
    pass

class LoaderQuantityInterface(ComponentInterface):
    pass

class MagazineLoadedInterface(ComponentInterface):
    pass

class MagazineQuantityInterface(ComponentInterface):
    def createLoadedMagazine(self) -> MagazineLoadedInterface:
        raise RuntimeError('The createLoadedMagazine method must be implemented by classes derived from MagazineQuantityInterface')

class AmmoLoadedInterface(ComponentInterface):
    pass

class MultiMountLoadedInterface(ComponentInterface):
    pass

class AmmoQuantityInterface(ComponentInterface):
    def createLoadedAmmo(self) -> AmmoLoadedInterface:
        raise RuntimeError('The createLoadedAmmo method must be implemented by classes derived from AmmoQuantityInterface')

class InternalPowerPackLoadedInterface(AmmoLoadedInterface):
    pass

class ExternalPowerPackLoadedInterface(AmmoLoadedInterface):
    pass

class ProjectorPropellantQuantityInterface(ComponentInterface):
    pass

class HandGrenadeQuantityInterface(ComponentInterface):
    pass
