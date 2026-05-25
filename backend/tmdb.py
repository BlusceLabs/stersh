"""TMDB API proxy and metadata service for watchfy frontend."""
from __future__ import annotations

import os
import time
import hashlib
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, Query, Response
from fastapi.responses import JSONResponse
from fastapi import FastAPI

from redis_utils import tmdb_cache_get, tmdb_cache_set, tmdb_cache_delete
from hls_parser import parse_master_manifest

# ── Config ────────────────────────────────────────────────────────────────────

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

TMDB_BASE = "https://api.themoviedb.org/3"

# ── HTTP client ───────────────────────────────────────────────────────────────

_client: httpx.AsyncClient | None = None

async def _get_tmdb_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {TMDB_API_KEY}"},
            timeout=15.0,
            follow_redirects=True,
        )
    return _client

# ── Cache key generation ──────────────────────────────────────────────────────

def _make_cache_key(
    path: str,
    params: Dict[str, Any] | None = None,
    method: str = "GET",
) -> str:
    """Generate a cache key for TMDB responses."""
    parts = [method, path]
    if params:
        for key in sorted(params.keys()):
            parts.append(f"{key}={params[key]}")
    return hashlib.md5(":".join(parts).encode()).hexdigest()

# ── Router ─────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/tmdb", tags=["tmdb"])

# ── Generic TMDB proxy endpoint ────────────────────────────────────────────────

@router.get("/{path:path}")
@router.post("/{path:path}")
@router.put("/{path:path}")
@router.delete("/{path:path}")
async def proxy_tmdb_endpoint(
    request: Request,
    path: str,
    query: dict | None = None,
    data: dict | None = None,
) -> Response:
    """Proxy any TMDB API request with caching.
    
    This endpoint acts as a generic proxy for all TMDB API endpoints.
    It supports GET, POST, PUT, DELETE methods.
    
    Example routes:
    - /api/tmdb/movie/550
    - /api/tmdb/tv/1399
    - /api/tmdb/search/movie?query=Inception
    - /api/tmdb/movie/550/credits
    """
    clean_path = path.strip("/")
    if not clean_path:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    # Build query parameters
    tmdb_params: Dict[str, Any] = {"api_key": TMDB_API_KEY}
    if query:
        tmdb_params.update(query)
    
    # Include language if not specified
    if "language" not in tmdb_params:
        tmdb_params["language"] = "en-US"
    
    # Determine HTTP method
    method = request.method
    
    # Cache key
    cache_key = _make_cache_key(clean_path, tmdb_params, method)
    
    # Check cache (only for GET/HEAD requests)
    if method in ("GET", "HEAD"):
        cached = tmdb_cache_get(cache_key)
        if cached:
            return JSONResponse(content=cached, status_code=200)
    
    # Make request to TMDB API
    client = await _get_tmdb_client()
    url = f"{TMDB_BASE}/{clean_path}"
    
    try:
        if method == "GET":
            resp = await client.get(url, params=tmdb_params)
        elif method == "POST":
            resp = await client.post(url, json=data, params=tmdb_params)
        elif method == "PUT":
            resp = await client.put(url, json=data, params=tmdb_params)
        elif method == "DELETE":
            resp = await client.delete(url, params=tmdb_params)
        else:
            raise HTTPException(status_code=405, detail="Method not allowed")
        
        resp.raise_for_status()
        data = resp.json()
        
    except httpx.HTTPStatusError as exc:
        # Pass through TMDB errors
        if exc.response.status_code >= 400:
            error_data = exc.response.json()
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=error_data.get("status_message", "TMDB API error")
            )
        raise HTTPException(status_code=502, detail="TMDB service unavailable")
    except Exception as exc:
        raise HTTPException(status_code=502, detail="TMDB service unavailable")
    
    # Cache response (only for GET/HEAD)
    if method in ("GET", "HEAD"):
        tmdb_cache_set(cache_key, data)
    
    return JSONResponse(content=data, status_code=resp.status_code)

# ── Specific convenience endpoints ─────────────────────────────────────────────

@router.get("/movie/{tmdb_id}")
async def get_movie(
    request: Request,
    tmdb_id: int,
    language: str = Query("en-US", alias="l", description="Language code"),
) -> Any:
    """Get movie details by TMDB ID."""
    return await proxy_tmdb_endpoint(
        request=request, 
        path=f"movie/{tmdb_id}", 
        query={"language": language}
    )

@router.get("/tv/{tmdb_id}")
async def get_tv_show(
    request: Request,
    tmdb_id: int,
    language: str = Query("en-US", alias="l"),
) -> Any:
    """Get TV show details by TMDB ID."""
    return await proxy_tmdb_endpoint(
        request=request, 
        path=f"tv/{tmdb_id}", 
        query={"language": language}
    )

@router.get("/search")
async def search(
    request: Request,
    query: str,
    media_type: str = Query("multi", pattern="^movie|tv|person|all$"),
    page: int = 1,
    year: int | None = Query(None),
    language: str = Query("en-US"),
) -> Any:
    """Search for movies, TV shows, and people."""
    params: Dict[str, Any] = {
        "query": query,
        "page": page,
        "language": language,
        "include_adult": False,
    }
    if media_type != "all":
        params["media_type"] = media_type
    if year:
        params["year"] = year
    
    return await proxy_tmdb_endpoint(request=request, path="search/multi", query=params)

@router.get("/configuration")
async def get_configuration(request: Request) -> Any:
    """Get TMDB configuration (image base URLs, sizes)."""
    return await proxy_tmdb_endpoint(request=request, path="configuration")

@router.get("/genre/movie/list")
async def get_movie_genres(request: Request) -> Any:
    """Get list of movie genres."""
    return await proxy_tmdb_endpoint(request=request, path="genre/movie/list")

@router.get("/genre/tv/list")
async def get_tv_genres(request: Request) -> Any:
    """Get list of TV genres."""
    return await proxy_tmdb_endpoint(request=request, path="genre/tv/list")

@router.get("/media/{media_type}/{tmdb_id}")
async def get_media_metadata(
    request: Request,
    media_type: str,
    tmdb_id: int,
    season: int | None = None,
    episode: int | None = None,
) -> Any:
    """Get comprehensive metadata for a movie or TV show.
    
    This endpoint combines multiple TMDB endpoints into one call for frontend simplicity.
    """
    if media_type not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type must be 'movie' or 'tv'")
    
    # Get basic metadata
    if media_type == "movie":
        data = await proxy_tmdb_endpoint(
            request=request, 
            path=f"movie/{tmdb_id}"
        )
        credits = await proxy_tmdb_endpoint(
            request=request, 
            path=f"movie/{tmdb_id}/credits"
        )
        videos = await proxy_tmdb_endpoint(
            request=request, 
            path=f"movie/{tmdb_id}/videos"
        )
    else:
        data = await proxy_tmdb_endpoint(
            request=request, 
            path=f"tv/{tmdb_id}"
        )
        credits = await proxy_tmdb_endpoint(
            request=request, 
            path=f"tv/{tmdb_id}/credits"
        )
        videos = await proxy_tmdb_endpoint(
            request=request, 
            path=f"tv/{tmdb_id}/videos"
        )
        if season is not None and episode is not None:
            episode_data = await proxy_tmdb_endpoint(
                request=request, 
                path=f"tv/{tmdb_id}/season/{season}/episode/{episode}"
            )
            data["episode_details"] = episode_data
    
    # Enhance with additional data
    data["credits"] = credits
    data["videos"] = videos
    
    return data

# ── Include in main app ─────────────────────────────────────────────────────────

def include_router(app: FastAPI) -> None:
    """Include TMDB router in FastAPI app."""
    app.include_router(router)