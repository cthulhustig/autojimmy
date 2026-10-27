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

    def update(self, elements: typing.Union[typing.Iterable[T], 'InstanceCounter[T]']) -> None:
        if isinstance(elements, InstanceCounter):
            for element in elements:
                current = self._dict.get(element, 0)
                self._dict[element] = current + elements.count(element)
        else:
            for element in elements:
                self.add(element)

    def remove(self, element: T) -> int:
        count = self._dict[element] - 1
        if count == 0:
            del self._dict[element]
        else:
            self._dict[element] = count
        return count

    def count(self, element: T) -> int:
        return self._dict.get(element, 0)

    def clear(self) -> None:
        self._dict.clear()

    def min(self) -> typing.List[T]:
        minCount = None
        for count in self._dict.values():
            if minCount is None or count < minCount:
                minCount = count

        elements = []
        for element, count in self._dict.items():
            if count == minCount:
                elements.append(element)
        return elements

    def max(self) -> typing.List[T]:
        maxCount = None
        for count in self._dict.values():
            if maxCount is None or count > maxCount:
                maxCount = count

        elements = []
        for element, count in self._dict.items():
            if count == maxCount:
                elements.append(element)
        return elements

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

