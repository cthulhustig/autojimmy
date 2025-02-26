import collections
import typing

K = typing.TypeVar('K')  # Key type
V = typing.TypeVar('V')  # Value type
T = typing.TypeVar('D')  # Default value type

class LRUCache(typing.Generic[K, V]):
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._mapping = collections.OrderedDict()

    def put(
            self,
            key: K,
            value: V
            ) -> None:
        if key in self._mapping:
            self._mapping.move_to_end(key)
        elif len(self._mapping) >= self._capacity:
            self._mapping.popitem(False)
        self._mapping[key] = value

    # TODO: Multiple typevars in the return type might require Python 3.9.
    # If so this will need an update to the main md file
    def get(self, key: K, default: T = None) -> typing.Union[V, T]:
        if key not in self._mapping:
            return default
        self._mapping.move_to_end(key)
        return self._mapping[key]

    def remove(self, key: K) -> None:
        if key not in self._mapping:
            raise KeyError('Key "{key}" is not in the cache')
        del self._mapping[key]

    def clear(self) -> None:
        self._mapping.clear()

    def isFull(self) -> bool:
        return len(self._mapping) >= self._capacity

    def pop(self) -> typing.Tuple[K, V]:
        return self._mapping.popitem(False)

    def ensureCapacity(self, capacity: int) -> None:
        if capacity > self._capacity:
            self._capacity = capacity

    def __contains__(self, key: K) -> bool:
        return key in self._mapping

    def __setitem__(self, key: K, value: V) -> None:
        self.put(key, value)

    def __getitem__(self, key: K) -> typing.Any:
        if key not in self._mapping:
            raise KeyError('Key "{key}" is not in the cache')
        self._mapping.move_to_end(key)
        return self._mapping[key]

    def __repr__(self) -> str:
        return repr(self._mapping)

    def __len__(self):
        return len(self._mapping)

    def __delitem__(self, key: K) -> None:
        self.remove(key)
