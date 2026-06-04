"""Security headers middleware.

Applies a defense-in-depth set of HTTP response headers to every
request. Configurable via environment variables so production
deployments can tighten the policy without code changes.

Headers applied:
    X-Content-Type-Options: nosniff
        Block MIME-sniffing attacks.
    X-Frame-Options: SAMEORIGIN
        Clickjacking protection (legacy header, see CSP frame-ancestors).
    Referrer-Policy: strict-origin-when-cross-origin
        Limit referer leakage to same-origin requests.
    Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
        Force HTTPS for 1 year on supporting browsers. Skipped when
        the request is plain HTTP or when HSTS is disabled.
    Content-Security-Policy: <directive string>
        Restrict which resources the response can load. A relaxed
        policy is used for the auto-generated docs (Swagger UI / ReDoc)
        so that they can load their CDN-hosted assets.
    Permissions-Policy: <directive string>
        Disable browser features the app does not need.
    Cross-Origin-Opener-Policy: same-origin
        Isolate the browsing context.
    Cross-Origin-Resource-Policy: same-origin
        Limit who can embed resources from this origin.

Environment variables:
    SECURITY_HSTS_ENABLED   "true" (default) | "false"   toggle HSTS
    SECURITY_CSP_OVERRIDE   full CSP string              overrides default
    SECURITY_PERMISSIONS_OVERRIDE  full PP string        overrides default
    SECURITY_HSTS_MAX_AGE   seconds (default 31536000)   HSTS lifetime
"""
from __future__ import annotations

import os
from typing import Final

from fastapi import FastAPI, Request
from fastapi.responses import Response


DEFAULT_CSP: Final[str] = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://www.youtube.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "img-src 'self' data: https:; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "connect-src 'self' https:; "
    "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com; "
    "media-src 'self' https: data:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'self';"
)


# Relaxed CSP for /api/docs and /api/redoc which load Swagger UI / ReDoc
# from CDN and require inline scripts to render.
DOCS_CSP: Final[str] = (
    "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https:; "
    "img-src 'self' data: https:; "
    "frame-ancestors 'self';"
)


DEFAULT_PERMISSIONS_POLICY: Final[str] = (
    "accelerometer=(), "
    "autoplay=(self), "
    "camera=(), "
    "display-capture=(), "
    "fullscreen=(self), "
    "geolocation=(), "
    "gyroscope=(), "
    "magnetometer=(), "
    "microphone=(), "
    "payment=(), "
    "picture-in-picture=(self), "
    "publickey-credentials-get=(), "
    "screen-wake-lock=(), "
    "sync-xhr=(), "
    "usb=(), "
    "web-share=(), "
    "xr-spatial-tracking=()"
)


DEFAULT_HSTS_MAX_AGE: Final[int] = 31536000  # 1 year
HSTS_HEADER_VALUE: Final[str] = "max-age={max_age}; includeSubDomains; preload"


DOCS_PATH_PREFIXES: Final[tuple[str, ...]] = ("/api/docs", "/api/redoc")


def _is_https(request: Request) -> bool:
    """Detect HTTPS even when the app sits behind a reverse proxy.

    The proxy is expected to forward the original scheme via the
    X-Forwarded-Proto header.
    """
    if request.url.scheme == "https":
        return True
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
    return forwarded_proto == "https"


def setup_security_headers(app: FastAPI) -> None:
    """Register the security-headers middleware on the given FastAPI app."""
    csp = os.environ.get("SECURITY_CSP_OVERRIDE", DEFAULT_CSP)
    permissions_policy = os.environ.get(
        "SECURITY_PERMISSIONS_OVERRIDE", DEFAULT_PERMISSIONS_POLICY
    )
    hsts_enabled = os.environ.get("SECURITY_HSTS_ENABLED", "true").lower() != "false"
    try:
        hsts_max_age = int(os.environ.get("SECURITY_HSTS_MAX_AGE", DEFAULT_HSTS_MAX_AGE))
    except ValueError:
        hsts_max_age = DEFAULT_HSTS_MAX_AGE

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", permissions_policy)
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")

        if request.url.path.startswith(DOCS_PATH_PREFIXES):
            response.headers["Content-Security-Policy"] = DOCS_CSP
        else:
            response.headers.setdefault("Content-Security-Policy", csp)

        if hsts_enabled and _is_https(request):
            response.headers.setdefault(
                "Strict-Transport-Security",
                HSTS_HEADER_VALUE.format(max_age=hsts_max_age),
            )

        return response
