"""watchfy — FastAPI application entry point.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
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
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.providers.black import (
    router as black_router,
    shutdown_black_browser,
    shutdown_black_client,
)
from app.api.providers.white import (
    router as white_router,
    shutdown_white_browser,
    shutdown_white_client,
)
from app.core.extractors.white import close_pooled_session as close_white_session
from app.api.proxy import router as proxy_router
from app.api.ffmpeg_remux import router as ffmpeg_router
from app.api.tmdb import include_router as include_tmdb_router

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────────

_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=_LOG_LEVEL,
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":%(message)s}',
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_FRONTEND     = Path(__file__).parent.parent / "frontend"
_INDEX        = _FRONTEND / "index.html"
_STARTUP_TIME = time.time()

if not _INDEX.exists():
    _INDEX = Path(__file__).parent.parent / "index.html"

# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info('"watchfy_starting"')
    yield
    logger.info('"watchfy_shutting_down"')
    results = await asyncio.gather(
        shutdown_black_browser(),
        shutdown_black_client(),
        shutdown_white_browser(),
        shutdown_white_client(),
        close_white_session(),

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
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.middleware("http")
async def latency_middleware(request: Request, call_next) -> Response:
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


# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(black_router)
app.include_router(white_router)

app.include_router(proxy_router)
app.include_router(ffmpeg_router)
include_tmdb_router(app)

# ── Health & meta endpoints ────────────────────────────────────────────────────

@app.get("/api/health", tags=["meta"], summary="Liveness probe")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "uptime_s": round(time.time() - _STARTUP_TIME, 1)})


@app.get("/api/ready", tags=["meta"], summary="Readiness probe")
async def ready() -> JSONResponse:
    return JSONResponse({"status": "ready"}, status_code=200)


# ── Static frontend (SPA catch-all) ───────────────────────────────────────────

if _FRONTEND.exists() and (_FRONTEND / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND / "assets")), name="assets")


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = "") -> FileResponse:
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")

    target = _INDEX if _INDEX.exists() else Path(__file__).parent.parent / "index.html"

    if not target.exists():
        raise HTTPException(status_code=503, detail="Frontend not built")

    return FileResponse(
        str(target),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
