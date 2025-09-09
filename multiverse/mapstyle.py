import enum

class MapStyle(enum.Enum):
    Poster = 'Poster'
    Print = 'Print'
    Mongoose = 'Mongoose'
    Candy = 'Eye Candy'
    Draft = 'Draft'
    Fasa = 'FASA'
    Atlas = 'Atlas'
    Terminal = 'Terminal'


_DarkStyles = [
    MapStyle.Poster,
    MapStyle.Candy,
    MapStyle.Terminal
]

def isLightStyle(style: MapStyle) -> bool:
    return style not in _DarkStyles

def isDarkStyle(style: MapStyle) -> bool:
    return style in _DarkStyles
