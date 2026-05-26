"""White (111movies.net) source extraction using Playwright.

Follows the same pattern as the black (vidking.net) extractor:
   1. Block ads/trackers/images before navigation
   2. Intercept network responses for .m3u8 URLs passively
   3. Click-to-play trigger if nothing captured
   4. Deep DOM / JS player probe
   5. Fetch master manifest -> parse quality variants
   6. Return ExtractionResult sorted highest resolution first
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

ONETOONE_BASE = "https://111movies.net"

_BLOCKED_TYPES = {"image", "font", "media"}
_BLOCKED_DOMAINS = frozenset({
    "googlesyndication.com",
    "doubleclick.net",
    "adservice.google.com",
    "googletagmanager.com",
    "facebook.net",
    "hotjar.com",
    "clarity.ms",
    "ads.pubmatic.com",
    "securepubads.g.doubleclick.net",
    "pagead2.googlesyndication.com",
    "asokapygmoid.com",
})

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

_PLAY_SELECTORS = [
    ".vjs-big-play-button",
    ".plyr__control--overlaid",
    "[data-plyr='play']",
    ".jwplayer .jw-display-icon-container",
    ".video-js",
    "[class*='play-btn']",
    "[id*='play-btn']",
    "button[aria-label*='play' i]",
    ".fp-play",
    ".mejs__overlay-play",
    "video",
]

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
    browser=None,
    cdn_headers: dict | None = None,
) -> ExtractionResult | None:
    from playwright.async_api import async_playwright

    page_url = _build_page_url(tmdb_id, media_type, season, episode)

    own_playwright = None
    own_browser = browser is None
    if own_browser:
        own_playwright = await async_playwright().start()
        browser = await own_playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--mute-audio",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )

    context = await browser.new_context(
        user_agent=_CDN_HEADERS["User-Agent"],
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    await context.add_init_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
    )

    page = await context.new_page()

    async def _route(route, request):
        if request.resource_type in _BLOCKED_TYPES:
            await route.abort()
            return
        host = request.url.split("/")[2] if "//" in request.url else ""
        if any(d in host for d in _BLOCKED_DOMAINS):
            await route.abort()
            return
        await route.continue_()

    await page.route("**/*", _route)

    captured_hls: str | None = None
    captured_mp4s: list[str] = []

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
        await page.goto(page_url, wait_until="networkidle", timeout=60_000)
    except Exception as exc:
        logger.warning('"white_networkidle_timeout":{"err":"%s"}', exc)
        try:
            await page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as exc2:
            logger.error('"white_page_load_failed":{"err":"%s"}', exc2)
            await context.close()
            if own_browser and own_playwright:
                await browser.close()
                await own_playwright.stop()
            return None

    for _ in range(20):
        if captured_hls:
            break
        await asyncio.sleep(1)

    if captured_hls:
        logger.info('"white_phase1_success"')

    if not captured_hls:
        logger.info('"white_phase2_click_to_play"')
        await _click_play(page)

        for _ in range(12):
            if captured_hls:
                break
            await asyncio.sleep(1)

        if captured_hls:
            logger.info('"white_phase2_success"')

    probe: dict = {}
    if not captured_hls:
        logger.info('"white_phase3_dom_probe"')
        try:
            probe = await page.evaluate(_DOM_PROBE_SCRIPT) or {}
        except Exception as exc:
            logger.warning('"white_probe_error":{"err":"%s"}', exc)

        for url in probe.get("urls", []):
            if ".m3u8" in url.lower() and not captured_hls:
                captured_hls = url
                logger.info('"white_phase3_hls_found":{"url":"%s"}', url[:120])
            elif ".mp4" in url.lower():
                captured_mp4s.append(url)

    probe_downloads: list[str] = probe.get("downloads", [])

    await asyncio.sleep(0.5)
    await context.close()
    if own_browser and own_playwright:
        await browser.close()
        await own_playwright.stop()

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


async def _click_play(page) -> None:
    for sel in _PLAY_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click(force=True, timeout=2000)
                logger.info('"white_clicked":{"selector":"%s"}', sel)
                return
        except Exception:
            pass


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
        variants = _parse_ext_x_stream_inf(text, base)
        if not variants:
            return fallback

        logger.info('"white_variants_parsed":{"count":%d}', len(variants))
        return variants

    except Exception as exc:
        logger.warning('"white_manifest_error":{"err":"%s"}', exc)
        return fallback


def _parse_ext_x_stream_inf(text: str, base_url: str) -> list[StreamSource]:
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
                    if not uri.startswith("http"):
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
    for m in re.finditer(r'([A-Z0-9_-]+)=(?:"([^"]*)"|([\w@.,\-/]*))', s):
        out[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
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
    browser=None,
    cdn_headers: dict | None = None,
) -> list[dict] | None:
    result = await extract_hls_from_white(
        tmdb_id, media_type, season, episode, browser, cdn_headers
    )
    if result is None:
        return None
    combined = result.to_legacy_list()
    return combined or None
