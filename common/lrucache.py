import collections
import typing

class LRUCache(object):
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._mapping = dict()
        self._order = collections.deque()

    def put(
            self,
            key: typing.Any,
            value: typing.Any
            ) -> None:
        if key in self._mapping:
            self._order.remove(key)
        if len(self._order) >= self._capacity:
            oldest = self._order.popleft()
            del self._mapping[oldest]
        self._mapping[key] = value
        self._order.append(key)

    def get(self, key: typing.Any, default: typing.Any = None) -> typing.Any:
        if key not in self._mapping:
            return default
        self._order.remove(key)
        self._order.append(key)
        return self._mapping[key]

    def remove(self, key: typing.Any) -> None:
        if key not in self._mapping:
            raise KeyError('Key "{key}" is not in the cache')
        del self._mapping[key]
        self._order.remove(key)

    def clear(self) -> None:
        self._mapping.clear()
        self._order.clear()

    def __contains__(self, key: typing.Any) -> bool:
        return key in self._mapping

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        self.put(key, value)

    def __getitem__(self, key: typing.Any) -> typing.Any:
        if key not in self._mapping:
            raise KeyError('Key "{key}" is not in the cache')
        self._order.remove(key)
        self._order.append(key)
        return self._mapping[key]

    def __repr__(self) -> str:
        s = '{'

        first = True
        for key in reversed(self._order):
            if not first:
                s += ', '
            first = False

            s += repr(key)
            s += ':'
            s += repr(self._mapping[key])

        s += '}'
        return s

    def __len__(self):
        return len(self._mapping)

    def __delitem__(self, key: typing.Any) -> None:
        self.remove(key)
