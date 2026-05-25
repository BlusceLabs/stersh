"""FastAPI router for watchfy's White server (111movies.net).

Exposes:
  GET /api/white/source      — extract HLS + MP4 sources via Playwright
  GET /api/white/proxy/hls   — proxy and rewrite HLS manifests
  GET /api/white/proxy/seg/{token} — proxy individual HLS segments
  GET /api/white/prewarm     — background cache warm-up
  GET /api/white/refresh     — force-evict cache and re-extract
  GET /api/white/download    — serve proxied MP4 download with progress headers
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

from .white import extract_hls_from_111movies, extract_sources_legacy

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

_WHITE_CACHE_TTL = int(os.environ.get("WHITE_CACHE_TTL", 15 * 60))
_WHITE_STALE_TTL = int(os.environ.get("WHITE_STALE_TTL", 30 * 60))
_SHORT_TOKEN_LEN = 16

ALLOWED_WHITE_HOSTS = frozenset(
    {
        "111movies.net",
        "www.111movies.net",
        "cdn.111movies.net",
        "cloudnestra.com",
        "whisperingauroras.com",
    }
)

_CDN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.111movies.net/",
    "Origin": "https://www.111movies.net",
}

# ── In-memory state ───────────────────────────────────────────────────────────

_white_cache: TTLCache[str, list[dict]] = TTLCache(maxsize=300, ttl=_WHITE_CACHE_TTL)
_white_timestamps: dict[str, float] = {}
_white_refreshing: set[str] = set()
_white_futures: dict[str, asyncio.Future] = {}
_white_futures_lock = asyncio.Lock()

_url_token_cache: TTLCache[str, str] = TTLCache(maxsize=2000, ttl=1800)

# Shared httpx client
_white_client: httpx.AsyncClient | None = None


# ── Browser singleton ─────────────────────────────────────────────────────────

_white_browser = None
_white_playwright = None
_white_browser_lock = asyncio.Lock()


async def _get_white_browser():
    global _white_browser, _white_playwright
    async with _white_browser_lock:
        if _white_browser is None or not _white_browser.is_connected():
            from playwright.async_api import async_playwright
            _white_playwright = await async_playwright().start()
            _white_browser = await _white_playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-gpu",
                    "--mute-audio",
                ],
            )
    return _white_browser


async def shutdown_white_browser() -> None:
    global _white_browser, _white_playwright
    async with _white_browser_lock:
        for obj, method in [(_white_browser, "close"), (_white_playwright, "stop")]:
            if obj is not None:
                try:
                    await getattr(obj, method)()
                except Exception:
                    pass
        _white_browser = None
        _white_playwright = None
    logger.info('"white_browser_shutdown"')


async def shutdown_white_client() -> None:
    global _white_client
    if _white_client and not _white_client.is_closed:
        await _white_client.aclose()
        _white_client = None
    logger.info('"white_client_shutdown"')


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_white_client() -> httpx.AsyncClient:
    global _white_client
    if _white_client is None or _white_client.is_closed:
        _white_client = httpx.AsyncClient(
            headers=_CDN_HEADERS,
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=30, max_keepalive_connections=10),
        )
    return _white_client


def _cache_key(tmdb_id: int, media_type: str, season: int, episode: int) -> str:
    return f"white:{tmdb_id}:{media_type}:{season}:{episode}"


def _store_url(url: str) -> str:
    token = hashlib.sha256(url.encode()).hexdigest()[:_SHORT_TOKEN_LEN]
    _url_token_cache[token] = url
    return token


def _resolve_token(token: str) -> str | None:
    return _url_token_cache.get(token)


def _validate_host(url: str) -> None:
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid scheme")
    if parsed.hostname not in ALLOWED_WHITE_HOSTS:
        raise HTTPException(status_code=403, detail=f"Host not allowed: {parsed.hostname}")


def _is_stale(ck: str) -> bool:
    ts = _white_timestamps.get(ck)
    return ts is None or (time.monotonic() - ts) > _WHITE_CACHE_TTL


# ── Singleflight extraction ───────────────────────────────────────────────────

async def _extract_coalesced(ck: str, tmdb_id: int, media_type: str, season: int, episode: int) -> list[dict] | None:
    async with _white_futures_lock:
        if ck in _white_futures:
            fut = _white_futures[ck]
        else:
            loop = asyncio.get_event_loop()
            fut: asyncio.Future = loop.create_future()
            _white_futures[ck] = fut

            async def _run():
                try:
                    browser = await _get_white_browser()
                    result = await extract_sources_legacy(
                        tmdb_id, media_type, season, episode,
                        browser=browser,
                        cdn_headers=_CDN_HEADERS,
                    )
                    fut.set_result(result)
                except Exception as exc:
                    fut.set_exception(exc)
                finally:
                    async with _white_futures_lock:
                        _white_futures.pop(ck, None)

            asyncio.get_event_loop().create_task(_run())

    return await asyncio.shield(fut)


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/white", tags=["white"])


@router.get("/source")
async def white_source(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
    refresh: bool = Query(default=False),
) -> dict:
    """Extract HLS + MP4 download sources from 111movies.net.

    Returns sources sorted highest quality first.
    MP4 entries carry ``"type": "mp4"`` for client-side download UI.
    """
    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")

    ck = _cache_key(tmdbId, mediaType, season, episode)

    if refresh:
        _white_cache.pop(ck, None)
        _white_timestamps.pop(ck, None)
    else:
        cached = _white_cache.get(ck)
        if cached is not None:
            stale = _is_stale(ck)
            if stale and ck not in _white_refreshing:
                _white_refreshing.add(ck)
                asyncio.get_event_loop().create_task(
                    _background_refresh(ck, tmdbId, mediaType, season, episode)
                )
            return {"sources": cached, "cached": True, "stale": stale, "server": "white"}

    try:
        sources = await asyncio.wait_for(
            _extract_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        stale = _white_cache.get(ck)
        if stale:
            return {"sources": stale, "cached": True, "stale": True, "server": "white"}
        raise HTTPException(status_code=504, detail="White source extraction timed out")
    except Exception as exc:
        stale = _white_cache.get(ck)
        if stale:
            return {"sources": stale, "cached": True, "stale": True, "server": "white"}
        raise HTTPException(status_code=502, detail=f"White extraction failed: {exc}")

    if sources:
        _white_cache[ck] = sources
        _white_timestamps[ck] = time.monotonic()

    return {"sources": sources or [], "cached": False, "stale": False, "server": "white"}


@router.get("/prewarm")
async def white_prewarm(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Pre-warm 111movies cache for a title — fire and forget."""
    ck = _cache_key(tmdbId, mediaType, season, episode)
    if ck in _white_cache:
        if _is_stale(ck) and ck not in _white_refreshing:
            _white_refreshing.add(ck)
            asyncio.get_event_loop().create_task(
                _background_refresh(ck, tmdbId, mediaType, season, episode)
            )
            return {"status": "cached_refreshing"}
        return {"status": "cached"}
    if ck not in _white_futures:
        asyncio.get_event_loop().create_task(
            _warm_and_cache(tmdbId, mediaType, season, episode)
        )
    return {"status": "warming"}


@router.get("/refresh")
async def white_refresh(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Force-refresh the white source cache."""
    return await white_source(
        request=None,  # type: ignore[arg-type]
        tmdbId=tmdbId,
        mediaType=mediaType,
        season=season,
        episode=episode,
        refresh=True,
    )


# ── HLS manifest proxy ────────────────────────────────────────────────────────

@router.get("/proxy/hls")
async def white_proxy_hls(url: str = Query(...)) -> Response:
    """Proxy and rewrite a white-server HLS manifest."""
    if len(url) == _SHORT_TOKEN_LEN and all(c in "0123456789abcdef" for c in url):
        resolved = _resolve_token(url)
        if not resolved:
            raise HTTPException(status_code=410, detail="Token expired — refresh manifest")
        url = resolved

    _validate_host(url)
    client = await _get_white_client()
    resp = await client.get(url)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="HLS proxy failed")

    base_url = url.rsplit("/", 1)[0] + "/"
    lines: list[str] = []
    for line in resp.text.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            if not stripped.startswith("http"):
                stripped = base_url + stripped
            token = _store_url(stripped)
            lines.append(f"/api/white/proxy/seg/{token}")
        else:
            lines.append(line)

    return Response(
        content="\n".join(lines),
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "no-cache", "Access-Control-Allow-Origin": "*"},
    )


@router.get("/proxy/seg/{token}")
async def white_proxy_seg(token: str) -> Response:
    """Proxy a single white-server HLS segment with 3-attempt retry."""
    url = _resolve_token(token)
    if not url:
        return Response(status_code=410, headers={"X-Segment-Expired": "true"})
    _validate_host(url)
    client = await _get_white_client()
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = await client.get(url)
            if resp.is_success:
                return Response(
                    content=resp.content,
                    media_type=resp.headers.get("content-type", "video/MP2T"),
                    headers={"Cache-Control": "public, max-age=3600", "Access-Control-Allow-Origin": "*"},
                )
            last_exc = Exception(f"HTTP {resp.status_code}")
        except Exception as exc:
            last_exc = exc
        if attempt < 2:
            await asyncio.sleep(0.5 * (attempt + 1))
    raise HTTPException(status_code=502, detail=f"Segment unavailable: {last_exc}")


@router.get("/download")
async def white_download(url: str = Query(...), filename: str = Query(default="watchfy.mp4")) -> StreamingResponse:
    """Proxy an MP4 download with proper Content-Disposition headers.

    Streams the file byte-by-byte — no disk buffering.
    """
    _validate_host(url)
    client = await _get_white_client()

    async def _stream():
        async with client.stream("GET", url) as resp:
            if not resp.is_success:
                return
            async for chunk in resp.aiter_bytes(65536):
                yield chunk

    # HEAD request to get content-length for progress bar
    try:
        head = await client.head(url)
        content_length = head.headers.get("content-length", "")
    except Exception:
        content_length = ""

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-store",
    }
    if content_length:
        headers["Content-Length"] = content_length

    return StreamingResponse(_stream(), media_type="video/mp4", headers=headers)


# ── Background tasks ──────────────────────────────────────────────────────────

async def _warm_and_cache(tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    ck = _cache_key(tmdb_id, media_type, season, episode)
    try:
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _white_cache[ck] = sources
            _white_timestamps[ck] = time.monotonic()
    except Exception as exc:
        logger.error('"white_prewarm_error":{"key":"%s","err":"%s"}', ck, exc)


async def _background_refresh(ck: str, tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    try:
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _white_cache[ck] = sources
            _white_timestamps[ck] = time.monotonic()
    except Exception as exc:
        logger.error('"white_bg_refresh_error":{"key":"%s","err":"%s"}', ck, exc)
    finally:
        _white_refreshing.discard(ck)