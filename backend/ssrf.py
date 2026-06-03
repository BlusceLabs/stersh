"""SSRF guard for outbound URLs accepted from user input.

Centralizes the allowlist + private-network rejection logic that
`/api/ffmpeg/remux`, `/api/ffmpeg/probe`, and `/api/subtitles/proxy`
must enforce before fetching an arbitrary URL server-side.

The allowlist mirrors `ENHANCED_ALLOWED_HOSTS` in `app/api/proxy.py`
so the same set of CDN mirrors is trusted across endpoints. Private
and link-local addresses (RFC 1918, loopback, multicast, link-local
v4/v6, ULA v6) are always rejected — even when the host appears on
the allowlist — to prevent DNS rebinding and IP-literal bypass.

`redirect_event_hook` is an httpx event hook that re-validates the
URL of every redirect response. Without it, a CDN on the allowlist
could 302 the request to `http://127.0.0.1:6379/` and httpx would
happily follow it (SSRF via cross-host redirect).
"""
from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Final
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Mirror of proxy.py allowlist — single source of truth lives here now.
# proxy.py is updated to import from this module.
ALLOWED_HOSTS: Final[frozenset[str]] = frozenset(
    {
        # Vidking CDN
        "easy.speedsterwave.app",
        "cdn.vidking.net",
        "vidking.net",
        "www.vidking.net",
        # Mousedoor CDN (vidking stream host)
        "hello.mousedoor.com",
        "mousedoor.com",
        # White CDN (111movies.net)
        "cloudnestra.com",
        "whisperingauroras.com",
        "111movies.net",
        "www.111movies.net",
        "cdn.111movies.net",
        # Workers proxies
        "tylerfisher55.workers.dev",
        "old.tylerfisher55.workers.dev",
        "broad.tylerfisher55.workers.dev",
        "black.tylerfisher55.workers.dev",
        # Common HLS CDN mirrors
        "cdn.jwplayer.com",
        "content.jwplatform.com",
        "cdn.plyr.io",
        # Subtitle provider assets (dl.subdl.com hosts the proxied VTT/SRT)
        "dl.subdl.com",
    }
)

_MAX_URL_LEN: Final[int] = 2048
_ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})


def _is_private_ip(ip_str: str) -> bool:
    """Return True if the IP literal is non-public (loopback, private, link-local, etc)."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _hostname_resolves_to_public(host: str) -> bool:
    """Resolve `host` and reject if any returned address is non-public.

    This catches `localhost`, IP-literal forms (127.0.0.1, ::1, 169.254.169.254),
    DNS that resolves to private RFC1918 ranges, and DNS-rebinding cases where
    the public hostname resolves to a private IP.

    NOTE (DNS-rebinding TOCTOU): we resolve once and check, then httpx resolves
    again on connect. A host that returns short-TTL private IPs could in theory
    race: present a public IP to satisfy this check, then return a private IP
    to the second resolution. The hostname allowlist constrains the attacker
    set to compromised or attacker-controlled CDN mirrors, so practical risk
    is low. A complete fix would pin the resolved IP for the connection via a
    custom httpx transport (resolve callback). Not implemented because no
    allowlisted host currently exhibits this behavior; revisit if the
    allowlist grows or threat model changes.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        logger.warning('"ssrf_dns_failure":{"host":"%s","err":"%s"}', host, exc)
        return False
    if not infos:
        return False
    for family, _type, _proto, _canon, sockaddr in infos:
        if family == socket.AF_INET:
            ip_str = sockaddr[0]
        elif family == socket.AF_INET6:
            ip_str = sockaddr[0].split("%", 1)[0]
        else:
            continue
        if _is_private_ip(ip_str):
            logger.warning('"ssrf_blocked_private":{"host":"%s","ip":"%s"}', host, ip_str)
            return False
    return True


def validate_outbound_url(url: str) -> None:
    """Validate an outbound URL: scheme, length, allowlist, and IP range.

    Raises `fastapi.HTTPException` on any rejection. Logs at WARNING level
    with a stable JSON tag for downstream monitoring.
    """
    if not isinstance(url, str):
        raise HTTPException(status_code=400, detail="url must be a string")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    if len(url) > _MAX_URL_LEN:
        raise HTTPException(status_code=400, detail="url too long")
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in url):
        raise HTTPException(status_code=400, detail="url contains control characters")

    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Malformed URL: {exc}")

    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise HTTPException(status_code=400, detail="URL scheme must be http or https")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL must include a hostname")
    host = parsed.hostname.lower()

    if host not in ALLOWED_HOSTS:
        raise HTTPException(status_code=403, detail=f"Host not in allowlist: {host}")

    if not _hostname_resolves_to_public(host):
        raise HTTPException(
            status_code=403,
            detail=f"Host resolves to non-public address: {host}",
        )


async def redirect_event_hook(response: httpx.Response) -> None:
    """Reject cross-host or non-public redirect targets.

    Hook this into an `httpx.AsyncClient(event_hooks={'response': [...]})`
    that is created with `follow_redirects=True`. The hook raises on any
    redirect that points at a host outside the allowlist or at a private
    IP literal — blocking the classic CDN-→-internal-service SSRF.
    """
    # response.history is empty until the response chain is built; the
    # only Response objects that arrive at this hook are redirect (3xx)
    # responses, because httpx does not invoke response hooks for the
    # final 2xx.
    if not (300 <= response.status_code < 400):
        return
    location = response.headers.get("location")
    if not location:
        return
    try:
        validate_outbound_url(location)
    except HTTPException as exc:
        logger.warning(
            '"ssrf_blocked_redirect":{"from":"%s","to":"%s","status":%d,"reason":"%s"}',
            str(response.request.url) if response.request else "?",
            location,
            response.status_code,
            exc.detail,
        )
        # Raise so httpx aborts the redirect chain.
        raise

