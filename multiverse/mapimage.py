import enum
import typing

# TODO: Most/all off this shouldn't be needed by the time I'm finished. There
# might be a couple of bits that are used in the tooltip code but it could
# probably be moved there (it definitely shouldn't live in multiverse)

# NOTE: The values for this enum should be the standard file extension for that format
class MapFormat(enum.Enum):
    PNG = 'png'
    JPEG = 'jpeg'
    SVG = 'svg'


# NOTE: These values for this map should be lower case
_FormatToMimeType = {
    MapFormat.PNG: 'image/png',
    MapFormat.JPEG: 'image/jpeg',
    MapFormat.SVG: 'image/svg+xml',
}

def mapFormatToMimeType(format: MapFormat) -> str:
    return _FormatToMimeType[format]

def mimeTypeToMapFormat(mimeType: str) -> typing.Optional[MapFormat]:
    mimeType = mimeType.lower()
    for format, otherType in _FormatToMimeType.items():
        if mimeType == otherType:
            return format
    return None

class MapImage(object):
    def __init__(
            self,
            bytes: bytes,
            format: MapFormat
            ) -> None:
        self._bytes = bytes
        self._format = format

    def bytes(self) -> bytes:
        return self._bytes

    def size(self) -> int:
        return len(self._bytes)

    def format(self) -> MapFormat:
        return self._format
