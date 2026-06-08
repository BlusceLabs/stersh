"""Subtitle fetching and format conversion for watchfy streaming backend.

Sources tried in order:
  1. OpenSubtitles REST API v1 (requires API key in env)
  2. Subdl.com (free, no key needed)
  3. Fallback: empty list (player proceeds without subtitles)

Subtitle files are always served through /api/subtitles/proxy which:
  - Converts SRT → WebVTT on the fly
  - Adds CORS headers so HLS.js / video players can load them
  - Caches valid responses for 24 h
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_OPENSUBTITLES_API = "https://api.opensubtitles.com/api/v1"
_SUBDL_API = "https://api.subdl.com/api/v1/subtitles"
_OPENSUBTITLES_KEY = os.environ.get("OPENSUBTITLES_API_KEY", "")
_SUBDL_KEY = os.environ.get("SUBDL_API_KEY", "")

# ISO 639-1 → human label
_LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "sv": "Swedish",
    "tr": "Turkish",
}


@dataclass
class SubtitleTrack:
    label: str
    language: str
    url: str
    format: str = "vtt"


async def fetch_subtitles(
    imdb_id: str,
    language: str = "en",
    season: int | None = None,
    episode: int | None = None,
) -> list[SubtitleTrack]:
    """Fetch subtitle tracks, trying multiple providers.

    Returns a list of SubtitleTrack objects with proxied URLs.
    """
    tracks: list[SubtitleTrack] = []

    # Provider 1: OpenSubtitles
    if _OPENSUBTITLES_KEY:
        try:
            tracks = await _fetch_opensubtitles(imdb_id, language, season, episode)
        except Exception as exc:
            logger.warning('"opensubtitles_error":{"err":"%s"}', exc)

    # Provider 2: Subdl (fallback)
    if not tracks:
        try:
            tracks = await _fetch_subdl(imdb_id, language, season, episode)
        except Exception as exc:
            logger.warning('"subdl_error":{"err":"%s"}', exc)

    if not tracks:
        logger.info('"no_subtitles_found":{"imdb":"%s","lang":"%s"}', imdb_id, language)

    return tracks


async def _fetch_opensubtitles(
    imdb_id: str,
    language: str,
    season: int | None,
    episode: int | None,
) -> list[SubtitleTrack]:
    params: dict = {
        "imdb_id": imdb_id.lstrip("tt"),
        "languages": language,
        "order_by": "download_count",
        "order_direction": "desc",
    }
    if season is not None:
        params["season_number"] = season
    if episode is not None:
        params["episode_number"] = episode

    async with httpx.AsyncClient(
        timeout=10.0,
        headers={
            "Api-Key": _OPENSUBTITLES_KEY,
            "Content-Type": "application/json",
            "User-Agent": "watchfy/2.0",
        },
    ) as client:
        resp = await client.get(f"{_OPENSUBTITLES_API}/subtitles", params=params)

    if not resp.is_success:
        logger.warning('"opensubtitles_http_error":{"status":%d}', resp.status_code)
        return []

    tracks: list[SubtitleTrack] = []
    for item in (resp.json().get("data") or [])[:8]:
        attrs = item.get("attributes", {})
        files = attrs.get("files") or []
        if not files:
            continue
        lang = attrs.get("language", language)
        label = _LANGUAGE_LABELS.get(lang, lang.upper())
        hearing_impaired = attrs.get("hearing_impaired", False)
        if hearing_impaired:
            label += " [HI]"
        file_id = files[0].get("file_id", "")
        # OpenSubtitles requires a download token — proxy fetches via their download API
        proxy_url = f"/api/subtitles/proxy?provider=opensubtitles&file_id={file_id}"
        tracks.append(SubtitleTrack(label=label, language=lang, url=proxy_url))
    return tracks


async def _fetch_subdl(
    imdb_id: str,
    language: str,
    season: int | None,
    episode: int | None,
) -> list[SubtitleTrack]:
    params: dict = {
        "api_key": _SUBDL_KEY,
        "imdb_id": imdb_id,
        "languages": language.upper(),
        "subs_per_page": 5,
        "type": "movie" if season is None else "tv",
    }
    if season is not None:
        params["season_number"] = season
    if episode is not None:
        params["episode_number"] = episode

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(_SUBDL_API, params=params)

    if not resp.is_success:
        return []

    tracks: list[SubtitleTrack] = []
    for item in (resp.json().get("subtitles") or [])[:5]:
        lang = (item.get("language") or language).lower()
        label = _LANGUAGE_LABELS.get(lang, lang.upper())
        url = item.get("url") or item.get("download_url", "")
        if not url:
            continue
        if not url.startswith("http"):
            url = f"https://dl.subdl.com{url}"
        proxy_url = f"/api/subtitles/proxy?url={url}"
        tracks.append(SubtitleTrack(label=label, language=lang, url=proxy_url))
    return tracks


# ── Format conversion ──────────────────────────────────────────────────────────

def convert_srt_to_vtt(srt: str) -> str:
    """Convert SubRip (.srt) subtitle text to WebVTT (.vtt) format.

    Handles:
      - Comma → dot in timecodes (00:00:01,000 → 00:00:01.000)
      - HTML tags already present in SRT (<i>, <b>, <u>) → kept as-is
      - Numeric cue indices → stripped
      - Windows CRLF → LF
    """
    text = srt.replace("\r\n", "\n").replace("\r", "\n")

    # Replace SRT comma-decimal separator in timecodes
    text = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", text)

    lines = text.split("\n")
    vtt_lines = ["WEBVTT", ""]
    skip_index = False

    for line in lines:
        stripped = line.strip()
        # Strip bare numeric cue indices
        if re.fullmatch(r"\d+", stripped):
            skip_index = True
            continue
        if skip_index and stripped == "":
            skip_index = False
            vtt_lines.append("")
            continue
        skip_index = False
        vtt_lines.append(line)

    return "\n".join(vtt_lines)


def convert_ass_to_vtt(ass: str) -> str:
    """Best-effort conversion of ASS/SSA subtitles to WebVTT.

    Strips formatting codes; does not preserve karaoke or complex styles.
    """
    vtt_lines = ["WEBVTT", ""]
    in_events = False
    format_fields: list[str] = []

    for line in ass.splitlines():
        stripped = line.strip()
        if stripped == "[Events]":
            in_events = True
            continue
        if stripped.startswith("[") and in_events:
            break
        if not in_events:
            continue
        if stripped.startswith("Format:"):
            format_fields = [f.strip() for f in stripped[len("Format:"):].split(",")]
            continue
        if not stripped.startswith("Dialogue:"):
            continue

        parts = stripped[len("Dialogue:"):].split(",", len(format_fields) - 1)
        if len(parts) < len(format_fields):
            continue
        row = dict(zip(format_fields, parts))

        start = _ass_time_to_vtt(row.get("Start", "0:00:00.00"))
        end = _ass_time_to_vtt(row.get("End", "0:00:00.00"))
        text = row.get("Text", "")
        # Strip ASS override tags {…}
        text = re.sub(r"\{[^}]*\}", "", text)
        text = text.replace(r"\N", "\n").replace(r"\n", "\n").strip()
        if not text:
            continue
        vtt_lines += [f"{start} --> {end}", text, ""]

    return "\n".join(vtt_lines)


def _ass_time_to_vtt(t: str) -> str:
    """Convert ASS time (H:MM:SS.cs) to WebVTT (HH:MM:SS.mmm)."""
    try:
        h, m, rest = t.split(":")
        s, cs = rest.split(".")
        ms = int(cs) * 10
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}.{ms:03d}"
    except Exception:
        return "00:00:00.000"