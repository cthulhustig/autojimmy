import construction
import enum

# NOTE: It looks like these come from the core rules (p130)
class SpeedBand(enum.Enum):
    Stopped = 'Stopped'
    Idle = 'Idle'
    VerySlow = 'Very Slow'
    Slow = 'Slow'
    Medium = 'Medium'
    High = 'High'
    Fast = 'Fast'
    VeryFast = 'Very Fast'
    Subsonic = 'Subsonic'
    Supersonic = 'Supersonic'
    Hypersonic = 'Hypersonic'

class RobotAttributeId(construction.ConstructionAttributeId):
    # Attributes Used By All Robots (Numeric unless otherwise stated)
    Size = 'Size'
    BaseSlots = 'Base Slots'
    AvailableSlots = 'Available Slots'
    AttackRollDM = 'Attack Roll DM'
    Hits = 'Hits'
    # TODO: I think Endurance can be a float. I'm not sure if it's important
    # but I should probably figure it out
    Endurance = 'Endurance' # In hours
    Agility = 'Agility'
    # TODO: Need to work out if Movement (p16) is the same as Speed (p22). I
    # think it's Speed as that's what it appears to be on the example robots
    # from the book
    Speed = 'Speed' # In meters
    VehicleSpeed = 'Vehicle Speed' # SpeedBand
    # TODO: Need to work out if this should be Protection or Armour, I think
    # it's the same thing and the rules use them interchangeably
    Protection = 'Protection'

    # Robot Numeric Traits (p7)
    # TODO: The Large & Small traits should be mutually exclusive
    Large = 'Large'
    Small = 'Small'
    Rads = 'Rads'

    # Robot Flag Traits (p7)
    HeightenedSenses = 'Heightened Senses'
    IrVision = 'IR Vision'
    IrUvVision = 'IR/UV Vision'

    # Locomotion Flag Traits (p17)
    ATV = 'ATV'
    Seafarer = 'Seafarer'
    ACV = 'ACV'

    # Locomotion Numeric Traits (p17)
    Thruster = 'Thruster' # In G

    # Locomotion Enum Traits (p17)
    Flyer = 'Flyer' # SpeedBand
