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
    # Some options give the robot cumulative protection from radiation. How
    # radiation affects a robot can be found on page (p106)
    Rads = 'Rads'

    # This attribute is a hack to allow zero slot options to track how many zero
    # slot options have been added to know if they should start consuming a slot.
    # This attribute shouldn't be included in the manifest
    ZeroSlotCount = 'Zero Slot Count'

    # TODO: I think this should actually be a skill but this is good enough until
    # I implement skills.
    # Update: I can't remember why I thought this would be a skill
    Autopilot = 'Autopilot'

    # Brain Attributes
    Intelligence = 'INT'
    # TODO: The bandwidth usage of an individual skill package can't exceed the
    # inherent bandwidth (p67).
    InherentBandwidth = 'Inherent Bandwidth'
    # The Max Bandwidth defines the total number of skills a robot can have
    MaxBandwidth = 'Max Bandwidth'
    # The zero bandwidth skill count is a hack similar to ZeroSlotCost. This
    # attribute is used to count the number of zero bandwidth skills added to
    # to the robot
    ZeroBandwidthSkillCount = 'Zero Bandwidth Skill Count'

    #
    # Robot Flag Traits
    #
    ACV = 'ACV' # (p17)    
    Alarm = 'Alarm' # (p7)
    Amphibious = 'Amphibious' # (p7)
    ATV = 'ATV' # (p8 & 17)
    # TODO: I suspect the intention is hardened brains get this but i'm not sure
    # it explicitly says it in the section that covers brain hardening
    Hardened = 'Hardened' # (p8)
    HeightenedSenses = 'Heightened Senses' # (p8)
    Invisible = 'Invisible' # (p8)
    # TODO: Not sure where this is used
    IrVision = 'IR Vision' # (p8)
    IrUvVision = 'IR/UV Vision' # (p8)
    Seafarer = 'Seafarer' # (p17)

    #
    # Robot Numeric Traits
    #
    # TODO: There is an armour trait, not sure how this relates to the
    # attribute Protection. It's currently commented out to avoid any confusion
    # Armour = 'Armour' # (p7)
    # TODO: The Large & Small traits should be mutually exclusive
    Large = 'Large' # (p8)
    Small = 'Small' # (p8)
    # TODO: There is a complexity here as there is also a Stealth Skill and
    # they're not the same thing (p7)
    Stealth = 'Stealth' # (p7)
    Thruster = 'Thruster' # In G (p17)    

    #
    # Locomotion Enum Traits
    #
    Flyer = 'Flyer' # SpeedBand (p8 & p17)

InternalAttributeIds = [
    RobotAttributeId.BaseProtection,
    RobotAttributeId.ZeroSlotCount,
    RobotAttributeId.ZeroBandwidthSkillCount
]

TraitAttributesIds = [
    RobotAttributeId.ACV,
    RobotAttributeId.Alarm,
    RobotAttributeId.Amphibious,
    RobotAttributeId.ATV,
    RobotAttributeId.Hardened,
    RobotAttributeId.HeightenedSenses,
    RobotAttributeId.Invisible,
    RobotAttributeId.IrVision,
    RobotAttributeId.IrUvVision,
    RobotAttributeId.Seafarer,
    RobotAttributeId.Large,
    RobotAttributeId.Small,
    RobotAttributeId.Stealth,
    RobotAttributeId.Thruster,
    RobotAttributeId.Flyer
]