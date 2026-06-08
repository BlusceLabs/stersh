"""HLS master manifest parser for watchfy streaming backend.

Parses a master .m3u8 playlist into typed dataclasses with quality
labels, absolute URIs, and track metadata.

Preferred entry point
---------------------
``parse_manifest(text, base_url) -> HLSManifest``

Back-compat helpers (signatures unchanged)
------------------------------------------
``parse_master_manifest(text, base_url) -> list[HLSVariant]``
``parse_audio_tracks(text, base_url)    -> list[HLSAudioTrack]``
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

__all__ = [
    "HLSVariant",
    "HLSAudioTrack",
    "HLSSubtitleTrack",
    "HLSManifest",
    "parse_manifest",
    "parse_master_manifest",
    "parse_audio_tracks",
    "parse_subtitle_tracks",
]

log = logging.getLogger(__name__)

# ── Quality tier tables (single source of truth) ──────────────────────────────

# (min_height_px, label)
_HEIGHT_TIERS: tuple[tuple[int, str], ...] = (
    (2160, "4K"),
    (1440, "1440p"),
    (1080, "1080p"),
    ( 720, "720p"),
    ( 480, "480p"),
    ( 360, "360p"),
    ( 240, "240p"),
)

# (min_bps, label, height_proxy) — for bandwidth-only variants and sort fallback
_BANDWIDTH_TIERS: tuple[tuple[int, str, int], ...] = (
    (15_000_000, "4K",    2160),
    ( 8_000_000, "1080p", 1080),
    ( 4_000_000, "720p",   720),
    ( 2_000_000, "480p",   480),
    (   800_000, "360p",   360),
)


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class HLSVariant:
    """A single rendition described by an ``#EXT-X-STREAM-INF`` tag."""

    url: str
    bandwidth: int
    resolution_height: int
    quality_label: str
    codecs: str = ""
    frame_rate: float = 0.0
    audio_group: str = ""
    subtitle_group: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "bandwidth": self.bandwidth,
            "resolution": self.resolution_height,
            "quality": self.quality_label,
            "codecs": self.codecs,
            "frameRate": self.frame_rate,
            "audioGroup": self.audio_group,
            "subtitleGroup": self.subtitle_group,
        }


@dataclass
class HLSAudioTrack:
    """An ``#EXT-X-MEDIA TYPE=AUDIO`` rendition."""

    group_id: str
    language: str
    name: str
    uri: str | None
    default: bool = False
    autoselect: bool = False

    def to_dict(self) -> dict:
        return {
            "groupId": self.group_id,
            "language": self.language,
            "name": self.name,
            "uri": self.uri,
            "default": self.default,
            "autoselect": self.autoselect,
        }


@dataclass
class HLSSubtitleTrack:
    """An ``#EXT-X-MEDIA TYPE=SUBTITLES`` rendition."""

    group_id: str
    language: str
    name: str
    uri: str | None
    default: bool = False
    autoselect: bool = False
    forced: bool = False

    def to_dict(self) -> dict:
        return {
            "groupId": self.group_id,
            "language": self.language,
            "name": self.name,
            "uri": self.uri,
            "default": self.default,
            "autoselect": self.autoselect,
            "forced": self.forced,
        }


@dataclass
class HLSManifest:
    """Fully-parsed master HLS manifest."""

    variants: list[HLSVariant] = field(default_factory=list)
    audio_tracks: list[HLSAudioTrack] = field(default_factory=list)
    subtitle_tracks: list[HLSSubtitleTrack] = field(default_factory=list)
    version: int = 0

    # ── Convenience accessors ──────────────────────────────────────────────

    @property
    def best(self) -> HLSVariant | None:
        """Highest-quality variant, or ``None`` if the manifest is empty."""
        return self.variants[0] if self.variants else None

    def variants_by_quality(self) -> dict[str, HLSVariant]:
        """``{quality_label: variant}``, first-wins per label."""
        out: dict[str, HLSVariant] = {}
        for v in self.variants:
            out.setdefault(v.quality_label, v)
        return out

    def audio_for_group(self, group_id: str) -> list[HLSAudioTrack]:
        """All audio tracks belonging to *group_id*."""
        return [t for t in self.audio_tracks if t.group_id == group_id]

    def subtitles_for_group(self, group_id: str) -> list[HLSSubtitleTrack]:
        """All subtitle tracks belonging to *group_id*."""
        return [t for t in self.subtitle_tracks if t.group_id == group_id]

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "variants": [v.to_dict() for v in self.variants],
            "audioTracks": [a.to_dict() for a in self.audio_tracks],
            "subtitleTracks": [s.to_dict() for s in self.subtitle_tracks],
        }


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_manifest(text: str, base_url: str) -> HLSManifest:
    """Parse a master HLS manifest and return a fully-typed :class:`HLSManifest`.

    Parameters
    ----------
    text:
        Raw ``.m3u8`` content.
    base_url:
        URL of the manifest, used to absolutise relative URIs.
    """
    return HLSManifest(
        variants=parse_master_manifest(text, base_url),
        audio_tracks=parse_audio_tracks(text, base_url),
        subtitle_tracks=parse_subtitle_tracks(text, base_url),
        version=_parse_version(text),
    )


def parse_master_manifest(text: str, base_url: str) -> list[HLSVariant]:
    """Parse a master HLS manifest and return quality variants sorted highest first.

    * Handles absolute and relative variant URIs.
    * Deduplicates identical ``(resolution_height, bandwidth)`` pairs,
      keeping the first occurrence.
    * Skips blank lines and comment lines between the tag and the URI.
    """
    variants: list[HLSVariant] = []
    seen: set[tuple[int, int]] = set()
    lines = text.splitlines()
    n = len(lines)
    i = 0

    while i < n:
        line = lines[i].strip()
        if not line.startswith("#EXT-X-STREAM-INF:"):
            i += 1
            continue

        attrs = _parse_attribute_list(line[len("#EXT-X-STREAM-INF:"):])
        bandwidth = _safe_int(attrs.get("BANDWIDTH", ""), label="BANDWIDTH", context=line)
        height    = _parse_height(attrs.get("RESOLUTION", ""))
        frame_rate = _safe_float(attrs.get("FRAME-RATE", ""))
        quality_label = (
            _height_to_label(height) if height else _bandwidth_to_label(bandwidth)
        )

        # Scan forward past blanks / inline comments to find the URI line.
        j = i + 1
        while j < n and _is_blank_or_comment(lines[j]):
            j += 1

        if j >= n or not lines[j].strip():
            log.warning("Missing URI after #EXT-X-STREAM-INF at line %d; skipping.", i)
            i = j
            continue

        uri = _make_absolute(lines[j].strip(), base_url)
        key = (height, bandwidth)

        if key not in seen:
            seen.add(key)
            variants.append(
                HLSVariant(
                    url=uri,
                    bandwidth=bandwidth,
                    resolution_height=height,
                    quality_label=quality_label,
                    codecs=attrs.get("CODECS", ""),
                    frame_rate=frame_rate,
                    audio_group=attrs.get("AUDIO", ""),
                    subtitle_group=attrs.get("SUBTITLES", ""),
                )
            )
        else:
            log.debug(
                "Skipping duplicate variant (height=%d, bw=%d) %s",
                height, bandwidth, uri,
            )

        i = j + 1

    variants.sort(
        key=lambda v: v.resolution_height or _bandwidth_sort_key(v.bandwidth),
        reverse=True,
    )
    return variants


def parse_audio_tracks(text: str, base_url: str) -> list[HLSAudioTrack]:
    """Parse ``#EXT-X-MEDIA TYPE=AUDIO`` entries from a master manifest."""
    return [
        HLSAudioTrack(
            group_id=attrs.get("GROUP-ID", ""),
            language=attrs.get("LANGUAGE", "und"),
            name=attrs.get("NAME", "Audio"),
            uri=_resolve_optional_uri(attrs.get("URI"), base_url),
            default=_yes(attrs.get("DEFAULT", "")),
            autoselect=_yes(attrs.get("AUTOSELECT", "")),
        )
        for attrs in _iter_media_attrs(text, "AUDIO")
    ]


def parse_subtitle_tracks(text: str, base_url: str) -> list[HLSSubtitleTrack]:
    """Parse ``#EXT-X-MEDIA TYPE=SUBTITLES`` entries from a master manifest."""
    return [
        HLSSubtitleTrack(
            group_id=attrs.get("GROUP-ID", ""),
            language=attrs.get("LANGUAGE", "und"),
            name=attrs.get("NAME", "Subtitles"),
            uri=_resolve_optional_uri(attrs.get("URI"), base_url),
            default=_yes(attrs.get("DEFAULT", "")),
            autoselect=_yes(attrs.get("AUTOSELECT", "")),
            forced=_yes(attrs.get("FORCED", "")),
        )
        for attrs in _iter_media_attrs(text, "SUBTITLES")
    ]


# ── Internal helpers ───────────────────────────────────────────────────────────

# Matches KEY="value" and KEY=barevalue in an HLS attribute-list.
# Unquoted pattern [^,\s"]* handles integers, floats, resolutions (1920x1080),
# hex sequences (0x1F4), and enumerated strings without over-matching.
_ATTR_RE = re.compile(r'([A-Z0-9][A-Z0-9_-]*)=(?:"([^"]*)"|([^,\s"]*))')


def _parse_attribute_list(attr_str: str) -> dict[str, str]:
    """Parse an HLS attribute-list string into a plain ``{key: value}`` dict."""
    return {
        m.group(1): (m.group(2) if m.group(2) is not None else (m.group(3) or ""))
        for m in _ATTR_RE.finditer(attr_str)
    }


def _parse_version(text: str) -> int:
    """Extract the ``#EXT-X-VERSION`` integer; returns 0 if absent or malformed."""
    for line in text.splitlines():
        if line.startswith("#EXT-X-VERSION:"):
            return _safe_int(line.split(":", 1)[1].strip(), label="#EXT-X-VERSION")
    return 0


def _parse_height(resolution: str) -> int:
    """Extract pixel height from a ``WIDTHxHEIGHT`` string; returns 0 on failure."""
    if "x" in resolution:
        try:
            return int(resolution.split("x", 1)[1])
        except (ValueError, IndexError):
            pass
    return 0


def _safe_int(value: str, *, label: str = "", context: str = "") -> int:
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        log.warning(
            "Non-integer %s value %r%s",
            label, value, f" in: {context}" if context else "",
        )
        return 0


def _safe_float(value: str, *, default: float = 0.0) -> float:
    try:
        return float(value) if value else default
    except ValueError:
        return default


def _yes(value: str) -> bool:
    return value.strip().upper() == "YES"


def _is_blank_or_comment(line: str) -> bool:
    s = line.strip()
    return not s or s.startswith("#")


def _make_absolute(uri: str, base_url: str) -> str:
    """Return an absolute URL, resolving *uri* against *base_url* when it has no scheme."""
    return uri if urlparse(uri).scheme else urljoin(base_url, uri)


def _resolve_optional_uri(uri: str | None, base_url: str) -> str | None:
    return _make_absolute(uri, base_url) if uri else None


def _iter_media_attrs(text: str, media_type: str) -> list[dict[str, str]]:
    """Return attribute dicts for all ``#EXT-X-MEDIA`` lines matching *media_type*."""
    out = []
    for line in text.splitlines():
        if line.startswith("#EXT-X-MEDIA:"):
            attrs = _parse_attribute_list(line[len("#EXT-X-MEDIA:"):])
            if attrs.get("TYPE") == media_type:
                out.append(attrs)
    return out


def _height_to_label(height: int) -> str:
    for min_h, label in _HEIGHT_TIERS:
        if height >= min_h:
            return label
    return f"{height}p"


def _bandwidth_to_label(bandwidth: int) -> str:
    for min_bps, label, _ in _BANDWIDTH_TIERS:
        if bandwidth >= min_bps:
            return label
    return "Auto"


def _bandwidth_sort_key(bandwidth: int) -> int:
    """Map bandwidth to an approximate pixel height for sort stability."""
    for min_bps, _, proxy_h in _BANDWIDTH_TIERS:
        if bandwidth >= min_bps:
            return proxy_h
    return 0