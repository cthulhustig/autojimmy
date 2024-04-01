import enum

class Characteristics(enum.Enum):
    Strength = 'Strength'
    Dexterity = 'Dexterity'
    Endurance = 'Endurance'
    Intellect = 'Intellect'
    Education = 'Education'
    Social = 'Social'

"""
0     = -3
1-2   = -2
3-5   = -1
6-8   = 0
9-11  = +1
12-14 = +2
15+   = +3
"""
def characteristicDM(level: int) -> int:
    if level <= 0:
        return -3
    elif level <= 2:
        return -2
    elif level <= 5:
        return -1
    elif level <= 8:
        return 0
    elif level <= 11:
        return +1
    elif level <= 14:
        return +2
    else: # 15+
        return +3
    