import common
import typing

class SectorSource(object):
    def __init__(
            self,
            publication: typing.Optional[str],
            author: typing.Optional[str],
            publisher: typing.Optional[str],
            reference: typing.Optional[str]
            ) -> None:
        common.validateStr(name='publication', value=publication, allowEmpty=False, allowNone=True)
        common.validateStr(name='author', value=author, allowEmpty=False, allowNone=True)
        common.validateStr(name='publisher', value=publisher, allowEmpty=False, allowNone=True)
        common.validateStr(name='reference', value=reference, allowEmpty=False, allowNone=True)

        self._publication = publication
        self._author = author
        self._publisher = publisher
        self._reference = reference

    def publication(self) -> typing.Optional[str]:
        return self._publication

    def author(self) -> typing.Optional[str]:
        return self._author

    def publisher(self) -> typing.Optional[str]:
        return self._publisher

    def reference(self) -> typing.Optional[str]:
        return self._reference
