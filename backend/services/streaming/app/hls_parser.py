"""HLS manifest parser — extracts variant streams with quality metadata."""
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HLSVariant:
    """A single variant stream from an HLS manifest."""

    url: str
    bandwidth: int  # bits per second
    resolution: str  # e.g. "1920x1080"
    resolution_height: int  # e.g. 1080
    codecs: str
    quality_label: str  # e.g. "1080p", "720p"


def parse_master_manifest(manifest_text: str, base_url: str) -> list[HLSVariant]:
    """Parse an HLS master manifest and return all variant streams.

    Args:
        manifest_text: Raw m3u8 manifest text.
        base_url: Base URL for resolving relative segment paths.

    Returns:
        List of HLSVariant sorted by quality (highest first).
    """
    variants: list[HLSVariant] = []
    lines = manifest_text.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for #EXT-X-STREAM-INF tags
        if line.startswith("#EXT-X-STREAM-INF"):
            # Parse attributes from STREAM-INF line
            bandwidth = _extract_attribute(line, "BANDWIDTH")
            resolution = _extract_attribute(line, "RESOLUTION")
            codecs = _extract_attribute(line, "CODECS")

            # Next line should be the variant URL
            if i + 1 < len(lines):
                variant_url = lines[i + 1].strip()
                if variant_url and not variant_url.startswith("#"):
                    # Resolve relative URLs
                    if not variant_url.startswith("http"):
                        variant_url = _resolve_url(base_url, variant_url)

                    height = _resolution_height(resolution)
                    quality_label = _quality_label(height, bandwidth)

                    variants.append(
                        HLSVariant(
                            url=variant_url,
                            bandwidth=int(bandwidth) if bandwidth else 0,
                            resolution=resolution,
                            resolution_height=height,
                            codecs=codecs,
                            quality_label=quality_label,
                        )
                    )
                    i += 2
                    continue
        i += 1

    # Sort by quality (highest first)
    variants.sort(key=lambda v: (v.resolution_height, v.bandwidth), reverse=True)
    return variants


def _extract_attribute(line: str, attr: str) -> str:
    """Extract an attribute value from an HLS tag line."""
    # Matches ATTR=VALUE or ATTR="VALUE"
    pattern = rf'{attr}=("?)([^",\s]+)\1'
    match = re.search(pattern, line, re.IGNORECASE)
    if match:
        return match.group(2)
    return ""


def _resolution_height(resolution: str) -> int:
    """Extract height from a resolution string like '1920x1080'."""
    if not resolution:
        return 0
    match = re.search(r"(\d+)x(\d+)", resolution)
    if match:
        return int(match.group(2))
    return 0


def _quality_label(height: int, bandwidth: int) -> str:
    """Generate a human-readable quality label from resolution and bandwidth."""
    if height >= 2160:
        return "4K"
    if height >= 1080:
        return "1080p"
    if height >= 720:
        return "720p"
    if height >= 480:
        return "480p"
    if height >= 360:
        return "360p"
    if height > 0:
        return f"{height}p"
    # Fallback to bandwidth-based labeling
    if bandwidth >= 5_000_000:
        return "1080p"
    if bandwidth >= 3_000_000:
        return "720p"
    if bandwidth >= 1_500_000:
        return "480p"
    return "Auto"


def _resolve_url(base_url: str, relative_url: str) -> str:
    """Resolve a relative URL against a base URL."""
    if relative_url.startswith("http"):
        return relative_url
    # Strip filename from base_url to get directory
    base_dir = base_url.rsplit("/", 1)[0] + "/"
    return base_dir + relative_url


def get_default_variant(variants: list[HLSVariant]) -> Optional[HLSVariant]:
    """Return the highest quality variant, or None if list is empty."""
    return variants[0] if variants else None


def get_variant_by_height(variants: list[HLSVariant], height: int) -> Optional[HLSVariant]:
    """Find the closest matching variant for a given height."""
    if not variants:
        return None
    # Find exact or next lower match
    for v in variants:
        if v.resolution_height <= height:
            return v
    return variants[-1]
