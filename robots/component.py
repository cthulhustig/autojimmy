import construction
import traveller
import typing

class RobotComponentInterface(construction.ComponentInterface):
    pass

class ChassisInterface(RobotComponentInterface):
    pass

class LocomotionInterface(RobotComponentInterface):
    def isNatural(self) -> bool:
        raise RuntimeError(f'{type(self)} is derived from LocomotionInterface so must implement isNatural') 

class PrimaryLocomotionInterface(LocomotionInterface):
    pass

class SecondaryLocomotionInterface(LocomotionInterface):
    pass

class SyntheticInterface(RobotComponentInterface):
    pass

class ArmourModificationInterface(RobotComponentInterface):
    pass

class EnduranceModificationInterface(RobotComponentInterface):
    pass

class ResiliencyModificationInterface(RobotComponentInterface):
    pass

class AgilityEnhancementInterface(RobotComponentInterface):
    pass

class SpeedModificationInterface(RobotComponentInterface):
    pass

class ManipulatorInterface(RobotComponentInterface):
    def size(self) -> int:
        raise RuntimeError(f'{type(self)} is derived from ManipulatorInterface so must implement size')

    def strength(self) -> int:
        raise RuntimeError(f'{type(self)} is derived from ManipulatorInterface so must implement strength')

    def dexterity(self) -> int:
        raise RuntimeError(f'{type(self)} is derived from ManipulatorInterface so must implement dexterity')

class BaseManipulatorInterface(ManipulatorInterface):
    pass

class AdditionalManipulatorInterface(ManipulatorInterface):
    pass

class LegManipulatorInterface(ManipulatorInterface):
    pass

class SlotOptionsInterface(RobotComponentInterface):
    pass

class DefaultSuiteOptionInterface(SlotOptionsInterface):
    pass

class SlotOptionInterface(SlotOptionsInterface):
    pass

class MountedWeaponInterface(RobotComponentInterface):
    def mountSize(self) -> traveller.WeaponSize:
        raise RuntimeError(f'{type(self)} is derived from WeaponMountInterface so must implement mountSize')
    
    def weaponName(self) -> str:
        raise RuntimeError(f'{type(self)} is derived from WeaponMountInterface so must implement weaponName')

    def weaponData(
            self,
            weaponSet: traveller.StockWeaponSet
            ) -> typing.Optional[traveller.StockWeapon]:
        raise RuntimeError(f'{type(self)} is derived from WeaponMountInterface so must implement weaponData')
        
    def autoloaderMagazineCount(self) -> typing.Optional[int]:
        raise RuntimeError(f'{type(self)} is derived from WeaponMountInterface so must implement autoloaderMagazineCount')

class BrainInterface(RobotComponentInterface):
    pass

class SkillPackageInterface(RobotComponentInterface):
    pass

class SkillInterface(RobotComponentInterface):
    pass

class UnusedSlotRemovalInterface(RobotComponentInterface):
    pass

class FinalisationInterface(RobotComponentInterface):
    pass