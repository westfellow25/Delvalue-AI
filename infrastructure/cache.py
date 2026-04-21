"""
DelValue AI — Caching Layer

Thread-safe in-memory LRU cache with TTL support.
Designed to swap out for Redis in production via the same interface.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from functools import wraps
from threading import Lock
from typing import Any, Callable, Optional


class TTLCache:
    """Thread-safe TTL-aware LRU cache."""

    def __init__(self, max_size: int = 10_000):
        self._data: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = Lock()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self.misses += 1
                return None
            value, expires_at = entry
            if time.time() >= expires_at:
                del self._data[key]
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        with self._lock:
            expires_at = time.time() + ttl_seconds
            self._data[key] = (value, expires_at)
            self._data.move_to_end(key)
            while len(self._data) > self.max_size:
                self._data.popitem(last=False)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [k for k in self._data if k.startswith(prefix)]
            for k in keys:
                del self._data[k]
            return len(keys)

    def stats(self) -> dict:
        total = self.hits + self.misses
        hit_rate = (self.hits / total) if total > 0 else 0.0
        with self._lock:
            return {
                "size": len(self._data),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
            }

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


_default_cache = TTLCache()


def get_cache() -> TTLCache:
    return _default_cache


def cache_key(*parts: Any) -> str:
    """Build a deterministic cache key from arbitrary parts."""
    serialized = json.dumps([str(p) for p in parts], sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:32]


def cached(ttl_seconds: int = 3600, key_prefix: str = "") -> Callable:
    """Decorator for caching function results."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, *kwargs.items())}"
            hit = _default_cache.get(key)
            if hit is not None:
                return hit
            result = func(*args, **kwargs)
            _default_cache.set(key, result, ttl_seconds=ttl_seconds)
            return result

        return wrapper

    return decorator
