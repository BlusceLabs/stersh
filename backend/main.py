"""watchfy — main FastAPI entry point.

Start dev:
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Production:
  gunicorn main:app -k uvicorn.workers.UvicornWorker -w 2 --bind 0.0.0.0:8000
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv

load_dotenv()

# Must run before any watchfy imports — registers services.streaming.app.* aliases
import pkg_shim  # noqa: F401

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Routers ────────────────────────────────────────────────────────────────────
from routes import router as vidking_router
from routes import (
    lifespan as routes_lifespan,
    request_id_middleware,
    _close_browser as _vk_close_browser,
    _close_client  as _vk_close_client,
)
from black_routes  import router as black_router
from black_routes  import shutdown_black_browser, shutdown_black_client
from white_routes  import router as white_router
from white_routes  import shutdown_white_browser, shutdown_white_client
from pink_routes   import router as pink_router
from pink_routes   import shutdown_pink_browser, shutdown_pink_client
from proxy_routes  import router as proxy_router
from ffmpeg_routes import router as ffmpeg_router
from tmdb          import include_router as include_tmdb_router

# ── Logging ────────────────────────────────────────────────────────────────────

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=_LOG_LEVEL,
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":%(message)s}',
)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_FRONTEND     = Path(__file__).parent / "frontend"
_INDEX        = _FRONTEND / "index.html"
_STARTUP_TIME = time.time()

if not _INDEX.exists():
    _INDEX = Path(__file__).parent / "index.html"

# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info('"watchfy_starting"')
    yield
    logger.info('"watchfy_shutting_down"')
    results = await asyncio.gather(
        _vk_close_browser(),
        _vk_close_client(),
        shutdown_black_browser(),
        shutdown_black_client(),
        shutdown_white_browser(),
        shutdown_white_client(),
        shutdown_pink_browser(),
        shutdown_pink_client(),
        return_exceptions=True,
    )
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning('"shutdown_error","task":%d,"error":"%s"', i, result)
    logger.info('"watchfy_stopped"')


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Watchfy Streaming Service",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST", "HEAD", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Segment-Expired",
        "X-Latency-Ms",
        "X-Bandwidth-Kbps",
        "Content-Range",
    ],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next) -> Response:
    """Attach security headers to every non-streaming response."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.middleware("http")
async def latency_middleware(request: Request, call_next) -> Response:
    """Record wall-clock latency and attach it to every response."""
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    response.headers["X-Latency-Ms"] = str(elapsed_ms)
    if elapsed_ms > 5_000:
        logger.warning(
            '"slow_request","method":"%s","path":"%s","latency_ms":%s',
            request.method, request.url.path, elapsed_ms,
        )
    return response


app.middleware("http")(request_id_middleware)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(vidking_router)
app.include_router(black_router)
app.include_router(white_router)
app.include_router(pink_router)
app.include_router(proxy_router)
app.include_router(ffmpeg_router)
include_tmdb_router(app)

# ── Health & meta endpoints ────────────────────────────────────────────────────

@app.get("/api/health", tags=["meta"], summary="Liveness probe")
async def health() -> JSONResponse:
    """Returns 200 as long as the process is alive."""
    return JSONResponse({"status": "ok", "uptime_s": round(time.time() - _STARTUP_TIME, 1)})


@app.get("/api/ready", tags=["meta"], summary="Readiness probe")
async def ready() -> JSONResponse:
    """
    Extend this check to verify DB connections, browser pools, etc.
    Returns 503 when the service is not ready to accept traffic.
    """
    checks: dict[str, str] = {}
    all_ok = all(v == "ok" for v in checks.values()) if checks else True

    status_code = 200 if all_ok else 503
    return JSONResponse(
        {"status": "ready" if all_ok else "degraded", "checks": checks},
        status_code=status_code,
    )


# ── Static frontend (SPA catch-all) ───────────────────────────────────────────

if _FRONTEND.exists() and (_FRONTEND / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND / "assets")), name="assets")


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = "") -> FileResponse:
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")

    target = _INDEX if _INDEX.exists() else Path(__file__).parent / "index.html"

    if not target.exists():
        raise HTTPException(status_code=503, detail="Frontend not built")

    return FileResponse(
        str(target),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


# ── Dev entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 8000)),
        reload=os.environ.get("RELOAD", "false").lower() == "true",
        log_level=_LOG_LEVEL.lower(),
        access_log=True,
    )