import typing

class SectorSource(object):
    def __init__(
            self,
            publication: typing.Optional[str],
            author: typing.Optional[str],
            publisher: typing.Optional[str],
            reference: typing.Optional[str]
            ) -> None:
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

class SectorSources(object):
    def __init__(
            self,
            credits: typing.Optional[str],
            primary: typing.Optional[SectorSource],
            products: typing.Optional[typing.Collection[SectorSource]]
            ) -> None:
        self._credits = credits
        self._primary = primary
        self._products = list(products) if products else list()

    def credits(self) -> typing.Optional[str]:
        return self._credits

    def primary(self) -> typing.Optional[SectorSource]:
        return self._primary

    def products(self) -> typing.List[SectorSource]:
        return list(self._products)
