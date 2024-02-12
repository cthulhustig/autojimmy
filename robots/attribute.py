import construction
import enum

"""
- Used by Vehicle Speed Movement locomotion modification (p23)
- NOTE: This feels similar to Physical Signature
- TODO: This list is possibly incomplete, it might have come from the Vehicle rule book
"""
class SpeedBand(enum.Enum):
    VerySlow = 'Very Slow'
    Slow = 'Slow'
    Medium = 'Medium'
    High = 'High'

class RobotAttributeId(construction.ConstructionAttributeId):
    # Attributes Used By All Robots (Numeric unless otherwise stated)
    BaseSlots = 'Base Slots'
    BaseHits = 'Base Hits'
    AttackRollDM = 'Attack Roll DM'
    AvailableSlots = 'Available Slots'
    Endurance = 'Endurance' # In hours
    Agility = 'Agility'
    Movement = 'Movement' # In meters

    # Robot Numeric Traits (p7)
    # TODO: The Large & Small traits should be mutually exclusive
    Large = 'Large'
    Small = 'Small'

    # Locomotion Flag Traits (p17)
    ATV = 'ATV'
    Seafarer = 'Seafarer'
    ACV = 'ACV'

    # Locomotion Numeric Traits (p17)
    Thruster = 'Thruster' # In G

    # Locomotion Enum Traits (p17)
    Flyer = 'Flyer' # SpeedBand
