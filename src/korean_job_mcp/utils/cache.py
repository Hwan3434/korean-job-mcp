from __future__ import annotations
import time
from typing import Any, Optional


class TTLCache:
    """Simple in-memory TTL cache."""

    def __init__(self, ttl_seconds: int = 1800):
        self._store: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.time() + self._ttl)

    def clear(self) -> None:
        self._store.clear()


# Shared cache instance (30 min TTL)
cache = TTLCache(ttl_seconds=1800)
