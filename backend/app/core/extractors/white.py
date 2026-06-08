"""Watchfy streaming extraction backend for 111movies.net (codename "white").

Entry points
------------
extract_hls_from_white(...)     -> ExtractionResult | None
extract_sources_legacy(...)     -> tuple[list[dict] | None, str]  (compat shim)
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Final, Literal

from curl_cffi.requests import AsyncSession as CurlSession

# Shared HLS parser — single source of truth for quality tiers and manifest parsing.
# Eliminates the private duplicates (_parse_ext_x_stream_inf, _height_to_label, etc.)
# that previously lived in this module.
from app.core.hls import HLSVariant, parse_master_manifest as _parse_hls_manifest

logger = logging.getLogger(__name__)

ONETOONE_BASE: Final[str] = "https://111movies.net"

# String literal union for ExtractionResult.method.
ExtractionMethod = Literal["network", "dom_probe", "unknown"]

# ── DOM probe script ──────────────────────────────────────────────────────────
# Injected into the live page to pull stream URLs from every known player API
# (HLS.js, video.js, JW Player, Plyr, Flowplayer, FastStream, …) and by
# scanning inline <script> blocks for bare .m3u8 URLs.
_DOM_PROBE_SCRIPT: Final[str] = """
(() => {
    const res = { urls: [], downloads: [] };

    for (const v of document.querySelectorAll('video')) {
        const s = v.src || v.currentSrc || '';
        if (s && s.startsWith('http')) res.urls.push(s);
        for (const src of v.querySelectorAll('source')) {
            if (src.src) res.urls.push(src.src);
        }
    }

    if (window.Hls) {
        try {
            const instances = window.Hls._instances || [];
            for (const inst of instances) {
                if (inst.url) res.urls.push(inst.url);
            }
        } catch(e) {}
    }

    try {
        if (window.videojs && window.videojs.getPlayers) {
            const players = window.videojs.getPlayers();
            for (const id in players) {
                const p = players[id];
                const u = (typeof p.src === 'function' ? p.src() : p.src)
                        || (typeof p.currentSrc === 'function' ? p.currentSrc() : '');
                if (u) res.urls.push(u);
            }
        }
    } catch(e) {}

    try {
        if (window.jwplayer) {
            const jw = window.jwplayer();
            if (jw && jw.getPlaylistItem) {
                const item = jw.getPlaylistItem();
                if (item && item.file) res.urls.push(item.file);
                const sources = item && item.sources || [];
                for (const s of sources) if (s.file) res.urls.push(s.file);
            }
        }
    } catch(e) {}

    try {
        if (window.plyr || window.Plyr) {
            const p = window.plyr || window.Plyr;
            if (p.source && p.source.sources) {
                for (const s of p.source.sources) if (s.src) res.urls.push(s.src);
            }
        }
    } catch(e) {}

    try {
        if (window.flowplayer) {
            const fp = window.flowplayer(0);
            if (fp && fp.conf && fp.conf.clip) {
                const sources = fp.conf.clip.sources || [];
                for (const s of sources) if (s.src) res.urls.push(s.src);
            }
        }
    } catch(e) {}

    try {
        const fsc = window.FastStreamClient;
        if (fsc) {
            if (fsc.source && fsc.source.url) res.urls.push(fsc.source.url);
            if (fsc.player) {
                const s = fsc.player.getSource && fsc.player.getSource();
                if (s && s.url) res.urls.push(s.url);
                const v = fsc.player.getVideo && fsc.player.getVideo();
                if (v && (v.src || v.currentSrc)) res.urls.push(v.src || v.currentSrc);
            }
        }
    } catch(e) {}

    for (const key of ['player', 'hls', 'fluidPlayer', 'Clappr', 'Playerjs', 'FastStreamClient', 'VideoSource']) {
        try {
            const obj = window[key];
            if (!obj) continue;
            const u = (typeof obj.src === 'string' && obj.src)
                    || (typeof obj.currentSrc === 'string' && obj.currentSrc)
                    || (obj.source && obj.source.url)
                    || (obj.config && obj.config.src)
                    || (obj.url)
                    || (typeof obj.getConfig === 'function' && obj.getConfig().file)
                    || (obj._sourceUrl);
            if (u) res.urls.push(u);
        } catch(e) {}
    }

    const pat = /https?:\\/\\/[^\\s"'`\\\\]+\\.m3u8[^\\s"'`\\\\]*/g;
    for (const sc of document.querySelectorAll('script:not([src])')) {
        const matches = sc.textContent.match(pat) || [];
        res.urls.push(...matches);
    }

    for (const a of document.querySelectorAll('a[href]')) {
        const h = a.href || '';
        if (h.includes('.mp4') || h.toLowerCase().includes('download')) {
            res.downloads.push(h);
        }
    }

    res.urls      = [...new Set(res.urls.filter(Boolean))];
    res.downloads = [...new Set(res.downloads.filter(Boolean))];
    return res;
})()
"""


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class StreamSource:
    url: str
    quality: str = "Auto"
    resolution: int = 0
    bandwidth: int = 0
    source_type: Literal["hls", "mp4", "unknown"] = "hls"

    @classmethod
    def from_hls_variant(cls, v: HLSVariant) -> StreamSource:
        """Adapt a :class:`~.hls_manifest.HLSVariant` to a :class:`StreamSource`."""
        return cls(
            url=v.url,
            quality=v.quality_label,
            resolution=v.resolution_height,
            bandwidth=v.bandwidth,
            source_type="hls",
        )

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "quality": self.quality,
            "resolution": self.resolution,
            "bandwidth": self.bandwidth,
            "type": self.source_type,
        }


@dataclass
class ExtractionResult:
    sources: list[StreamSource] = field(default_factory=list)
    downloads: list[StreamSource] = field(default_factory=list)
    method: ExtractionMethod = "unknown"
    raw_hls_url: str = ""

    def best(self) -> StreamSource | None:
        return self.sources[0] if self.sources else None

    def to_legacy_list(self) -> list[dict]:
        return [s.to_dict() for s in self.sources] + [s.to_dict() for s in self.downloads]

    def to_dict(self) -> dict:
        return {
            "sources": [s.to_dict() for s in self.sources],
            "downloads": [s.to_dict() for s in self.downloads],
            "method": self.method,
            "master_url": self.raw_hls_url or "",
        }


# ── Compatibility stubs ────────────────────────────────────────────────────────

async def close_pooled_session() -> None:
    """No-op retained for API compatibility; session pooling was removed."""


async def shutdown_browser() -> None:
    """No-op retained for router compatibility; browser lifecycle is now per-request."""


# ── Public API ─────────────────────────────────────────────────────────────────

async def extract_hls_from_white(
    tmdb_id: int,
    media_type: str,
    season: int = 1,
    episode: int = 1,
    session=None,  # noqa: ARG001 — kept for call-site compatibility
    cdn_headers: dict | None = None,
) -> ExtractionResult | None:
    from scrapling.fetchers import AsyncStealthySession

    page_url = _build_page_url(tmdb_id, media_type, season, episode)

    captured_hls: str | None = None
    captured_mp4s: list[str] = []
    probe_result: dict | None = None
    hls_captured_event = asyncio.Event()

    async def _setup_page(page) -> None:
        async def _on_response(response) -> None:
            nonlocal captured_hls
            url = response.url
            low = url.lower()
            if ".m3u8" in low and captured_hls is None:
                captured_hls = url
                hls_captured_event.set()
                logger.info('"white_hls_captured":{"url":"%s"}', url[:120])
            elif ".mp4" in low and url not in captured_mp4s:
                cl = int(response.headers.get("content-length", "0") or "0")
                if cl == 0 or cl > 500_000:
                    captured_mp4s.append(url)

        page.on("response", _on_response)

    async def _run_action(page) -> None:
        nonlocal captured_hls, probe_result
        # Skip DOM probe if network interception already found the HLS URL.
        if captured_hls is not None:
            return
        try:
            probe_result = await page.evaluate(_DOM_PROBE_SCRIPT) or {}
            for url in probe_result.get("urls", []):
                low = url.lower()
                if ".m3u8" in low and not captured_hls:
                    captured_hls = url
                    hls_captured_event.set()
                    logger.info('"white_hls_dom_found":{"url":"%s"}', url[:120])
                elif ".mp4" in low and url not in captured_mp4s:
                    captured_mp4s.append(url)
        except Exception as exc:
            logger.warning('"white_dom_probe_error":{"err":"%s"}', exc)

    logger.info('"white_loading":{"url":"%s"}', page_url)
    try:
        import app.api.providers.white as white_api

        async with AsyncStealthySession(
            headless=True,
            solve_cloudflare=True,
            block_ads=True,
            block_webrtc=True,
            hide_canvas=True,
            timeout=120_000,
            disable_resources=True,
        ) as stealthy:
            resp = await stealthy.fetch(
                page_url,
                page_setup=_setup_page,
                page_action=_run_action,
                wait=2500,
            )

            # Capture cookies while the browser context is still alive.
            try:
                cookies = await stealthy.context.cookies() if stealthy.context else []
                parsed = {c["name"]: c["value"] for c in cookies or []}
                await white_api.set_cookies(parsed)
                logger.info('"white_cookies_captured":{"count":%d}', len(parsed))
            except Exception as exc:
                logger.warning('"white_cookie_capture_failed":{"err":"%s"}', exc)

            # Give late-firing network responses a short grace period.
            if captured_hls is None:
                try:
                    await asyncio.wait_for(hls_captured_event.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    pass

        # Browser is closed; now fetch and parse the manifest.
        return await _post_process(
            resp, captured_hls, captured_mp4s, page_url, cdn_headers, probe_result
        )

    except Exception as exc:
        logger.error('"white_extraction_error":{"err":"%s"}', exc)
        return None


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _post_process(
    page,
    captured_hls: str | None,
    captured_mp4s: list[str],
    page_url: str,
    cdn_headers: dict | None,
    probe_result: dict | None = None,
) -> ExtractionResult | None:
    probe: dict = probe_result or {}

    # Fallback: scan DOM probe results if network interception missed the HLS URL.
    if not captured_hls:
        logger.info('"white_phase3_dom_probe"')
        for url in probe.get("urls", []):
            low = url.lower()
            if ".m3u8" in low and not captured_hls:
                captured_hls = url
                logger.info('"white_phase3_hls_found":{"url":"%s"}', url[:120])
            elif ".mp4" in low and url not in captured_mp4s:
                captured_mp4s.append(url)

    probe_downloads: list[str] = probe.get("downloads", [])

    if not captured_hls and not captured_mp4s and not probe_downloads:
        logger.warning('"white_extraction_failed":{"url":"%s"}', page_url)
        return None

    result = ExtractionResult(raw_hls_url=captured_hls or "")

    # Collect MP4 download links; preserve insertion order, deduplicate.
    mp4_urls = list(dict.fromkeys(
        captured_mp4s + [u for u in probe_downloads if ".mp4" in u.lower()]
    ))
    for mp4_url in mp4_urls:
        q = _guess_quality_from_url(mp4_url)
        result.downloads.append(StreamSource(
            url=mp4_url,
            quality=q,
            resolution=_quality_label_to_height(q),
            source_type="mp4",
        ))

    if captured_hls:
        result.sources = await _fetch_and_parse_manifest(captured_hls, cdn_headers)
        result.method = (
            "dom_probe" if captured_hls in probe.get("urls", []) else "network"
        )

    _sort_sources(result.sources)
    _sort_sources(result.downloads)

    logger.info(
        '"white_extraction_done":{"hls":%d,"mp4":%d,"method":"%s"}',
        len(result.sources), len(result.downloads), result.method,
    )
    return result


def _build_page_url(tmdb_id: int, media_type: str, season: int, episode: int) -> str:
    if media_type == "movie":
        return f"{ONETOONE_BASE}/movie/{tmdb_id}"
    return f"{ONETOONE_BASE}/tv/{tmdb_id}/{season}/{episode}"


async def _fetch_and_parse_manifest(
    hls_url: str,
    cdn_headers: dict | None,
) -> list[StreamSource]:
    """Fetch the HLS master manifest and return quality-sorted StreamSources.

    Falls back to a single Auto-quality source on any fetch or parse failure.
    """
    import app.api.providers.white as white_api

    headers = {**white_api._CDN_HEADERS, **(cdn_headers or {})}
    fallback = _fallback_hls(hls_url)

    client: CurlSession | None = None
    try:
        cookies = await white_api._ensure_browser_session()
        adapted_cookies = white_api._adapt_cookies_for_domain(cookies, hls_url)
        client = CurlSession(
            headers=headers,
            timeout=30,
            allow_redirects=True,
            impersonate="chrome131",
            cookies=adapted_cookies,
        )
        resp = await client.get(hls_url)
    except Exception as exc:
        logger.warning('"white_manifest_error":{"err":"%s"}', exc)
        return fallback
    finally:
        if client is not None:
            await client.close()

    if not resp.ok:
        logger.warning('"white_manifest_fetch_failed":{"status":%d}', resp.status_code)
        return fallback

    text: str = resp.text
    if "#EXT-X-STREAM-INF" not in text:
        return fallback

    base = hls_url.rsplit("/", 1)[0] + "/"
    variants = _parse_hls_manifest(text, base)
    if not variants:
        return fallback

    sources = [StreamSource.from_hls_variant(v) for v in variants]
    logger.info('"white_variants_parsed":{"count":%d}', len(sources))
    return sources


def _fallback_hls(url: str) -> list[StreamSource]:
    """Single-item Auto-quality list returned when manifest parsing cannot proceed."""
    return [StreamSource(url=url, quality="Auto", resolution=0, bandwidth=0, source_type="hls")]


# Matches "1080p", "720P", "1920x1080", etc. in a URL path.
_Q_RE: Final = re.compile(r"(\d{3,4})[pP]|(\d{3,4})x(\d{3,4})")


def _guess_quality_from_url(url: str) -> str:
    m = _Q_RE.search(url)
    if not m:
        return "Auto"
    height = m.group(1) or m.group(3)  # group(1) = "Np" form; group(3) = "WxH" form
    return f"{height}p" if height else "Auto"


def _quality_label_to_height(label: str) -> int:
    m = re.match(r"(\d+)", label)
    return int(m.group(1)) if m else 0


def _sort_sources(sources: list[StreamSource]) -> None:
    """Sort in-place: highest known resolution first, then bandwidth; unknowns last."""
    sources.sort(key=lambda s: (s.resolution == 0, -s.resolution, -s.bandwidth))


# ── Compatibility shim ─────────────────────────────────────────────────────────

async def extract_sources_legacy(
    tmdb_id: int,
    media_type: str,
    season: int = 1,
    episode: int = 1,
    session=None,
    cdn_headers: dict | None = None,
) -> tuple[list[dict] | None, str]:
    """Compatibility shim — prefer :func:`extract_hls_from_white` for new callers."""
    result = await extract_hls_from_white(
        tmdb_id, media_type, season, episode, session, cdn_headers
    )
    if result is None:
        return None, ""
    combined = result.to_legacy_list()
    return (combined or None), result.raw_hls_url