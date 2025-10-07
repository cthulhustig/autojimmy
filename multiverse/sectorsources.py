import typing

class SourceProduct(object):
    def __init__(
            self,
            title: str,
            publisher: str,
            author: typing.Optional[str],
            reference: typing.Optional[str]
            ) -> None:
        self._title = title
        self._publisher = publisher
        self._author = author
        self._reference = reference

    def title(self) -> str:
        return self._title

    def publisher(self) -> str:
        return self._publisher

    def author(self) -> typing.Optional[str]:
        return self._author

    def reference(self) -> typing.Optional[str]:
        return self._reference

class SectorSources(object):
    def __init__(
            self,
            credits: typing.Optional[str],
            source: typing.Optional[str],
            author: typing.Optional[str],
            publisher: typing.Optional[str],
            reference: typing.Optional[str],
            products: typing.Optional[typing.Collection[SourceProduct]]
            ) -> None:
        self._credits = credits
        self._source = source
        self._author = author
        self._publisher = publisher
        self._reference = reference
        self._products = list(products) if products else list()

    def credits(self) -> typing.Optional[str]:
        return self._credits

    def source(self) -> typing.Optional[str]:
        return self._source

    def author(self) -> typing.Optional[str]:
        return self._author

    def publisher(self) -> typing.Optional[str]:
        return self._publisher

    def reference(self) -> typing.Optional[str]:
        return self._reference

    def products(self) -> typing.Optional[typing.List[SourceProduct]]:
        return list(self._products)