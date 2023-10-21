import enum
import typing

# NOTE: The values for this enum should be the standard file extension for that format
class MapFormat(enum.Enum):
    PNG = 'png'
    JPEG = 'jpeg'

# NOTE: These values for this map should be lower case
_FormatToMimeType = {
    MapFormat.PNG: 'image/png',
    MapFormat.JPEG: 'image/jpeg',
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
