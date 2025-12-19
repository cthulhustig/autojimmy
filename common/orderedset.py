import typing

_T = typing.TypeVar("_T")

class OrderedSet(typing.Generic[_T]):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, iterable: typing.Iterable[_T]) -> None: ...

    def __init__(self, iterable: typing.Optional[typing.Iterable[_T]] = None) -> None:
        self._orderedList = list[_T](iterable) if iterable is not None else list[_T]()
        self._unorderedSet = set[_T](self._orderedList)

    def add(self, element: _T) -> None:
        if element in self._unorderedSet:
            return

        self._unorderedSet.add(element)
        self._orderedList.append(element)

    def clear(self) -> None:
        self._unorderedSet.clear()
        self._orderedList.clear()

    def copy(self) -> 'OrderedSet[_T]':
        return OrderedSet(iterable=self._orderedList)

    def discard(self, element: _T) -> None:
        if element not in self._unorderedSet:
            return

        self._unorderedSet.discard(element)
        self._orderedList.remove(element)

    def pop(self) -> _T:
        element = self._orderedList.pop() # Pop in order
        self._unorderedSet.discard(element)
        return element

    def remove(self, element: _T) -> None:
        self._unorderedSet.remove(element)
        self._orderedList.remove(element)

    def __len__(self) -> int:
        return self._orderedList.__len__()

    def __contains__(self, element: object) -> bool:
        return self._unorderedSet.__contains__(element)

    def __iter__(self) -> typing.Iterator[_T]:
        return self._orderedList.__iter__()

    def __eq__(self, value: object) -> bool:
        if isinstance(value, OrderedSet):
            return self._orderedList.__eq__(value._orderedList)
        if isinstance(value, list):
            return self._orderedList.__eq__(value)
        if isinstance(value, set):
            return self._unorderedSet.__eq__(value)
        return NotImplemented

    def __str__(self) -> str:
        return self._orderedList.__str__()
