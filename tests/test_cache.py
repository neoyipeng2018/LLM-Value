"""Tests for the file-based cache."""

import json
import time

from afq.cache import FileCache


class TestFileCache:
    def test_set_and_get(self, tmp_cache):
        tmp_cache.set("test_key", {"foo": "bar"})
        result = tmp_cache.get("test_key")
        assert result == {"foo": "bar"}

    def test_get_missing_key(self, tmp_cache):
        result = tmp_cache.get("nonexistent")
        assert result is None

    def test_ttl_expiry(self, tmp_path):
        cache = FileCache(ttl_hours=0, cache_dir=tmp_path)  # 0 hours = immediate expiry
        cache.set("expires", {"data": 1})
        # Sleep just past 0 seconds TTL
        time.sleep(0.01)
        result = cache.get("expires")
        assert result is None

    def test_stores_list(self, tmp_cache):
        data = [{"ticker": "AAPL"}, {"ticker": "MSFT"}]
        tmp_cache.set("stocks", data)
        result = tmp_cache.get("stocks")
        assert len(result) == 2
        assert result[0]["ticker"] == "AAPL"

    def test_clear(self, tmp_cache):
        tmp_cache.set("a", {"x": 1})
        tmp_cache.set("b", {"y": 2})
        count = tmp_cache.clear()
        assert count == 2
        assert tmp_cache.get("a") is None
        assert tmp_cache.get("b") is None

    def test_corrupt_file_returns_none(self, tmp_cache):
        tmp_cache.set("corrupt", {"data": 1})
        # Corrupt the file
        path = tmp_cache._key_to_path("corrupt")
        path.write_text("not valid json{{{")
        result = tmp_cache.get("corrupt")
        assert result is None

    def test_different_keys_no_collision(self, tmp_cache):
        tmp_cache.set("key_one", {"v": 1})
        tmp_cache.set("key_two", {"v": 2})
        assert tmp_cache.get("key_one") == {"v": 1}
        assert tmp_cache.get("key_two") == {"v": 2}
