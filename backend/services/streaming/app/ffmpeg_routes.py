"""FFmpeg-based remuxing endpoints for browser-compatible streaming."""
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ffmpeg")


@router.get("/remux")
async def remux_proxy(url: str = Query(...), format: str = Query(default="hls")):
    """Remux a video source to a browser-compatible format.

    Uses FFmpeg to repackage the stream.
    """
    from .ffmpeg_utils import remux_to_hls

    output_dir = "/tmp/watchfy_remux"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    result = await remux_to_hls(url, output_dir)

    if not result:
        return Response(status_code=502, content="Remux failed")

    if format == "hls":
        return FileResponse(
            path=result,
            media_type="application/vnd.apple.mpegurl",
            filename="stream.m3u8",
        )

    return Response(status_code=400, content="Unsupported format")
