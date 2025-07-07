import enum

class TagLevel(enum.Enum):
    Desirable = 0
    Warning = 1
    Danger = 2

    def __ge__(self, other: 'TagLevel') -> bool:
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other: 'TagLevel') -> bool:
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other: 'TagLevel') -> bool:
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other: 'TagLevel') -> bool:
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented
