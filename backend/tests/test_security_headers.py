"""Unit tests for the security-headers middleware."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.security_headers import (
    DEFAULT_CSP,
    DEFAULT_HSTS_MAX_AGE,
    DEFAULT_PERMISSIONS_POLICY,
    DOCS_CSP,
    setup_security_headers,
)


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"ok": True}

    @app.get("/api/items/{item_id}")
    async def item(item_id: int):
        return {"id": item_id}

    setup_security_headers(app)
    return app


class SecurityHeadersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = _build_app()
        self.client = TestClient(self.app)

    def test_basic_security_headers_present(self) -> None:
        resp = self.client.get("/")
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(resp.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

    def test_content_security_policy_default(self) -> None:
        resp = self.client.get("/")
        csp = resp.headers.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("frame-ancestors 'self'", csp)
        self.assertIn("object-src 'none'", csp)

    def test_permissions_policy_disables_sensitive_features(self) -> None:
        resp = self.client.get("/")
        pp = resp.headers.get("Permissions-Policy", "")
        self.assertIn("camera=()", pp)
        self.assertIn("microphone=()", pp)
        self.assertIn("geolocation=()", pp)
        self.assertIn("payment=()", pp)
        self.assertIn("usb=()", pp)

    def test_cross_origin_policies(self) -> None:
        resp = self.client.get("/")
        self.assertEqual(resp.headers.get("Cross-Origin-Opener-Policy"), "same-origin")
        self.assertEqual(resp.headers.get("Cross-Origin-Resource-Policy"), "same-origin")

    def test_hsts_absent_on_http(self) -> None:
        resp = self.client.get("/")
        self.assertNotIn("Strict-Transport-Security", resp.headers)

    def test_hsts_present_on_https(self) -> None:
        resp = self.client.get("/", headers={"X-Forwarded-Proto": "https"})
        hsts = resp.headers.get("Strict-Transport-Security", "")
        self.assertIn(f"max-age={DEFAULT_HSTS_MAX_AGE}", hsts)
        self.assertIn("includeSubDomains", hsts)
        self.assertIn("preload", hsts)

    def test_hsts_disabled_by_env(self) -> None:
        with patch.dict(os.environ, {"SECURITY_HSTS_ENABLED": "false"}):
            app = _build_app()
            client = TestClient(app)
            resp = client.get("/", headers={"X-Forwarded-Proto": "https"})
            self.assertNotIn("Strict-Transport-Security", resp.headers)

    def test_hsts_max_age_env_override(self) -> None:
        with patch.dict(os.environ, {"SECURITY_HSTS_MAX_AGE": "60"}):
            app = _build_app()
            client = TestClient(app)
            resp = client.get("/", headers={"X-Forwarded-Proto": "https"})
            self.assertIn("max-age=60", resp.headers.get("Strict-Transport-Security", ""))

    def test_hsts_max_age_invalid_uses_default(self) -> None:
        with patch.dict(os.environ, {"SECURITY_HSTS_MAX_AGE": "not-a-number"}):
            app = _build_app()
            client = TestClient(app)
            resp = client.get("/", headers={"X-Forwarded-Proto": "https"})
            self.assertIn(f"max-age={DEFAULT_HSTS_MAX_AGE}", resp.headers.get("Strict-Transport-Security", ""))

    def test_csp_env_override(self) -> None:
        custom = "default-src 'none'; script-src 'self'"
        with patch.dict(os.environ, {"SECURITY_CSP_OVERRIDE": custom}):
            app = _build_app()
            client = TestClient(app)
            resp = client.get("/")
            self.assertEqual(resp.headers.get("Content-Security-Policy"), custom)

    def test_permissions_policy_env_override(self) -> None:
        custom = "camera=(self)"
        with patch.dict(os.environ, {"SECURITY_PERMISSIONS_OVERRIDE": custom}):
            app = _build_app()
            client = TestClient(app)
            resp = client.get("/")
            self.assertEqual(resp.headers.get("Permissions-Policy"), custom)

    def test_docs_path_uses_relaxed_csp(self) -> None:
        docs_app = FastAPI()

        @docs_app.get("/api/docs")
        async def docs():
            return {"html": "swagger"}

        @docs_app.get("/api/redoc")
        async def redoc():
            return {"html": "redoc"}

        setup_security_headers(docs_app)
        client = TestClient(docs_app)

        for path in ("/api/docs", "/api/redoc"):
            resp = client.get(path)
            csp = resp.headers.get("Content-Security-Policy", "")
            self.assertIn("'unsafe-inline'", csp)
            self.assertIn("'unsafe-eval'", csp)
            self.assertIn("https:", csp)

    def test_existing_response_headers_preserved(self) -> None:
        custom_app = FastAPI()

        @custom_app.get("/")
        async def root():
            from fastapi.responses import JSONResponse
            return JSONResponse(
                content={"ok": True},
                headers={"X-Custom": "preserved"},
            )

        setup_security_headers(custom_app)
        client = TestClient(custom_app)
        resp = client.get("/")
        self.assertEqual(resp.headers.get("X-Custom"), "preserved")
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")

    def test_no_hsts_on_plain_http_even_with_xfp_http(self) -> None:
        resp = self.client.get("/", headers={"X-Forwarded-Proto": "http"})
        self.assertNotIn("Strict-Transport-Security", resp.headers)

    def test_csp_applied_to_api_paths(self) -> None:
        resp = self.client.get("/api/items/42")
        self.assertIn("default-src", resp.headers.get("Content-Security-Policy", ""))
        self.assertIn("X-Content-Type-Options", resp.headers)


class SecurityHeadersDefaultsTests(unittest.TestCase):
    """Sanity checks on the module-level constants."""

    def test_default_csp_includes_critical_directives(self) -> None:
        for directive in (
            "default-src",
            "script-src",
            "style-src",
            "img-src",
            "object-src 'none'",
            "base-uri 'self'",
            "frame-ancestors 'self'",
        ):
            with self.subTest(directive=directive):
                self.assertIn(directive, DEFAULT_CSP)

    def test_default_permissions_policy_disables_sensitive_features(self) -> None:
        for feature in ("camera", "microphone", "geolocation", "payment", "usb"):
            with self.subTest(feature=feature):
                self.assertIn(f"{feature}=( )".replace(" ", ""), DEFAULT_PERMISSIONS_POLICY.replace(" ", ""))
                self.assertIn(f"{feature}=", DEFAULT_PERMISSIONS_POLICY)

    def test_docs_csp_is_more_permissive(self) -> None:
        self.assertIn("'unsafe-eval'", DOCS_CSP)
        self.assertIn("https:", DOCS_CSP)

    def test_default_hsts_max_age_is_one_year(self) -> None:
        self.assertEqual(DEFAULT_HSTS_MAX_AGE, 31536000)


if __name__ == "__main__":
    unittest.main()
