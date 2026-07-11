"""Enhanced proxy routes for stersh — multi-CDN adaptive proxy.

Extends the base proxy with:
  - HTTP Range request pass-through (seek support for MP4 progressive download)
  - Bandwidth estimation via per-host EMA (X-Bandwidth-Kbps)
  - CDN fallback chain: primary → mirrors → error, guarded by per-host circuit breakers
  - Per-segment latency logging for QoS analytics
  - CORS preflight handling
  - /api/proxy/multi/health — fan-out source health check across all CDN mirrors
  - Request coalescing: concurrent fetches for the same token share one upstream call
  - Full-jitter exponential back-off on retries
  - Namespaced tokens (seg: / var:) prevent cross-type resolution
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from typing import NamedTuple
from urllib.parse import urlparse, urlunparse

import httpx
from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.core.security import ALLOWED_HOSTS as ENHANCED_ALLOWED_HOSTS  # re-exported for back-compat

__all__ = ["router", "shutdown_enhanced_client", "ENHANCED_ALLOWED_HOSTS"]

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_TOKEN_HEX_LEN = 16
_TOKEN_CHARS   = frozenset("0123456789abcdef")
_NS_SEG        = "seg"   # segment-token namespace
_NS_VAR        = "var"   # variant/manifest-token namespace

_STORE_MAX   = 5_000
_STORE_TTL_S = 86_400   # 24 h — outlasts any film

_MAX_MIRRORS = 3        # mirror URLs stored per token

_RETRY_MAX    = 3
_RETRY_BASE_S = 0.3     # full-jitter base (seconds)
_RETRY_CAP_S  = 2.0     # full-jitter ceiling

_CB_THRESHOLD   = 5     # consecutive failures before circuit opens
_CB_HALF_OPEN_S = 30    # seconds before half-open probe

_BW_ALPHA  = 0.25       # EMA smoothing — lower = more stable estimate
_MP4_CHUNK = 65_536     # bytes per streaming chunk

_CDN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}

_CORS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "Range, Content-Type, Accept",
    "Access-Control-Max-Age":       "86400",
}

# ── Token Store ───────────────────────────────────────────────────────────────

class _TokenEntry(NamedTuple):
    """A proxied URL plus optional CDN mirror alternates."""
    primary: str
    mirrors: tuple[str, ...] = ()


# Keyed internally as "{ns}:{hex}"; callers receive only the hex fragment,
# so URL paths stay clean and cross-namespace token reuse is structurally impossible.
_url_store: TTLCache[str, _TokenEntry] = TTLCache(maxsize=_STORE_MAX, ttl=_STORE_TTL_S)


def _store(url: str, *, ns: str, mirrors: tuple[str, ...] = ()) -> str:
    """Hash *url* under namespace *ns*, persist it, and return a URL-safe hex token.

    Collisions (two different URLs sharing the same 16-char hex prefix) are
    handled by extending the hash; they are vanishingly rare in practice.
    """
    hex_tok = hashlib.sha256(url.encode()).hexdigest()[:_TOKEN_HEX_LEN]
    key     = f"{ns}:{hex_tok}"

    existing = _url_store.get(key)
    if existing is not None and existing.primary != url:
        # True collision on a different URL — extend digest to disambiguate.
        hex_tok = hashlib.sha256(f"{url}\x00alt".encode()).hexdigest()[:_TOKEN_HEX_LEN + 4]
        key     = f"{ns}:{hex_tok}"

    _url_store[key] = _TokenEntry(primary=url, mirrors=mirrors[:_MAX_MIRRORS])
    return hex_tok


def _resolve(token: str, *, ns: str) -> _TokenEntry | None:
    """Look up *token* within *ns*; returns ``None`` if absent or expired."""
    return _url_store.get(f"{ns}:{token}")


# ── Circuit Breaker ───────────────────────────────────────────────────────────

@dataclass
class _Breaker:
    """Per-host circuit breaker.

    Opens after ``_CB_THRESHOLD`` consecutive failures and enters half-open
    state after ``_CB_HALF_OPEN_S`` seconds, allowing a single probe request.
    A successful response closes the circuit; each success also decrements the
    failure counter so a partially-degraded host recovers gracefully.
    """
    failures:  int   = 0
    opened_at: float = field(default=0.0, repr=False)

    def is_open(self) -> bool:
        return (
            self.failures >= _CB_THRESHOLD
            and (time.monotonic() - self.opened_at) < _CB_HALF_OPEN_S
        )

    def record_failure(self, host: str) -> None:
        self.failures += 1
        if self.failures == _CB_THRESHOLD:
            self.opened_at = time.monotonic()
            _qlog("circuit_open", host=host, failures=str(self.failures))

    def record_success(self, host: str) -> None:
        if self.failures >= _CB_THRESHOLD:
            _qlog("circuit_closed", host=host)
        self.failures = max(0, self.failures - 1)


_breakers: dict[str, _Breaker] = {}


def _cb(host: str) -> _Breaker:
    """Return (creating if needed) the circuit breaker for *host*."""
    if host not in _breakers:
        _breakers[host] = _Breaker()
    return _breakers[host]


# ── Bandwidth EMA ─────────────────────────────────────────────────────────────

_bw_ema: dict[str, float] = {}  # hostname → kbps


def _update_bw(host: str, byte_count: int, elapsed_s: float) -> int:
    """Update per-host exponential-moving-average bandwidth; return kbps estimate."""
    if elapsed_s <= 0 or byte_count <= 0:
        return int(_bw_ema.get(host, 0))
    sample   = (byte_count * 8) / (elapsed_s * 1_000)
    previous = _bw_ema.get(host, sample)
    _bw_ema[host] = _BW_ALPHA * sample + (1.0 - _BW_ALPHA) * previous
    return int(_bw_ema[host])


# ── Request Coalescing ────────────────────────────────────────────────────────

_coalesce: dict[str, asyncio.Task[httpx.Response]] = {}


async def _fetch_once(
    client:  httpx.AsyncClient,
    url:     str,
    headers: dict[str, str],
) -> httpx.Response:
    """Issue at most one upstream GET per ``(url, Range)`` pair.

    Concurrent callers for the same segment share a single ``asyncio.Task``.
    ``asyncio.shield`` prevents an individual awaiter's cancellation from
    tearing down the shared task; other waiters continue to completion.
    """
    key = f"{url}\x00{headers.get('Range', '')}"

    if key in _coalesce:
        return await asyncio.shield(_coalesce[key])

    task: asyncio.Task[httpx.Response] = asyncio.create_task(
        client.get(url, headers=headers)
    )
    _coalesce[key] = task
    try:
        return await asyncio.shield(task)
    finally:
        _coalesce.pop(key, None)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _backoff(attempt: int) -> float:
    """Full-jitter exponential back-off — returns seconds to sleep."""
    return random.uniform(0.0, min(_RETRY_CAP_S, _RETRY_BASE_S * (2 ** attempt)))


def _hostname(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _validate(url: str) -> str:
    """Assert *url* may be safely proxied.  Returns the resolved hostname."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    host = (parsed.hostname or "").lower()
    if host not in ENHANCED_ALLOWED_HOSTS:
        raise HTTPException(status_code=403, detail=f"Host not in allowlist: {host}")
    return host


def _qlog(event: str, **kv: str) -> None:
    """Emit a compact, machine-parseable log line."""
    tail = " ".join(f'{k}="{v}"' for k, v in kv.items())
    logger.info("[proxy] event=%r %s", event, tail)


def _range_headers(resp: httpx.Response) -> dict[str, str]:
    """Extract byte-range response headers for downstream forwarding."""
    result: dict[str, str] = {}
    for h in ("Content-Range", "Content-Length", "Accept-Ranges", "ETag"):
        if v := resp.headers.get(h.lower()):
            result[h] = v
    return result


# ── HTTP client ───────────────────────────────────────────────────────────────

_proxy_client: httpx.AsyncClient | None = None


async def _get_proxy_client() -> httpx.AsyncClient:
    global _proxy_client
    if _proxy_client is None or _proxy_client.is_closed:
        _proxy_client = httpx.AsyncClient(
            headers=_CDN_HEADERS,
            timeout=httpx.Timeout(connect=8.0, read=25.0, write=8.0, pool=5.0),
            follow_redirects=True,
            http2=True,  # prefer HTTP/2 for multiplexed segment fetches
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=60),
        )
    return _proxy_client


async def shutdown_enhanced_client() -> None:
    global _proxy_client
    if _proxy_client and not _proxy_client.is_closed:
        await _proxy_client.aclose()
        _proxy_client = None


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/proxy", tags=["proxy"])


@router.options("/{path:path}")
async def proxy_cors_preflight(path: str) -> Response:
    """Handle CORS preflight for all proxy routes."""
    return Response(status_code=204, headers=_CORS)


# ── HLS manifest ──────────────────────────────────────────────────────────────

@router.get("/hls")
async def enhanced_proxy_hls(
    request: Request,
    url:     str = Query(...),
    origin:  str = Query(default=""),
    mirrors: str = Query(
        default="",
        description="Comma-separated alternate CDN base URLs for segment failover",
    ),
) -> Response:
    """Proxy and rewrite an HLS manifest; all fetchable URIs route through the proxy.

    ``url`` may be a 16-char var-token (fast re-fetch) or a full CDN URL.
    ``origin`` overrides the Referer/Origin headers sent upstream — useful
    when the CDN validates the referring domain.
    ``mirrors`` registers fallback CDN bases at manifest-fetch time.  Mirror
    URLs are embedded in each segment token so ``/seg/{token}`` can fail-over
    without a manifest re-fetch.
    """
    # Resolve short var-token → full URL
    if len(url) == _TOKEN_HEX_LEN and all(c in _TOKEN_CHARS for c in url):
        entry = _resolve(url, ns=_NS_VAR)
        if not entry:
            raise HTTPException(status_code=410, detail="Token expired — refresh manifest")
        url = entry.primary

    host   = _validate(url)
    client = await _get_proxy_client()

    upstream_headers: dict[str, str] = {}
    if origin:
        upstream_headers.update(Referer=origin, Origin=origin)

    try:
        resp = await client.get(url, headers=upstream_headers)
    except httpx.TimeoutException:
        _cb(host).record_failure(host)
        raise HTTPException(status_code=504, detail="CDN manifest timeout")
    except httpx.RequestError as exc:
        _cb(host).record_failure(host)
        raise HTTPException(status_code=502, detail=f"CDN unreachable: {exc}")

    if not resp.is_success:
        _cb(host).record_failure(host)
        raise HTTPException(status_code=resp.status_code, detail="CDN manifest error")

    _cb(host).record_success(host)

    mirror_bases = tuple(m.strip().rstrip("/") for m in mirrors.split(",") if m.strip())
    base_url     = url.rsplit("/", 1)[0] + "/"
    rewritten    = _rewrite_manifest(resp.text, base_url, mirror_bases=mirror_bases)

    return Response(
        content=rewritten,
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control":                 "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin":   "*",
            "Access-Control-Expose-Headers": "X-Bandwidth-Kbps",
        },
    )


# ── HLS segments ──────────────────────────────────────────────────────────────

@router.get("/seg/{token}")
async def enhanced_proxy_seg(token: str, request: Request) -> Response:
    """Proxy an HLS segment with Range support, CDN failover, and request coalescing.

    Fetch order: primary → mirror[0] → mirror[1] … Circuit-broken hosts are
    skipped; if *all* candidates are open the primary is tried anyway as a
    half-open probe.  Concurrent requests for the same ``(token, Range)`` pair
    share a single upstream fetch via ``_fetch_once``.  ``X-CDN-Attempt``
    in the response indicates which candidate succeeded.
    """
    entry = _resolve(token, ns=_NS_SEG)
    if not entry:
        return Response(status_code=410, headers={"X-Segment-Expired": "true"})

    _validate(entry.primary)
    client = await _get_proxy_client()

    range_hdr = request.headers.get("Range")
    upstream_headers: dict[str, str] = {"Range": range_hdr} if range_hdr else {}

    # Build candidate list, skipping circuit-broken hosts.
    # Fall back to [primary] if every candidate's circuit is open (half-open probe).
    candidates = [entry.primary, *entry.mirrors]
    available  = (
        [u for u in candidates if not _cb(_hostname(u)).is_open()]
        or [entry.primary]
    )

    t0        = time.monotonic()
    last_exc: Exception | None = None

    for attempt, url in enumerate(available[:_RETRY_MAX]):
        host = _hostname(url)
        try:
            resp = await _fetch_once(client, url, upstream_headers)
        except httpx.TimeoutException as exc:
            last_exc = exc
            _cb(host).record_failure(host)
            _qlog("seg_timeout", attempt=str(attempt + 1), host=host)
            if attempt < len(available) - 1:
                await asyncio.sleep(_backoff(attempt))
            continue
        except Exception as exc:
            last_exc = exc
            _cb(host).record_failure(host)
            _qlog("seg_error", attempt=str(attempt + 1), host=host, err=str(exc)[:80])
            if attempt < len(available) - 1:
                await asyncio.sleep(_backoff(attempt))
            continue

        if resp.status_code in (404, 410):
            return Response(status_code=410, headers={"X-Segment-Expired": "true"})

        if resp.status_code == 206:  # Range satisfied
            _cb(host).record_success(host)
            return Response(
                content=resp.content,
                status_code=206,
                media_type=resp.headers.get("content-type", "video/MP2T"),
                headers={
                    **_range_headers(resp),
                    "Access-Control-Allow-Origin": "*",
                    "X-Latency-Ms":                str(int((time.monotonic() - t0) * 1_000)),
                    "X-CDN-Attempt":               str(attempt + 1),
                },
            )

        if resp.is_success:
            _cb(host).record_success(host)
            elapsed = time.monotonic() - t0
            bw_kbps = _update_bw(host, len(resp.content), elapsed)
            return Response(
                content=resp.content,
                media_type=resp.headers.get("content-type", "video/MP2T"),
                headers={
                    "Cache-Control":               "public, max-age=3600",
                    "Access-Control-Allow-Origin": "*",
                    "X-Latency-Ms":                str(int(elapsed * 1_000)),
                    "X-Bandwidth-Kbps":            str(bw_kbps),
                    "X-CDN-Attempt":               str(attempt + 1),
                },
            )

        last_exc = Exception(f"HTTP {resp.status_code}")
        _cb(host).record_failure(host)
        if attempt < len(available) - 1:
            await asyncio.sleep(_backoff(attempt))

    raise HTTPException(
        status_code=502,
        detail=(
            f"Segment unavailable after {min(len(available), _RETRY_MAX)} attempt(s): {last_exc}"
        ),
    )


@router.head("/seg/{token}")
async def enhanced_proxy_seg_head(token: str) -> Response:
    """HEAD support — lets players probe segment size before fetching."""
    entry = _resolve(token, ns=_NS_SEG)
    if not entry:
        return Response(status_code=410)

    _validate(entry.primary)
    client = await _get_proxy_client()

    try:
        resp    = await client.head(entry.primary)
        headers = {"Access-Control-Allow-Origin": "*", "Accept-Ranges": "bytes"}
        if cl := resp.headers.get("content-length"):
            headers["Content-Length"] = cl
        if ct := resp.headers.get("content-type"):
            headers["Content-Type"] = ct
        return Response(status_code=resp.status_code, headers=headers)
    except Exception:
        return Response(status_code=502)


# ── MP4 streaming ─────────────────────────────────────────────────────────────

@router.get("/mp4")
async def proxy_mp4_stream(
    request:  Request,
    url:      str = Query(...),
    filename: str = Query(default="stersh-download.mp4"),
) -> StreamingResponse:
    """Stream-proxy an MP4 file with byte-range support for in-browser seeking."""
    host   = _validate(url)
    client = await _get_proxy_client()

    range_hdr = request.headers.get("Range")
    upstream_headers: dict[str, str] = {"Range": range_hdr} if range_hdr else {}

    try:
        head         = await client.head(url)
        total_size   = head.headers.get("content-length", "")
        content_type = head.headers.get("content-type", "video/mp4")
    except Exception:
        total_size, content_type = "", "video/mp4"

    async def _stream():
        try:
            async with client.stream("GET", url, headers=upstream_headers) as resp:
                if not resp.is_success and resp.status_code != 206:
                    _qlog("mp4_upstream_error", host=host, status=str(resp.status_code))
                    return
                async for chunk in resp.aiter_bytes(_MP4_CHUNK):
                    yield chunk
        except Exception as exc:
            _qlog("mp4_stream_error", host=host, err=str(exc)[:80])

    response_headers: dict[str, str] = {
        "Content-Disposition":           f'attachment; filename="{filename}"',
        "Accept-Ranges":                 "bytes",
        "Access-Control-Allow-Origin":   "*",
        "Access-Control-Expose-Headers": "Content-Length, Content-Range",
        "Cache-Control":                 "no-store",
    }
    if total_size:
        response_headers["Content-Length"] = total_size

    return StreamingResponse(
        _stream(),
        status_code=206 if range_hdr else 200,
        media_type=content_type,
        headers=response_headers,
    )


# ── Multi-CDN health ──────────────────────────────────────────────────────────

@router.get("/multi/health")
async def multi_source_health(
    urls: str = Query(..., description="Comma-separated CDN URLs to probe"),
) -> dict:
    """Fan-out HEAD requests across CDN mirrors; return latency-ranked results.

    Circuit-broken hosts are reported immediately without an upstream probe,
    keeping response time low even when some mirrors are degraded.
    """
    url_list = [u.strip() for u in urls.split(",") if u.strip()][:8]
    client   = await _get_proxy_client()

    async def _probe(url: str) -> dict:
        try:
            host = _validate(url)
            if _cb(host).is_open():
                return {
                    "url":        url,
                    "ok":         False,
                    "status":     0,
                    "latency_ms": -1,
                    "reason":     "circuit_open",
                }
            t0   = time.monotonic()
            resp = await asyncio.wait_for(client.head(url), timeout=5.0)
            lat  = int((time.monotonic() - t0) * 1_000)
            if resp.is_success:
                _cb(host).record_success(host)
            else:
                _cb(host).record_failure(host)
            return {
                "url":            url,
                "ok":             resp.is_success,
                "status":         resp.status_code,
                "latency_ms":     lat,
                "content_length": resp.headers.get("content-length"),
            }
        except HTTPException as exc:
            return {"url": url, "ok": False, "status": exc.status_code, "latency_ms": -1}
        except Exception as exc:
            return {"url": url, "ok": False, "error": str(exc), "latency_ms": -1}

    results = await asyncio.gather(*[_probe(u) for u in url_list])
    ranked  = sorted(results, key=lambda r: (not r.get("ok"), r.get("latency_ms", 9_999)))
    return {
        "results": ranked,
        "best":    ranked[0]["url"] if ranked and ranked[0].get("ok") else None,
    }


# ── Manifest rewriter ─────────────────────────────────────────────────────────

def _rewrite_manifest(
    text:         str,
    base_url:     str,
    *,
    mirror_bases: tuple[str, ...] = (),
) -> str:
    """Rewrite HLS manifest URIs so all requests flow through the proxy.

    *Master playlist* (``#EXT-X-STREAM-INF``)
      Variant URIs → ``/api/proxy/hls?url=<var-token>``

    *Media playlist* (segments)
      Segment URIs → ``/api/proxy/seg/<seg-token>``

    ``mirror_bases`` is an optional tuple of alternate CDN origin prefixes
    (scheme + host only, e.g. ``https://cdn2.example.com``).  For each
    segment, mirror URLs are derived by substituting only the origin part of
    the primary CDN URL, then stored alongside the primary in the token entry.
    This allows ``enhanced_proxy_seg`` to fail-over at the CDN level without
    needing a manifest re-fetch.

    Mirror hosts that are not in ``ENHANCED_ALLOWED_HOSTS`` are silently
    dropped before processing begins.

    ``#EXT-X-ENDLIST`` and ``#EXT-X-PLAYLIST-TYPE`` are preserved verbatim
    so VOD playlists remain VOD and never poll for new segments.
    """
    # Validate mirror origins against the allowlist upfront.
    mirror_bases = tuple(
        mb for mb in mirror_bases
        if (urlparse(mb).hostname or "").lower() in ENHANCED_ALLOWED_HOSTS
    )[:_MAX_MIRRORS]

    lines:      list[str] = []
    is_variant: bool      = False

    for raw in text.splitlines():
        stripped = raw.strip()

        # Comment / tag lines pass through; detect the variant-stream marker.
        if not stripped or stripped.startswith("#"):
            if stripped.startswith("#EXT-X-STREAM-INF:"):
                is_variant = True
            lines.append(raw)
            continue

        # Resolve relative URIs against base_url.
        full_url = stripped if stripped.startswith("http") else base_url + stripped

        if is_variant:
            token = _store(full_url, ns=_NS_VAR)
            lines.append(f"/api/proxy/hls?url={token}")
            is_variant = False
        else:
            # Derive per-segment mirror URLs by substituting the origin
            # (scheme + netloc) while preserving the path exactly.
            full_parsed = urlparse(full_url)
            seg_mirrors: list[str] = []
            for mb in mirror_bases:
                mp = urlparse(mb)
                mirror_url = urlunparse((
                    mp.scheme or full_parsed.scheme,
                    mp.netloc,
                    full_parsed.path,
                    full_parsed.params,
                    full_parsed.query,
                    "",
                ))
                if mirror_url != full_url:
                    seg_mirrors.append(mirror_url)

            token = _store(full_url, ns=_NS_SEG, mirrors=tuple(seg_mirrors))
            lines.append(f"/api/proxy/seg/{token}")

    return "\n".join(lines)