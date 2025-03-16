import common
import math
import typing

class HtmlColors(object):
    TravellerRed = '#E32736'
    TravellerAmber = '#FFCC00'
    TravellerGreen = '#048104'

    AliceBlue = '#F0F8FF'
    AntiqueWhite = '#FAEBD7'
    Aqua = '#00FFFF'
    Aquamarine = '#7FFFD4'
    Azure = '#F0FFFF'
    Beige = '#F5F5DC'
    Bisque = '#FFE4C4'
    Black = '#000000'
    BlanchedAlmond = '#FFEBCD'
    Blue = '#0000FF'
    BlueViolet = '#8A2BE2'
    Brown = '#A52A2A'
    BurlyWood = '#DEB887'
    CadetBlue = '#5F9EA0'
    Chartreuse = '#7FFF00'
    Chocolate = '#D2691E'
    Coral = '#FF7F50'
    CornflowerBlue = '#6495ED'
    Cornsilk = '#FFF8DC'
    Crimson = '#DC143C'
    Cyan = '#00FFFF'
    DarkBlue = '#00008B'
    DarkCyan = '#008B8B'
    DarkGoldenrod = '#B8860B'
    DarkGray = '#A9A9A9'
    DarkGreen = '#006400'
    DarkKhaki = '#BDB76B'
    DarkMagenta = '#8B008B'
    DarkOliveGreen = '#556B2F'
    DarkOrange = '#FF8C00'
    DarkOrchid = '#9932CC'
    DarkRed = '#8B0000'
    DarkSalmon = '#E9967A'
    DarkSeaGreen = '#8FBC8F'
    DarkSlateBlue = '#483D8B'
    DarkSlateGray = '#2F4F4F'
    DarkTurquoise = '#00CED1'
    DarkViolet = '#9400D3'
    DeepPink = '#FF1493'
    DeepSkyBlue = '#00BFFF'
    DimGray = '#696969'
    DodgerBlue = '#1E90FF'
    Firebrick = '#B22222'
    FloralWhite = '#FFFAF0'
    ForestGreen = '#228B22'
    Fuchsia = '#FF00FF'
    Gainsboro = '#DCDCDC'
    GhostWhite = '#F8F8FF'
    Gold = '#FFD700'
    Goldenrod = '#DAA520'
    Gray = '#808080'
    Green = '#008000'
    GreenYellow = '#ADFF2F'
    Honeydew = '#F0FFF0'
    HotPink = '#FF69B4'
    IndianRed = '#CD5C5C'
    Indigo = '#4B0082'
    Ivory = '#FFFFF0'
    Khaki = '#F0E68C'
    Lavender = '#E6E6FA'
    LavenderBlush = '#FFF0F5'
    LawnGreen = '#7CFC00'
    LemonChiffon = '#FFFACD'
    LightBlue = '#ADD8E6'
    LightCoral = '#F08080'
    LightCyan = '#E0FFFF'
    LightGoldenrodYellow = '#FAFAD2'
    LightGray = '#D3D3D3'
    LightGreen = '#90EE90'
    LightPink = '#FFB6C1'
    LightSalmon = '#FFA07A'
    LightSeaGreen = '#20B2AA'
    LightSkyBlue = '#87CEFA'
    LightSlateGray = '#778899'
    LightSteelBlue = '#B0C4DE'
    LightYellow = '#FFFFE0'
    Lime = '#00FF00'
    LimeGreen = '#32CD32'
    Linen = '#FAF0E6'
    Magenta = '#FF00FF'
    Maroon = '#800000'
    MediumAquamarine = '#66CDAA'
    MediumBlue = '#0000CD'
    MediumOrchid = '#BA55D3'
    MediumPurple = '#9370DB'
    MediumSeaGreen = '#3CB371'
    MediumSlateBlue = '#7B68EE'
    MediumSpringGreen = '#00FA9A'
    MediumTurquoise = '#48D1CC'
    MediumVioletRed = '#C71585'
    MidnightBlue = '#191970'
    MintCream = '#F5FFFA'
    MistyRose = '#FFE4E1'
    Moccasin = '#FFE4B5'
    NavajoWhite = '#FFDEAD'
    Navy = '#000080'
    OldLace = '#FDF5E6'
    Olive = '#808000'
    OliveDrab = '#6B8E23'
    Orange = '#FFA500'
    OrangeRed = '#FF4500'
    Orchid = '#DA70D6'
    PaleGoldenrod = '#EEE8AA'
    PaleGreen = '#98FB98'
    PaleTurquoise = '#AFEEEE'
    PaleVioletRed = '#DB7093'
    PapayaWhip = '#FFEFD5'
    PeachPuff = '#FFDAB9'
    Peru = '#CD853F'
    Pink = '#FFC0CB'
    Plum = '#DDA0DD'
    PowderBlue = '#B0E0E6'
    Purple = '#800080'
    Red = '#FF0000'
    RosyBrown = '#BC8F8F'
    RoyalBlue = '#4169E1'
    SaddleBrown = '#8B4513'
    Salmon = '#FA8072'
    SandyBrown = '#F4A460'
    SeaGreen = '#2E8B57'
    SeaShell = '#FFF5EE'
    Sienna = '#A0522D'
    Silver = '#C0C0C0'
    SkyBlue = '#87CEEB'
    SlateBlue = '#6A5ACD'
    SlateGray = '#708090'
    Snow = '#FFFAFA'
    SpringGreen = '#00FF7F'
    SteelBlue = '#4682B4'
    Tan = '#D2B48C'
    Teal = '#008080'
    Thistle = '#D8BFD8'
    Tomato = '#FF6347'
    Turquoise = '#40E0D0'
    Violet = '#EE82EE'
    Wheat = '#F5DEB3'
    White = '#FFFFFF'
    WhiteSmoke = '#F5F5F5'
    Yellow = '#FFFF00'
    YellowGreen = '#9ACD32'

#[k for k, v in vars(CONSTANT).items() if not callable(v) and not k.startswith("__")]
_NameToColorMap = {name.lower(): color for name, color in common.getClassVariables(HtmlColors).items()}

def parseHtmlColor(
        htmlColor: str
        ) -> typing.Tuple[
            int, # Red
            int, # Green
            int, # Blue
            int, # Alpha
        ]:
    length = len(htmlColor)
    if not length:
        raise ValueError(f'Invalid color "{htmlColor}"')
    if htmlColor[0] != '#':
        namedColor = _NameToColorMap.get(htmlColor.lower())
        if not namedColor:
            raise ValueError(f'Invalid color "{htmlColor}"')
        htmlColor = namedColor
        length = len(namedColor)

    if length == 7:
        try:
            alpha = 255
            red = int(htmlColor[1:3], 16)
            green = int(htmlColor[3:5], 16)
            blue = int(htmlColor[5:7], 16)
        except:
            raise ValueError(f'Invalid color "{htmlColor}"')
    elif length == 9:
        try:
            alpha = int(htmlColor[1:3], 16)
            red = int(htmlColor[3:5], 16)
            green = int(htmlColor[5:7], 16)
            blue = int(htmlColor[7:9], 16)
        except:
            raise ValueError(f'Invalid color "{htmlColor}"')
    else:
        raise ValueError(f'Invalid color "{htmlColor}"')

    return (red, green, blue, alpha)

def formatHtmlColor(red: int, green: int, blue: int, alpha: int = 255) -> str:
    return f'#{alpha:02X}{red:02X}{green:02X}{blue:02X}'

def _convertRGBtoXYZ(r: int, g: int, b: int) -> typing.Tuple[float, float, float]:
    rl = r / 255.0
    gl = g / 255.0
    bl = b / 255.0

    sr = math.pow((rl + 0.055) / (1 + 0.055), 2.2) if rl > 0.04045 else (rl / 12.92)
    sg = math.pow((gl + 0.055) / (1 + 0.055), 2.2) if gl > 0.04045 else (gl / 12.92)
    sb = math.pow((bl + 0.055) / (1 + 0.055), 2.2) if bl > 0.04045 else (bl / 12.92)

    return (
        sr * 0.4124 + sg * 0.3576 + sb * 0.1805, # x
        sr * 0.2126 + sg * 0.7152 + sb * 0.0722, # y
        sr * 0.0193 + sg * 0.1192 + sb * 0.9505) # z

def _calculateFxyz(t: float) -> float:
    return math.pow(t, (1.0 / 3.0)) if t > 0.008856 else (7.787 * t + 16.0 / 116.0)

def _convertXYZtoLab(x: float, y: float, z: float) -> typing.Tuple[float, float, float]:
    D65X = 0.9505
    D65Y = 1.0
    D65Z = 1.0890
    return (
        116.0 * _calculateFxyz(y / D65Y) - 16, # l
        500.0 * (_calculateFxyz(x / D65X) - _calculateFxyz(y / D65Y)), # a
        200.0 * (_calculateFxyz(y / D65Y) - _calculateFxyz(z / D65Z))) # b

def _deltaE76(l1: float, a1: float, b1: float, l2: float, a2: float, b2: float) -> float:
    c1 = l1 - l2
    c2 = a1 - a2
    c3 = b1 - b2
    return math.sqrt(c1 * c1 + c2 * c2 + c3 * c3)

def noticeableColorDifference(a: str, b: str) -> bool:
    JND = 13 # 2.3

    aRed, aGreen, aBlue, _ = parseHtmlColor(a)
    bRed, bGreen, bBlue, _ = parseHtmlColor(b)

    ax, ay, az = _convertRGBtoXYZ(aRed, aGreen, aBlue)
    bx, by, bz = _convertRGBtoXYZ(bRed, bGreen, bBlue)

    al, aa, ab = _convertXYZtoLab(ax, ay, az)
    bl, ba, bb = _convertXYZtoLab(bx, by, bz)

    return _deltaE76(al, aa, ab, bl, ba, bb) > JND
