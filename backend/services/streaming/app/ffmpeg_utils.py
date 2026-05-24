"""FFmpeg utilities for video remuxing and processing."""
import subprocess
import logging

logger = logging.getLogger(__name__)


def get_ffmpeg_version() -> str | None:
    """Get the installed FFmpeg version."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.split("\n")[0]
        return None
    except Exception as e:
        logger.warning("FFmpeg not found: %s", e)
        return None


async def remux_to_hls(input_url: str, output_dir: str) -> str:
    """Remux a video stream to HLS format using FFmpeg."""
    import asyncio

    output_path = f"{output_dir}/output.m3u8"

    cmd = [
        "ffmpeg",
        "-i", input_url,
        "-c", "copy",
        "-f", "hls",
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-hls_flags", "delete_segments",
        output_path,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error("FFmpeg remux failed: %s", stderr.decode())
            return ""

        return output_path
    except Exception as e:
        logger.error("FFmpeg remux error: %s", e)
        return ""


def probe_duration(input_url: str) -> float | None:
    """Get video duration using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_url,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    except Exception as e:
        logger.warning("ffprobe failed: %s", e)
        return None
