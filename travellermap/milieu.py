import enum

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

def milieuDescription(milieu: Milieu) -> str:
    return _MilieuDescriptionMap[milieu]
