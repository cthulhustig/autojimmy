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
    BaseProtection = 'Base Protection' # NOTE: This is an internal attribute
    MaxSlots = 'Max Slots'
    # NOTE: The AttackRollDM is the modifier attackers get when attacking the
    # robot (due to its size)
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

    # This attribute is a hack to allow zero slot options to track how many zero
    # slot options have been added to know if they should start consuming a slot.
    # This attribute shouldn't be included in the manifest
    ZeroSlotCount = 'Zero Slot Count'

    # TODO: I think this should actually be a skill but this is good enough until
    # I implement skills
    Autopilot = 'Autopilot'

    # Brain Attributes
    Intelligence = 'INT'
    # TODO: The bandwidth usage of an individual skill package can't exceed the
    # inherent bandwidth (p67).
    InherentBandwidth = 'Inherent Bandwidth'
    # The Max Bandwidth defines the total number of skills a robot can have
    MaxBandwidth = 'Max Bandwidth'
    MaxSkills = 'Max Skills'
    # The zero bandwidth skill count is a hack similar to ZeroSlotCost. This
    # attribute is used to count the number of zero bandwidth skills added to
    # to the robot
    ZeroBandwidthSkillCount = 'Zero Bandwidth Skill Count'

    # Robot Numeric Traits (p7)
    # TODO: The Large & Small traits should be mutually exclusive
    Large = 'Large'
    Small = 'Small'
    Rads = 'Rads'

    # Robot Flag Traits (p7)
    HeightenedSenses = 'Heightened Senses'
    IrVision = 'IR Vision'
    IrUvVision = 'IR/UV Vision'
    Invisible = 'Invisible'

    # Robot Numeric Traits (p7)
    # TODO: There is a complexity here as there is also a Stealth Skill and
    # they're not the same thing (p7)
    Stealth = 'Stealth'

    # Locomotion Flag Traits (p17)
    ATV = 'ATV'
    Seafarer = 'Seafarer'
    ACV = 'ACV'

    # Locomotion Numeric Traits (p17)
    Thruster = 'Thruster' # In G

    # Locomotion Enum Traits (p17)
    Flyer = 'Flyer' # SpeedBand

InternalAttributeIds = [
    RobotAttributeId.BaseProtection,
    RobotAttributeId.ZeroSlotCount,
    RobotAttributeId.ZeroBandwidthSkillCount
]