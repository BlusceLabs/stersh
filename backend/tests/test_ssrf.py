"""Unit tests for backend/ssrf.py.

Covers the four security-critical cases:
  1. Allowlist miss — non-allowlisted hostname is rejected
  2. Private IP — allowlisted hostname resolving to a private IP is rejected
  3. Control characters — URL containing NUL / control bytes is rejected
  4. Redirect loop — redirect_event_hook aborts a 3xx pointing at a non-allowlisted host

All tests run against the real ALLOWED_HOSTS list in ssrf.py and use only
the stdlib + the existing fastapi/httpx deps — no mocking of the SSRF
module itself (testing the public surface, not the implementation).
"""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.core import security as ssrf


def _run(coro):
    """Drive an async test coroutine to completion in a fresh loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class ValidateOutboundURL(unittest.TestCase):
    def test_rejects_non_allowlisted_host(self):
        """A hostname NOT in ALLOWED_HOSTS must be rejected with 403."""
        with self.assertRaises(HTTPException) as ctx:
            ssrf.validate_outbound_url("https://evil.example.com/foo")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("allowlist", ctx.exception.detail.lower())

    def test_rejects_loopback_literal(self):
        """IP-literal loopback must be rejected (no DNS, direct IP check)."""
        with self.assertRaises(HTTPException) as ctx:
            ssrf.validate_outbound_url("https://127.0.0.1/foo")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("allowlist", ctx.exception.detail.lower())

    def test_rejects_rfc1918_literal(self):
        """IP-literal RFC1918 must be rejected."""
        for ip in ("10.0.0.1", "172.16.0.1", "192.168.1.1"):
            with self.assertRaises(HTTPException) as ctx:
                ssrf.validate_outbound_url(f"https://{ip}/foo")
            self.assertEqual(ctx.exception.status_code, 403, ip)

    def test_rejects_imds_literal(self):
        """AWS IMDS link-local 169.254.169.254 must be rejected."""
        with self.assertRaises(HTTPException) as ctx:
            ssrf.validate_outbound_url("https://169.254.169.254/latest/meta-data/")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_rejects_control_characters(self):
        """URLs containing NUL or other control chars must be rejected with 400."""
        for bad in ("\x00", "\x1f", "\x7f", "\n", "\r"):
            with self.assertRaises(HTTPException) as ctx:
                ssrf.validate_outbound_url(f"https://example.com/{bad}path")
            self.assertEqual(ctx.exception.status_code, 400, repr(bad))
            self.assertIn("control", ctx.exception.detail.lower())

    def test_rejects_oversize_url(self):
        """URLs over _MAX_URL_LEN bytes must be rejected with 400."""
        long_path = "a" * (ssrf._MAX_URL_LEN + 1)
        with self.assertRaises(HTTPException) as ctx:
            ssrf.validate_outbound_url(f"https://example.com/{long_path}")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("too long", ctx.exception.detail.lower())

    def test_rejects_non_http_scheme(self):
        """file://, ftp://, etc. must be rejected."""
        for scheme in ("file", "ftp", "gopher", "javascript"):
            with self.assertRaises(HTTPException) as ctx:
                ssrf.validate_outbound_url(f"{scheme}://example.com/x")
            self.assertEqual(ctx.exception.status_code, 400, scheme)

    def test_rejects_empty_url(self):
        """Empty string must be rejected with 400."""
        with self.assertRaises(HTTPException) as ctx:
            ssrf.validate_outbound_url("")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_rejects_non_string_url(self):
        """Non-string input must be rejected with 400."""
        with self.assertRaises(HTTPException) as ctx:
            ssrf.validate_outbound_url(None)  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.status_code, 400)

    def test_rejects_hostname_resolving_to_private(self):
        """Allowlisted host that resolves to a private IP must be rejected.

        localhost. resolves to 127.0.0.1 on every system. We override
        getaddrinfo via monkey-patch to avoid the real DNS resolution,
        but the function under test is _hostname_resolves_to_public, so
        we call it directly to assert the DNS-rejection path.
        """
        import socket

        original = socket.getaddrinfo
        socket.getaddrinfo = lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.5", 0))
        ]
        try:
            self.assertFalse(ssrf._hostname_resolves_to_public("evil.example"))
        finally:
            socket.getaddrinfo = original

    def test_accepts_public_resolution(self):
        """A hostname resolving to a public IP should pass the DNS check."""
        import socket

        original = socket.getaddrinfo
        socket.getaddrinfo = lambda *a, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 0))
        ]
        try:
            self.assertTrue(ssrf._hostname_resolves_to_public("dns.google"))
        finally:
            socket.getaddrinfo = original


class RedirectEventHook(unittest.TestCase):
    def test_passes_through_non_redirect(self):
        """A 2xx response must not trigger validation."""
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"location": "https://evil.example.com/"}
        resp.request = MagicMock()
        resp.request.url = "https://cdn.vidking.net/"
        # Should resolve to None (no exception).
        result = _run(ssrf.redirect_event_hook(resp))
        self.assertIsNone(result)

    def test_blocks_redirect_to_non_allowlisted_host(self):
        """A 302 to evil.example.com must raise HTTPException."""
        resp = MagicMock()
        resp.status_code = 302
        resp.headers = {"location": "https://evil.example.com/"}
        resp.request = MagicMock()
        resp.request.url = "https://cdn.vidking.net/"
        with self.assertRaises(HTTPException) as ctx:
            _run(ssrf.redirect_event_hook(resp))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_blocks_redirect_to_loopback(self):
        """A 302 to 127.0.0.1 (CDN→internal-service SSRF) must raise."""
        resp = MagicMock()
        resp.status_code = 302
        resp.headers = {"location": "http://127.0.0.1:6379/"}
        resp.request = MagicMock()
        resp.request.url = "https://cdn.vidking.net/"
        with self.assertRaises(HTTPException) as ctx:
            _run(ssrf.redirect_event_hook(resp))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_passes_redirect_without_location(self):
        """A 3xx with no Location header is a no-op for the hook."""
        resp = MagicMock()
        resp.status_code = 302
        resp.headers = {}
        resp.request = MagicMock()
        resp.request.url = "https://cdn.vidking.net/"
        result = _run(ssrf.redirect_event_hook(resp))
        self.assertIsNone(result)

    def test_passes_redirect_to_allowlisted_host(self):
        """A 302 to another allowlisted host must not be rejected on
        allowlist grounds. (DNS resolution may fail in CI; we accept
        that as a non-allowlist rejection.)"""
        resp = MagicMock()
        resp.status_code = 302
        resp.headers = {"location": "https://111movies.net/other"}
        resp.request = MagicMock()
        resp.request.url = "https://cdn.vidking.net/"
        try:
            _run(ssrf.redirect_event_hook(resp))
        except HTTPException as exc:
            self.assertNotEqual(exc.status_code, 403)
            self.assertNotIn("allowlist", exc.detail.lower())


class PrivateIPCheck(unittest.TestCase):
    def test_loopback_v4(self):
        self.assertTrue(ssrf._is_private_ip("127.0.0.1"))
        self.assertTrue(ssrf._is_private_ip("127.255.255.254"))

    def test_loopback_v6(self):
        self.assertTrue(ssrf._is_private_ip("::1"))

    def test_rfc1918(self):
        self.assertTrue(ssrf._is_private_ip("10.0.0.1"))
        self.assertTrue(ssrf._is_private_ip("172.16.0.1"))
        self.assertTrue(ssrf._is_private_ip("192.168.1.1"))

    def test_link_local_v4(self):
        self.assertTrue(ssrf._is_private_ip("169.254.169.254"))
        self.assertTrue(ssrf._is_private_ip("169.254.0.1"))

    def test_link_local_v6(self):
        self.assertTrue(ssrf._is_private_ip("fe80::1"))

    def test_unspecified(self):
        self.assertTrue(ssrf._is_private_ip("0.0.0.0"))
        self.assertTrue(ssrf._is_private_ip("::"))

    def test_multicast(self):
        self.assertTrue(ssrf._is_private_ip("224.0.0.1"))

    def test_public_ipv4(self):
        self.assertFalse(ssrf._is_private_ip("8.8.8.8"))
        self.assertFalse(ssrf._is_private_ip("1.1.1.1"))

    def test_public_ipv6(self):
        self.assertFalse(ssrf._is_private_ip("2606:4700:4700::1111"))

    def test_invalid_input(self):
        """Garbage that isn't a valid IP literal must be treated as non-public."""
        self.assertTrue(ssrf._is_private_ip("not-an-ip"))
        self.assertTrue(ssrf._is_private_ip(""))


if __name__ == "__main__":
    unittest.main()
