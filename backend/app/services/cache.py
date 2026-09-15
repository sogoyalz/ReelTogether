"""Bounded, process-local caches. Values never outlive their TTL."""
from collections import OrderedDict
from collections.abc import Callable, MutableMapping
from threading import RLock
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


class ExpiringMap(MutableMapping):
    def __init__(self, ttl_seconds=1800, max_entries=512):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries = OrderedDict()
        self._lock = RLock()

    def __getitem__(self, key):
        with self._lock:
            value, expires = self._entries[key]
            if expires <= monotonic():
                del self._entries[key]
                raise KeyError(key)
            return value

    def __setitem__(self, key, value):
        with self._lock:
            self._entries.pop(key, None)
            # Transient missing-provider responses retry sooner than successful data.
            ttl = min(self.ttl_seconds, 30) if value is None else self.ttl_seconds
            self._entries[key] = (value, monotonic() + ttl)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def __delitem__(self, key):
        with self._lock:
            del self._entries[key]

    def __iter__(self):
        with self._lock:
            return iter(list(self._entries))

    def __len__(self):
        with self._lock:
            return len(self._entries)

    def clear(self):
        with self._lock:
            self._entries.clear()


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds=60, max_entries=512):
        self.ttl_seconds = ttl_seconds
        self._entries = ExpiringMap(ttl_seconds, max_entries)

    def get_or_set(self, key: str, factory: Callable[[], T]) -> T:
        try:
            return self._entries[key]
        except KeyError:
            value = factory()
            self._entries[key] = value
            return value

    def clear(self):
        self._entries.clear()
