import construction

ConstructionDecimalPlaces = 3

# The order of this enum determines basic construction order
# NOTE: BaseChassis phase contains the Chassis and Locomotion components to
# allow the Base Chassis Cost to be calculated as the phase cost
# NOTE: Skills needs to be it's own phase so that finalisation can calculate
# the cost for all phases except skills when applying the additional cost
# for synthetic robots
class RobotPhase(construction.ConstructionPhase):
    BaseChassis = 'Base Chassis'
    ChassisOptions = 'Chassis Options'
    LocomotiveMods = 'Locomotive Modifications'
    Manipulators = 'Manipulators'
    SlotOptions = 'Slot Options'
    Weapons = 'Weapons'
    Brain = 'Brain'
    Skills = 'Skills'
    Finalisation = 'Finalisation'

# Internal phases
InternalConstructionPhases = [
    RobotPhase.Finalisation,
]
