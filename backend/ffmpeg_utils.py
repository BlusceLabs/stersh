"""FFmpeg utilities for watchfy streaming backend.

Provides:
  - get_ffmpeg_version()  – safe version probe
  - remux_hls_to_mp4()   – stream HLS → MP4 via subprocess pipe
  - ffmpeg_routes         – /api/ffmpeg/* FastAPI router
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

_FFMPEG_BIN = shutil.which("ffmpeg") or os.environ.get("FFMPEG_BIN", "ffmpeg")
_FFPROBE_BIN = shutil.which("ffprobe") or os.environ.get("FFPROBE_BIN", "ffprobe")
_FFMPEG_TIMEOUT = 300  # seconds per remux job
_CHUNK_SIZE = 64 * 1024  # 64 KB streaming chunks


# ── Version probe ──────────────────────────────────────────────────────────────

def get_ffmpeg_version() -> str | None:
    """Return the ffmpeg version string, or None if ffmpeg is not available."""
    try:
        result = subprocess.run(
            [_FFMPEG_BIN, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        match = re.search(r"ffmpeg version (\S+)", result.stdout)
        return match.group(1) if match else result.stdout.split("\n")[0]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def get_ffprobe_version() -> str | None:
    try:
        result = subprocess.run(
            [_FFPROBE_BIN, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        match = re.search(r"ffprobe version (\S+)", result.stdout)
        return match.group(1) if match else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


# ── Remux helpers ──────────────────────────────────────────────────────────────

async def remux_hls_to_mp4_stream(hls_url: str) -> AsyncIterator[bytes]:
    """Stream-remux an HLS URL to fMP4 (fragmented MP4) via ffmpeg pipe.

    Uses stream copy (no transcode) so CPU load is minimal.
    Yields chunks as they arrive from the ffmpeg stdout pipe.
    """
    cmd = [
        _FFMPEG_BIN,
        "-loglevel", "error",
        "-i", hls_url,
        "-c", "copy",          # stream copy — no re-encode
        "-movflags", "frag_keyframe+empty_moov+faststart",
        "-f", "mp4",
        "pipe:1",              # write to stdout
    ]
    logger.info('"ffmpeg_remux_start":{"url":"%s"}', hls_url)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        while True:
            chunk = await proc.stdout.read(_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
    except asyncio.CancelledError:
        proc.kill()
        raise
    finally:
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()

    stderr = await proc.stderr.read()
    if proc.returncode not in (0, None) and stderr:
        logger.warning('"ffmpeg_stderr":{"msg":"%s"}', stderr.decode(errors="replace")[:300])


async def remux_hls_to_ts_stream(hls_url: str) -> AsyncIterator[bytes]:
    """Stream-remux an HLS URL to MPEG-TS for direct playback."""
    cmd = [
        _FFMPEG_BIN,
        "-loglevel", "error",
        "-i", hls_url,
        "-c", "copy",
        "-f", "mpegts",
        "pipe:1",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        while True:
            chunk = await proc.stdout.read(_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
    except asyncio.CancelledError:
        proc.kill()
        raise
    finally:
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()


async def probe_stream(url: str) -> dict:
    """Run ffprobe on a URL and return codec/format info."""
    cmd = [
        _FFPROBE_BIN,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        url,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=20.0)
        import json
        return json.loads(stdout.decode())
    except Exception as exc:
        logger.warning('"ffprobe_failed":{"err":"%s"}', exc)
        return {}


# ── FastAPI router ─────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/ffmpeg", tags=["ffmpeg"])


@router.get("/remux")
async def remux_proxy(
    url: str = Query(..., description="Source HLS (.m3u8) URL to remux"),
    format: str = Query(default="mp4", description="Output format: mp4 or ts"),
) -> StreamingResponse:
    """Remux an HLS stream to MP4 or MPEG-TS via FFmpeg and stream the result.

    Useful for browsers/clients that can't natively play HLS but can play MP4.
    The entire output is streamed — no temporary file is written to disk.
    """
    if get_ffmpeg_version() is None:
        raise HTTPException(status_code=503, detail="FFmpeg not available on this server")

    if format not in ("mp4", "ts"):
        raise HTTPException(status_code=400, detail="format must be 'mp4' or 'ts'")

    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid source URL")

    if format == "mp4":
        media_type = "video/mp4"
        generator = remux_hls_to_mp4_stream(url)
        filename = "stream.mp4"
    else:
        media_type = "video/mp2t"
        generator = remux_hls_to_ts_stream(url)
        filename = "stream.ts"

    return StreamingResponse(
        generator,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/probe")
async def probe_endpoint(url: str = Query(...)) -> dict:
    """Probe a stream URL with ffprobe and return codec/format metadata."""
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")
    info = await probe_stream(url)
    if not info:
        raise HTTPException(status_code=502, detail="ffprobe returned no data")
    return info