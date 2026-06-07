"""Unit tests for backend/app/api/tmdb.py — cache keying, TTL selection, and error handling."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import HTTPException

# We import the module under test; it only needs env vars set.
import os
os.environ.setdefault("TMDB_API_KEY", "test-key")

from app.api import tmdb as tmdb_mod


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class CacheKeyTest(unittest.TestCase):
    def test_deterministic(self):
        """Same path + params must always produce the same key."""
        k1 = tmdb_mod._cache_key("movie/123", {"language": "en-US"})
        k2 = tmdb_mod._cache_key("movie/123", {"language": "en-US"})
        self.assertEqual(k1, k2)

    def test_different_params_differ(self):
        """Different params must produce different keys."""
        k1 = tmdb_mod._cache_key("movie/123", {"language": "en-US"})
        k2 = tmdb_mod._cache_key("movie/123", {"language": "fr-FR"})
        self.assertNotEqual(k1, k2)

    def test_strips_api_key(self):
        """api_key must not appear in the cache key."""
        k1 = tmdb_mod._cache_key("movie/123", {"language": "en-US", "api_key": "secret"})
        k2 = tmdb_mod._cache_key("movie/123", {"language": "en-US"})
        self.assertEqual(k1, k2)

    def test_param_order_independent(self):
        """Params sorted alphabetically so order doesn't matter."""
        k1 = tmdb_mod._cache_key("discover/movie", {"a": "1", "b": "2"})
        k2 = tmdb_mod._cache_key("discover/movie", {"b": "2", "a": "1"})
        self.assertEqual(k1, k2)


class TTLForTest(unittest.TestCase):
    def test_search_gets_short_ttl(self):
        self.assertEqual(tmdb_mod._ttl_for("search/movie"), tmdb_mod._CACHE_TTL_SEARCH)

    def test_config_gets_long_ttl(self):
        self.assertEqual(tmdb_mod._ttl_for("configuration"), tmdb_mod._CACHE_TTL_CONFIG)

    def test_movie_gets_default_ttl(self):
        self.assertEqual(tmdb_mod._ttl_for("movie/123"), tmdb_mod._CACHE_TTL_DEFAULT)

    def test_discover_gets_default_ttl(self):
        self.assertEqual(tmdb_mod._ttl_for("discover/movie"), tmdb_mod._CACHE_TTL_DEFAULT)


class TmdbGetTest(unittest.TestCase):
    def setUp(self):
        """Reset the shared client before each test."""
        tmdb_mod._client = None

    def _mock_client(self, status_code=200, json_body=None, raise_error=None):
        """Return a mock httpx.AsyncClient whose .get() returns a mock response."""
        client = AsyncMock()
        if raise_error:
            client.get = AsyncMock(side_effect=raise_error)
        else:
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = status_code
            resp.json.return_value = json_body or {"results": []}
            resp.raise_for_status = MagicMock()
            if status_code >= 400:
                resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "err", request=MagicMock(), response=resp
                )
            client.get = AsyncMock(return_value=resp)
        return client

    @patch.object(tmdb_mod, "tmdb_cache_get", return_value=None)
    @patch.object(tmdb_mod, "tmdb_cache_set")
    def test_returns_cached_value(self, mock_set, mock_get):
        """When cache hit, _tmdb_get must return cached data without HTTP call."""
        mock_get.return_value = {"cached": True}
        result = _run(tmdb_mod._tmdb_get("movie/123"))
        self.assertEqual(result, {"cached": True})

    @patch.object(tmdb_mod, "tmdb_cache_get", return_value=None)
    @patch.object(tmdb_mod, "tmdb_cache_set")
    def test_caches_miss_then_hit(self, mock_set, mock_get):
        """On cache miss, result must be fetched and stored."""
        mock_get.return_value = None
        tmdb_mod._client = self._mock_client(json_body={"id": 123})
        result = _run(tmdb_mod._tmdb_get("movie/123"))
        self.assertEqual(result["id"], 123)
        mock_set.assert_called_once()

    @patch.object(tmdb_mod, "tmdb_cache_get", return_value=None)
    def test_raises_on_upstream_404(self, mock_get):
        """TMDB 404 must become HTTPException with upstream status."""
        mock_get.return_value = None
        tmdb_mod._client = self._mock_client(status_code=404, json_body={"status_message": "Not found"})
        with self.assertRaises(HTTPException) as ctx:
            _run(tmdb_mod._tmdb_get("movie/0"))
        self.assertEqual(ctx.exception.status_code, 404)

    @patch.object(tmdb_mod, "tmdb_cache_get", return_value=None)
    def test_raises_502_on_connection_error(self, mock_get):
        """Connection failure must become 502."""
        mock_get.return_value = None
        tmdb_mod._client = self._mock_client(raise_error=httpx.RequestError("conn refused"))
        with self.assertRaises(HTTPException) as ctx:
            _run(tmdb_mod._tmdb_get("movie/123"))
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("unreachable", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
