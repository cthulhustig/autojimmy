import enum

class Style(enum.Enum):
    Poster = 'Poster'
    Print = 'Print'
    Mongoose = 'Mongoose'
    Candy = 'Eye Candy'
    Draft = 'Draft'
    Fasa = 'FASA'
    Atlas = 'Atlas'
    Terminal = 'Terminal'


_DarkStyles = [
    Style.Poster,
    Style.Candy,
    Style.Terminal
]

def isLightStyle(style: Style) -> bool:
    return style not in _DarkStyles

def isDarkStyle(style: Style) -> bool:
    return style in _DarkStyles
