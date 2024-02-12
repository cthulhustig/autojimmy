import construction

ConstructionDecimalPlaces = 3

# The order of this enum determines construction order
# NOTE: BaseChassis phase contains the Chassis and Locomotion components to
# allow the Base Chassis Cost to be calculated as the phase cost
class RobotPhase(construction.ConstructionPhase):
    BaseChassis = 'Base Chassis'
    ChassisOptions = 'Chassis Options'
    LocomotionOptions = 'Locomotion Options'
