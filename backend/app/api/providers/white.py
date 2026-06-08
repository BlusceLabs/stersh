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

# Background tasks set to prevent garbage collection
_background_tasks: set[asyncio.Task] = set()

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
    "cdn.111movies.net",
    "hello.mousedoor.com",
    "mousedoor.com",
} | set(h.strip() for h in os.environ.get("WHITE_EXTRA_HOSTS", "").split(",") if h.strip()))

_ONETOONE_SUFFIXES: tuple[str, ...] = (
    ".mousedoor.com",
    ".speedsterwave.app",
    ".vidking.net",
    ".cloudnestra.com",
    ".workers.dev",
)

_CDN_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "video/mp2t, application/vnd.apple.mpegurl, application/x-mpegURL, text/html, application/xhtml+xml, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://111movies.net/",
    "Origin": "https://111movies.net",
}

_cache: TTLCache[str, list[dict]] = TTLCache(maxsize=400, ttl=_ONETOONE_CACHE_TTL)
_master_urls: dict[str, str] = {}
_timestamps: dict[str, float] = {}
_refreshing: set[str] = set()
_dynamic_onetoone_hosts: set[str] = set()

_futures: dict[str, asyncio.Future] = {}
_futures_lock = asyncio.Lock()

_url_tokens: TTLCache[str, str] = TTLCache(maxsize=2000, ttl=86400)
_upstream_cache: TTLCache[str, tuple[bytes, str]] = TTLCache(maxsize=500, ttl=300)

_prewarm_semaphore = asyncio.Semaphore(2)
_upstream_semaphore = asyncio.Semaphore(1)

_client: httpx.AsyncClient | None = None
_cookies: dict[str, str] = {}


def _adapt_cookies_for_domain(cookies: dict[str, str], target_url: str) -> dict[str, str]:
    """Adapt cookies for different CDN domains."""
    adapted = {}
    for name, value in cookies.items():
        adapted[name] = value
    return adapted


async def _ensure_browser_session():
    """Return cookies from the browser session used for extraction."""
    return _cookies


async def shutdown_white_browser() -> None:
    from app.core.extractors.white import shutdown_browser
    await shutdown_browser()


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


def _register_onetoone_hosts(sources: list[dict]) -> None:
    for src in sources:
        u = src.get("url")
        if u:
            try:
                h = urlparse(u).hostname
                if h and h not in ALLOWED_ONETOONE_HOSTS:
                    _dynamic_onetoone_hosts.add(h)
                    logger.info('"white_dynamic_host":{"host":"%s"}', h)
            except Exception:
                pass


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
    hostname = parsed.hostname or ""
    if hostname in ALLOWED_ONETOONE_HOSTS or hostname in _dynamic_onetoone_hosts:
        return
    if hostname.endswith(_ONETOONE_SUFFIXES):
        return
    raise HTTPException(status_code=403, detail=f"Host not allowed: {hostname}")


async def _fetch_upstream(url: str) -> httpx.Response:
    """Fetch from upstream with retry logic for transient failures."""
    async with _upstream_semaphore:
        client = await _get_client()
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = await client.get(url, cookies=_cookies if _cookies else None)
                if resp.is_success:
                    return resp
                status = resp.status_code
                if status in (404, 410):
                    raise HTTPException(status_code=410, detail="Resource expired")
                if status < 500:
                    raise HTTPException(status_code=status, detail=f"Upstream error: {status}")
                logger.warning('"white_upstream_5xx","url":"%s","attempt":%d,"status":%d,"body":"%.200s"', url[:120], attempt + 1, status, resp.text[:200])
                last_exc = Exception(f"HTTP {status}")
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning('"white_upstream_timeout","url":"%s","attempt":%d,"err":"%s"', url[:80], attempt + 1, exc)
            except HTTPException:
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning('"white_upstream_error","url":"%s","attempt":%d,"err":"%s"', url[:80], attempt + 1, exc)
            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))
        raise HTTPException(status_code=502, detail=f"Upstream unavailable: {last_exc}")


async def _prefetch_upstream_content(url: str) -> None:
    """Pre-fetch an upstream URL and cache its response."""
    if url in _upstream_cache:
        return
    async with _upstream_semaphore:
        try:
            client = await _get_client()
            resp = await client.get(url, cookies=_cookies if _cookies else None)
            if resp.is_success:
                content_type = resp.headers.get("content-type", "video/MP2T")
                _upstream_cache[url] = (resp.content, content_type)
                logger.info('"white_prefetch_done","url":"%s"', url[:80])
        except Exception:
            pass


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
            loop = asyncio.get_running_loop()
            fut: asyncio.Future = loop.create_future()
            _futures[ck] = fut

            async def _run():
                try:
                    sources, master_url = await extract_sources_legacy(
                        tmdb_id, media_type, season, episode,
                        cdn_headers=_CDN_HEADERS,
                    )
                    if master_url:
                        _master_urls[ck] = master_url
                    fut.set_result(sources)
                except Exception as exc:
                    fut.set_exception(exc)
                finally:
                    async with _futures_lock:
                        _futures.pop(ck, None)

            task = asyncio.create_task(_run())
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)

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
                task = asyncio.create_task(
                    _bg_refresh(ck, tmdbId, mediaType, season, episode)
                )
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
            return {"sources": cached, "cached": True, "stale": stale, "server": "white", "master_url": _master_urls.get(ck, "")}

    try:
        sources = await asyncio.wait_for(
            _extract_coalesced(ck, tmdbId, mediaType, season, episode),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        stale = _cache.get(ck)
        if stale:
            return {"sources": stale, "cached": True, "stale": True, "server": "white", "master_url": _master_urls.get(ck, "")}
        raise HTTPException(status_code=504, detail="Refresh timed out")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Refresh failed: {exc}")
    if sources:
        _cache[ck] = sources
        _timestamps[ck] = time.monotonic()
        _register_onetoone_hosts(sources)
    return {"sources": sources or [], "refreshed": True, "server": "white", "master_url": _master_urls.get(ck, "")}


@router.get("/proxy/hls")
async def onetoone_proxy_hls(url: str = Query(...)) -> Response:
    if len(url) == _SHORT_TOKEN_LEN and all(c in "0123456789abcdef" for c in url):
        resolved = _resolve_token(url)
        if not resolved:
            raise HTTPException(status_code=410, detail="Token expired — refresh manifest")
        url = resolved

    _validate_host(url)

    cached = _upstream_cache.get(url)
    if cached is not None:
        body, content_type = cached
        return Response(content=body, media_type=content_type, headers={
            "Cache-Control": "public, max-age=300",
            "Access-Control-Allow-Origin": "*",
        })

    logger.info('"white_proxy_fetch","url":"%s"', url)
    resp = await _fetch_upstream(url)

    body = resp.content
    content_type = resp.headers.get("content-type", "video/MP2T")
    _upstream_cache[url] = (body, content_type)

    text = body.decode("utf-8", errors="replace")

    try:
        if text.startswith("#EXTM3U"):
            from urllib.parse import urlparse as up
            parsed = up(url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            base_dir = url.rsplit("/", 1)[0] + "/"

            def resolve(href: str) -> str:
                if href.startswith("http"):
                    return href
                if href.startswith("//"):
                    return f"{parsed.scheme}:{href}"
                if href.startswith("/"):
                    return f"{origin}{href}"
                return f"{base_dir}{href}"

            prefetch_urls: list[str] = []
            lines: list[str] = []

            for line in text.split("\n"):
                stripped = line.strip()

                if stripped.startswith("#EXT-X-PLAYLIST-TYPE:"):
                    lines.append(line)
                    continue

                if stripped.startswith("#"):
                    lines.append(line)
                    continue

                if stripped:
                    abs_url = resolve(stripped)
                    prefetch_urls.append(abs_url)
                    token = _store_token(abs_url)
                    lines.append(f"/api/white/proxy/hls?url={token}")
                else:
                    lines.append(line)

            if prefetch_urls:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*[_prefetch_upstream_content(pu) for pu in prefetch_urls]),
                        timeout=10.0,
                    )
                except asyncio.TimeoutError:
                    pass

            return Response(
                content="\n".join(lines),
                media_type="application/vnd.apple.mpegurl",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        return Response(
            content=body,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except Exception as exc:
        logger.error('"white_proxy_hls_process_error","url":"%s","err":"%s"}', url[:120], exc)
        raise HTTPException(status_code=500, detail="HLS response processing failed")


@router.get("/proxy/seg/{token}")
async def onetoone_proxy_seg(token: str) -> Response:
    url = _resolve_token(token)
    if not url:
        return Response(status_code=410, headers={"X-Segment-Expired": "true", "Retry-After": "0"})

    _validate_host(url)

    cached = _upstream_cache.get(url)
    if cached is not None:
        body, content_type = cached
        return Response(
            content=body,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
            },
        )

    try:
        resp = await _fetch_upstream(url)
    except HTTPException as exc:
        if exc.status_code == 410:
            return Response(status_code=410, headers={"X-Segment-Expired": "true"})
        raise

    content_type = resp.headers.get("content-type", "video/MP2T")
    _upstream_cache[url] = (resp.content, content_type)
    return Response(
        content=resp.content,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )


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


@router.get("/prewarm/popular")
async def white_prewarm_popular(
    limit: int = Query(default=10, ge=1, le=50),
) -> dict:
    """Prewarm extraction cache for popular movies and TV shows from TMDB."""
    api_key = os.environ.get("TMDB_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="TMDB_API_KEY not configured")

    client = await _get_client()

    async def fetch_popular(media_type: str) -> list[dict]:
        url = f"https://api.themoviedb.org/3/{media_type}/popular"
        resp = await client.get(url, params={"api_key": api_key, "language": "en-US", "page": 1})
        if resp.is_success:
            return (resp.json().get("results") or [])[:limit]
        return []

    movies, tv_shows = await asyncio.gather(
        fetch_popular("movie"),
        fetch_popular("tv"),
    )

    count = 0
    for item in movies:
        tmdb_id = item["id"]
        task = asyncio.create_task(_warm_and_cache(tmdb_id, "movie", 1, 1))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        count += 1

    for item in tv_shows:
        tmdb_id = item["id"]
        task = asyncio.create_task(_warm_and_cache(tmdb_id, "tv", 1, 1))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        count += 1

    return {
        "status": "warming",
        "server": "white",
        "movies": len(movies),
        "tv_shows": len(tv_shows),
        "total": count,
    }


@router.get("/prewarm")
async def white_prewarm(
    tmdbId: int = Query(...),
    mediaType: str = Query(...),
    season: int = Query(default=1),
    episode: int = Query(default=1),
) -> dict:
    task = asyncio.create_task(
        _warm_and_cache(tmdbId, mediaType, season, episode)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "warming", "server": "white"}


async def _warm_and_cache(tmdb_id: int, media_type: str, season: int, episode: int) -> None:
    async with _prewarm_semaphore:
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
