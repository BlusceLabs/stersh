"""Cache warming for TMDB data on startup."""
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

_TMDB_BASE = "https://api.themoviedb.org/3"


async def _fetch_tmdb(path: str, params: dict) -> dict | None:
    """Fetch a TMDB endpoint via the project's shared httpx client.

    Returns the parsed JSON body on success, or `None` on any error so
    the caller can decide how to react. The shared `tmdb.get_client()`
    is used so we inherit any global timeout / header configuration.
    """
    api_key = os.environ.get("TMDB_API_KEY", "")
    if not api_key:
        logger.warning('"tmdb_cache_warm_skipped":{"reason":"no_api_key","path":"%s"}', path)
        return None
    try:
        from tmdb import _get_client as get_tmdb_client
        client = get_tmdb_client()
        resp = await client.get(
            path,
            params={**params, "api_key": api_key},
        )
        if resp.status_code != 200:
            logger.warning(
                '"tmdb_cache_warm_http":{"path":"%s","status":%d}', path, resp.status_code
            )
            return None
        return resp.json()
    except Exception as exc:
        logger.warning('"tmdb_cache_warm_failed":{"path":"%s","err":"%s"}', path, exc)
        return None


async def warm_tmdb_caches() -> None:
    """Preload popular movies and TV shows into Redis on startup."""
    from redis_utils import tmdb_cache_set

    popular_movies = await _fetch_tmdb(
        "/movie/popular", {"language": "en-US", "page": 1}
    )
    if popular_movies is not None:
        tmdb_cache_set("movie:popular:page1", popular_movies)

    popular_tv = await _fetch_tmdb(
        "/tv/popular", {"language": "en-US", "page": 1}
    )
    if popular_tv is not None:
        tmdb_cache_set("tv:popular:page1", popular_tv)

    logger.info('"tmdb_caches_warmed"')


async def startup_event() -> None:
    """Run once at app startup: sanity-check DB, Redis, and TMDB."""
    logger.info('"startup_event"')

    try:
        from database import get_db
        db = next(get_db())
        db.close()
        logger.info('"database_connection_ok"')
    except Exception as exc:
        logger.error('"database_connection_failed":{"err":"%s"}', exc)

    try:
        from redis_utils import cleanup_redis
        cleanup_redis()
        logger.info('"redis_cache_reset"')
    except Exception as exc:
        logger.warning('"redis_cache_reset_failed":{"err":"%s"}', exc)

    config = await _fetch_tmdb("/configuration", {})
    if config is not None:
        try:
            from redis_utils import tmdb_cache_set
            tmdb_cache_set("configuration", config)
            logger.info('"tmdb_configuration_cached"')
        except Exception as exc:
            logger.error('"tmdb_cache_set_failed":{"err":"%s"}', exc)

    asyncio.create_task(warm_tmdb_caches())