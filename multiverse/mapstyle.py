import enum

# TODO: Once the datastore has been updated to no longer read MapStyle
# for custom sectors it should be possible to move this to cartographer/.
# It probably means splitting it so the enum goes into primitives.py and
# the functions got into utils.py

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
