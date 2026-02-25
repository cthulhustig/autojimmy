import typing

_T = typing.TypeVar("_T")

class OrderedSet(typing.Generic[_T]):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, iterable: typing.Iterable[_T]) -> None: ...

    def __init__(self, iterable: typing.Optional[typing.Iterable[_T]] = None) -> None:
        self._dict = dict.fromkeys(iterable) if iterable is not None else dict()

    def add(self, element: _T) -> None:
        self._dict[element] = None

    def clear(self) -> None:
        self._dict.clear()

    def copy(self) -> 'OrderedSet[_T]':
        return OrderedSet(iterable=self._dict.keys())

    def discard(self, element: _T) -> None:
        self._dict.pop(element, None)

    def remove(self, element: _T) -> None:
        del self._dict[element]

    def __len__(self) -> int:
        return len(self._dict)

    def __contains__(self, element: object) -> bool:
        return element in self._dict

    def __iter__(self) -> typing.Iterator[_T]:
        return iter(self._dict.keys())

    def __eq__(self, value: object) -> bool:
        if isinstance(value, OrderedSet):
            return self._dict == value._dict
        if isinstance(value, list):
            if len(self._dict) != len(value):
                return False
            for v in value:
                if v not in self._dict:
                    return False
            return True
        if isinstance(value, set):
            return self._dict.keys() == value
        return NotImplemented

    def __str__(self) -> str:
        return '{{{contents}}}'.format(contents=', '.join(map(str, self._dict.keys())))
