"""FastAPI router for watchfy's Pink server (flickystream.ru).

Exposes:
  GET /api/pink/source      — extract HLS + MP4 sources via Playwright
  GET /api/pink/proxy/hls   — proxy and rewrite HLS manifests
  GET /api/pink/proxy/seg/{token} — proxy individual HLS segments
  GET /api/pink/prewarm     — background cache warm-up
  GET /api/pink/refresh     — force-evict cache and re-extract
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query, Request, Response

from .pink import extract_hls_from_flickystream, extract_sources_legacy

logger = logging.getLogger(__name__)

_PINK_CACHE_TTL = int(os.environ.get("PINK_CACHE_TTL", 15 * 60))
_SHORT_TOKEN_LEN = 16

ALLOWED_PINK_HOSTS = frozenset(
    {
        "hydrahd.ru",
        "www.hydrahd.ru",
        "cdn.hydrahd.ru",
    }
)

_CDN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.hydrahd.ru/",
    "Origin": "https://www.hydrahd.ru",
}

# Cache
_pink_cache: TTLCache[str, list[dict]] = TTLCache(maxsize=300, ttl=_PINK_CACHE_TTL)
_pink_timestamps: dict[str, float] = {}
_pink_refreshing: set[str] = set()
_pink_futures: dict[str, asyncio.Future] = {}
_pink_futures_lock = asyncio.Lock()
_url_token_cache: TTLCache[str, str] = TTLCache(maxsize=2000, ttl=1800)

# Browser / client singletons
_pink_browser = None
_pink_playwright = None
_pink_browser_lock = asyncio.Lock()
_pink_client: httpx.AsyncClient | None = None


async def _get_pink_browser():
    global _pink_browser, _pink_playwright
    async with _pink_browser_lock:
        if _pink_browser is None or not _pink_browser.is_connected():
            from playwright.async_api import async_playwright
            _pink_playwright = await async_playwright().start()
            _pink_browser = await _pink_playwright.chromium.launch(
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
    return _pink_browser


async def shutdown_pink_browser() -> None:
    global _pink_browser, _pink_playwright
    async with _pink_browser_lock:
        for obj, method in [(_pink_browser, "close"), (_pink_playwright, "stop")]:
            if obj is not None:
                try:
                    await getattr(obj, method)()
                except Exception:
                    pass
        _pink_browser = None
        _pink_playwright = None
    logger.info('"pink_browser_shutdown"')


async def shutdown_pink_client() -> None:
    global _pink_client
    if _pink_client and not _pink_client.is_closed:
        await _pink_client.aclose()
        _pink_client = None
    logger.info('"pink_client_shutdown"')


async def _get_pink_client() -> httpx.AsyncClient:
    global _pink_client
    if _pink_client is None or _pink_client.is_closed:
        _pink_client = httpx.AsyncClient(
            headers=_CDN_HEADERS,
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=30, max_keepalive_connections=10),
        )
    return _pink_client


def _cache_key(tmdb_id: int, media_type: str, season: int, episode: int) -> str:
    return f"pink:{tmdb_id}:{media_type}:{season}:{episode}"


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
    if parsed.hostname not in ALLOWED_PINK_HOSTS:
        raise HTTPException(status_code=403, detail=f"Host not allowed: {parsed.hostname}")


def _is_stale(ck: str) -> bool:
    ts = _pink_timestamps.get(ck)
    return ts is None or (time.monotonic() - ts) > _PINK_CACHE_TTL


async def _extract_coalesced(ck: str, tmdb_id: int, media_type: str, season: int, episode: int) -> list[dict] | None:
    async with _pink_futures_lock:
        if ck in _pink_futures:
            fut = _pink_futures[ck]
        else:
            loop = asyncio.get_event_loop()
            fut: asyncio.Future = loop.create_future()
            _pink_futures[ck] = fut

            async def _run():
                try:
                    browser = await _get_pink_browser()
                    result = await extract_sources_legacy(
                        tmdb_id, media_type, season, episode,
                        browser=browser,
                        cdn_headers=_CDN_HEADERS,
                    )
                    fut.set_result(result)
                except Exception as exc:
                    fut.set_exception(exc)
                finally:
                    async with _pink_futures_lock:
                        _pink_futures.pop(ck, None)

            asyncio.get_event_loop().create_task(_run())

    return await asyncio.shield(fut)


router = APIRouter(prefix="/api/pink", tags=["pink"])


@router.get("/source")
async def pink_source(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
    refresh: bool = Query(default=False),
) -> dict:
    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")

    ck = _cache_key(tmdbId, mediaType, season, episode)

    if refresh:
        _pink_cache.pop(ck, None)
        _pink_timestamps.pop(ck, None)
    else:
        cached = _pink_cache.get(ck)
        if cached is not None:
            stale = _is_stale(ck)
            if stale and ck not in _pink_refreshing:
                _pink_refreshing.add(ck)
                asyncio.get_event_loop().create_task(
                    _background_refresh(ck, tmdbId, mediaType, season, episode)
                )
            return {"sources": cached, "cached": True, "stale": stale, "server": "pink"}

    try:
        sources = await asyncio.wait_for(
            _extract_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        stale = _pink_cache.get(ck)
        if stale:
            return {"sources": stale, "cached": True, "stale": True, "server": "pink"}
        raise HTTPException(status_code=504, detail="Pink source extraction timed out")
    except Exception as exc:
        stale = _pink_cache.get(ck)
        if stale:
            return {"sources": stale, "cached": True, "stale": True, "server": "pink"}
        raise HTTPException(status_code=502, detail=f"Pink extraction failed: {exc}")

    if sources:
        _pink_cache[ck] = sources
        _pink_timestamps[ck] = time.monotonic()

    return {"sources": sources or [], "cached": False, "stale": False, "server": "pink"}


@router.get("/prewarm")
async def pink_prewarm(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    ck = _cache_key(tmdbId, mediaType, season, episode)
    if ck in _pink_cache:
        if _is_stale(ck) and ck not in _pink_refreshing:
            _pink_refreshing.add(ck)
            asyncio.get_event_loop().create_task(
                _background_refresh(ck, tmdbId, mediaType, season, episode)
            )
            return {"status": "cached_refreshing"}
        return {"status": "cached"}
    if ck not in _pink_futures:
        asyncio.get_event_loop().create_task(
            _warm_and_cache(tmdbId, mediaType, season, episode)
        )
    return {"status": "warming"}


@router.get("/refresh")
async def pink_refresh(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    return await pink_source(
        request=None,  # type: ignore
        tmdbId=tmdbId,
        mediaType=mediaType,
        season=season,
        episode=episode,
        refresh=True,
    )


@router.get("/proxy/hls")
async def pink_proxy_hls(url: str = Query(...)) -> Response:
    if len(url) == _SHORT_TOKEN_LEN and all(c in "0123456789abcdef" for c in url):
        resolved = _resolve_token(url)
        if not resolved:
            raise HTTPException(status_code=410, detail="Token expired")
        url = resolved

    _validate_host(url)
    client = await _get_pink_client()
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
            lines.append(f"/api/pink/proxy/seg/{token}")
        else:
            lines.append(line)

    return Response(
        content="\n".join(lines),
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "no-cache", "Access-Control-Allow-Origin": "*"},
    )


@router.get("/proxy/seg/{token}")
async def pink_proxy_seg(token: str) -> Response:
    url = _resolve_token(token)
    if not url:
        return Response(status_code=410, headers={"X-Segment-Expired": "true"})
    _validate_host(url)
    client = await _get_pink_client()
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


async def _warm_and_cache(tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    ck = _cache_key(tmdb_id, media_type, season, episode)
    try:
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _pink_cache[ck] = sources
            _pink_timestamps[ck] = time.monotonic()
    except Exception as exc:
        logger.error('"pink_prewarm_error":{"key":"%s","err":"%s"}', ck, exc)


async def _background_refresh(ck: str, tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    try:
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _pink_cache[ck] = sources
            _pink_timestamps[ck] = time.monotonic()
    except Exception as exc:
        logger.error('"pink_bg_refresh_error":{"key":"%s","err":"%s"}', ck, exc)
    finally:
        _pink_refreshing.discard(ck)