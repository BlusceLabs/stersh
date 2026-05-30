"""Cache warming for TMDB data on startup."""
import asyncio
from datetime import datetime, timedelta
from typing import List

async def warm_tmdb_caches():
    """Warm up TMDB caches on startup."""
    try:
        # Preload popular movies and TV shows
        from .tmdb import proxy_tmdb_endpoint
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Popular movies
            resp = await client.get(
                "https://api.themoviedb.org/3/movie/popular",
                params={"api_key": os.environ.get("TMDB_API_KEY", ""), "language": "en-US", "page": 1}
            )
            if resp.status_code == 200:
                from .redis_utils import tmdb_cache_set
                tmdb_cache_set("movie:popular:page1", resp.json())
            
            # Popular TV shows
            resp = await client.get(
                "https://api.themoviedb.org/3/tv/popular",
                params={"api_key": os.environ.get("TMDB_API_KEY", ""), "language": "en-US", "page": 1}
            )
            if resp.status_code == 200:
                tmdb_cache_set("tv:popular:page1", resp.json())
            
            logger.info('"tmdb_caches_warmed"')
    except Exception as exc:
        logger.error('"tmdb_cache_warm_failed":{"err":"%s"}', exc)

# Add this to startup_tasks.py
async def startup_event():
    logger.info('"startup_event"')
    
    # Test database connection
    try:
        from database import get_db
        db = get_db()
        db.close()
        logger.info('"database_connection_ok"')
    except Exception as exc:
        logger.error('"database_connection_failed":{"err":"%s"}', exc)
    
    # Test Redis connection
    try:
        from .redis_utils import get_redis_client
        client = get_redis_client()
        if not client.ping():
            raise Exception("Redis not responding")
        logger.info('"redis_connection_ok"')
    except Exception as exc:
        logger.error('"redis_connection_failed":{"err":"%s"}', exc)
    
    # Preload TMDB configuration into Redis cache
    try:
        from .redis_utils import tmdb_cache_set
        import httpx
        async with httpx.AsyncClient() as test_client:
            test_resp = await test_client.get(
                "https://api.themovdb.org/3/configuration",
                params={"api_key": os.environ.get("TMDB_API_KEY", "")}
            )
            if test_resp.status_code == 200:
                tmdb_cache_set("configuration", test_resp.json())
                logger.info('"tmdb_configuration_cached"')
    except Exception as exc:
        logger.error('"tmdb_cache_failed":{"err":"%s"}', exc)
    
    # Warm TMDB caches
    asyncio.create_task(warm_tmdb_caches())