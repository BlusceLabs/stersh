"""FastAPI router for hoodTV backend — TMDB proxy, WASM cache, and Playwright source extraction."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import re
import time
from datetime import datetime
from urllib.parse import urlencode, urlparse

import httpx
from cachetools import TTLCache
from fastapi import FastAPI, APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from .hls_parser import parse_master_manifest, HLSVariant
from .white_routes import router as white_router
from .white_routes import shutdown_white_browser, shutdown_white_client

logger = logging.getLogger(__name__)

SHORT_TOKEN_LEN = 16
_url_token_cache: TTLCache = TTLCache(maxsize=2000, ttl=600)


def _store_url(url: str) -> str:
    token = hashlib.sha256(url.encode()).hexdigest()[:SHORT_TOKEN_LEN]
    _url_token_cache[token] = url
    return token


def _resolve_url(token: str) -> str | None:
    return _url_token_cache.get(token)

router = APIRouter(prefix="/api")

TMDB_PROXY_BASE = "https://db.videasy.net/3"
VIDKING_BASE = "https://www.vidking.net"
HTTP_TIMEOUT = 30.0

# Allowed CDN domains for proxy endpoints
ALLOWED_PROXY_HOSTS = {
    "easy.speedsterwave.app",
    "cdn.vidking.net",
    "vidking.net",
    "cloudnestra.com",
    "whisperingauroras.com",
    "111movies.net",
    "www.111movies.net",
}

wasm_cache: bytes | None = None

# Shared httpx client with CDN-friendly headers
_cdn_headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.vidking.net/",
    "Origin": "https://www.vidking.net",
}

# ── HLS URL cache (bounded TTL) ──────────────────────────────

_HLS_CACHE_TTL = int(os.environ.get("HLS_CACHE_TTL", 5 * 60))  # default 5 min
_HLS_STALE_TTL = int(os.environ.get("HLS_STALE_TTL", 10 * 60))  # serve stale for 10 min
_hls_cache: TTLCache[str, list[dict]] = TTLCache(maxsize=500, ttl=_HLS_CACHE_TTL)
_hls_cache_timestamps: dict[str, float] = {}  # track when each entry was cached
_hls_cache_refreshing: set[str] = set()  # keys currently being refreshed in background


def _cache_key(tmdbId: int, mediaType: str, season: int = 1, episode: int = 1) -> str:
    return f"{tmdbId}:{mediaType}:{season}:{episode}"


def _is_cache_stale(ck: str) -> bool:
    """Check if a cache entry is stale (past TTL but within stale window)."""
    ts = _hls_cache_timestamps.get(ck)
    if ts is None:
        return True
    age = time.time() - ts
    return age > _HLS_CACHE_TTL


def _is_cache_expired(ck: str) -> bool:
    """Check if a cache entry is fully expired (past stale window)."""
    ts = _hls_cache_timestamps.get(ck)
    if ts is None:
        return True
    age = time.time() - ts
    return age > _HLS_STALE_TTL


# ── Lazy playwright import ──────────────────────────────────

_playwright_instance = None
_playwright_browser = None
_playwright_lock = asyncio.Lock()


async def _get_browser():
    """Get or create a shared Playwright browser instance."""
    global _playwright_instance, _playwright_browser
    async with _playwright_lock:
        if _playwright_browser is None or not _playwright_browser.is_connected():
            from playwright.async_api import async_playwright

            _playwright_instance = await async_playwright().start()
            _playwright_browser = await _playwright_instance.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
    return _playwright_browser


async def shutdown_browser():
    """Clean up Playwright resources on application shutdown."""
    global _playwright_instance, _playwright_browser
    async with _playwright_lock:
        if _playwright_browser is not None:
            try:
                await _playwright_browser.close()
            except Exception:
                pass
            _playwright_browser = None
        if _playwright_instance is not None:
            try:
                await _playwright_instance.stop()
            except Exception:
                pass
            _playwright_instance = None
        logger.info("Playwright browser shut down cleanly")


# ── Shared httpx client ─────────────────────────────────────

_httpx_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    """Get a shared httpx client with CDN-friendly headers."""
    global _httpx_client
    if _httpx_client is None:
        _httpx_client = httpx.AsyncClient(
            headers=_cdn_headers,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
        )
    return _httpx_client


async def shutdown_client():
    """Close the shared httpx client on application shutdown."""
    global _httpx_client
    if _httpx_client is not None:
        await _httpx_client.aclose()
        _httpx_client = None
        logger.info("httpx client closed cleanly")


# ── URL validation ──────────────────────────────────────────

def _validate_proxy_url(url: str) -> None:
    """Validate that a proxy URL points to an allowed CDN host."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")
    if parsed.hostname not in ALLOWED_PROXY_HOSTS:
        raise HTTPException(status_code=403, detail="Host not allowed")


# ── Rate limiting (simple in-memory sliding window) ─────────────────

_rate_limit_lock = asyncio.Lock()
_rate_limit_buckets: dict[str, list[float]] = {}
_RATE_LIMIT_MAX = 15  # max requests
_RATE_LIMIT_WINDOW = 60.0  # per 60 seconds


async def _check_rate_limit(client_id: str) -> None:
    """Raise 429 if client has exceeded rate limit."""
    now = time.time()
    async with _rate_limit_lock:
        timestamps = _rate_limit_buckets.get(client_id, [])
        # Prune old entries
        timestamps = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
        if len(timestamps) >= _RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
                headers={"Retry-After": str(int(_RATE_LIMIT_WINDOW - (now - timestamps[0])))},
            )
        timestamps.append(now)
        _rate_limit_buckets[client_id] = timestamps


# ── Health check ────────────────────────────────────────────

@router.get("/health")
async def health() -> dict:
    """Health check with dependency status."""
    browser_ok = _playwright_browser is not None and _playwright_browser.is_connected()
    from .ffmpeg_utils import get_ffmpeg_version

    ffmpeg_ver = get_ffmpeg_version()
    return {
        "status": "ok",
        "browser": "connected" if browser_ok else "disconnected",
        "cache_size": len(_hls_cache),
        "cache_ttl": _HLS_CACHE_TTL,
        "ffmpeg": ffmpeg_ver or "unavailable",
    }


# ── vidking TMDB metadata proxy ──────────────────────────────

@router.get("/vidking/tmdb/{media_type}/{tmdb_id}")
async def vidking_tmdb(media_type: str, tmdb_id: int) -> dict:
    """Proxy TMDB metadata from db.videasy.net (title, year, imdbId)."""
    url = f"{TMDB_PROXY_BASE}/{media_type}/{tmdb_id}?append_to_response=external_ids"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(url)
    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="TMDB proxy failed")
    data = resp.json()
    if media_type == "movie":
        title = data.get("title", "")
        year = _parse_year(data.get("release_date"))
    else:
        title = data.get("name", "")
        year = _parse_year(data.get("first_air_date"))
    imdb_id = (data.get("external_ids") or {}).get("imdb_id") or ""
    return {"title": title, "year": year, "imdbId": imdb_id}


# ── vidking WASM module cache ───────────────────────────────

@router.get("/vidking/wasm")
async def vidking_wasm() -> Response:
    """Serve vidking's WASM decrypt module, fetched and cached on first request."""
    global wasm_cache
    if wasm_cache is None:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(f"{VIDKING_BASE}/assets/wasm/module1.wasm")
        if not resp.is_success:
            raise HTTPException(status_code=502, detail="Failed to fetch WASM module")
        wasm_cache = resp.content
    return Response(content=wasm_cache, media_type="application/wasm")


# ── HLS stream proxy ────────────────────────────────────────

@router.get("/vidking/proxy/hls")
async def proxy_hls(url: str = Query(...), remux: bool = Query(default=False)):
    """Fetch an HLS manifest and rewrite segment URLs through our proxy.

    If remux=1, delegates to FFmpeg remux for browser-compatible repackaging.

    The `url` param may be a short token (16-char hex) for URLs stored
    in the token cache, or a full URL for direct use.
    """
    if len(url) == SHORT_TOKEN_LEN and all(c in "0123456789abcdef" for c in url):
        resolved = _resolve_url(url)
        if not resolved:
            raise HTTPException(
                status_code=410,
                detail="Token expired, refresh manifest",
                headers={"Retry-After": "0"},
            )
        url = resolved

    if remux:
        from .ffmpeg_routes import remux_proxy
        return await remux_proxy(url=url, format="hls")

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
            lines.append(f"/api/vidking/proxy/seg/{token}")
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


@router.get("/vidking/proxy/seg")
async def proxy_seg_legacy(url: str = Query(...)):
    """Legacy handler for old-style segment URLs (?url=...).

    Forwards to the token-based handler. This ensures cached manifests
    with old-style URLs don't break after the token migration.
    """
    token = _store_url(url)
    return await proxy_seg(token)


@router.get("/vidking/proxy/seg/{token}")
async def proxy_seg(token: str):
    """Proxy a single HLS segment from the CDN with retry logic.

    Uses a short token that maps to the real URL to avoid excessively
    long query strings that trigger 431 Request Header Fields Too Large.
    """
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
            logger.warning("Segment fetch attempt %d failed: %s", attempt + 1, e)
        if attempt < 2:
            await asyncio.sleep(0.5 * (attempt + 1))

    logger.error("Segment fetch failed after 3 attempts: %s", last_error)
    raise HTTPException(status_code=502, detail="Segment fetch failed")


# ── Stream health: client-reported metrics ──────────────────────────

_playback_health_log: dict[str, list[dict]] = {}


@router.post("/vidking/health/report")
async def health_report(request: Request):
    """Accept playback health reports from the client.

    Clients send periodic reports with buffer state, stall counts,
    and quality changes. Used for monitoring and debugging.
    """
    data = await request.json()
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{data.get('tmdbId', 'unknown')}"
    entry = {
        "timestamp": time.time(),
        "currentTime": data.get("currentTime"),
        "buffered": data.get("buffered"),
        "stallCount": data.get("stallCount", 0),
        "quality": data.get("quality"),
        "resolution": data.get("resolution"),
        "errorCount": data.get("errorCount", 0),
    }
    if key not in _playback_health_log:
        _playback_health_log[key] = []
    _playback_health_log[key].append(entry)
    # Keep only last 100 entries per client/content
    if len(_playback_health_log[key]) > 100:
        _playback_health_log[key] = _playback_health_log[key][-100:]
    return {"status": "ok"}


@router.get("/vidking/refresh")
async def refresh_source(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Force-refresh the cached HLS source for a movie/episode.

    Called by the client when playback stalls or segments expire.
    Bypasses cache and re-runs Playwright extraction.
    """
    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")

    client_ip = request.client.host if request.client else "unknown"
    await _check_rate_limit(client_ip)

    ck = _cache_key(tmdbId, mediaType, season, episode)
    _hls_cache.pop(ck, None)

    try:
        sources = await asyncio.wait_for(
            _extract_hls_from_vidking(tmdbId, mediaType, season, episode),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Refresh timed out")
    except Exception as e:
        logger.error("Refresh failed: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Refresh failed: {e}")

    if sources:
        _hls_cache[ck] = sources
        return {"sources": sources, "refreshed": True}

    return {"sources": [], "refreshed": False}


# ── Subtitle endpoints ─────────────────────────────────────────────

@router.get("/subtitles")
async def get_subtitles(
    imdbId: str = Query(...),
    language: str = Query(default="en"),
):
    """Fetch available subtitles for a movie/episode.

    Returns a list of subtitle tracks with URLs.
    """
    from .subtitles import fetch_subtitles

    tracks = await fetch_subtitles(imdbId, language)
    return {
        "subtitles": [
            {
                "label": t.label,
                "language": t.language,
                "url": t.url,
                "format": t.format,
            }
            for t in tracks
        ]
    }


@router.get("/subtitles/proxy")
async def proxy_subtitle(url: str = Query(...)):
    """Proxy a subtitle file, converting SRT to WebVTT if needed.

    This avoids CORS issues when loading subtitles directly from
    external providers.
    """
    from .subtitles import convert_srt_to_vtt

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url)
    except Exception as e:
        logger.warning("Subtitle fetch failed: %s", e)
        raise HTTPException(status_code=502, detail="Subtitle fetch failed")

    if not resp.is_success:
        raise HTTPException(status_code=resp.status_code, detail="Subtitle fetch failed")

    content = resp.text
    content_type = "text/vtt"

    # Auto-convert SRT to VTT
    if url.endswith(".srt") or not url.endswith(".vtt"):
        content = convert_srt_to_vtt(content)

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=86400",
        },
    )


# ── Shared Playwright extraction logic ─────────────────────────────

async def _extract_hls_from_vidking(
    tmdbId: int,
    mediaType: str,
    season: int = 1,
    episode: int = 1,
) -> list[dict] | None:
    """Extract HLS URLs from vidking.net using Playwright.

    Returns a list of source dicts with url, quality, resolution, bandwidth,
    or None if extraction fails.
    """
    if mediaType == "movie":
        embed_url = f"{VIDKING_BASE}/embed/movie/{tmdbId}?autoPlay=true&color=c8956c"
    else:
        embed_url = (
            f"{VIDKING_BASE}/embed/tv/{tmdbId}/{season}/{episode}"
            f"?autoPlay=true&color=c8956c&episodeSelector=true&nextEpisode=true"
        )

    browser = await _get_browser()
    context = await browser.new_context(
        user_agent=_cdn_headers["User-Agent"],
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
    )

    # Mask webdriver to reduce bot detection
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    page = await context.new_page()

    hls_url: str | None = None

    async def on_response(response):
        nonlocal hls_url
        if hls_url is not None:
            return
        url = response.url
        if ".m3u8" in url.lower():
            hls_url = url

    page.on("response", on_response)

    logger.info("Loading vidking embed: %s", embed_url)
    try:
        await page.goto(embed_url, wait_until="networkidle", timeout=60000)
    except Exception as e:
        logger.warning("vidking navigation error (networkidle): %s", e)
        await page.goto(embed_url, wait_until="domcontentloaded", timeout=60000)

    # Give the lazy player time to initialise
    await asyncio.sleep(3)

    if not hls_url:
        logger.warning("No HLS source captured within timeout, trying click-to-play")

        play_selectors = [
            "video",
            "[class*='play']",
            "[id*='play']",
            "button[aria-label*='play' i]",
            ".vjs-big-play-button",
            ".plyr__control",
            "[data-testid='play-button']",
        ]
        for sel in play_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click(force=True, timeout=2000)
                    logger.info("Clicked play selector: %s", sel)
                    break
            except Exception:
                pass

        await asyncio.sleep(8)
        if hls_url:
            logger.info("Captured HLS source after click: %s", hls_url)
        else:
            logger.warning("Still no HLS source after click-to-play")

    # Fallback: inspect video elements / JS players directly
    if not hls_url:
        try:
            video_src = await page.evaluate("""
                (() => {
                    const v = document.querySelector('video');
                    if (!v) return null;
                    return v.src || v.currentSrc || null;
                })()
            """)
            if video_src and video_src.startswith("http"):
                logger.info("Found video src from DOM: %s", video_src)
                hls_url = video_src

            js_src = await page.evaluate("""
                (() => {
                    if (window.hls && window.hls.url) return window.hls.url;
                    if (window.player && window.player.config && window.player.config.src)
                        return window.player.config.src;
                    if (window.videojs && window.videojs.getPlayers) {
                        const players = window.videojs.getPlayers();
                        for (const k in players) {
                            const src = players[k].src || players[k].currentSrc();
                            if (src) return src;
                        }
                    }
                    return null;
                })()
            """)
            if js_src and js_src.startswith("http"):
                logger.info("Found HLS URL from JS player: %s", js_src)
                hls_url = js_src
        except Exception as e:
            logger.warning("DOM fallback extraction failed: %s", e)

    await asyncio.sleep(1)
    await context.close()

    if not hls_url:
        return None

    # Fetch the master manifest and parse variants
    client = await _get_client()
    try:
        resp = await client.get(hls_url)
        if not resp.is_success:
            logger.warning("Failed to fetch master manifest: %s", hls_url)
            # Fallback: return the single URL as "Auto"
            token = _store_url(hls_url)
            proxy_url = f"/api/vidking/proxy/hls?url={token}"
            return [{"url": proxy_url, "quality": "Auto", "resolution": 0, "bandwidth": 0}]

        manifest_text = resp.text
        base_url = hls_url.rsplit("/", 1)[0] + "/"
        variants = parse_master_manifest(manifest_text, base_url)

        if not variants:
            # Not a master manifest — treat as single stream
            token = _store_url(hls_url)
            proxy_url = f"/api/vidking/proxy/hls?url={token}"
            return [{"url": proxy_url, "quality": "Auto", "resolution": 0, "bandwidth": 0}]

        # Convert variants to source dicts with proxy URLs
        sources = []
        for v in variants:
            token = _store_url(v.url)
            proxy_url = f"/api/vidking/proxy/hls?url={token}"
            sources.append({
                "url": proxy_url,
                "quality": v.quality_label,
                "resolution": v.resolution_height,
                "bandwidth": v.bandwidth,
            })

        logger.info("Parsed %d quality variants: %s", len(sources), [s["quality"] for s in sources])
        return sources

    except Exception as e:
        logger.warning("Failed to parse master manifest: %s", e)
        token = _store_url(hls_url)
        proxy_url = f"/api/vidking/proxy/hls?url={token}"
        return [{"url": proxy_url, "quality": "Auto", "resolution": 0, "bandwidth": 0}]


# ── Playwright-based vidking source extraction ──────────────────────

@router.get("/vidking/source")
async def vidking_source(
    request: Request,
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
    refresh: bool = Query(default=False),
) -> dict:
    """Extract video source URLs from vidking.net using Playwright.

    Checks cache first — if a URL was already extracted for this
    movie/episode, returns instantly. Use ?refresh=1 to bypass cache
    (e.g. when segments have expired mid-playback).
    """
    if mediaType not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="mediaType must be 'movie' or 'tv'")

    # Rate limit by client IP
    client_ip = request.client.host if request.client else "unknown"
    await _check_rate_limit(client_ip)

    ck = _cache_key(tmdbId, mediaType, season, episode)

    # Check cache first (skip if refresh requested)
    if not refresh:
        cached = _hls_cache.get(ck)
        if cached:
            # Stale-while-revalidate: if stale, serve cached but refresh in background
            if _is_cache_stale(ck) and ck not in _hls_cache_refreshing:
                _hls_cache_refreshing.add(ck)
                asyncio.ensure_future(_background_refresh(ck, tmdbId, mediaType, season, episode))
            return {
                "sources": cached,
                "embedUrl": None,
                "cached": True,
                "stale": _is_cache_stale(ck),
            }
    else:
        _hls_cache.pop(ck, None)
        _hls_cache_timestamps.pop(ck, None)

    # Cache miss or force refresh — extract fresh sources
    try:
        sources = await asyncio.wait_for(
            _extract_hls_from_vidking(tmdbId, mediaType, season, episode),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        logger.error("Playwright source extraction timed out for %s", ck)
        # If we have a stale cache, serve it rather than erroring
        stale = _hls_cache.get(ck)
        if stale:
            return {"sources": stale, "embedUrl": None, "cached": True, "stale": True}
        raise HTTPException(status_code=504, detail="Source extraction timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Playwright source extraction failed: %s", e, exc_info=True)
        stale = _hls_cache.get(ck)
        if stale:
            return {"sources": stale, "embedUrl": None, "cached": True, "stale": True}
        raise HTTPException(status_code=502, detail=f"Source extraction failed: {e}")

    if sources:
        _hls_cache[ck] = sources
        _hls_cache_timestamps[ck] = time.time()
        return {
            "sources": sources,
            "embedUrl": None,
            "cached": False,
            "stale": False,
        }

    return {"sources": [], "embedUrl": None, "cached": False, "stale": False}


@router.get("/vidking/prewarm")
async def vidking_prewarm(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    """Pre-warm the HLS cache for a movie/episode.

    Called from detail pages in the background — starts extraction
    early so the watch page loads instantly.
    """
    ck = _cache_key(tmdbId, mediaType, season, episode)
    if ck in _hls_cache:
        # If stale, trigger background refresh even if already cached
        if _is_cache_stale(ck) and ck not in _hls_cache_refreshing:
            _hls_cache_refreshing.add(ck)
            asyncio.ensure_future(_background_refresh(ck, tmdbId, mediaType, season, episode))
            return {"status": "cached_refreshing"}
        return {"status": "cached"}

    # Fire and forget — don't wait for the result
    asyncio.ensure_future(_extract_and_cache(tmdbId, mediaType, season, episode))
    return {"status": "warming"}


async def _extract_and_cache(tmdbId: int, mediaType: str, season: int, episode: int):
    """Run extraction in background and cache the result."""
    try:
        ck = _cache_key(tmdbId, mediaType, season, episode)
        sources = await _extract_hls_from_vidking(tmdbId, mediaType, season, episode)
        if sources:
            _hls_cache[ck] = sources
            _hls_cache_timestamps[ck] = time.time()
            logger.info("Pre-warm cached %d sources for %s", len(sources), ck)
        else:
            logger.warning("Pre-warm failed for %s:%s:%s:%s", tmdbId, mediaType, season, episode)
    except Exception as e:
        logger.error("Pre-warm error: %s", e, exc_info=True)


async def _background_refresh(ck: str, tmdbId: int, mediaType: str, season: int, episode: int):
    """Refresh a stale cache entry in the background.

    Serves stale content to clients while fetching fresh sources.
    """
    try:
        logger.info("Background refresh for %s", ck)
        sources = await _extract_hls_from_vidking(tmdbId, mediaType, season, episode)
        if sources:
            _hls_cache[ck] = sources
            _hls_cache_timestamps[ck] = time.time()
            logger.info("Background refresh completed for %s (%d sources)", ck, len(sources))
        else:
            logger.warning("Background refresh returned no sources for %s", ck)
    except Exception as e:
        logger.error("Background refresh failed for %s: %s", ck, e)
    finally:
        _hls_cache_refreshing.discard(ck)


# ── helpers ─────────────────────────────────────────────────

def _parse_year(date_str: str | None) -> str:
    if not date_str:
        return ""
    try:
        return str(datetime.strptime(date_str[:10], "%Y-%m-%d").year)
    except ValueError:
        return ""

# ── FastAPI app ────────────────────────────────────────────────

app = FastAPI(title="Watch!fy Streaming Service")
app.include_router(router)
app.include_router(white_router)


@app.on_event("shutdown")
async def shutdown():
    await shutdown_browser()
    await shutdown_client()
    await shutdown_white_browser()
    await shutdown_white_client()
