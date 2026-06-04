import common
import enum
import typing

# TODO: This needs to support arbitrary tags. The fact it doesn't means
# I will loose any tags I don't explicitly cover if the user imports a
# sector then exports it.

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
        common.validateOptionalCollection(name='tags', value=tags, elementType=SectorTag)

        self._tags = common.OrderedSet(tags) if tags else common.OrderedSet()

    def tags(self) -> typing.Collection[SectorTag]:
        return common.ConstCollectionRef(self._tags)

    def contains(self, tag: SectorTag) -> bool:
        return tag in self._tags

