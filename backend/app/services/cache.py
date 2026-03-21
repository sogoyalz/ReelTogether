from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Generic, TypeVar

from app.services.redis_store import get_json, set_json

T = TypeVar("T")


@dataclass
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, _CacheEntry[T]] = {}
        self._lock = Lock()

    def get_or_set(self, key: str, factory: Callable[[], T]) -> T:
        redis_value = get_json(key)
        if redis_value is not None:
            return redis_value

        now = time.time()
        with self._lock:
            entry = self._entries.get(key)
            if entry and entry.expires_at > now:
                return entry.value

        value = factory()
        set_json(key, value, self.ttl_seconds)
        with self._lock:
            self._entries[key] = _CacheEntry(value=value, expires_at=now + self.ttl_seconds)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
