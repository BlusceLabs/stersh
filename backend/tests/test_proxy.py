"""Unit tests for backend/app/api/proxy.py — token store, URL validation, manifest rewriting."""
from __future__ import annotations

import unittest

from fastapi import HTTPException

from app.api import proxy as proxy_mod


class TokenStoreTest(unittest.TestCase):
    def test_store_returns_hex_token(self):
        """_store must return a hex string of _SHORT_TOKEN_LEN."""
        token = proxy_mod._store("https://cdn.vidking.net/seg.ts")
        self.assertEqual(len(token), proxy_mod._SHORT_TOKEN_LEN)
        self.assertTrue(all(c in "0123456789abcdef" for c in token))

    def test_resolve_round_trip(self):
        """_resolve(_store(url)) must return the original url."""
        url = "https://cdn.vidking.net/seg.ts"
        token = proxy_mod._store(url)
        self.assertEqual(proxy_mod._resolve(token), url)

    def test_resolve_unknown_returns_none(self):
        """_resolve with an unknown token must return None."""
        self.assertIsNone(proxy_mod._resolve("deadbeef12345678"))

    def test_same_url_same_token(self):
        """Storing the same URL twice must return the same token (idempotent)."""
        url = "https://cdn.vidking.net/seg.ts"
        t1 = proxy_mod._store(url)
        t2 = proxy_mod._store(url)
        self.assertEqual(t1, t2)


class ValidateTest(unittest.TestCase):
    def test_rejects_non_allowlisted_host(self):
        with self.assertRaises(HTTPException) as ctx:
            proxy_mod._validate("https://evil.example.com/seg.ts")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_rejects_non_http_scheme(self):
        with self.assertRaises(HTTPException) as ctx:
            proxy_mod._validate("ftp://cdn.vidking.net/seg.ts")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_accepts_allowlisted_host(self):
        """An allowlisted host must not raise."""
        proxy_mod._validate("https://cdn.vidking.net/seg.ts")

    def test_rejects_malformed_url(self):
        with self.assertRaises(HTTPException) as ctx:
            proxy_mod._validate("://no-scheme")
        self.assertEqual(ctx.exception.status_code, 400)


class RewriteManifestTest(unittest.TestCase):
    def test_rewrites_segment_urls(self):
        """Media playlist segment URIs must become /api/proxy/seg/<token>."""
        manifest = "#EXTM3U\n#EXTINF:10.0,\nhttps://cdn.vidking.net/seg1.ts"
        result = proxy_mod._rewrite_manifest(manifest, "https://cdn.vidking.net/")
        self.assertIn("/api/proxy/seg/", result)
        self.assertNotIn("https://cdn.vidking.net/seg1.ts", result)

    def test_rewrites_variant_urls(self):
        """Master playlist variant URIs must become /api/proxy/hls?url=<token>."""
        manifest = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000\nhttps://cdn.vidking.net/low.m3u8"
        result = proxy_mod._rewrite_manifest(manifest, "https://cdn.vidking.net/")
        self.assertIn("/api/proxy/hls?url=", result)
        self.assertNotIn("https://cdn.vidking.net/low.m3u8", result)

    def test_preserves_endlist(self):
        """#EXT-X-ENDLIST must be preserved so VOD stays VOD."""
        manifest = "#EXTM3U\n#EXTINF:10.0,\nseg.ts\n#EXT-X-ENDLIST"
        result = proxy_mod._rewrite_manifest(manifest, "https://cdn.vidking.net/")
        self.assertIn("#EXT-X-ENDLIST", result)

    def test_preserves_playlist_type(self):
        """#EXT-X-PLAYLIST-TYPE tags must be preserved."""
        manifest = "#EXTM3U\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXTINF:10.0,\nseg.ts"
        result = proxy_mod._rewrite_manifest(manifest, "https://cdn.vidking.net/")
        self.assertIn("#EXT-X-PLAYLIST-TYPE:VOD", result)

    def test_resolves_relative_urls(self):
        """Relative segment URIs must be resolved against base_url."""
        manifest = "#EXTM3U\n#EXTINF:10.0,\nseg.ts"
        result = proxy_mod._rewrite_manifest(manifest, "https://cdn.vidking.net/vod/")
        self.assertIn("/api/proxy/seg/", result)
        # The rewritten token must resolve back to the full URL
        token = result.split("/api/proxy/seg/")[1].strip()
        self.assertEqual(proxy_mod._resolve(token), "https://cdn.vidking.net/vod/seg.ts")

    def test_comments_preserved(self):
        """Comment lines (starting with # but not directives) must be kept."""
        manifest = "#EXTM3U\n#EXTINF:10.0,\nseg.ts"
        result = proxy_mod._rewrite_manifest(manifest, "https://cdn.vidking.net/")
        self.assertIn("#EXTM3U", result)
        self.assertIn("#EXTINF:10.0,", result)


class BandwidthEstimationTest(unittest.TestCase):
    def test_zero_for_zero_length(self):
        self.assertEqual(proxy_mod._estimate_bandwidth(0, 100.0), 0)

    def test_zero_for_zero_elapsed(self):
        import time
        now = time.monotonic()
        self.assertEqual(proxy_mod._estimate_bandwidth(1000, now), 0)

    def test_positive_for_valid_input(self):
        import time
        start = time.monotonic() - 1.0  # 1 second ago
        bw = proxy_mod._estimate_bandwidth(125000, start)  # 125 KB in 1s = ~1000 kbps
        self.assertGreater(bw, 0)


if __name__ == "__main__":
    unittest.main()
