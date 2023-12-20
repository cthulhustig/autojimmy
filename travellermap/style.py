import enum

class Style(enum.Enum):
    Poster = 'Poster'
    Print = 'Print'
    Atlas = 'Atlas'
    Candy = 'Eye Candy'
    Draft = 'Draft'
    Fasa = 'FASA'
    Terminal = 'Terminal'
    Mongoose = 'Mongoose'


_DarkStyles = [
    Style.Poster,
    Style.Candy,
    Style.Terminal
]

def isLightStyle(style: Style) -> bool:
    return style not in _DarkStyles

def isDarkStyle(style: Style) -> bool:
    return style in _DarkStyles
