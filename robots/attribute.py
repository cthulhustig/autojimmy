import construction
import enum

# NOTE: The robot rules don't give a complete list of Speed Bands these came
# from the construction spreadsheet someone put together and I think it might be
# based on the Speed Bands from the Vehicle Handbook
# https://forum.mongoosepublishing.com/threads/google-sheets-worksheets.123753/
class SpeedBand(enum.Enum):
    Idle = 'Idle'
    VerySlow = 'Very Slow'
    Slow = 'Slow'
    Medium = 'Medium'
    High = 'High'
    Fast = 'Fast'
    VeryHigh = 'Very Fast'
    Subsonic = 'Subsonic'
    Supersonic = 'Supersonic'

class RobotAttributeId(construction.ConstructionAttributeId):
    # Attributes Used By All Robots (Numeric unless otherwise stated)
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

    # Locomotion Flag Traits (p17)
    ATV = 'ATV'
    Seafarer = 'Seafarer'
    ACV = 'ACV'

    # Locomotion Numeric Traits (p17)
    Thruster = 'Thruster' # In G

    # Locomotion Enum Traits (p17)
    Flyer = 'Flyer' # SpeedBand
