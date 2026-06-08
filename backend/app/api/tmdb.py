"""TMDB API proxy and metadata service for watchfy frontend."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import Any, TypeAlias

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.responses import JSONResponse

from redis_utils import tmdb_cache_get, tmdb_cache_set

__all__ = ["router", "close_client", "include_router", "validate_config"]

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

_TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
_TMDB_BASE    = os.environ.get("TMDB_BASE_URL", "https://api.themoviedb.org/3")

# Cache TTL tiers (seconds) — ordered fastest-changing → slowest
_TTL_SEARCH        =  300    # 5 min  — real-time relevance matters
_TTL_TRENDING_DAY  =  900    # 15 min — daily refresh, but staleness hurts UX
_TTL_TRENDING_WEEK = 3_600   # 1 h
_TTL_POPULAR       = 1_800   # 30 min — lists shift daily
_TTL_DEFAULT       = 3_600   # 1 h    — metadata, recommendations, similar
_TTL_CONFIG        = 86_400  # 24 h   — image base URLs rarely change

_BLOCKED_PATHS = frozenset({"account", "session", "authentication"})

_Params: TypeAlias = dict[str, Any]


def validate_config() -> None:
    """Assert required config is present.  Call this from the app lifespan."""
    if not _TMDB_API_KEY:
        raise RuntimeError(
            "TMDB_API_KEY environment variable is not set. "
            "Obtain a key from https://www.themoviedb.org/settings/api"
        )


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
            http2=True,
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

def _cache_key(path: str, params: _Params) -> str:
    """Stable, URL-safe cache key derived from path + sorted params (api_key excluded)."""
    parts = [path] + [f"{k}={params[k]}" for k in sorted(params) if k != "api_key"]
    return hashlib.sha256(":".join(parts).encode()).hexdigest()


def _ttl_for(path: str) -> int:
    if path.startswith("search/"):
        return _TTL_SEARCH
    if path.startswith("trending/"):
        return _TTL_TRENDING_DAY if path.endswith("/day") else _TTL_TRENDING_WEEK
    if path.endswith(("/popular", "/top_rated")):
        return _TTL_POPULAR
    if path == "configuration":
        return _TTL_CONFIG
    return _TTL_DEFAULT


# ── Param helpers ──────────────────────────────────────────────────────────────

def _compact(**kv: Any) -> _Params:
    """Return *kv* with all ``None`` values removed — avoids chains of ``if val:`` guards."""
    return {k: v for k, v in kv.items() if v is not None}


# ── Structured logging ─────────────────────────────────────────────────────────

def _qlog(event: str, **kv: str) -> None:
    tail = " ".join(f'{k}="{v}"' for k, v in kv.items())
    logger.info("[tmdb] event=%r %s", event, tail)


# ── Guards ─────────────────────────────────────────────────────────────────────

def _require_media_type(
    media_type: str,
    *,
    allow: tuple[str, ...] = ("movie", "tv"),
) -> None:
    """Raise 400 if *media_type* is not in *allow*, deduplicating the check across routes."""
    if media_type not in allow:
        joined = ", ".join(f"'{t}'" for t in allow)
        raise HTTPException(status_code=400, detail=f"media_type must be one of: {joined}")


# ── Request coalescing ─────────────────────────────────────────────────────────

_inflight: dict[str, asyncio.Task[Any]] = {}


# ── Core fetch ─────────────────────────────────────────────────────────────────

async def _tmdb_get(path: str, extra: _Params | None = None) -> Any:
    """Low-level GET against TMDB with transparent Redis caching and request coalescing.

    Concurrent cache misses for the same key share one upstream call via a
    shared ``asyncio.Task``, preventing Redis cold-start stampedes.  Each
    caller gets the result via ``asyncio.shield`` so individual cancellations
    don't abort in-flight fetches.
    """
    params: _Params = {
        "api_key":  _TMDB_API_KEY,
        "language": "en-US",
        **(extra or {}),
    }

    clean = path.strip("/")
    key   = _cache_key(clean, params)

    cached = tmdb_cache_get(key)
    if cached is not None:
        return cached

    if key in _inflight:
        return await asyncio.shield(_inflight[key])

    task: asyncio.Task[Any] = asyncio.create_task(_fetch_and_cache(clean, params, key))
    _inflight[key] = task
    try:
        return await asyncio.shield(task)
    finally:
        _inflight.pop(key, None)


async def _fetch_and_cache(path: str, params: _Params, cache_key: str) -> Any:
    """Issue one upstream GET, cache on success, raise ``HTTPException`` on failure."""
    try:
        resp = await _get_client().get(path, params=params)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        try:
            detail = exc.response.json().get("status_message", "TMDB error")
        except Exception:
            detail = "TMDB error"
        _qlog("tmdb_upstream_error", path=path, status=str(status))
        raise HTTPException(status_code=status, detail=detail) from exc
    except httpx.RequestError as exc:
        _qlog("tmdb_request_error", path=path, err=str(exc)[:80])
        raise HTTPException(status_code=502, detail="TMDB service unreachable") from exc

    payload = resp.json()
    tmdb_cache_set(cache_key, payload, ttl=_ttl_for(path))
    return payload


# ── Router ─────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/tmdb", tags=["tmdb"])

# ── Typed endpoints (declared before the catch-all) ───────────────────────────


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
    _require_media_type(media_type)
    return await _tmdb_get(f"{media_type}/{tmdb_id}/recommendations", {
        "language": language, "page": page,
    })


@router.get("/{media_type}/{tmdb_id:int}/similar")
async def get_similar(
    media_type: str,
    tmdb_id: int,
    page: int = Query(1, ge=1, le=500),
    language: str = Query("en-US"),
) -> Any:
    """Similar content for a movie or TV show."""
    _require_media_type(media_type)
    return await _tmdb_get(f"{media_type}/{tmdb_id}/similar", {
        "language": language, "page": page,
    })


@router.get("/{media_type}/popular")
async def get_popular(
    media_type: str,
    page: int = Query(1, ge=1, le=500),
    language: str = Query("en-US"),
    region: str | None = Query(None),
) -> Any:
    """Popular movies or TV shows."""
    _require_media_type(media_type)
    return await _tmdb_get(f"{media_type}/popular", _compact(
        language=language, page=page, region=region,
    ))


@router.get("/{media_type}/top_rated")
async def get_top_rated(
    media_type: str,
    page: int = Query(1, ge=1, le=500),
    language: str = Query("en-US"),
) -> Any:
    """Top-rated movies or TV shows."""
    _require_media_type(media_type)
    return await _tmdb_get(f"{media_type}/top_rated", {
        "language": language, "page": page,
    })


@router.get("/{media_type}/discover")
async def discover(
    media_type: str,
    request: Request,
    page: int = Query(1, ge=1, le=500),
    language: str = Query("en-US"),
    with_genres: str | None = Query(None, description="Pipe-separated genre IDs, e.g. '27|53'"),
    with_original_language: str | None = Query(None),
    with_origin_country: str | None = Query(None, description="ISO 3166-1, e.g. 'KR'"),
    primary_release_year: int | None = Query(None),
    first_air_date_year: int | None = Query(None),
    primary_release_date_gte: str | None = Query(None, alias="primary_release_date.gte"),
    primary_release_date_lte: str | None = Query(None, alias="primary_release_date.lte"),
    first_air_date_gte: str | None = Query(None, alias="first_air_date.gte"),
    first_air_date_lte: str | None = Query(None, alias="first_air_date.lte"),
    sort_by: str = Query("popularity.desc"),
    vote_count_gte: float | None = Query(None, alias="vote_count.gte"),
    vote_average_gte: float | None = Query(None, alias="vote_average.gte"),
    vote_average_lte: float | None = Query(None, alias="vote_average.lte"),
    with_runtime_gte: int | None = Query(None, alias="with_runtime.gte"),
    with_runtime_lte: int | None = Query(None, alias="with_runtime.lte"),
    with_status: int | None = Query(None, description="TV: 0=Returning, 1=Planned, 2=In Production, 3=Ended, 4=Cancelled, 5=Pilot"),
) -> Any:
    """TMDB discover endpoint — the correct way to filter by genre, year, runtime, country, etc.

    Typed parameters are validated and forwarded.  Any additional query
    parameters (certification_country, with_cast, region, etc.) are passed
    upstream as-is for forward compatibility with the full TMDB discover spec.

    Example: GET /api/tmdb/tv/discover?with_genres=18&with_origin_country=KR
    """
    _require_media_type(media_type)

    # Non-dotted params: can be keyword-unpacked cleanly
    params: _Params = _compact(
        language=language,
        page=page,
        sort_by=sort_by,
        with_genres=with_genres,
        with_original_language=with_original_language,
        with_origin_country=with_origin_country,
        primary_release_year=primary_release_year,
        first_air_date_year=first_air_date_year,
        with_status=with_status,
    )

    # Dotted-key params can't be Python kwargs — add them as a table
    for dotkey, val in (
        ("primary_release_date.gte", primary_release_date_gte),
        ("primary_release_date.lte", primary_release_date_lte),
        ("first_air_date.gte",       first_air_date_gte),
        ("first_air_date.lte",       first_air_date_lte),
        ("vote_count.gte",           vote_count_gte),
        ("vote_average.gte",         vote_average_gte),
        ("vote_average.lte",         vote_average_lte),
        ("with_runtime.gte",         with_runtime_gte),
        ("with_runtime.lte",         with_runtime_lte),
    ):
        if val is not None:
            params[dotkey] = val

    # Forward any extra caller-supplied params; strip api_key and already-handled keys
    reserved = set(params) | {
        "api_key", "language", "page", "sort_by", "with_genres",
        "with_original_language", "with_origin_country",
        "primary_release_year", "first_air_date_year", "with_status",
        "primary_release_date.gte", "primary_release_date.lte",
        "first_air_date.gte",       "first_air_date.lte",
        "vote_count.gte",           "vote_average.gte", "vote_average.lte",
        "with_runtime.gte",         "with_runtime.lte",
    }
    for k, v in request.query_params.items():
        if k not in reserved:
            params[k] = v

    return await _tmdb_get(f"discover/{media_type}", params)


@router.get("/{media_type}/trending/{time_window}")
async def get_trending(
    media_type: str,
    time_window: str = "day",
    language: str = Query("en-US"),
) -> Any:
    """Trending movies or TV shows."""
    _require_media_type(media_type)
    if time_window not in ("day", "week"):
        raise HTTPException(status_code=400, detail="time_window must be 'day' or 'week'")
    return await _tmdb_get(f"trending/{media_type}/{time_window}", {"language": language})


@router.get("/search/{media_type}")
async def search(
    media_type: str = Path(pattern="^(movie|tv|person|multi)$"),
    query: str = Query(..., alias="query"),
    page: int = Query(1, ge=1, le=500),
    year: int | None = Query(None),
    language: str = Query("en-US"),
) -> Any:
    """Search for movies, TV shows, or people."""
    return await _tmdb_get(f"search/{media_type}", _compact(
        query=query,
        page=page,
        language=language,
        include_adult=False,
        year=year,
    ))


@router.get("/media/{media_type}/{tmdb_id:int}")
async def get_media_metadata(
    media_type: str,
    tmdb_id: int,
    season: int | None = Query(None),
    episode: int | None = Query(None),
    language: str = Query("en-US"),
) -> Any:
    """Aggregate metadata for a movie or TV episode in one round-trip.

    Uses TMDB's ``append_to_response`` so a single upstream call returns
    details + credits + videos.  When *season* and *episode* are both
    provided for a TV show, the episode details are fetched concurrently.
    """
    _require_media_type(media_type)

    fetch_episode = media_type == "tv" and season is not None and episode is not None

    coros: list[Any] = [
        _tmdb_get(f"{media_type}/{tmdb_id}", {
            "language":           language,
            "append_to_response": "credits,videos",
        }),
    ]
    if fetch_episode:
        coros.append(
            _tmdb_get(
                f"tv/{tmdb_id}/season/{season}/episode/{episode}",
                {"language": language},
            )
        )

    results = await asyncio.gather(*coros, return_exceptions=True)

    base_data = results[0]
    if isinstance(base_data, BaseException):
        raise base_data

    if fetch_episode:
        episode_data = results[1]
        if isinstance(episode_data, dict):
            base_data["episode_details"] = episode_data
        else:
            if isinstance(episode_data, Exception):
                _qlog("episode_fetch_failed", tmdb_id=str(tmdb_id), err=str(episode_data)[:80])
            base_data["episode_details"] = None

    return base_data


@router.get("/configuration")
async def get_configuration() -> Any:
    """TMDB configuration — image base URLs and valid sizes."""
    return await _tmdb_get("configuration")


@router.get("/genre/movie/list")
async def get_movie_genres(language: str = Query("en-US")) -> Any:
    """All movie genre IDs and names."""
    return await _tmdb_get("genre/movie/list", {"language": language})


@router.get("/genre/tv/list")
async def get_tv_genres(language: str = Query("en-US")) -> Any:
    """All TV genre IDs and names."""
    return await _tmdb_get("genre/tv/list", {"language": language})


# ── Generic catch-all proxy (declared last to avoid shadowing typed routes) ────

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD"])
async def proxy_tmdb(request: Request, path: str) -> Response:
    """Generic proxy for any TMDB endpoint not covered by the typed routes above.

    - GET / HEAD  : transparently cached
    - POST / PUT  : forwarded as-is, never cached
    - DELETE      : always rejected (no write operations proxied)

    Callers may not override ``api_key`` through query parameters.
    Paths rooted at account / session / authentication are blocked entirely.
    """
    method = request.method
    clean  = path.strip("/")

    if not clean:
        raise HTTPException(status_code=400, detail="Path required")

    # Block sensitive path roots regardless of HTTP method
    if any(clean.startswith(p) for p in _BLOCKED_PATHS):
        raise HTTPException(status_code=403, detail="Path not accessible via proxy")

    if method == "DELETE":
        raise HTTPException(status_code=405, detail="DELETE not permitted via proxy")

    # Scrub any client-supplied api_key; inject language default
    params: _Params = {
        k: v for k, v in request.query_params.items() if k != "api_key"
    }
    params.setdefault("language", "en-US")

    if method in ("GET", "HEAD"):
        return JSONResponse(await _tmdb_get(clean, params))

    # POST / PUT — forward mutation, skip cache
    raw_body = await request.body()
    try:
        body: Any = await request.json() if raw_body else None
    except Exception:
        body = None

    params["api_key"] = _TMDB_API_KEY
    fn = _get_client().post if method == "POST" else _get_client().put
    try:
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


# ── App integration ────────────────────────────────────────────────────────────

def include_router(app: FastAPI) -> None:
    app.include_router(router)