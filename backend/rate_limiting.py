"""Rate limiting middleware for watchfy backend."""
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from .redis_utils import rate_limit_check

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
        
        # Check rate limit (15 requests per minute)
        allowed, remaining, reset = rate_limit_check(
            client_id=client_ip,
            max_requests=15,
            window=60
        )
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={
                    "Retry-After": str(reset),
                    "X-RateLimit-Limit": "15",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = "15"
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
        
        return response