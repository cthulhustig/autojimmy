import enum
import fnmatch
import re
import typing

class Glyph(object):
    class GlyphBias(enum.Enum):
        NoBias = 0
        Top = 1
        Bottom = 2

    @typing.overload
    def __init__(self, chars: str, highlight: bool = False, bias: GlyphBias = GlyphBias.NoBias) -> None: ...
    @typing.overload
    def __init__(self, other: 'Glyph', highlight: bool = False, bias: GlyphBias = GlyphBias.NoBias) -> None: ...

    def __init__(self, *args, **kwargs) -> None:
        if not args and not kwargs:
            self.characters = ''
            self.highlight = False
            self.bias = Glyph.GlyphBias.NoBias
        else:
            if args:
                if isinstance(args[0], Glyph):
                    self.characters = args[0].characters
                else:
                    self.characters = str(args[0])
            elif 'chars' in kwargs:
                self.characters = str(kwargs['chars'])
            elif 'other' in kwargs:
                other = kwargs['other']
                if not isinstance(other, Glyph):
                    raise TypeError('The other parameter must be a Glyph')
                self.characters = other.characters
            else:
                raise ValueError('Invalid arguments')
            self.highlight = int(args[1] if len(args) > 1 else kwargs.get('highlight', False))
            self.bias = args[2] if len(args) > 2 else kwargs.get('bias', Glyph.GlyphBias.NoBias)

    @property
    def isPrintable(self) -> bool:
        return len(self.characters) > 0

class GlyphDefs(object):
    NoGlyph = Glyph('')
    Diamond = Glyph('\u2666') # U+2666 (BLACK DIAMOND SUIT)
    DiamondX = Glyph('\u2756') # U+2756 (BLACK DIAMOND MINUS WHITE X)
    Circle = Glyph('\u2022') # U+2022 (BULLET); alternate:  U+25CF (BLACK CIRCLE)
    Triangle = Glyph('\u25B2') # U+25B2 (BLACK UP-POINTING TRIANGLE)
    Square = Glyph('\u25A0') # U+25A0 (BLACK SQUARE)
    Star4Point = Glyph('\u2726') # U+2726 (BLACK FOUR POINTED STAR)
    Star5Point = Glyph('\u2605') # U+2605 (BLACK STAR)
    StarStar = Glyph('**') # Would prefer U+2217 (ASTERISK OPERATOR) but font coverage is poor

    # Research Stations
    Alpha = Glyph('\u0391', highlight=True)
    Beta = Glyph('\u0392', highlight=True)
    Gamma = Glyph('\u0393', highlight=True)
    Delta = Glyph('\u0394', highlight=True)
    Epsilon = Glyph('\u0395', highlight=True)
    Zeta = Glyph('\u0396', highlight=True)
    Eta = Glyph('\u0397', highlight=True)
    Theta = Glyph('\u0398', highlight=True)
    Omicron = Glyph('\u039F', highlight=True)

    # Other Textual
    Prison = Glyph('P', highlight=True)
    Reserve = Glyph('R')
    ExileCamp = Glyph('X')

    # TNE
    HiverSupplyBase = Glyph('\u2297')
    Terminus = Glyph('\u2297')
    Interface = Glyph('\u2297')

    _ResearchCodeMap = {
        'A': Alpha,
        'B': Beta,
        'G': Gamma,
        'D': Delta,
        'E': Epsilon,
        'Z': Zeta,
        'H': Eta,
        'T': Theta,
        'O': Omicron}

    @staticmethod
    def fromResearchStation(researchStation: str) -> Glyph:
        glyph = GlyphDefs.Gamma
        if researchStation:
            glyph = GlyphDefs._ResearchCodeMap.get(researchStation, glyph)
        return glyph

    @staticmethod
    def _compileGlyphRegex(wildcard: str) -> re.Pattern:
        return re.compile(fnmatch.translate(wildcard))

    _BaseGlyphs: typing.List[typing.Tuple[re.Pattern, Glyph]] = [
        (_compileGlyphRegex(r'*.C'), Glyph(StarStar, bias=Glyph.GlyphBias.Bottom)), # Vargr Corsair Base
        (_compileGlyphRegex(r'Im.D'), Glyph(Square, bias=Glyph.GlyphBias.Bottom)), # Imperial Depot
        (_compileGlyphRegex(r'*.D'), Glyph(Square, highlight=True)), # Depot
        (_compileGlyphRegex(r'*.E'), Glyph(StarStar, bias=Glyph.GlyphBias.Bottom)), # Hiver Embassy
        (_compileGlyphRegex(r'*.K'), Glyph(Star5Point, highlight=True, bias=Glyph.GlyphBias.Top)), # Naval Base
        (_compileGlyphRegex(r'*.M'), Glyph(Star4Point, bias=Glyph.GlyphBias.Bottom)), # Military Base
        (_compileGlyphRegex(r'*.N'), Glyph(Star5Point, bias=Glyph.GlyphBias.Top)), # Imperial Naval Base
        (_compileGlyphRegex(r'*.O'), Glyph(Square, highlight=True, bias=Glyph.GlyphBias.Top)), # K'kree Naval Outpost (non-standard)
        (_compileGlyphRegex(r'*.R'), Glyph(StarStar, bias=Glyph.GlyphBias.Bottom)), # Aslan Clan Base
        (_compileGlyphRegex(r'*.S'), Glyph(Triangle, bias=Glyph.GlyphBias.Bottom)), # Imperial Scout Base
        (_compileGlyphRegex(r'*.T'), Glyph(Star5Point, highlight=True, bias=Glyph.GlyphBias.Top)), # Aslan Tlaukhu Base
        (_compileGlyphRegex(r'*.V'), Glyph(Circle, bias=Glyph.GlyphBias.Bottom)), # Exploration Base
        (_compileGlyphRegex(r'Zh.W'), Glyph(Diamond, highlight=True)), # Zhodani Relay Station
        (_compileGlyphRegex(r'*.W'), Glyph(Triangle, highlight=True, bias=Glyph.GlyphBias.Bottom)), # Imperial Scout Waystation
        (_compileGlyphRegex(r'Zh.Z'), Diamond), # Zhodani Base (Special case for "Zh.KM")
        # For TNE
        (_compileGlyphRegex(r'Sc.H'), HiverSupplyBase), # Hiver Supply Base
        (_compileGlyphRegex(r'*.I'), Interface), # Interface
        (_compileGlyphRegex(r'*.T'), Terminus), # Terminus
        # Fallback
        (_compileGlyphRegex(r'*.*'), Circle)] # Independent Base

    @staticmethod
    def fromBaseCode(allegiance: str, code: str) -> Glyph:
        for regex, glyph in GlyphDefs._BaseGlyphs:
            if regex.match(allegiance + '.' + code):
                return glyph
        return GlyphDefs.Circle