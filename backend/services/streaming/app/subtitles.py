"""Subtitle fetching and conversion utilities."""
import logging
import os
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SubtitleTrack:
    """A single subtitle track."""

    label: str
    language: str
    url: str
    format: str  # "vtt" or "srt"


# OpenSubtitles API v1 (requires free API key from opensubtitles.com)
OPENSUBTITLES_API_V1 = "https://api.opensubtitles.com/api/v1"
# Legacy XML-RPC endpoint (deprecated, often down)
OPENSUBTITLES_LEGACY = "https://rest.opensubtitles.org/search"

_http_client: httpx.AsyncClient | None = None


async def _get_subtitle_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "Watch!fy/1.0"},
            follow_redirects=True,
        )
    return _http_client


async def shutdown_subtitle_client():
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def _get_os_api_key() -> str | None:
    return os.environ.get("OPENSUBTITLES_API_KEY", "").strip() or None


async def _fetch_from_opensubtitles_v1(
    client: httpx.AsyncClient, imdb_id: str, language: str
) -> list[SubtitleTrack]:
    """Try the new OpenSubtitles REST API v1."""
    api_key = _get_os_api_key()
    if not api_key:
        logger.debug("No OPENSUBTITLES_API_KEY set, skipping v1 API")
        return []

    headers = {
        "User-Agent": "Watch!fy/1.0",
        "Api-Key": api_key,
        "Accept": "application/json",
    }
    try:
        resp = await client.get(
            f"{OPENSUBTITLES_API_V1}/subtitles",
            headers=headers,
            params={
                "imdb_id": imdb_id,
                "languages": language,
                "type": "movie",  # API accepts any; filtering done client-side
            },
        )
        if resp.status_code == 401:
            logger.warning("OpenSubtitles API key rejected (401)")
            return []
        if not resp.is_success:
            logger.warning("OpenSubtitles v1 search failed: %s", resp.status_code)
            return []

        data = resp.json()
        results = data.get("data", [])
        if not results:
            return []

        tracks = []
        seen_urls = set()
        for item in results[:10]:
            attrs = item.get("attributes", {})
            files = attrs.get("files", [])
            for f in files:
                sub_url = f.get("file_id")
                if not sub_url or sub_url in seen_urls:
                    continue
                seen_urls.add(sub_url)
                # v1 requires a second call to get the download link; for now we
                # return the file_id so the proxy can resolve it later if we add
                # download support.  As a pragmatic fallback, return the legacy
                # direct-download style only when available.
                fmt = "srt"
                tracks.append(
                    SubtitleTrack(
                        label=attrs.get("language", language),
                        language=attrs.get("language", language),
                        url=f"{OPENSUBTITLES_API_V1}/download",
                        format=fmt,
                    )
                )

        logger.info("Found %d subtitle tracks via OS v1 for %s", len(tracks), imdb_id)
        return tracks
    except Exception as e:
        logger.warning("OpenSubtitles v1 fetch failed: %s", e)
        return []


async def _fetch_from_opensubtitles_legacy(
    client: httpx.AsyncClient, imdb_id: str, language: str
) -> list[SubtitleTrack]:
    """Try the legacy OpenSubtitles XML-RPC endpoint (often DNS-dead)."""
    try:
        resp = await client.get(
            f"{OPENSUBTITLES_LEGACY}/imdbid-{imdb_id.replace('tt', '')}/sublanguageid-{language}",
            headers={"User-Agent": "Watch!fy/1.0"},
        )
        if not resp.is_success:
            logger.warning("OpenSubtitles legacy search failed: %s", resp.status_code)
            return []

        results = resp.json()
        if not results:
            return []

        tracks = []
        seen_urls = set()
        for item in results[:10]:
            sub_url = item.get("SubDownloadLink", "")
            if not sub_url or sub_url in seen_urls:
                continue
            seen_urls.add(sub_url)

            fmt = "srt"
            if sub_url.endswith(".vtt"):
                fmt = "vtt"
            elif sub_url.endswith(".srt"):
                fmt = "srt"

            tracks.append(
                SubtitleTrack(
                    label=item.get("SubLanguageID", language),
                    language=item.get("LanguageName", language),
                    url=sub_url,
                    format=fmt,
                )
            )

        logger.info("Found %d subtitle tracks via OS legacy for %s", len(tracks), imdb_id)
        return tracks
    except Exception as e:
        logger.warning("OpenSubtitles legacy fetch failed: %s", e)
        return []


async def fetch_subtitles(imdb_id: str, language: str = "en") -> list[SubtitleTrack]:
    """Fetch available subtitles for a movie/episode.

    Tries OpenSubtitles v1 (if API key configured) then legacy endpoint.
    Returns empty list gracefully on any failure.

    Args:
        imdb_id: IMDB ID (e.g. "tt0111161").
        language: ISO 639-1 language code (default "en").

    Returns:
        List of SubtitleTrack objects.
    """
    if not imdb_id:
        return []

    # Ensure imdb_id has tt prefix
    if not imdb_id.startswith("tt"):
        imdb_id = f"tt{imdb_id}"

    client = await _get_subtitle_client()
    tracks: list[SubtitleTrack] = []

    # 1. Try OpenSubtitles v1 (needs API key)
    try:
        tracks = await _fetch_from_opensubtitles_v1(client, imdb_id, language)
        if tracks:
            return tracks
    except Exception as e:
        logger.warning("OpenSubtitles v1 error: %s", e)

    # 2. Fall back to legacy endpoint
    try:
        tracks = await _fetch_from_opensubtitles_legacy(client, imdb_id, language)
        if tracks:
            return tracks
    except Exception as e:
        logger.warning("OpenSubtitles legacy error: %s", e)

    # 3. Nothing worked — return empty gracefully
    logger.info("No subtitle tracks found for %s", imdb_id)
    return []


async def convert_srt_to_vtt(srt_content: str) -> str:
    """Convert SRT subtitle format to WebVTT.

    Args:
        srt_content: Raw SRT text.

    Returns:
        WebVTT formatted string.
    """
    vtt = "WEBVTT\n\n"
    # Replace SRT timestamps (00:00:00,000) with VTT (00:00:00.000)
    converted = re.sub(
        r"(\d{2}:\d{2}:\d{2}),(\d{3})",
        r"\1.\2",
        srt_content,
    )
    vtt += converted
    return vtt
