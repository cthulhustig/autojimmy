import construction

ConstructionDecimalPlaces = 3

# The order of this enum determines construction order
class RobotPhase(construction.ConstructionPhase):
    # TODO: I could possibly make chassis, locomotion etc stages and group them in a Body phase
    Chassis = 'Chassis'
