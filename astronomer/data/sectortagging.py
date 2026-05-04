import common
import enum
import typing

class SectorTag(enum.Enum):
    Official = 'Official'
    Preserve = 'Preserve'
    InReview = 'InReview'
    Unreviewed = 'Unreviewed'
    Apocryphal = 'Apocryphal'
_TagStringMap = {e.value.lower(): e for e in SectorTag}

def stringToSectorTag(string: str) -> typing.Optional[SectorTag]:
    return _TagStringMap.get(string.lower())

class SectorTagging(object):
    def __init__(
            self,
            tags: typing.Optional[typing.Collection[SectorTag]] = None
            ) -> None:
        self._tags = common.OrderedSet(tags) if tags else common.OrderedSet()

    def contains(self, tag: SectorTag) -> bool:
        return tag in self._tags

