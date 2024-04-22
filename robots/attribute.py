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
    Endurance = 'Endurance' # In hours
    Agility = 'Agility'
    Speed = 'Speed' # In meters per minor action
    # See the Armour trait below for details of how it relates to Protection
    Protection = 'Protection' # Base Protection + Protection from Armour
    # Some options give the robot cumulative protection from radiation. How
    # radiation affects a robot can be found on page (p106)
    Rads = 'Rads'

    # This is the speed of the vehicle when using Vehicle Speed Movement (p23).
    # When not using Vehicle Speed Movement my assumption is the Speed attribute
    # applies. As far as I can tell the only thing that sets this is the Vehicle
    # Speed Movement locomotion modifier
    VehicleSpeed = 'Vehicle Speed' # SpeedBand

    # This is added by me to hold the endurance while using Vehicle Speed
    # Movement (p23). It's done so the value can be displayed along with the
    # standard Endurance. In the Finale Endurance section (p23) the rules suggest
    # having the vehicle speed endurance in brackets after the standard endurance.
    VehicleEndurance = 'Vehicle Endurance'

    # This covers the base autopilot given by the Vehicle Speed Movement
    # locomotion modifier (p23) and Autopilot slot option (p49). It works the
    # same as the relevant vehicle skill for the robot piloting the form of
    # locomotion it has, but the two don't stack.
    # As far as I can tell the AutoPilot rating only applies when using Vehicle
    # Speed Movement this is based on the way the description of the AutoPilot
    # slot option is worded (p49). It talks about Vehicle Speed Movement a LOT
    # and doesn't have any mention of having AutoPilot in a robot not equipped
    # with Vehicle Speed Movement
    Autopilot = 'Autopilot'

    # This attribute is a hack to allow zero slot options to track how many zero
    # slot options have been added to know if they should start consuming a slot.
    # This attribute shouldn't be included in the manifest
    ZeroSlotCount = 'Zero Slot Count'    

    # Brain Attributes
    Intelligence = 'INT'
    # The Inherent Bandwidth is the base bandwidth of the brain. This is a hard
    # limit on the max bandwidth usage of individual skills. Modifications to
    # increase bandwidth don't increase the robot's inherent bandwidth
    InherentBandwidth = 'Inherent Bandwidth'
    # The Max Bandwidth limits the total number of skills a robot can have as
    # the total bandwidth can't exceed this value.
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
    Hardened = 'Hardened' # (p8)
    HeightenedSenses = 'Heightened Senses' # (p8)
    Invisible = 'Invisible' # (p8)
    IrVision = 'IR Vision' # (p8)
    IrUvVision = 'IR/UV Vision' # (p8)
    Seafarer = 'Seafarer' # (p17)

    #
    # Robot Numeric Traits
    #
    # NOTE: Based on the description of the Armour trait (p7) and what I can see
    # in the rest of the rules. The trait is equal to the robots final
    # Protection value (i.e. Base Protection from the chassis and Protection
    # from any armour added _or_ removed).
    Armour = 'Armour' # (p7)
    # NOTE: I believe the Large/Small traits are from the traits for Beasts in
    # the core rules (p81)
    # The Large/Small traits should be mutually exclusive but that that comes
    # for free because only the chassis sets them and it will only set one or
    # the other
    Large = 'Large' # (p8)
    Small = 'Small' # (p8)
    # NOTE: The Stealth trait is how well the robot can hide from being detected
    # by electronic means. Generally this is through the use of shielding and
    # advanced materials so is 'always on' rather than being something that is
    # activated. It's only given by the Active Camouflage and Stealth component
    # option and is not the same thing as the Stealth skill.
    Stealth = 'Stealth' # (p7)
    Thruster = 'Thruster' # In G (p17)

    #
    # Robot Enum Traits
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