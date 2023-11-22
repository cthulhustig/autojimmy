import datetime
import enum
import itertools
import locale
import math
import platform
import re
import typing

def extendEnum(
        baseEnum: typing.Type[enum.Enum],
        names: typing.List[str],
        values: typing.Optional[typing.List[str]] = None
        ) -> enum.Enum:
    if not values:
        values = names

    for item in baseEnum:
        names.append(item.name)
        values.append(item.value)

    return enum.Enum(baseEnum.__name__, dict(zip(names, values)))

def isWindows() -> bool:
    return platform.system() == 'Windows'

def isLinux() -> bool:
    return platform.system() == 'Linux'

def isMacOS() -> bool:
    return platform.system() == 'Darwin'

def formatNumber(
        number: typing.Union[int, float],
        thousandsSeparator: bool = True,
        alwaysIncludeSign: bool = False,
        decimalPlaces: int = 2, # Only applies for float values
        removeTrailingZeros: bool = True, # Only applies for float values
        infinityString: str = 'inf' # Only applies for float values
        ) -> str:
    if number == float('inf'):
        return '+' + infinityString if alwaysIncludeSign else infinityString
    elif number == float('-inf'):
        return '-' + infinityString

    format = f'{{0:{"+" if alwaysIncludeSign else ""}{"," if thousandsSeparator else ""}.{decimalPlaces}f}}'
    string = format.format(number)
    if decimalPlaces and removeTrailingZeros:
        # Strip trailing zeros (and decimal point if needed)
        string = string.rstrip('0')

        # When stripping the decimal point use the local specific character if
        # one is set
        conv = locale.localeconv()
        decimalPoint = None
        if 'decimal_point' in conv:
            decimalPoint = conv['decimal_point']

        # Note that his also catches the case where the locale isn't set so the
        # decimal point character stored in conv is an empty string
        if not decimalPoint:
            decimalPoint = '.'

        string = string.rstrip(decimalPoint)
    return string

def clamp(
        value: typing.Union[float, int],
        minValue: typing.Union[float, int],
        maxValue: typing.Union[float, int]
        ) -> typing.Union[float, int]:
    return max(minValue, min(value, maxValue))

# This is the recommended way get UTC time in Python 3 (rather than using datetime.utcnow)
# https://docs.python.org/3/library/datetime.html#datetime.datetime.utcnow
def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


# List of characters that are illegal in filenames on Windows, Linux and macOS.
# Based on this post https://stackoverflow.com/questions/1976007/what-characters-are-forbidden-in-windows-and-linux-directory-names
_WindowsIllegalCharacters = set(['/', '<', '>', ':', '"', '\\', '|', '?', '*'])
_LinuxIllegalCharacters = set(['/'])
_MacOSIllegalCharacters = set(['/', ':'])

# This is the list of characters that are encoded/decoded to generate a filename that's valid on any
# filesystem. I've added % as filenames containing these characters will be percent escaped
_EncodedCharacters = set(itertools.chain(
    set(['%']),
    _WindowsIllegalCharacters,
    _LinuxIllegalCharacters,
    _MacOSIllegalCharacters))

# Natural sort based on examples here
# https://stackoverflow.com/questions/4836710/is-there-a-built-in-function-for-string-natural-sort
_NaturalSortRegex = re.compile(r'(\d+)')
def naturalSortKey(string: str) -> typing.List[typing.Union[int, str]]:
    return [int(t) if i & 1 else t.lower() for i, t in enumerate(_NaturalSortRegex.split(string))]

def naturalSort(input: typing.Iterable[str]) -> typing.List[str]:
    return sorted(input, key=naturalSortKey)

def encodeFileName(rawFileName: str) -> str:
    escapedFileName = ''
    for index in range(0, len(rawFileName)):
        char = rawFileName[index]
        if char in _EncodedCharacters:
            char = f'%{format(ord(char), "x")}'
        escapedFileName += char
    return escapedFileName

def decodeFileName(encodedFileName: str) -> str:
    rawFileName = ''
    index = 0
    while index < len(encodedFileName):
        found = encodedFileName.find('%', index)
        if found < 0:
            rawFileName += encodedFileName[index:]
            break

        if found > index:
            rawFileName += encodedFileName[index:found]

        codeStart = found + 1
        codeEnd = codeStart + 2
        code = encodedFileName[codeStart:codeEnd]
        if not code:
            raise RuntimeError(f'Encoded file "{encodedFileName}" name contained invalid encoding at {found}')

        try:
            rawFileName += chr(int(code, 16))
        except ValueError:
            raise RuntimeError(f'Encoded file "{encodedFileName}" name contained invalid encoding at {found}')

        index = codeEnd

    return rawFileName

def sanitiseFileName(fileName: str) -> str:
    if isWindows():
        illegalCharacters = _WindowsIllegalCharacters
    elif isLinux():
        illegalCharacters = _LinuxIllegalCharacters
    elif isMacOS():
        illegalCharacters = _MacOSIllegalCharacters
    else:
        return fileName

    result = fileName
    for char in illegalCharacters:
        result = result.replace(char, '')
    return result

def getSubclasses(
        classType: typing.Type[typing.Any],
        topLevelOnly: bool = True
        ):
    subclasses = []

    for subclass in classType.__subclasses__():
        if subclass.__subclasses__():
            if not topLevelOnly:
                subclasses.append(subclass)
            subclasses.extend(getSubclasses(subclass, topLevelOnly))
        else:
            subclasses.append(subclass)

    return subclasses

def humanFriendlyListString(strings: typing.Sequence[str]) -> str:
    count = len(strings)
    if not count:
        return ''
    if count == 1:
        return strings[0]

    result = ''
    for index in range(count - 1):
        if result:
            result += ', '
        result += strings[index]

    result += ' & ' + strings[count - 1]
    return result


_ByteSizeSuffixes = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')
def humanFriendlyByteSizes(byteSize) -> str:
    if byteSize == 0:
        return '0B'
    i = int(math.floor(math.log(byteSize, 1024)))
    if i >= len(_ByteSizeSuffixes):
        return f'{byteSize}B'
    p = math.pow(1024, i)
    s = round(byteSize / p, 2)
    return f'{s}{_ByteSizeSuffixes[i]}'
