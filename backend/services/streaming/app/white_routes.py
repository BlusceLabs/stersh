"""White server (111movies.net) FastAPI routes — Playwright extraction, HLS proxy, caching."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from .hls_parser import parse_master_manifest
from .white import extract_hls_from_111movies

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/white")

SHORT_TOKEN_LEN = 16
WHITE_BASE = "https://www.111movies.net"
HTTP_TIMEOUT = 30.0

WHITE_ALLOWED_PROXY_HOSTS = {
    "111movies.net",
    "www.111movies.net",
}

_white_url_token_cache: TTLCache = TTLCache(maxsize=2000, ttl=600)

_white_cdn_headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.111movies.net/",
    "Origin": "https://www.111movies.net",
}

_HLS_CACHE_TTL = int(os.environ.get("WHITE_HLS_CACHE_TTL", 5 * 60))
_HLS_STALE_TTL = int(os.environ.get("WHITE_HLS_STALE_TTL", 10 * 60))
_white_hls_cache: TTLCache[str, list[dict]] = TTLCache(maxsize=500, ttl=_HLS_CACHE_TTL)
_white_hls_cache_timestamps: dict[str, float] = {}
_white_hls_cache_refreshing: set[str] = set()


def _cache_key(tmdbId: int, mediaType: str, season: int = 1, episode: int = 1) -> str:
    return f"white:{tmdbId}:{mediaType}:{season}:{episode}"


def _is_cache_stale(ck: str) -> bool:
    ts = _white_hls_cache_timestamps.get(ck)
    if ts is None:
        return True
    age = time.time() - ts
    return age > _HLS_CACHE_TTL


def _is_cache_expired(ck: str) -> bool:
    ts = _white_hls_cache_timestamps.get(ck)
    if ts is None:
        return True
    age = time.time() - ts
    return age > _HLS_STALE_TTL


def _store_url(url: str) -> str:
    token = hashlib.sha256(url.encode()).hexdigest()[:SHORT_TOKEN_LEN]
    _white_url_token_cache[token] = url
    return token


def _resolve_url(token: str) -> str | None:
    return _white_url_token_cache.get(token)


def _validate_proxy_url(url: str) -> None:
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    if parsed.hostname not in WHITE_ALLOWED_PROXY_HOSTS:
        raise HTTPException(status_code=403, detail="Host not allowed")


_white_playwright_instance = None
_white_playwright_browser = None
_white_playwright_lock = asyncio.Lock()


async def _get_browser():
    global _white_playwright_instance, _white_playwright_browser
    async with _white_playwright_lock:
        if _white_playwright_browser is None or not _white_playwright_browser.is_connected():
            from playwright.async_api import async_playwright

            _white_playwright_instance = await async_playwright().start()
            _white_playwright_browser = await _white_playwright_instance.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
    return _white_playwright_browser


async def shutdown_white_browser():
    global _white_playwright_instance, _white_playwright_browser
    async with _white_playwright_lock:
        if _white_playwright_browser is not None:
            try:
                await _white_playwright_browser.close()
            except Exception:
                pass
            _white_playwright_browser = None
        if _white_playwright_instance is not None:
            try:
                await _white_playwright_instance.stop()
            except Exception:
                pass
            _white_playwright_instance = None


_white_httpx_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    global _white_httpx_client
    if _white_httpx_client is None:
        _white_httpx_client = httpx.AsyncClient(
            headers=_white_cdn_headers,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
        )
    return _white_httpx_client


async def shutdown_white_client():
    global _white_httpx_client
    if _white_httpx_client is not None:
        await _white_httpx_client.aclose()
        _white_httpx_client = None


_rate_limit_lock = asyncio.Lock()
_rate_limit_buckets: dict[str, list[float]] = {}
_RATE_LIMIT_MAX = 15
_RATE_LIMIT_WINDOW = 60.0


async def _check_rate_limit(client_id: str) -> None:
    now = time.time()
    async with _rate_limit_lock:
        timestamps = _rate_limit_buckets.get(client_id, [])
        timestamps = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
        if len(timestamps) >= _RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
                headers={"Retry-After": str(int(_RATE_LIMIT_WINDOW - (now - timestamps[0])))},
            )
        timestamps.append(now)
        _rate_limit_buckets[client_id] = timestamps


@router.get("/health")
async def white_health() -> dict:
    browser_ok = _white_playwright_browser is not None and _white_playwright_browser.is_connected()
    return {
        "status": "ok",
        "browser": "connected" if browser_ok else "disconnected",
        "cache_size": len(_white_hls_cache),
        "cache_ttl": _HLS_CACHE_TTL,
    }


@router.get("/proxy/hls")
async def white_proxy_hls(url: str = Query(...)):
    if len(url) == SHORT_TOKEN_LEN and all(c in "0123456789abcdef" for c in url):
        resolved = _resolve_url(url)
        if not resolved:
            raise HTTPException(
                status_code=410,
                detail="Token expired, refresh manifest",
                headers={"Retry-After": "0"},
            )
        url = resolved

    _validate_proxy_url(url)
    client = await _get_client()
    resp = await client.get(url)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="HLS proxy failed")

    base_url = url.rsplit("/", 1)[0] + "/"
    text = resp.text

    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            if not stripped.startswith("http"):
                stripped = base_url + stripped
            token = _store_url(stripped)
            lines.append(f"/api/white/proxy/seg/{token}")
        else:
            lines.append(line)

    rewritten = "\n".join(lines)
    return Response(
        content=rewritten,
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/proxy/seg")
async def white_proxy_seg_legacy(url: str = Query(...)):
    token = _store_url(url)
    return await white_proxy_seg(token)


@router.get("/proxy/seg/{token}")
async def white_proxy_seg(token: str):
    url = _resolve_url(token)
    if not url:
        raise HTTPException(
            status_code=410,
            detail="Segment token expired, refresh manifest",
            headers={"Retry-After": "0"},
        )
    _validate_proxy_url(url)
    client = await _get_client()

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            resp = await client.get(url)
            if resp.is_success:
                content_type = resp.headers.get("content-type", "video/MP2T")
                return Response(
                    content=resp.content,
                    media_type=content_type,
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            if resp.status_code == 410:
                raise HTTPException(
                    status_code=503,
                    detail="Segment expired, refresh manifest",
                    headers={"Retry-After": "0"},
                )
            last_error = Exception(f"HTTP {resp.status_code}")
        except HTTPException:
            raise
        except Exception as e:
            last_error = e
            logger.warning("White segment fetch attempt %d failed: %s", attempt + 1, e)
        if attempt < 2:
            await asyncio.sleep(0.5 * (attempt + 1))

    logger.error("White segment fetch failed after 3 attempts: %s", last_error)
    raise HTTPException(status_code=502, detail="Segment fetch failed")


@router.post("/health/report")
async def white_health_report(request: Request):
    data = await request.json()
    client_ip = request.client.host if request.client else "unknown"
    logger.info("White health report from %s: %s", client_ip, data)
    return {"status": "ok"}


async def _extract_hls_from_white(
    tmdbId: int,
    mediaType: str,
    season: int = 1,
    episode: int = 1,
) -> list[dict] | None:
    browser = await _get_browser()
    sources = await extract_hls_from_111movies(
        tmdb_id=tmdbId,
        media_type=mediaType,
        season=season,
        episode=episode,
        browser=browser,
        cdn_headers=_white_cdn_headers,
    )
    if not sources:
        return None

    result = []
    client = await _get_client()

    for src in sources:
        url = src["url"]
        try:
            resp = await client.get(url)
            if resp.is_success:
                manifest_text = resp.text
                base_url = url.rsplit("/", 1)[0] + "/"

                if "#EXT-X-STREAM-INF" in manifest_text:
                    variants = parse_master_manifest(manifest_text, base_url)
                    if variants:
                        for v in variants:
                            token = _store_url(v.url)
                            proxy_url = f"/api/white/proxy/hls?url={token}"
                            result.append({
                                "url": proxy_url,
                                "quality": v.quality_label,
                                "resolution": v.resolution_height,
                                "bandwidth": v.bandwidth,
                            })
                        continue

            token = _store_url(url)
            proxy_url = f"/api/white/proxy/hls?url={token}"
            result.append({
                "url": proxy_url,
                "quality": src.get("quality", "Auto"),
                "resolution": src.get("resolution", 0),
                "bandwidth": src.get("bandwidth", 0),
            })
        except Exception as e:
            logger.warning("White manifest fetch failed: %s", e)
            token = _store_url(url)
            proxy_url = f"/api/white/proxy/hls?url={token}"
            result.append({
                "url": proxy_url,
                "quality": src.get("quality", "Auto"),
                "resolution": src.get("resolution", 0),
                "bandwidth": src.get("bandwidth", 0),
            })

    return result if result else None


@router.get("/source")
async def white_source(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
    refresh: bool = Query(default=False),
) -> dict:
    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")

    client_ip = request.client.host if request.client else "unknown"
    await _check_rate_limit(client_ip)

    ck = _cache_key(tmdbId, mediaType, season, episode)

    if not refresh:
        cached = _white_hls_cache.get(ck)
        if cached:
            if _is_cache_stale(ck) and ck not in _white_hls_cache_refreshing:
                _white_hls_cache_refreshing.add(ck)
                asyncio.ensure_future(_background_refresh(ck, tmdbId, mediaType, season, episode))
            return {
                "sources": cached,
                "embedUrl": None,
                "cached": True,
                "stale": _is_cache_stale(ck),
            }
    else:
        _white_hls_cache.pop(ck, None)
        _white_hls_cache_timestamps.pop(ck, None)

    try:
        sources = await asyncio.wait_for(
            _extract_hls_from_white(tmdbId, mediaType, season, episode),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        logger.error("White source extraction timed out for %s", ck)
        stale = _white_hls_cache.get(ck)
        if stale:
            return {"sources": stale, "embedUrl": None, "cached": True, "stale": True}
        raise HTTPException(status_code=504, detail="Source extraction timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("White source extraction failed: %s", e, exc_info=True)
        stale = _white_hls_cache.get(ck)
        if stale:
            return {"sources": stale, "embedUrl": None, "cached": True, "stale": True}
        raise HTTPException(status_code=502, detail=f"Source extraction failed: {e}")

    if sources:
        _white_hls_cache[ck] = sources
        _white_hls_cache_timestamps[ck] = time.time()
        return {
            "sources": sources,
            "embedUrl": None,
            "cached": False,
            "stale": False,
        }

    return {"sources": [], "embedUrl": None, "cached": False, "stale": False}


@router.get("/refresh")
async def white_refresh(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")

    client_ip = request.client.host if request.client else "unknown"
    await _check_rate_limit(client_ip)

    ck = _cache_key(tmdbId, mediaType, season, episode)
    _white_hls_cache.pop(ck, None)

    try:
        sources = await asyncio.wait_for(
            _extract_hls_from_white(tmdbId, mediaType, season, episode),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Refresh timed out")
    except Exception as e:
        logger.error("White refresh failed: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Refresh failed: {e}")

    if sources:
        _white_hls_cache[ck] = sources
        return {"sources": sources, "refreshed": True}

    return {"sources": [], "refreshed": False}


@router.get("/prewarm")
async def white_prewarm(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    ck = _cache_key(tmdbId, mediaType, season, episode)
    if ck in _white_hls_cache:
        if _is_cache_stale(ck) and ck not in _white_hls_cache_refreshing:
            _white_hls_cache_refreshing.add(ck)
            asyncio.ensure_future(_background_refresh(ck, tmdbId, mediaType, season, episode))
            return {"status": "cached_refreshing"}
        return {"status": "cached"}

    asyncio.ensure_future(_extract_and_cache(tmdbId, mediaType, season, episode))
    return {"status": "warming"}


async def _extract_and_cache(tmdbId: int, mediaType: str, season: int, episode: int):
    try:
        ck = _cache_key(tmdbId, mediaType, season, episode)
        sources = await _extract_hls_from_white(tmdbId, mediaType, season, episode)
        if sources:
            _white_hls_cache[ck] = sources
            _white_hls_cache_timestamps[ck] = time.time()
            logger.info("White pre-warm cached %d sources for %s", len(sources), ck)
        else:
            logger.warning("White pre-warm failed for %s:%s:%s:%s", tmdbId, mediaType, season, episode)
    except Exception as e:
        logger.error("White pre-warm error: %s", e, exc_info=True)


async def _background_refresh(ck: str, tmdbId: int, mediaType: str, season: int, episode: int):
    try:
        logger.info("White background refresh for %s", ck)
        sources = await _extract_hls_from_white(tmdbId, mediaType, season, episode)
        if sources:
            _white_hls_cache[ck] = sources
            _white_hls_cache_timestamps[ck] = time.time()
            logger.info("White background refresh completed for %s (%d sources)", ck, len(sources))
        else:
            logger.warning("White background refresh returned no sources for %s", ck)
    except Exception as e:
        logger.error("White background refresh failed for %s: %s", ck, e)
    finally:
        _white_hls_cache_refreshing.discard(ck)
