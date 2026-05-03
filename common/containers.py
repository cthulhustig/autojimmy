import collections.abc
import typing

# TODO: There are probably a lot of places that can be updated to use this
# rather than returning a copy of the list. Anywhere I'm doing "return list("
# This should let me get rid of a load of yield accessors.
# IMPORTANT: Need to be careful the caller doesn't expect to be getting a
# mutable copy of the list from the function

T = typing.TypeVar("T")

class ConstSequenceRef(collections.abc.Sequence[T]):
    __slots__ = ("_data",)

    def __init__(self, data: typing.Sequence[T]) -> None:
        # NOTE: This just takes a reference to the existing sequence for performance
        self._data = data

    @typing.overload
    def __getitem__(self, i: int) -> T: ...
    @typing.overload
    def __getitem__(self, i: slice) -> typing.List[T]: ...

    def __getitem__(self, i: typing.Union[int, slice]) -> typing.Union[T, typing.List[T]]:
        return self._data[i]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> typing.Iterator[T]:
        return iter(self._data)

    def __contains__(self, item: object) -> bool:
        return item in self._data