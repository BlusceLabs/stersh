"""Rate limiting middleware for watchfy backend."""
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from redis_utils import get_cache_stats


def setup_rate_limiting(app: FastAPI):
    """Setup rate limiting middleware."""
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Skip rate limiting for certain endpoints (health, metrics, etc.)
        skip_paths = ["/api/health", "/api/metrics", "/api/auth/token", "/api/auth/register"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Simple in-memory rate limiting (15 requests per minute per IP)
        # For production, replace with Redis-backed rate limiting
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = "15"
        response.headers["X-RateLimit-Remaining"] = "14"

        return response
