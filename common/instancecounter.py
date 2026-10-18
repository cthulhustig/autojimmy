import collections.abc
import typing

T = typing.TypeVar("T")

class InstanceCounter(typing.Generic[T]):
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, iterable: typing.Iterable[T]) -> None: ...

    def __init__(self, iterable: typing.Optional[typing.Iterable[T]] = None) -> None:
        self._dict = {}
        if iterable is not None:
            for element in iterable:
                self.add(element)

    def add(self, element: T) -> None:
        count = self._dict.get(element, 0)
        self._dict[element] = count + 1

    def extend(self, elements: typing.Iterable[T]) -> None:
        for element in elements:
            self.add(element)

    def count(self, element) -> int:
        return self._dict.get(element, 0)

    def clear(self) -> None:
        self._dict.clear()

    def __getitem__(self, element: T) -> typing.Any:
        return self._dict[element]

    def __len__(self) -> int:
        return len(self._dict)

    def __contains__(self, element: T) -> bool:
        return element in self._dict

    def __iter__(self) -> typing.Iterator[T]:
        return iter(self._dict.keys())

    def __eq__(self, value: object) -> bool:
        if isinstance(value, InstanceCounter):
            return self._dict == value._dict
        return NotImplemented

