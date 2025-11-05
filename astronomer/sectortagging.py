import enum
import typing

class SectorTagging(object):
    class Tag(enum.Enum):
        Official = 'Official'
        Preserve = 'Preserve'
        InReview = 'InReview'
        Unreviewed = 'Unreviewed'
        Apocryphal = 'Apocryphal'
    _TagStringMap = {e.value.lower(): e for e in Tag}

    def __init__(self, string: typing.Optional[str]) -> None:
        self._string = string if string is not None else ''
        self._tags = SectorTagging._parseTags(self._string)

    def string(self) -> str:
        return self._string

    def sanitised(self) -> str:
        return ' '.join(SectorTagging._TagStringMap[e].value for e in self._tags)

    def contains(self, tag: Tag) -> bool:
        return tag in self._tags

    @staticmethod
    def _parseTags(tags: str) -> typing.Set[Tag]:
        parsed = set()
        for s in tags.lower().split():
            tag = SectorTagging._TagStringMap.get(s)
            if tag is not None:
                parsed.add(tag)
        return parsed
