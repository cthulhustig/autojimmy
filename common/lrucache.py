import collections
import typing

class LRUCache(object):
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._mapping = collections.OrderedDict()

    def put(
            self,
            key: typing.Any,
            value: typing.Any
            ) -> None:
        if key in self._mapping:
            self._mapping.move_to_end(key)
        elif len(self._mapping) >= self._capacity:
            self._mapping.popitem(False)
        self._mapping[key] = value

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        if key not in self._mapping:
            return default
        self._mapping.move_to_end(key)
        return self._mapping[key]

    def remove(self, key: typing.Any) -> None:
        if key not in self._mapping:
            raise KeyError('Key "{key}" is not in the cache')
        del self._mapping[key]

    def clear(self) -> None:
        self._mapping.clear()

    def __contains__(self, key: typing.Any) -> bool:
        return key in self._mapping

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        self.put(key, value)

    def __getitem__(self, key: typing.Any) -> typing.Any:
        if key not in self._mapping:
            raise KeyError('Key "{key}" is not in the cache')
        self._mapping.move_to_end(key)
        return self._mapping[key]

    def __repr__(self) -> str:
        return repr(self._mapping)

    def __len__(self):
        return len(self._mapping)

    def __delitem__(self, key: typing.Any) -> None:
        self.remove(key)
