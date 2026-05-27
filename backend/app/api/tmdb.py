"""TMDB API proxy and metadata service for watchfy frontend."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from redis_utils import tmdb_cache_get, tmdb_cache_set

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

_TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
_TMDB_BASE    = "https://api.themoviedb.org/3"

# Default TTLs (seconds) by path prefix — callers can override
_CACHE_TTL_DEFAULT      = 3_600        # 1 h  — general metadata
_CACHE_TTL_SEARCH       = 300          # 5 min — search results change fast
_CACHE_TTL_CONFIG       = 86_400       # 24 h  — TMDB config rarely changes

# ── HTTP client ────────────────────────────────────────────────────────────────

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Return a lazily-created, reusable async HTTP client."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=_TMDB_BASE,
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
            follow_redirects=True,
            headers={"Accept": "application/json"},
        )
    return _client


async def close_client() -> None:
    """Gracefully close the shared HTTP client (call from app lifespan)."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None

# ── Cache helpers ──────────────────────────────────────────────────────────────

def _cache_key(path: str, params: dict[str, Any]) -> str:
    """Stable, URL-safe cache key derived from path + sorted params."""
    parts = [path] + [f"{k}={params[k]}" for k in sorted(params) if k != "api_key"]
    return hashlib.sha256(":".join(parts).encode()).hexdigest()


def _ttl_for(path: str) -> int:
    if path.startswith("search/"):
        return _CACHE_TTL_SEARCH
    if path == "configuration":
        return _CACHE_TTL_CONFIG
    return _CACHE_TTL_DEFAULT

# ── Core fetch primitive ────────────────────────────────────────────────────────

async def _tmdb_get(path: str, extra: dict[str, Any] | None = None) -> Any:
    """
    Low-level GET against TMDB with transparent Redis caching.

    Always injects ``api_key`` and ``language`` defaults; callers may override
    via *extra*.  Raises ``HTTPException`` on upstream errors so FastAPI
    handles the response correctly.
    """
    params: dict[str, Any] = {
        "api_key":  _TMDB_API_KEY,
        "language": "en-US",
        **(extra or {}),
    }

    clean = path.strip("/")
    key   = _cache_key(clean, params)

    cached = tmdb_cache_get(key)
    if cached is not None:
        return cached

    try:
        resp = await _get_client().get(clean, params=params)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        try:
            detail = exc.response.json().get("status_message", "TMDB error")
        except Exception:
            detail = "TMDB error"
        logger.warning('"tmdb_upstream_error","path":"%s","status":%d', clean, status)
        raise HTTPException(status_code=status, detail=detail) from exc
    except httpx.RequestError as exc:
        logger.error('"tmdb_request_error","path":"%s","error":"%s"', clean, exc)
        raise HTTPException(status_code=502, detail="TMDB service unreachable") from exc

    payload = resp.json()
    tmdb_cache_set(key, payload, ttl=_ttl_for(clean))
    return payload

# ── Router ─────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/tmdb", tags=["tmdb"])

# ── Specific endpoints (must be declared before the catch-all) ─────────────────

@router.get("/movie/{tmdb_id:int}")
async def get_movie(
    tmdb_id: int,
    language: str = Query("en-US"),
) -> Any:
    """Movie details by TMDB ID."""
    return await _tmdb_get(f"movie/{tmdb_id}", {"language": language})


@router.get("/tv/{tmdb_id:int}")
async def get_tv_show(
    tmdb_id: int,
    language: str = Query("en-US"),
) -> Any:
    """TV show details by TMDB ID."""
    return await _tmdb_get(f"tv/{tmdb_id}", {"language": language})


@router.get("/{media_type}/{tmdb_id:int}/recommendations")
async def get_recommendations(
    media_type: str,
    tmdb_id: int,
    page: int = Query(1, ge=1, le=500),
    language: str = Query("en-US"),
) -> Any:
    """Recommended content for a movie or TV show."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    return await _tmdb_get(f"{media_type}/{tmdb_id}/recommendations", {
        "language": language, "page": page
    })


@router.get("/{media_type}/{tmdb_id:int}/similar")
async def get_similar(
    media_type: str,
    tmdb_id: int,
    page: int = Query(1, ge=1, le=500),
    language: str = Query("en-US"),
) -> Any:
    """Similar content for a movie or TV show."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    return await _tmdb_get(f"{media_type}/{tmdb_id}/similar", {
        "language": language, "page": page
    })


@router.get("/{media_type}/popular")
async def get_popular(
    media_type: str,
    page: int = Query(1, ge=1, le=500),
    language: str = Query("en-US"),
    region: str | None = Query(None),
) -> Any:
    """Popular movies or TV shows with optional genre filter via catch-all."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    params: dict[str, Any] = {"language": language, "page": page}
    if region:
        params["region"] = region
    return await _tmdb_get(f"{media_type}/popular", params)


@router.get("/{media_type}/top_rated")
async def get_top_rated(
    media_type: str,
    page: int = Query(1, ge=1, le=500),
    language: str = Query("en-US"),
) -> Any:
    """Top rated movies or TV shows."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    return await _tmdb_get(f"{media_type}/top_rated", {"language": language, "page": page})


@router.get("/{media_type}/trending/{time_window}")
async def get_trending(
    media_type: str,
    time_window: str = "day",
    language: str = Query("en-US"),
) -> Any:
    """Trending movies or TV shows."""
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    if time_window not in ("day", "week"):
        raise HTTPException(status_code=400, detail="time_window must be 'day' or 'week'")
    return await _tmdb_get(f"trending/{media_type}/{time_window}", {"language": language})


@router.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    media_type: str = Query("multi", pattern="^(movie|tv|person|multi)$"),
    page: int = Query(1, ge=1, le=500),
    year: int | None = Query(None),
    language: str = Query("en-US"),
) -> Any:
    """Search for movies, TV shows, or people."""
    params: dict[str, Any] = {
        "query":         q,
        "page":          page,
        "language":      language,
        "include_adult": False,
    }
    if year:
        params["year"] = year
    # TMDB endpoint mirrors media_type: search/movie, search/tv, search/multi …
    return await _tmdb_get(f"search/{media_type}", params)


@router.get("/media/{media_type}/{tmdb_id:int}")
async def get_media_metadata(
    media_type: str,
    tmdb_id: int,
    season: int | None = Query(None),
    episode: int | None = Query(None),
    language: str = Query("en-US"),
) -> Any:
    """
    Aggregate metadata for a movie or TV show in one round-trip.

    Uses TMDB's ``append_to_response`` so a single upstream call fetches
    details + credits + videos.  For TV, an optional season/episode pair
    fetches episode details concurrently.
    """
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")

    base_params: dict[str, Any] = {
        "language":           language,
        "append_to_response": "credits,videos",
    }

    # Fire main + optional episode fetch concurrently
    episode_coro = (
        _tmdb_get(f"tv/{tmdb_id}/season/{season}/episode/{episode}", {"language": language})
        if media_type == "tv" and season is not None and episode is not None
        else asyncio.sleep(0)          # no-op placeholder
    )

    base_data, episode_data = await asyncio.gather(
        _tmdb_get(f"{media_type}/{tmdb_id}", base_params),
        episode_coro,
        return_exceptions=True,
    )

    if isinstance(base_data, Exception):
        raise base_data

    if isinstance(episode_data, dict):
        base_data["episode_details"] = episode_data
    elif isinstance(episode_data, Exception):
        logger.warning('"episode_fetch_failed","tmdb_id":%d,"error":"%s"', tmdb_id, episode_data)
        base_data["episode_details"] = None

    return base_data


@router.get("/configuration")
async def get_configuration() -> Any:
    """TMDB configuration — image base URLs and valid sizes."""
    return await _tmdb_get("configuration")


@router.get("/genre/movie/list")
async def get_movie_genres(language: str = Query("en-US")) -> Any:
    return await _tmdb_get("genre/movie/list", {"language": language})


@router.get("/genre/tv/list")
async def get_tv_genres(language: str = Query("en-US")) -> Any:
    return await _tmdb_get("genre/tv/list", {"language": language})


# ── Generic catch-all proxy (declared last to avoid shadowing above) ────────────

_BLOCKED_WRITE_PATHS = frozenset({"account", "session", "authentication"})


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD"])
async def proxy_tmdb(request: Request, path: str) -> Response:
    """
    Generic proxy for any TMDB endpoint not covered by the typed routes above.

    - GET / HEAD  : cached
    - POST / PUT  : forwarded as-is, not cached
    - DELETE      : rejected (no write operations proxied)

    Clients may not override ``api_key`` through query parameters.
    """
    method    = request.method
    clean     = path.strip("/")

    if not clean:
        raise HTTPException(status_code=400, detail="Path required")

    if method == "DELETE" or any(clean.startswith(p) for p in _BLOCKED_WRITE_PATHS):
        raise HTTPException(status_code=405, detail="Method not permitted via proxy")

    # Build upstream params — strip any client-supplied api_key
    params: dict[str, Any] = {
        k: v for k, v in request.query_params.items() if k != "api_key"
    }
    params.setdefault("language", "en-US")

    # Cached GET / HEAD
    if method in ("GET", "HEAD"):
        return JSONResponse(await _tmdb_get(clean, params))

    # Passthrough POST / PUT (mutations — no caching)
    try:
        body = await request.json() if await request.body() else None
    except Exception:
        body = None

    params["api_key"] = _TMDB_API_KEY

    try:
        fn   = _get_client().post if method == "POST" else _get_client().put
        resp = await fn(clean, json=body, params=params)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("status_message", "TMDB error")
        except Exception:
            detail = "TMDB error"
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="TMDB service unreachable") from exc

    return JSONResponse(resp.json(), status_code=resp.status_code)

# ── Include in main app ─────────────────────────────────────────────────────────

def include_router(app: FastAPI) -> None:
    app.include_router(router)