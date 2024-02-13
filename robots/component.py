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

class ArmourModificationInterface(LocomotionInterface):
    pass
