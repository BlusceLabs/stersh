"""Gzip compression middleware for ultra-fast responses."""
from fastapi import Request, FastAPI
from fastapi.responses import Response
import gzip
import io

def setup_gzip_middleware(app: FastAPI, min_size: int = 1024):
    """Setup gzip compression middleware."""
    @app.middleware("http")
    async def gzip_middleware(request: Request, call_next):
        # Skip compression for certain paths
        skip_paths = ["/health", "/metrics", "/config", "/version", "/system/info"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        response = await call_next(request)
        
        # Compress only if response is JSON or HTML and size > min_size
        content_type = response.headers.get("Content-Type", "").lower()
        if "json" in content_type or "html" in content_type:
            body = response.body
            if len(body) >= min_size:
                compressed = gzip.compress(body)
                if len(compressed) < len(body):
                    response.headers["Content-Encoding"] = "gzip"
                    response.headers["Content-Length"] = str(len(compressed))
                    response.body = compressed
        
        return response