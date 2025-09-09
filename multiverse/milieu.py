import enum

# NOTE: The names of these enums are when serialising jump routes (specifically
# the logistics). If I ever rename them I'll need to do something to maintain
# backwards compatibility
class Milieu(enum.Enum):
    IW = 'IW'
    M0 = 'M0'
    M990 = 'M990'
    M1105 = 'M1105'
    M1120 = 'M1120'
    M1201 = 'M1201'
    M1248 = 'M1248'
    M1900 = 'M1900'


_MilieuDescriptionMap = {
    Milieu.IW: 'The Interstellar Wars',
    Milieu.M0: '0 - Early Imperium',
    Milieu.M990: '990 - Solomani Rim War',
    Milieu.M1105: '1105 - The Golden Age',
    Milieu.M1120: '1120 - The Rebellion',
    Milieu.M1201: '1201 - The New Era',
    Milieu.M1248: '1248 - The New, New Era',
    Milieu.M1900: '1900 - The Far Far Future'
}

_MilieuYearMap = {
    Milieu.IW: -2404,
    Milieu.M0: 0,
    Milieu.M990: 990,
    Milieu.M1105: 1105,
    Milieu.M1120: 1120,
    Milieu.M1201: 1201,
    Milieu.M1248: 1248,
    Milieu.M1900: 1900
}

def milieuDescription(milieu: Milieu) -> str:
    return _MilieuDescriptionMap[milieu]

# TODO: Support arbitrary dates so you can see things like Empress
# wave progression (see Traveller Map currentYear in map.js)
def milieuToYear(milieu: Milieu) -> int:
    return _MilieuYearMap[milieu]
