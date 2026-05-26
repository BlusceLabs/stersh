"""FastAPI router for watchfy's Black server (vidking.net).

Mounts at /api/black/*:
  GET /api/black/source       — extract HLS + MP4 via black.py Playwright extractor
  GET /api/black/proxy/hls    — proxy + rewrite HLS manifests
  GET /api/black/proxy/seg/{token} — proxy individual HLS segments (3-retry)
  GET /api/black/prewarm      — background cache warm-up
  GET /api/black/refresh      — force-evict cache + re-extract
  GET /api/black/download     — stream-proxy an MP4 download
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from collections import defaultdict
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.core.extractors.black import extract_sources_legacy

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

_BLACK_CACHE_TTL = int(os.environ.get("BLACK_CACHE_TTL", 15 * 60))
_BLACK_STALE_TTL = int(os.environ.get("BLACK_STALE_TTL", 30 * 60))
_SHORT_TOKEN_LEN = 16

ALLOWED_BLACK_HOSTS = frozenset(
    {
        "easy.speedsterwave.app",
        "cdn.vidking.net",
        "vidking.net",
        "www.vidking.net",
        "cloudnestra.com",
        "whisperingauroras.com",
    }
)

_CDN_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.vidking.net/",
    "Origin": "https://www.vidking.net",
}

# ── In-memory state ────────────────────────────────────────────────────────────

_black_cache: TTLCache[str, list[dict]] = TTLCache(maxsize=400, ttl=_BLACK_CACHE_TTL)
_black_timestamps: dict[str, float] = {}
_black_refreshing: set[str] = set()

# Singleflight gate — maps cache key → Future
_black_futures: dict[str, asyncio.Future] = {}
_black_futures_lock = asyncio.Lock()

# URL token store
_url_tokens: TTLCache[str, str] = TTLCache(maxsize=2000, ttl=1800)

# Shared httpx client
_black_client: httpx.AsyncClient | None = None

# ── Playwright browser singleton ───────────────────────────────────────────────

_black_browser = None
_black_playwright = None
_black_browser_lock = asyncio.Lock()


async def _get_black_browser():
    global _black_browser, _black_playwright
    async with _black_browser_lock:
        if _black_browser is None or not _black_browser.is_connected():
            from playwright.async_api import async_playwright
            _black_playwright = await async_playwright().start()
            _black_browser = await _black_playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-gpu",
                    "--mute-audio",
                    "--autoplay-policy=no-user-gesture-required",
                ],
            )
    return _black_browser


async def shutdown_black_browser() -> None:
    global _black_browser, _black_playwright
    async with _black_browser_lock:
        for obj, method in [(_black_browser, "close"), (_black_playwright, "stop")]:
            if obj is not None:
                try:
                    await getattr(obj, method)()
                except Exception:
                    pass
        _black_browser = None
        _black_playwright = None
    logger.info('"black_browser_shutdown"')


async def shutdown_black_client() -> None:
    global _black_client
    if _black_client and not _black_client.is_closed:
        await _black_client.aclose()
        _black_client = None
    logger.info('"black_client_shutdown"')


# ── HTTP client ────────────────────────────────────────────────────────────────

async def _get_black_client() -> httpx.AsyncClient:
    global _black_client
    if _black_client is None or _black_client.is_closed:
        _black_client = httpx.AsyncClient(
            headers=_CDN_HEADERS,
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=40, max_keepalive_connections=15),
        )
    return _black_client


# ── Helpers ────────────────────────────────────────────────────────────────────

def _cache_key(tmdb_id: int, media_type: str, season: int, episode: int) -> str:
    return f"black:{tmdb_id}:{media_type}:{season}:{episode}"


def _store_token(url: str) -> str:
    token = hashlib.sha256(url.encode()).hexdigest()[:_SHORT_TOKEN_LEN]
    _url_tokens[token] = url
    return token


def _resolve_token(token: str) -> str | None:
    return _url_tokens.get(token)


def _validate_host(url: str) -> None:
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    if parsed.hostname not in ALLOWED_BLACK_HOSTS:
        raise HTTPException(status_code=403, detail=f"Host not allowed: {parsed.hostname}")


def _is_stale(ck: str) -> bool:
    ts = _black_timestamps.get(ck)
    return ts is None or (time.monotonic() - ts) > _BLACK_CACHE_TTL


# ── Singleflight coalescer ─────────────────────────────────────────────────────

async def _extract_coalesced(
    ck: str,
    tmdb_id: int,
    media_type: str,
    season: int,
    episode: int,
) -> list[dict] | None:
    """One Playwright tab per cache key regardless of concurrent callers."""
    async with _black_futures_lock:
        if ck in _black_futures:
            fut = _black_futures[ck]
        else:
            loop = asyncio.get_event_loop()
            fut: asyncio.Future = loop.create_future()
            _black_futures[ck] = fut

            async def _run():
                try:
                    browser = await _get_black_browser()
                    result = await extract_sources_legacy(
                        tmdb_id, media_type, season, episode,
                        browser=browser,
                        cdn_headers=_CDN_HEADERS,
                    )
                    fut.set_result(result)
                except Exception as exc:
                    fut.set_exception(exc)
                finally:
                    async with _black_futures_lock:
                        _black_futures.pop(ck, None)

            asyncio.get_event_loop().create_task(_run())

    return await asyncio.shield(fut)


# ── Router ─────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/black", tags=["black"])


# ── Source endpoint ────────────────────────────────────────────────────────────

@router.get("/source")
async def black_source(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
    refresh: bool = Query(default=False),
) -> dict:
    """Extract HLS + MP4 sources from vidking.net.

    - Cached: served instantly, stale entries revalidated in background.
    - Concurrent callers for the same key share one Playwright tab (singleflight).
    - MP4 entries carry ``"type": "mp4"`` for client download UI.
    """
    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")

    ck = _cache_key(tmdbId, mediaType, season, episode)

    if refresh:
        _black_cache.pop(ck, None)
        _black_timestamps.pop(ck, None)
    else:
        cached = _black_cache.get(ck)
        if cached is not None:
            stale = _is_stale(ck)
            if stale and ck not in _black_refreshing:
                _black_refreshing.add(ck)
                asyncio.get_event_loop().create_task(
                    _bg_refresh(ck, tmdbId, mediaType, season, episode)
                )
            return {"sources": cached, "cached": True, "stale": stale, "server": "black"}

    try:
        sources = await asyncio.wait_for(
            _extract_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        stale = _black_cache.get(ck)
        if stale:
            return {"sources": stale, "cached": True, "stale": True, "server": "black"}
        raise HTTPException(status_code=504, detail="Black source extraction timed out")
    except Exception as exc:
        stale = _black_cache.get(ck)
        if stale:
            return {"sources": stale, "cached": True, "stale": True, "server": "black"}
        raise HTTPException(status_code=502, detail=f"Black extraction failed: {exc}")

    if sources:
        _black_cache[ck] = sources
        _black_timestamps[ck] = time.monotonic()

    return {"sources": sources or [], "cached": False, "stale": False, "server": "black"}


# ── Prewarm ────────────────────────────────────────────────────────────────────

@router.get("/prewarm")
async def black_prewarm(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Fire-and-forget cache warm-up for vidking sources."""
    ck = _cache_key(tmdbId, mediaType, season, episode)
    if ck in _black_cache:
        if _is_stale(ck) and ck not in _black_refreshing:
            _black_refreshing.add(ck)
            asyncio.get_event_loop().create_task(
                _bg_refresh(ck, tmdbId, mediaType, season, episode)
            )
            return {"status": "cached_refreshing"}
        return {"status": "cached"}
    if ck not in _black_futures:
        asyncio.get_event_loop().create_task(
            _warm_and_cache(tmdbId, mediaType, season, episode)
        )
    return {"status": "warming"}


# ── Force refresh ──────────────────────────────────────────────────────────────

@router.get("/refresh")
async def black_refresh(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Evict cache and re-extract from vidking."""
    ck = _cache_key(tmdbId, mediaType, season, episode)
    _black_cache.pop(ck, None)
    _black_timestamps.pop(ck, None)
    try:
        sources = await asyncio.wait_for(
            _extract_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Refresh timed out")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Refresh failed: {exc}")
    if sources:
        _black_cache[ck] = sources
        _black_timestamps[ck] = time.monotonic()
    return {"sources": sources or [], "refreshed": True, "server": "black"}


# ── HLS manifest proxy ─────────────────────────────────────────────────────────

@router.get("/proxy/hls")
async def black_proxy_hls(url: str = Query(...)) -> Response:
    """Proxy and rewrite a vidking HLS manifest — segment URIs become local tokens."""
    if len(url) == _SHORT_TOKEN_LEN and all(c in "0123456789abcdef" for c in url):
        resolved = _resolve_token(url)
        if not resolved:
            raise HTTPException(status_code=410, detail="Token expired — refresh manifest")
        url = resolved

    _validate_host(url)
    client = await _get_black_client()
    resp = await client.get(url)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="HLS upstream error")

    base_url = url.rsplit("/", 1)[0] + "/"
    lines: list[str] = []
    for line in resp.text.split("\n"):
        stripped = line.strip()

        if stripped == "#EXT-X-ENDLIST":
            continue

        if stripped.startswith("#EXT-X-PLAYLIST-TYPE:VOD"):
            lines.append("#EXT-X-PLAYLIST-TYPE:EVENT")
            continue

        if stripped and not stripped.startswith("#"):
            if not stripped.startswith("http"):
                stripped = base_url + stripped
            token = _store_token(stripped)
            lines.append(f"/api/black/proxy/seg/{token}")
        else:
            lines.append(line)

    return Response(
        content="\n".join(lines),
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ── Segment proxy ──────────────────────────────────────────────────────────────

@router.get("/proxy/seg/{token}")
async def black_proxy_seg(token: str) -> Response:
    """Proxy a single vidking HLS segment — 3-attempt retry with backoff."""
    url = _resolve_token(token)
    if not url:
        return Response(status_code=410, headers={"X-Segment-Expired": "true", "Retry-After": "0"})

    _validate_host(url)
    client = await _get_black_client()
    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            resp = await client.get(url)
            if resp.is_success:
                return Response(
                    content=resp.content,
                    media_type=resp.headers.get("content-type", "video/MP2T"),
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            if resp.status_code in (404, 410):
                return Response(status_code=410, headers={"X-Segment-Expired": "true"})
            last_exc = Exception(f"HTTP {resp.status_code}")
        except httpx.TimeoutException as exc:
            last_exc = exc
            logger.warning('"black_seg_timeout":{"attempt":%d}', attempt + 1)
        except Exception as exc:
            last_exc = exc
            logger.warning('"black_seg_error":{"attempt":%d,"err":"%s"}', attempt + 1, exc)
        if attempt < 2:
            await asyncio.sleep(0.5 * (attempt + 1))

    raise HTTPException(status_code=502, detail=f"Segment unavailable: {last_exc}")


# ── MP4 download proxy ─────────────────────────────────────────────────────────

@router.get("/download")
async def black_download(
    url: str = Query(...),
    filename: str = Query(default="watchfy-black.mp4"),
) -> StreamingResponse:
    """Stream-proxy an MP4 download from vidking CDN. No disk buffering."""
    _validate_host(url)
    client = await _get_black_client()

    async def _stream():
        async with client.stream("GET", url) as resp:
            if not resp.is_success:
                return
            async for chunk in resp.aiter_bytes(65536):
                yield chunk

    try:
        head = await client.head(url)
        content_length = head.headers.get("content-length", "")
    except Exception:
        content_length = ""

    headers: dict[str, str] = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-store",
        "Accept-Ranges": "bytes",
    }
    if content_length:
        headers["Content-Length"] = content_length

    return StreamingResponse(_stream(), media_type="video/mp4", headers=headers)


# ── Background tasks ───────────────────────────────────────────────────────────

async def _warm_and_cache(tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    ck = _cache_key(tmdb_id, media_type, season, episode)
    try:
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _black_cache[ck] = sources
            _black_timestamps[ck] = time.monotonic()
            logger.info('"black_prewarm_done":{"key":"%s","count":%d}', ck, len(sources))
    except Exception as exc:
        logger.error('"black_prewarm_error":{"key":"%s","err":"%s"}', ck, exc)


async def _bg_refresh(ck: str, tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    try:
        logger.info('"black_bg_refresh_start":{"key":"%s"}', ck)
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _black_cache[ck] = sources
            _black_timestamps[ck] = time.monotonic()
            logger.info('"black_bg_refresh_done":{"key":"%s","count":%d}', ck, len(sources))
    except Exception as exc:
        logger.error('"black_bg_refresh_error":{"key":"%s","err":"%s"}', ck, exc)
    finally:
        _black_refreshing.discard(ck)