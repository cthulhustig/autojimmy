import common
import typing

class SectorTagging(object):
    def __init__(
            self,
            tags: typing.Optional[typing.Collection[str]] = None
            ) -> None:
        common.validateOptionalCollection(name='tags', value=tags, elementType=str)

        self._tags = list(tags) if tags else []
        self._lowerCaseTags = None

    def tags(self) -> typing.Collection[str]:
        return common.ConstCollectionRef(self._tags)

    def contains(self, tag: str) -> bool:
        if self._lowerCaseTags is None:
            self._lowerCaseTags = common.OrderedSet(tag.lower() for tag in self._tags)
        return tag.lower() in self._lowerCaseTags

    def hasOfficial(self) -> bool:
        if self._lowerCaseTags is None:
            self._lowerCaseTags = common.OrderedSet(tag.lower() for tag in self._tags)
        return 'official' in self._lowerCaseTags

    def hasPreserve(self) -> bool:
        if self._lowerCaseTags is None:
            self._lowerCaseTags = common.OrderedSet(tag.lower() for tag in self._tags)
        return 'preserve' in self._lowerCaseTags

    def hasInReview(self) -> bool:
        if self._lowerCaseTags is None:
            self._lowerCaseTags = common.OrderedSet(tag.lower() for tag in self._tags)
        return 'inreview' in self._lowerCaseTags

    def hasUnreviewed(self) -> bool:
        if self._lowerCaseTags is None:
            self._lowerCaseTags = common.OrderedSet(tag.lower() for tag in self._tags)
        return 'unreviewed' in self._lowerCaseTags

    def hasApocryphal(self) -> bool:
        if self._lowerCaseTags is None:
            self._lowerCaseTags = common.OrderedSet(tag.lower() for tag in self._tags)
        return 'apocryphal' in self._lowerCaseTags
