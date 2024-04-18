import construction

class RobotComponentInterface(construction.ComponentInterface):
    pass

class ChassisInterface(RobotComponentInterface):
    pass

class LocomotionInterface(RobotComponentInterface):
    pass

class PrimaryLocomotionInterface(LocomotionInterface):
    pass

class SecondaryLocomotionInterface(LocomotionInterface):
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

class WeaponMountInterface(RobotComponentInterface):
    pass

class BrainInterface(RobotComponentInterface):
    pass

class SkillPackageInterface(RobotComponentInterface):
    pass

class SkillInterface(RobotComponentInterface):
    pass

class SlotRemovalInterface(RobotComponentInterface):
    pass

class FinalisationInterface(RobotComponentInterface):
    pass