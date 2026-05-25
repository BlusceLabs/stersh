"""watchfy — main FastAPI entry point.

Start dev:
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Production:
  gunicorn main:app -k uvicorn.workers.UvicornWorker -w 2 --bind 0.0.0.0:8000
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Must run before any watchfy imports — registers services.streaming.app.* aliases
import pkg_shim  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ── Routers ────────────────────────────────────────────────────────────────────
from routes import router as vidking_router
from routes import (
    lifespan as routes_lifespan,
    request_id_middleware,
    _close_browser  as _vk_close_browser,
    _close_client   as _vk_close_client,
)
from black_routes  import router as black_router
from black_routes  import shutdown_black_browser, shutdown_black_client
from white_routes  import router as white_router
from white_routes  import shutdown_white_browser, shutdown_white_client
from pink_routes   import router as pink_router
from pink_routes   import shutdown_pink_browser, shutdown_pink_client
from proxy_routes import router as proxy_router
from ffmpeg_routes import router as ffmpeg_router
from tmdb import include_router as include_tmdb_router

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":%(message)s}',
)

# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging as _log
    _log.getLogger(__name__).info('"watchfy_starting"')
    yield
    import asyncio
    _log.getLogger(__name__).info('"watchfy_shutting_down"')
    await asyncio.gather(
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


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Watchfy Streaming Service",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.middleware("http")(request_id_middleware)

# Mount all routers
app.include_router(vidking_router)
app.include_router(black_router)
app.include_router(white_router)
app.include_router(pink_router)
app.include_router(proxy_router)
app.include_router(ffmpeg_router)
include_tmdb_router(app)

# ── Static frontend ────────────────────────────────────────────────────────────

_FRONTEND = Path(__file__).parent / "frontend"
_INDEX    = _FRONTEND / "index.html"

if not _INDEX.exists():
    _INDEX = Path(__file__).parent / "index.html"

if _FRONTEND.exists() and (_FRONTEND / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND / "assets")), name="assets")


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = "") -> FileResponse:
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    target = _INDEX if _INDEX.exists() else Path(__file__).parent / "index.html"
    return FileResponse(str(target))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 8000)),
        reload=os.environ.get("RELOAD", "false").lower() == "true",
        log_level="info",
    )