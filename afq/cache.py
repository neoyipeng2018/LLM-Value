"""File-based API response cache with configurable TTL."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from afq.config import DATA_DIR

CACHE_DIR = DATA_DIR / "cache"


class FileCache:
    """Simple file-based cache that stores JSON responses with a TTL."""

    def __init__(self, ttl_hours: int = 24, cache_dir: Path | None = None):
        self.ttl_seconds = ttl_hours * 3600
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        hashed = hashlib.sha256(key.encode()).hexdigest()[:16]
        safe_prefix = "".join(c if c.isalnum() else "_" for c in key[:60])
        return self.cache_dir / f"{safe_prefix}_{hashed}.json"

    def get(self, key: str) -> dict | list | None:
        """Return cached value if it exists and hasn't expired, else None."""
        path = self._key_to_path(key)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

        if time.time() - data.get("_cached_at", 0) > self.ttl_seconds:
            path.unlink(missing_ok=True)
            return None

        return data.get("value")

    def set(self, key: str, value: dict | list) -> None:
        """Store a value in the cache."""
        path = self._key_to_path(key)
        payload = {"_cached_at": time.time(), "value": value}
        path.write_text(json.dumps(payload, default=str))

    def clear(self) -> int:
        """Remove all cached files. Returns count of files removed."""
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        return count
