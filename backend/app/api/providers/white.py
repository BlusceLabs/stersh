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
from fastapi.responses import StreamingResponse

from app.core.extractors.white import extract_sources_legacy

logger = logging.getLogger(__name__)

_ONETOONE_CACHE_TTL = int(os.environ.get("ONETOONE_CACHE_TTL", 15 * 60))
_ONETOONE_STALE_TTL = int(os.environ.get("ONETOONE_STALE_TTL", 30 * 60))
_SHORT_TOKEN_LEN = 16

ALLOWED_ONETOONE_HOSTS = frozenset({
    "easy.speedsterwave.app",
    "cdn.vidking.net",
    "vidking.net",
    "www.vidking.net",
    "cloudnestra.com",
    "whisperingauroras.com",
    "111movies.net",
    "www.111movies.net",
})

_CDN_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://111movies.net/",
    "Origin": "https://111movies.net",
}

_cache: TTLCache[str, list[dict]] = TTLCache(maxsize=400, ttl=_ONETOONE_CACHE_TTL)
_timestamps: dict[str, float] = {}
_refreshing: set[str] = set()

_futures: dict[str, asyncio.Future] = {}
_futures_lock = asyncio.Lock()

_url_tokens: TTLCache[str, str] = TTLCache(maxsize=2000, ttl=1800)

_client: httpx.AsyncClient | None = None

_browser = None
_playwright = None
_browser_lock = asyncio.Lock()


async def _get_browser():
    global _browser, _playwright
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            from playwright.async_api import async_playwright
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(
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
    return _browser


async def shutdown_white_browser() -> None:
    global _browser, _playwright
    async with _browser_lock:
        for obj, method in [(_browser, "close"), (_playwright, "stop")]:
            if obj is not None:
                try:
                    await getattr(obj, method)()
                except Exception:
                    pass
        _browser = None
        _playwright = None
    logger.info('"white_browser_shutdown"')


async def shutdown_white_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None
    logger.info('"white_client_shutdown"')


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            headers=_CDN_HEADERS,
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=40, max_keepalive_connections=15),
        )
    return _client


def _cache_key(tmdb_id: int, media_type: str, season: int, episode: int) -> str:
    return f"white:{tmdb_id}:{media_type}:{season}:{episode}"


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
    if parsed.hostname not in ALLOWED_ONETOONE_HOSTS:
        raise HTTPException(status_code=403, detail=f"Host not allowed: {parsed.hostname}")


def _is_stale(ck: str) -> bool:
    ts = _timestamps.get(ck)
    return ts is None or (time.monotonic() - ts) > _ONETOONE_CACHE_TTL


async def _extract_coalesced(
    ck: str,
    tmdb_id: int,
    media_type: str,
    season: int,
    episode: int,
) -> list[dict] | None:
    async with _futures_lock:
        if ck in _futures:
            fut = _futures[ck]
        else:
            loop = asyncio.get_event_loop()
            fut: asyncio.Future = loop.create_future()
            _futures[ck] = fut

            async def _run():
                try:
                    browser = await _get_browser()
                    result = await extract_sources_legacy(
                        tmdb_id, media_type, season, episode,
                        browser=browser,
                        cdn_headers=_CDN_HEADERS,
                    )
                    fut.set_result(result)
                except Exception as exc:
                    fut.set_exception(exc)
                finally:
                    async with _futures_lock:
                        _futures.pop(ck, None)

            asyncio.get_event_loop().create_task(_run())

    return await asyncio.shield(fut)


router = APIRouter(prefix="/api/white", tags=["white"])


@router.get("/source")
async def onetoone_source(
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
        _cache.pop(ck, None)
        _timestamps.pop(ck, None)
    else:
        cached = _cache.get(ck)
        if cached is not None:
            stale = _is_stale(ck)
            if stale and ck not in _refreshing:
                _refreshing.add(ck)
                asyncio.get_event_loop().create_task(
                    _bg_refresh(ck, tmdbId, mediaType, season, episode)
                )
            return {"sources": cached, "cached": True, "stale": stale, "server": "white"}

    try:
        sources = await asyncio.wait_for(
            _extract_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        stale = _cache.get(ck)
        if stale:
            return {"sources": stale, "cached": True, "stale": True, "server": "white"}
        raise HTTPException(status_code=504, detail="Refresh timed out")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Refresh failed: {exc}")
    if sources:
        _cache[ck] = sources
        _timestamps[ck] = time.monotonic()
    return {"sources": sources or [], "refreshed": True, "server": "white"}


@router.get("/proxy/hls")
async def onetoone_proxy_hls(url: str = Query(...)) -> Response:
    if len(url) == _SHORT_TOKEN_LEN and all(c in "0123456789abcdef" for c in url):
        resolved = _resolve_token(url)
        if not resolved:
            raise HTTPException(status_code=410, detail="Token expired — refresh manifest")
        url = resolved

    _validate_host(url)
    client = await _get_client()
    resp = await client.get(url)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="HLS upstream error")

    base_url = url.rsplit("/", 1)[0] + "/"
    lines: list[str] = []
    next_is_variant = False

    for line in resp.text.split("\n"):
        stripped = line.strip()

        if stripped == "#EXT-X-ENDLIST":
            continue

        if stripped.startswith("#EXT-X-PLAYLIST-TYPE:VOD"):
            lines.append("#EXT-X-PLAYLIST-TYPE:EVENT")
            continue

        if stripped.startswith("#EXT-X-STREAM-INF:"):
            next_is_variant = True
            lines.append(line)
            continue

        if stripped and not stripped.startswith("#"):
            if not stripped.startswith("http"):
                stripped = base_url + stripped
            token = _store_token(stripped)
            if next_is_variant:
                lines.append(f"/api/white/proxy/hls?url={token}")
            else:
                lines.append(f"/api/white/proxy/seg/{token}")
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


@router.get("/proxy/seg/{token}")
async def onetoone_proxy_seg(token: str) -> Response:
    url = _resolve_token(token)
    if not url:
        return Response(status_code=410, headers={"X-Segment-Expired": "true", "Retry-After": "0"})

    _validate_host(url)
    client = await _get_client()
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
            logger.warning('"white_seg_timeout":{"attempt":%d}', attempt + 1)
        except Exception as exc:
            last_exc = exc
            logger.warning('"white_seg_error":{"attempt":%d,"err":"%s"}', attempt + 1, exc)
        if attempt < 2:
            await asyncio.sleep(0.5 * (attempt + 1))

    raise HTTPException(status_code=502, detail=f"Segment unavailable: {last_exc}")


@router.get("/download")
async def onetoone_download(
    url: str = Query(...),
    filename: str = Query(default="watchfy-white.mp4"),
) -> StreamingResponse:
    _validate_host(url)
    client = await _get_client()

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


async def _warm_and_cache(tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    ck = _cache_key(tmdb_id, media_type, season, episode)
    try:
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _cache[ck] = sources
            _timestamps[ck] = time.monotonic()
            logger.info('"white_prewarm_done":{"key":"%s","count":%d}', ck, len(sources))
    except Exception as exc:
        logger.error('"white_prewarm_error":{"key":"%s","err":"%s"}', ck, exc)


async def _bg_refresh(ck: str, tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    try:
        logger.info('"white_bg_refresh_start":{"key":"%s"}', ck)
        sources = await _extract_coalesced(ck, tmdb_id, media_type, season, episode)
        if sources:
            _cache[ck] = sources
            _timestamps[ck] = time.monotonic()
            logger.info('"white_bg_refresh_done":{"key":"%s","count":%d}', ck, len(sources))
    except Exception as exc:
        logger.error('"white_bg_refresh_error":{"key":"%s","err":"%s"}', ck, exc)
    finally:
        _refreshing.discard(ck)
