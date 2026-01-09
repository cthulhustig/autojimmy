import common
import enum
import multiverse
import typing

class SectorTagging(object):
    class Tag(enum.Enum):
        Official = 'Official'
        Preserve = 'Preserve'
        InReview = 'InReview'
        Unreviewed = 'Unreviewed'
        Apocryphal = 'Apocryphal'
    _TagStringMap = {e.value.lower(): e for e in Tag}

    def __init__(
            self,
            dbTags: typing.Optional[typing.Collection[multiverse.DbTag]]
            ) -> None:
        self._tags = common.OrderedSet[SectorTagging.Tag]()
        if dbTags:
            for dbTag in dbTags:
                tag = SectorTagging._TagStringMap.get(dbTag.tag().lower())
                if tag:
                    self._tags.add(tag)

    def contains(self, tag: Tag) -> bool:
        return tag in self._tags

