from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

ONETOONE_BASE = "https://111movies.net"

_CDN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://111movies.net/",
    "Origin": "https://111movies.net",
    "Accept-Language": "en-US,en;q=0.9",
}

_DOM_PROBE_SCRIPT = """
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


@dataclass
class StreamSource:
    url: str
    quality: str = "Auto"
    resolution: int = 0
    bandwidth: int = 0
    source_type: Literal["hls", "mp4", "unknown"] = "hls"

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
    method: str = "unknown"
    raw_hls_url: str = ""

    def best(self) -> StreamSource | None:
        return self.sources[0] if self.sources else None

    def to_legacy_list(self) -> list[dict]:
        return [s.to_dict() for s in self.sources] + [s.to_dict() for s in self.downloads]


async def extract_hls_from_white(
    tmdb_id: int,
    media_type: str,
    season: int = 1,
    episode: int = 1,
    session=None,
    cdn_headers: dict | None = None,
) -> ExtractionResult | None:
    from scrapling.fetchers import AsyncStealthySession

    page_url = _build_page_url(tmdb_id, media_type, season, episode)

    own_session = session is None
    if own_session:
        session = AsyncStealthySession(
            headless=True,
            solve_cloudflare=True,
            block_ads=True,
            block_webrtc=True,
            hide_canvas=True,
            timeout=120_000,
            disable_resources=True,
        )

    captured_hls: str | None = None
    captured_mp4s: list[str] = []

    async def _setup_page(page):
        async def _on_response(response):
            nonlocal captured_hls
            url = response.url
            low = url.lower()
            if ".m3u8" in low and captured_hls is None:
                captured_hls = url
                logger.info('"white_hls_captured":{"url":"%s"}', url[:120])
            elif ".mp4" in low and url not in captured_mp4s:
                cl = int(response.headers.get("content-length", "0") or "0")
                if cl == 0 or cl > 500_000:
                    captured_mp4s.append(url)

        page.on("response", _on_response)

    logger.info('"white_loading":{"url":"%s"}', page_url)
    try:
        if own_session:
            async with session as s:
                page = await s.fetch(
                    page_url,
                    page_setup=_setup_page,
                    wait=5000,
                )
                result = await _post_process(
                    page, captured_hls, captured_mp4s, page_url, cdn_headers
                )
            return result
        else:
            page = await session.fetch(
                page_url,
                page_setup=_setup_page,
                wait=5000,
            )
            return await _post_process(
                page, captured_hls, captured_mp4s, page_url, cdn_headers
            )

    except Exception as exc:
        logger.error('"white_extraction_error":{"err":"%s"}', exc)
        return None


async def _post_process(
    page, captured_hls: str | None, captured_mp4s: list[str],
    page_url: str, cdn_headers: dict | None,
) -> ExtractionResult | None:
    if not captured_hls:
        logger.info('"white_phase3_dom_probe"')
        try:
            probe = await page.evaluate(_DOM_PROBE_SCRIPT) or {}
        except Exception as exc:
            logger.warning('"white_probe_error":{"err":"%s"}', exc)
            probe = {}

        for url in probe.get("urls", []):
            if ".m3u8" in url.lower() and not captured_hls:
                captured_hls = url
                logger.info('"white_phase3_hls_found":{"url":"%s"}', url[:120])
            elif ".mp4" in url.lower():
                captured_mp4s.append(url)

        probe_downloads: list[str] = probe.get("downloads", [])
    else:
        probe = {}
        probe_downloads = []

    if not captured_hls and not captured_mp4s and not probe_downloads:
        logger.warning('"white_extraction_failed":{"url":"%s"}', page_url)
        return None

    result = ExtractionResult(raw_hls_url=captured_hls or "")

    all_mp4s = list(dict.fromkeys(
        captured_mp4s + [u for u in probe_downloads if ".mp4" in u.lower()]
    ))
    for mp4_url in all_mp4s:
        q = _guess_quality_from_url(mp4_url)
        result.downloads.append(StreamSource(
            url=mp4_url,
            quality=q,
            resolution=_quality_label_to_height(q),
            source_type="mp4",
        ))

    if captured_hls:
        hls_sources = await _parse_master_manifest(captured_hls, cdn_headers)
        result.sources = hls_sources
        result.method = "network" if captured_hls not in probe.get("urls", []) else "dom_probe"

    _sort_sources(result.sources)
    _sort_sources(result.downloads)

    logger.info(
        '"white_extraction_done":{"hls":%d,"mp4":%d,"method":"%s"}',
        len(result.sources),
        len(result.downloads),
        result.method,
    )
    return result


def _build_page_url(tmdb_id: int, media_type: str, season: int, episode: int) -> str:
    if media_type == "movie":
        return f"{ONETOONE_BASE}/movie/{tmdb_id}"
    return f"{ONETOONE_BASE}/tv/{tmdb_id}/{season}/{episode}"


async def _parse_master_manifest(
    hls_url: str,
    cdn_headers: dict | None,
) -> list[StreamSource]:
    headers = {**_CDN_HEADERS, **(cdn_headers or {})}
    fallback = [StreamSource(url=hls_url, quality="Auto", resolution=0, bandwidth=0)]

    try:
        async with httpx.AsyncClient(
            headers=headers, timeout=30.0, follow_redirects=True
        ) as client:
            resp = await client.get(hls_url)

        if not resp.is_success:
            logger.warning('"white_manifest_fetch_failed":{"status":%d}', resp.status_code)
            return fallback

        text = resp.text
        if "#EXT-X-STREAM-INF" not in text:
            return fallback

        base = hls_url.rsplit("/", 1)[0] + "/"
        variants = _parse_ext_x_stream_inf(text, base, hls_url)
        if not variants:
            return fallback

        logger.info('"white_variants_parsed":{"count":%d}', len(variants))
        return variants

    except Exception as exc:
        logger.warning('"white_manifest_error":{"err":"%s"}', exc)
        return fallback


def _parse_ext_x_stream_inf(text: str, base_url: str, master_url: str = "") -> list[StreamSource]:
    sources: list[StreamSource] = []
    seen: set[str] = set()
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXT-X-STREAM-INF:"):
            attrs = _parse_attrs(line[len("#EXT-X-STREAM-INF:"):])
            bw = int(attrs.get("BANDWIDTH", "0") or "0")
            res = attrs.get("RESOLUTION", "")
            height = 0
            if "x" in res:
                try:
                    height = int(res.split("x", 1)[1])
                except (ValueError, IndexError):
                    pass
            quality = _height_to_label(height) if height else _bandwidth_to_label(bw)

            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith("#")):
                j += 1

            if j < len(lines):
                uri = lines[j].strip()
                if uri and uri not in seen:
                    if uri.startswith("http"):
                        pass
                    elif uri.startswith("/"):
                        from urllib.parse import urlparse
                        parsed = urlparse(master_url)
                        uri = f"{parsed.scheme}://{parsed.netloc}{uri}"
                    else:
                        uri = base_url + uri
                    seen.add(uri)
                    sources.append(StreamSource(
                        url=uri,
                        quality=quality,
                        resolution=height,
                        bandwidth=bw,
                        source_type="hls",
                    ))
                i = j + 1
                continue
        i += 1
    return sources


def _parse_attrs(s: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(r'([A-Z0-9_-]+)=(?:"([^"]*)"|([^,"\s]+))', s):
        out[m.group(1)] = m.group(2) if m.group(3) is None else m.group(3)
    return out


def _height_to_label(h: int) -> str:
    if h >= 2160: return "4K"
    if h >= 1440: return "1440p"
    if h >= 1080: return "1080p"
    if h >= 720:  return "720p"
    if h >= 480:  return "480p"
    if h >= 360:  return "360p"
    if h >= 240:  return "240p"
    return f"{h}p"


def _bandwidth_to_label(bw: int) -> str:
    mbps = bw / 1_000_000
    if mbps >= 15: return "4K"
    if mbps >= 8:  return "1080p"
    if mbps >= 4:  return "720p"
    if mbps >= 2:  return "480p"
    if mbps >= 0.8: return "360p"
    return "Auto"


_Q_RE = re.compile(r'(\d{3,4})[pP]|(\d{3,4})x(\d{3,4})')


def _guess_quality_from_url(url: str) -> str:
    m = _Q_RE.search(url)
    if not m:
        return "Auto"
    if m.group(1):
        return f"{m.group(1)}p"
    if m.group(3):
        return f"{m.group(3)}p"
    return "Auto"


def _quality_label_to_height(label: str) -> int:
    m = re.match(r"(\d+)", label)
    return int(m.group(1)) if m else 0


def _sort_sources(sources: list[StreamSource]) -> None:
    sources.sort(key=lambda s: (s.resolution == 0, -s.resolution, -s.bandwidth))


async def extract_sources_legacy(
    tmdb_id: int,
    media_type: str,
    season: int = 1,
    episode: int = 1,
    session=None,
    cdn_headers: dict | None = None,
) -> list[dict] | None:
    result = await extract_hls_from_white(
        tmdb_id, media_type, season, episode, session, cdn_headers
    )
    if result is None:
        return None
    combined = result.to_legacy_list()
    return combined or None
