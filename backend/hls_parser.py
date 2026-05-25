"""HLS master manifest parser for watchfy streaming backend.

Parses #EXT-X-STREAM-INF entries from a master .m3u8 playlist into
typed HLSVariant objects with quality labels and absolute URLs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin


@dataclass
class HLSVariant:
    url: str
    bandwidth: int
    resolution_height: int
    quality_label: str
    codecs: str = ""
    frame_rate: float = 0.0
    audio_group: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "bandwidth": self.bandwidth,
            "resolution": self.resolution_height,
            "quality": self.quality_label,
            "codecs": self.codecs,
            "frameRate": self.frame_rate,
        }


@dataclass
class HLSAudioTrack:
    group_id: str
    language: str
    name: str
    uri: str | None
    default: bool = False
    autoselect: bool = False


def parse_master_manifest(text: str, base_url: str) -> list[HLSVariant]:
    """Parse a master HLS manifest and return quality variants sorted highest first.

    Handles both absolute and relative variant URIs.
    Deduplicates identical resolution/bandwidth pairs, keeping the first.
    """
    variants: list[HLSVariant] = []
    seen: set[tuple[int, int]] = set()
    lines = text.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXT-X-STREAM-INF:"):
            attrs = _parse_attribute_list(line[len("#EXT-X-STREAM-INF:"):])
            bandwidth = int(attrs.get("BANDWIDTH", "0") or "0")
            resolution = attrs.get("RESOLUTION", "")
            codecs = attrs.get("CODECS", "")
            frame_rate_str = attrs.get("FRAME-RATE", "0")
            audio_group = attrs.get("AUDIO", "")

            height = 0
            if "x" in resolution:
                try:
                    height = int(resolution.split("x", 1)[1])
                except (ValueError, IndexError):
                    pass

            frame_rate = 0.0
            try:
                frame_rate = float(frame_rate_str)
            except ValueError:
                pass

            quality_label = _height_to_label(height) if height else _bandwidth_to_label(bandwidth)

            # Advance to URI line (skip blank / comment lines)
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                j += 1

            if j < len(lines):
                uri = lines[j].strip()
                if uri:
                    if not uri.startswith("http"):
                        uri = urljoin(base_url, uri)
                    key = (height, bandwidth)
                    if key not in seen:
                        seen.add(key)
                        variants.append(
                            HLSVariant(
                                url=uri,
                                bandwidth=bandwidth,
                                resolution_height=height,
                                quality_label=quality_label,
                                codecs=codecs,
                                frame_rate=frame_rate,
                                audio_group=audio_group,
                            )
                        )
                i = j + 1
                continue
        i += 1

    # Highest resolution / bandwidth first
    variants.sort(
        key=lambda v: (v.resolution_height or _bandwidth_sort_key(v.bandwidth)),
        reverse=True,
    )
    return variants


def parse_audio_tracks(text: str, base_url: str) -> list[HLSAudioTrack]:
    """Parse #EXT-X-MEDIA TYPE=AUDIO entries from a master manifest."""
    tracks: list[HLSAudioTrack] = []
    for line in text.splitlines():
        if not line.startswith("#EXT-X-MEDIA:"):
            continue
        attrs = _parse_attribute_list(line[len("#EXT-X-MEDIA:"):])
        if attrs.get("TYPE") != "AUDIO":
            continue
        uri = attrs.get("URI")
        if uri and not uri.startswith("http"):
            uri = urljoin(base_url, uri)
        tracks.append(
            HLSAudioTrack(
                group_id=attrs.get("GROUP-ID", ""),
                language=attrs.get("LANGUAGE", "und"),
                name=attrs.get("NAME", "Audio"),
                uri=uri,
                default=attrs.get("DEFAULT", "NO").upper() == "YES",
                autoselect=attrs.get("AUTOSELECT", "NO").upper() == "YES",
            )
        )
    return tracks


# ── Internal helpers ───────────────────────────────────────────────────────────

def _parse_attribute_list(attr_str: str) -> dict[str, str]:
    """Parse HLS attribute-list format: KEY=VALUE, KEY="VALUE", ..."""
    result: dict[str, str] = {}
    for match in re.finditer(
        r'([A-Z0-9_-]+)=(?:"([^"]*)"|([\w@.,\-/]*))',
        attr_str,
    ):
        key = match.group(1)
        value = match.group(2) if match.group(2) is not None else match.group(3)
        result[key] = value
    return result


def _height_to_label(height: int) -> str:
    if height >= 2160:
        return "4K"
    if height >= 1440:
        return "1440p"
    if height >= 1080:
        return "1080p"
    if height >= 720:
        return "720p"
    if height >= 480:
        return "480p"
    if height >= 360:
        return "360p"
    if height >= 240:
        return "240p"
    return f"{height}p"


def _bandwidth_to_label(bandwidth: int) -> str:
    mbps = bandwidth / 1_000_000
    if mbps >= 15:
        return "4K"
    if mbps >= 8:
        return "1080p"
    if mbps >= 4:
        return "720p"
    if mbps >= 2:
        return "480p"
    if mbps >= 0.8:
        return "360p"
    return "Auto"


def _bandwidth_sort_key(bandwidth: int) -> int:
    """Approximate height from bandwidth for sorting when resolution is unknown."""
    mbps = bandwidth / 1_000_000
    if mbps >= 15:
        return 2160
    if mbps >= 8:
        return 1080
    if mbps >= 4:
        return 720
    if mbps >= 2:
        return 480
    if mbps >= 0.8:
        return 360
    return 240