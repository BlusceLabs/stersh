"""CDN support middleware for ultra-fast content delivery."""
from fastapi import Request, FastAPI
from fastapi.responses import Response

def setup_cdn_middleware(app: FastAPI):
    """Setup CDN caching headers."""
    @app.middleware("http")
    async def cdn_middleware(request: Request, call_next):
        response = await call_next(request)
        
        # Set CDN caching headers for static assets and API responses
        # Cache for 1 hour for API, longer for static
        cache_time = 3600  # 1 hour
        
        # Don't cache these paths
        skip_cache = ["/auth/", "/user/", "/admin/"]
        if any(request.url.path.startswith(path) for path in skip_cache):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            return response
        
        # Set caching headers
        response.headers["Cache-Control"] = f"public, max-age={cache_time}, immutable"
        response.headers["Surrogate-Control"] = f"public, max-age={cache_time}, immutable"
        response.headers["Vary"] = "Accept-Encoding, Origin"
        
        # Add CDN-specific headers
        response.headers["X-Cache-Key"] = request.url.path + "?" + request.url.query
        response.headers["X-Cache"] = "HIT"
        
        return response