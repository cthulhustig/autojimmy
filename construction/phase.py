import enum

# Construction implementations should create an enum derived from this class
# with entries for each of the phases of construction, in the order the occur.
# The value of the entry should be the human readable name of the attribute to
# be displayed to the user
class ConstructionPhase(enum.Enum):
    pass
