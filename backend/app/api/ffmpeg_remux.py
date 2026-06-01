"""FFmpeg remux routes for watchfy — provides remux_proxy callable.

Imported by routes.py as:
    from .services.streaming.app.ffmpeg_routes import remux_proxy

Also mounts its own APIRouter at /api/ffmpeg for direct access.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ssrf import redirect_event_hook, validate_outbound_url

logger = logging.getLogger(__name__)

_FFMPEG_BIN  = shutil.which("ffmpeg")  or "ffmpeg"
_FFPROBE_BIN = shutil.which("ffprobe") or "ffprobe"
_CHUNK = 64 * 1024   # 64 KB read chunks


# ── Shared stream generators ──────────────────────────────────────────────────

async def _stream_mp4(hls_url: str):
    """Remux HLS → fragmented MP4 via pipe; yields chunks."""
    # Validate the initial URL and any redirect target. ffmpeg is invoked
    # with the validated URL — we cannot easily hook its internal HTTP
    # client, so a curl/ffmpeg-level SSRF via redirects is out of scope
    # here; the URL is already allowlisted.
    cmd = [
        _FFMPEG_BIN, "-loglevel", "error",
        "-i", hls_url,
        "-c", "copy",
        "-movflags", "frag_keyframe+empty_moov+faststart",
        "-f", "mp4", "pipe:1",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        while chunk := await proc.stdout.read(_CHUNK):
            yield chunk
    except asyncio.CancelledError:
        proc.kill()
        raise
    finally:
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()


async def _stream_ts(hls_url: str):
    """Remux HLS → MPEG-TS via pipe; yields chunks."""
    cmd = [
        _FFMPEG_BIN, "-loglevel", "error",
        "-i", hls_url,
        "-c", "copy",
        "-f", "mpegts", "pipe:1",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        while chunk := await proc.stdout.read(_CHUNK):
            yield chunk
    except asyncio.CancelledError:
        proc.kill()
        raise
    finally:
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()


# ── Public callable used by routes.py ────────────────────────────────────────

async def remux_proxy(url: str, format: str = "mp4") -> StreamingResponse:
    """Remux an HLS URL to MP4 or TS and return a StreamingResponse.

    Called inline from /api/vidking/proxy/hls?remux=1.
    No temp file is written; the pipe streams directly to the client.
    """
    if not shutil.which(_FFMPEG_BIN):
        raise HTTPException(status_code=503, detail="FFmpeg not available on this server")

    if format not in ("mp4", "ts"):
        raise HTTPException(status_code=400, detail="format must be 'mp4' or 'ts'")

    validate_outbound_url(url)

    logger.info('"remux_start":{"url":"%s","fmt":"%s"}', url[:100], format)

    if format == "mp4":
        return StreamingResponse(
            _stream_mp4(url),
            media_type="video/mp4",
            headers={
                "Content-Disposition": 'attachment; filename="watchfy.mp4"',
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*",
            },
        )
    return StreamingResponse(
        _stream_ts(url),
        media_type="video/mp2t",
        headers={
            "Content-Disposition": 'attachment; filename="watchfy.ts"',
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ── Standalone router ─────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/ffmpeg", tags=["ffmpeg"])


@router.get("/remux")
async def remux_endpoint(
    url: str = Query(...),
    format: str = Query(default="mp4"),
) -> StreamingResponse:
    """Remux any HLS URL to MP4 or TS. Streams; no disk writes."""
    return await remux_proxy(url=url, format=format)


@router.get("/probe")
async def probe_endpoint(url: str = Query(...)) -> dict:
    """Run ffprobe on a URL and return stream + format metadata."""
    validate_outbound_url(url)
    import json
    cmd = [
        _FFPROBE_BIN, "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        url,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=20.0)
        return json.loads(stdout.decode())
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="ffprobe timed out")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ffprobe failed: {exc}")


@router.get("/version")
async def version_endpoint() -> dict:
    """Return installed ffmpeg/ffprobe versions."""
    import subprocess
    def _ver(bin_: str) -> str | None:
        try:
            r = subprocess.run([bin_, "-version"], capture_output=True, text=True, timeout=5)
            m = re.search(r"version (\S+)", r.stdout)
            return m.group(1) if m else None
        except Exception:
            return None

    return {
        "ffmpeg":  _ver(_FFMPEG_BIN),
        "ffprobe": _ver(_FFPROBE_BIN),
    }