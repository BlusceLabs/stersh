"""Enhanced proxy routes for watchfy — multi-CDN adaptive proxy.

Extends the base proxy with:
  - HTTP Range request pass-through (seek support for MP4 progressive download)
  - Bandwidth estimation header injection (X-Bandwidth-Kbps)
  - CDN fallback chain: primary → mirror → error
  - Per-segment latency logging for QoS analytics
  - CORS preflight handling
  - /api/proxy/multi — fan-out source health check across all CDN mirrors
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

# ── Allowed CDN hosts (union of vidking + white + additional mirrors) ──────────

ENHANCED_ALLOWED_HOSTS = frozenset(
    {
        # Vidking CDN
        "easy.speedsterwave.app",
        "cdn.vidking.net",
        "vidking.net",
        # White / 111movies CDN
        "cloudnestra.com",
        "whisperingauroras.com",
        "111movies.net",
        "www.111movies.net",
        "cdn.111movies.net",
        # Common HLS CDN mirrors
        "cdn.jwplayer.com",
        "content.jwplatform.com",
        "cdn.plyr.io",
    }
)

_CDN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
}

_SHORT_TOKEN_LEN = 16
_url_store: dict[str, str] = {}

_proxy_client: httpx.AsyncClient | None = None


async def _get_proxy_client() -> httpx.AsyncClient:
    global _proxy_client
    if _proxy_client is None or _proxy_client.is_closed:
        _proxy_client = httpx.AsyncClient(
            headers=_CDN_HEADERS,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=40),
        )
    return _proxy_client


async def shutdown_enhanced_client() -> None:
    global _proxy_client
    if _proxy_client and not _proxy_client.is_closed:
        await _proxy_client.aclose()
        _proxy_client = None


def _store(url: str) -> str:
    token = hashlib.sha256(url.encode()).hexdigest()[:_SHORT_TOKEN_LEN]
    _url_store[token] = url
    return token


def _resolve(token: str) -> str | None:
    return _url_store.get(token)


def _validate(url: str) -> None:
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    if parsed.hostname not in ENHANCED_ALLOWED_HOSTS:
        raise HTTPException(status_code=403, detail=f"Host not in allowlist: {parsed.hostname}")


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/proxy", tags=["proxy"])


@router.options("/{path:path}")
async def proxy_cors_preflight(path: str) -> Response:
    """Handle CORS preflight for all proxy routes."""
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type, Accept",
            "Access-Control-Max-Age": "86400",
        },
    )


@router.get("/hls")
async def enhanced_proxy_hls(
    request: Request,
    url: str = Query(...),
    origin: str = Query(default=""),
) -> Response:
    """Proxy and rewrite an HLS manifest with full segment token wrapping.

    `origin` overrides the Referer/Origin headers sent upstream — useful
    when the CDN checks the referring domain.
    """
    # Token resolution
    if len(url) == _SHORT_TOKEN_LEN and all(c in "0123456789abcdef" for c in url):
        resolved = _resolve(url)
        if not resolved:
            raise HTTPException(status_code=410, detail="Token expired — refresh manifest")
        url = resolved

    _validate(url)
    client = await _get_proxy_client()

    upstream_headers = {}
    if origin:
        upstream_headers["Referer"] = origin
        upstream_headers["Origin"] = origin

    try:
        resp = await client.get(url, headers=upstream_headers)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="CDN manifest timeout")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"CDN unreachable: {exc}")

    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="CDN manifest error")

    base_url = url.rsplit("/", 1)[0] + "/"
    rewritten = _rewrite_manifest(resp.text, base_url)

    return Response(
        content=rewritten,
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "X-Bandwidth-Kbps",
        },
    )


@router.get("/seg/{token}")
async def enhanced_proxy_seg(token: str, request: Request) -> Response:
    """Proxy an HLS segment with Range support, retries, and latency headers.

    Range requests are forwarded verbatim — enables mid-segment seeking
    in some HLS.js configurations.
    """
    url = _resolve(token)
    if not url:
        return Response(status_code=410, headers={"X-Segment-Expired": "true"})

    _validate(url)
    client = await _get_proxy_client()

    # Pass-through Range header if present (byte-range seeks)
    upstream_headers: dict[str, str] = {}
    range_header = request.headers.get("Range")
    if range_header:
        upstream_headers["Range"] = range_header

    t0 = time.monotonic()
    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            resp = await client.get(url, headers=upstream_headers)
            latency_ms = int((time.monotonic() - t0) * 1000)

            if resp.status_code == 206:  # Partial Content — range satisfied
                return Response(
                    content=resp.content,
                    status_code=206,
                    media_type=resp.headers.get("content-type", "video/MP2T"),
                    headers={
                        **_extract_range_headers(resp),
                        "Access-Control-Allow-Origin": "*",
                        "X-Latency-Ms": str(latency_ms),
                    },
                )

            if resp.is_success:
                content_length = int(resp.headers.get("content-length", "0") or "0")
                bandwidth_kbps = _estimate_bandwidth(content_length, t0)
                return Response(
                    content=resp.content,
                    media_type=resp.headers.get("content-type", "video/MP2T"),
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*",
                        "X-Latency-Ms": str(latency_ms),
                        "X-Bandwidth-Kbps": str(bandwidth_kbps),
                    },
                )

            if resp.status_code in (404, 410):
                return Response(status_code=410, headers={"X-Segment-Expired": "true"})

            last_exc = Exception(f"HTTP {resp.status_code}")

        except httpx.TimeoutException as exc:
            last_exc = exc
            logger.warning('"seg_timeout":{"attempt":%d,"url":"%s"}', attempt + 1, url[:80])
        except Exception as exc:
            last_exc = exc
            logger.warning('"seg_error":{"attempt":%d,"err":"%s"}', attempt + 1, exc)

        if attempt < 2:
            await asyncio.sleep(0.4 * (attempt + 1))

    raise HTTPException(status_code=502, detail=f"Segment unavailable after 3 attempts: {last_exc}")


@router.head("/seg/{token}")
async def enhanced_proxy_seg_head(token: str) -> Response:
    """HEAD request support — lets players probe segment size before fetching."""
    url = _resolve(token)
    if not url:
        return Response(status_code=410)
    _validate(url)
    client = await _get_proxy_client()
    try:
        resp = await client.head(url)
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Accept-Ranges": "bytes",
        }
        if cl := resp.headers.get("content-length"):
            headers["Content-Length"] = cl
        if ct := resp.headers.get("content-type"):
            headers["Content-Type"] = ct
        return Response(status_code=resp.status_code, headers=headers)
    except Exception:
        return Response(status_code=502)


@router.get("/mp4")
async def proxy_mp4_stream(
    request: Request,
    url: str = Query(...),
    filename: str = Query(default="watchfy-download.mp4"),
) -> StreamingResponse:
    """Stream-proxy an MP4 file with byte-range support for video seeking.

    Forwards Range headers so the browser can seek within the download.
    """
    _validate(url)
    client = await _get_proxy_client()

    upstream_headers: dict[str, str] = {}
    range_header = request.headers.get("Range")
    if range_header:
        upstream_headers["Range"] = range_header

    # HEAD first to get total size
    try:
        head = await client.head(url)
        total_size = head.headers.get("content-length", "")
        content_type = head.headers.get("content-type", "video/mp4")
    except Exception:
        total_size = ""
        content_type = "video/mp4"

    async def _stream():
        async with client.stream("GET", url, headers=upstream_headers) as resp:
            if not resp.is_success and resp.status_code != 206:
                return
            async for chunk in resp.aiter_bytes(65536):
                yield chunk

    status_code = 206 if range_header else 200
    response_headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Accept-Ranges": "bytes",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "Content-Length, Content-Range",
        "Cache-Control": "no-store",
    }
    if total_size:
        response_headers["Content-Length"] = total_size

    return StreamingResponse(
        _stream(),
        status_code=status_code,
        media_type=content_type,
        headers=response_headers,
    )


@router.get("/multi/health")
async def multi_source_health(
    urls: str = Query(..., description="Comma-separated list of CDN URLs to probe"),
) -> dict:
    """Fan-out HEAD requests to multiple CDN mirrors and return latency + status.

    Used by the player to pick the fastest available source before playback.
    """
    url_list = [u.strip() for u in urls.split(",") if u.strip()][:8]
    client = await _get_proxy_client()

    async def _probe(url: str) -> dict:
        try:
            _validate(url)
            t0 = time.monotonic()
            resp = await asyncio.wait_for(client.head(url), timeout=5.0)
            latency_ms = int((time.monotonic() - t0) * 1000)
            return {
                "url": url,
                "ok": resp.is_success,
                "status": resp.status_code,
                "latency_ms": latency_ms,
                "content_length": resp.headers.get("content-length"),
            }
        except HTTPException as exc:
            return {"url": url, "ok": False, "status": exc.status_code, "latency_ms": -1}
        except Exception as exc:
            return {"url": url, "ok": False, "error": str(exc), "latency_ms": -1}

    results = await asyncio.gather(*[_probe(u) for u in url_list])
    # Sort: working sources first, then by latency
    ranked = sorted(results, key=lambda r: (not r.get("ok"), r.get("latency_ms", 9999)))
    return {"results": ranked, "best": ranked[0]["url"] if ranked and ranked[0]["ok"] else None}


# ── Manifest rewriter ──────────────────────────────────────────────────────────

def _rewrite_manifest(text: str, base_url: str) -> str:
    """Rewrite all segment URIs in an HLS manifest to go through our proxy."""
    lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            if not stripped.startswith("http"):
                stripped = base_url + stripped
            token = _store(stripped)
            lines.append(f"/api/proxy/seg/{token}")
        else:
            lines.append(line)
    return "\n".join(lines)


# ── Bandwidth estimation ───────────────────────────────────────────────────────

def _estimate_bandwidth(content_length_bytes: int, start_time: float) -> int:
    """Estimate downstream bandwidth from a completed segment fetch."""
    elapsed = time.monotonic() - start_time
    if elapsed <= 0 or content_length_bytes <= 0:
        return 0
    return int((content_length_bytes * 8) / (elapsed * 1000))  # kbps


def _extract_range_headers(resp: httpx.Response) -> dict[str, str]:
    """Forward relevant range-response headers downstream."""
    headers: dict[str, str] = {}
    for h in ("Content-Range", "Content-Length", "Accept-Ranges", "ETag"):
        if v := resp.headers.get(h.lower()):
            headers[h] = v
    return headers