"""Prometheus metrics for watchfy backend."""
from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, FastAPI, Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Metrics definitions
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_DURATION = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "path"])
ACTIVE_CONNECTIONS = Gauge("active_connections", "Number of active connections")
CACHE_HITS = Counter("cache_hits_total", "Cache hit count")
CACHE_MISSES = Counter("cache_misses_total", "Cache miss count")
DB_CONNECTIONS = Gauge("database_connections", "Database connection status")
REDIS_CONNECTIONS = Gauge("redis_connections", "Redis connection status")

# Middleware to collect metrics
def collect_metrics_middleware(app: FastAPI):
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start_time = time.time()
        ACTIVE_CONNECTIONS.inc()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration = time.time() - start_time
            status_code = response.status_code if response else 500
            REQUEST_DURATION.labels(method=request.method, path=request.url.path).observe(duration)
            REQUEST_COUNT.labels(method=request.method, path=request.url.path, status=status_code).inc()
            ACTIVE_CONNECTIONS.dec()

@router.get("/")
async def metrics_handler():
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain",
        headers={"Content-Type": "text/plain; version=0.0.4"}
    )

@router.get("/status")
async def metrics_status():
    """Get metrics status."""
    return {
        "active_connections": ACTIVE_CONNECTIONS._value.get(),
        "request_count": REQUEST_COUNT._value.get(),
        "cache_hits": CACHE_HITS._value.get(),
        "cache_misses": CACHE_MISSES._value.get(),
        "db_connected": DB_CONNECTIONS._value.get() > 0,
        "redis_connected": REDIS_CONNECTIONS._value.get() > 0,
    }