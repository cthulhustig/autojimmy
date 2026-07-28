import common
import re
import typing

# NOTE: This code is a little hacky due to the "odd" way Traveller Map
# metadata uses hexes in paths & label position for regions and borders.
# The hexes of a sector are indexed 1-32 in X and 1-40 in Y, and only
# hexes in those ranges are valid for system positions. However, the
# Traveller Map metadata definition allows paths & label positions to
# use the range 0-33 in X and 0-41 in Y.
# For paths this is used to allow borders/regions that extend outside
# a sector to still be closed polygons so they can be filled. When a
# border/region leaves a sector the path loops round the outside of the
# sector in this invalid border space until it gets to the point where
# border/region "re-enters" the sector.
# Why the hexes used for label positions also need to be placed in this
# invalid border space I don't know. I think it might be so, when a
# small border/region spans multiple sectors, a label can be placed in
# this region for one sector then in the corresponding valid hex in the
# adjacent sector. This allows both sectors to have the label for if they
# get drawn stand alone, but means you don't get 2 copies of the label
# half overlap when drawn together. I'm not sure about this though as
# it feels like the same thing could be achieved using the world space
# label offsets.

_HexPattern = re.compile(r'(\d{2})(\d{2})')
_MinHexX = 1
_MaxHexX = 32
_MinHexY = 1
_MaxHexY = 40

def parseHexString(
        string: str,
        allowInvalid: bool = False, # Used for Border/Region Label & Path Hexes
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Tuple[
            typing.Optional[int],
            typing.Optional[int]]:
    result = _HexPattern.match(string)
    if not result:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Hex string "{string}"')
        return (None, None)

    minX = _MinHexX
    maxX = _MaxHexX
    minY = _MinHexY
    maxY = _MaxHexY
    if allowInvalid:
        minX -= 1
        maxX += 1
        minY -= 1
        maxY += 1

    x = int(result[1])
    if x < minX or x > maxX:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Hex X value "{result[1]}"')
        x = None

    y = int(result[2])
    if y < minY or y > maxY:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Hex Y value "{result[2]}"')
        y = None

    return (x, y)

def formatHexString(
        x: int,
        y: int,
        allowInvalid: bool = False, # Used for Border/Region Label & Path Hexes
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    minX = _MinHexX
    maxX = _MaxHexX
    minY = _MinHexY
    maxY = _MaxHexY
    if allowInvalid:
        minX -= 1
        maxX += 1
        minY -= 1
        maxY += 1

    if x < minX or x > maxX:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Hex X value "{x}"')
        x = None

    if y < minY or y > maxY:
        if reporter:
            reporter.addMessage(f'Ignoring invalid Hex Y value "{y}"')
        y = None

    if x is None or y is None:
        return None

    return f'{x:02d}{y:02d}'

def parseHexListString(
        string: str,
        allowInvalid: bool = False, # Used for Border/Region Label & Path Hexes
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
    hexes = []
    for index, hex in enumerate(string.split(' ')):
        x, y = parseHexString(string=hex, allowInvalid=allowInvalid, reporter=reporter)
        if x is None or y is None:
            if reporter:
                reporter.addMessage(f'Ignoring Hex List with invalid hex "{hex}" at index {index}')
            return None
        hexes.append((x, y))
    return hexes

def formatHexListString(
        hexes: typing.Iterable[typing.Tuple[int, int]],
        allowInvalid: bool = False, # Used for Border/Region Label & Path Hexes
        reporter: typing.Optional[common.Reporter] = None
        ) -> typing.Optional[str]:
    strings = []
    for index, (x, y) in enumerate(hexes):
        hex = formatHexString(x=x, y=y, allowInvalid=allowInvalid, reporter=reporter)
        if hex is None:
            if reporter:
                reporter.addMessage(f'Ignoring Hex List with invalid hex "{x}, {y}" at index {index}')
            return None
        strings.append(hex)
    return ' '.join(strings)

def validateHexX(
        name: str,
        value: typing.Optional[int],
        allowNone: bool = False,
        allowInvalid: bool = False, # Used for Border/Region Label & Path Hexes
        ) -> typing.Optional[int]:
    return common.validateInt(
        name=name,
        value=value,
        allowNone=allowNone,
        min=_MinHexX if not allowInvalid else _MinHexX - 1,
        max=_MaxHexX if not allowInvalid else _MaxHexX + 1)

def validateHexY(
        name: str,
        value: typing.Optional[int],
        allowNone: bool = False,
        allowInvalid: bool = False, # Used for Border/Region Label & Path Hexes
        ) -> typing.Optional[int]:
    return common.validateInt(
        name=name,
        value=value,
        allowNone=allowNone,
        min=_MinHexY if not allowInvalid else _MinHexY - 1,
        max=_MaxHexY if not allowInvalid else _MaxHexY + 1)

def validateHexCollection(
        name: str,
        value: typing.Optional[typing.Collection[typing.Tuple[int, int]]],
        allowNone: bool = False,
        allowEmpty: bool = True,
        allowInvalid: bool = False, # Used for Border/Region Label & Path Hexes
        ) -> typing.Optional[typing.Collection[typing.Tuple[int, int]]]:
    return common.validateCollection(
        name=name,
        value=value,
        allowNone=allowNone,
        allowEmpty=allowEmpty,
        validationFn=lambda n, i, v: _validateHexTuple(n, i, v, allowInvalid))

@staticmethod
def _validateHexTuple(
        name: str,
        index: int,
        value: typing.Tuple[int, int],
        allowInvalid: bool = False, # Used for Border/Region Label & Path Hexes
        ) -> None:
    if len(value) != 2:
        raise ValueError(f'{name} should contain tuples containing 2 integers')
    common.validateInt(
        name=f'{name}[{index}]\\X',
        value=value[0],
        min=_MinHexX if not allowInvalid else _MinHexX - 1,
        max=_MaxHexX if not allowInvalid else _MaxHexX + 1)
    common.validateInt(
        name=f'{name}[{index}]\\Y',
        value=value[1],
        min=_MinHexY if not allowInvalid else _MinHexY - 1,
        max=_MaxHexY if not allowInvalid else _MaxHexY + 1)