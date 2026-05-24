"""111movies.net (White server) source extraction using Playwright.

Implements an adaptive polling strategy that waits for client-side
decryption to complete before extracting the stream URL.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

WHITE_BASE = "https://www.111movies.net"


async def extract_hls_from_111movies(
    tmdb_id: int,
    media_type: str,
    season: int = 1,
    episode: int = 1,
    browser=None,
    cdn_headers: dict | None = None,
) -> list[dict] | None:
    """Extract HLS URLs from 111movies.net using Playwright.

    Strategy:
      1. Load the page and wait for network idle.
      2. Poll the DOM / JS state every 1s for up to 20s to catch
         the decrypted video source.
      3. If still not found, simulate a click on the player area to
         trigger lazy initialisation.
      4. Continue polling for another 15s.
      5. Fallback to inspecting Fluid/FastStream player internals.

    Returns a list of source dicts with url, quality, resolution, bandwidth,
    or None if extraction fails.
    """
    from playwright.async_api import async_playwright

    if media_type == "movie":
        embed_url = f"{WHITE_BASE}/movie/{tmdb_id}"
    else:
        embed_url = f"{WHITE_BASE}/tv/{tmdb_id}/{season}/{episode}"

    own_browser = False
    if browser is None:
        p = await async_playwright().start()
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        own_browser = True

    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
    )

    # Mask webdriver to reduce bot detection
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    page = await context.new_page()

    captured_url: str | None = None
    download_urls: list[str] = []

    async def on_response(response):
        nonlocal captured_url, download_urls
        if captured_url is not None:
            return
        url = response.url
        lower_url = url.lower()
        if ".m3u8" in lower_url:
            captured_url = url
        if ".mp4" in lower_url and url not in download_urls:
            download_urls.append(url)

    page.on("response", on_response)

    logger.info("Loading 111movies embed: %s", embed_url)
    try:
        await page.goto(embed_url, wait_until="networkidle", timeout=60000)
    except Exception as e:
        logger.warning("111movies navigation error: %s", e)
        await page.goto(embed_url, wait_until="domcontentloaded", timeout=60000)

    # ── Phase 1: passive polling (20 s) ──────────────────────────
    for _ in range(20):
        if captured_url:
            break
        await asyncio.sleep(1)

    if captured_url:
        logger.info("Captured HLS source during passive poll: %s", captured_url)

    # ── Phase 2: click-to-play trigger ───────────────────────────
    if not captured_url:
        logger.info("No source yet — clicking player to trigger decryption")

        # Try clicking the big centre play button or video container
        click_selectors = [
            ".fluid_control_playpause_big_circle",
            ".fluid_initial_play",
            ".fluid_control_playpause",
            ".video-container",
            ".mainplayer",
            "video",
        ]
        for sel in click_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click(force=True, timeout=2000)
                    logger.info("Clicked: %s", sel)
                    break
            except Exception:
                pass

        # Phase 2b: active polling after click (15 s)
        for _ in range(15):
            if captured_url:
                break
            await asyncio.sleep(1)

        if captured_url:
            logger.info("Captured HLS source after click: %s", captured_url)

    # ── Phase 3: deep JS/DOM inspection ────────────────────────
    if not captured_url:
        logger.info("No network capture — probing DOM / JS internals")

        # FastStream / Fluid Player expose the source on the player instance.
        # We walk common global objects that streaming players create.
        probe_scripts = [
            # video element direct src
            """
            (() => {
                const v = document.querySelector('video');
                if (!v) return null;
                return v.src || v.currentSrc || null;
            })()
            """,
            # FastStream client (window.FastStreamClient)
            """
            (() => {
                if (window.FastStreamClient && window.FastStreamClient.instances) {
                    for (const inst of window.FastStreamClient.instances) {
                        if (inst.source && inst.source.url) return inst.source.url;
                        if (inst.videoElement) {
                            const s = inst.videoElement.src || inst.videoElement.currentSrc;
                            if (s) return s;
                        }
                    }
                }
                return null;
            })()
            """,
            # Generic player globals
            """
            (() => {
                for (const key of ['player', 'fluidPlayer', 'hls', 'videojs', 'plyr']) {
                    const obj = window[key];
                    if (!obj) continue;
                    if (obj.src) return obj.src;
                    if (obj.currentSrc) return obj.currentSrc;
                    if (obj.source && obj.source.url) return obj.source.url;
                    if (obj.config && obj.config.src) return obj.config.src;
                }
                return null;
            })()
            """,
            # Fluid Player specific
            """
            (() => {
                if (window.fluidPlayer && window.fluidPlayer.instances) {
                    for (const id in window.fluidPlayer.instances) {
                        const p = window.fluidPlayer.instances[id];
                        if (p.source && p.source.url) return p.source.url;
                        if (p.domPlayer && p.domPlayer.src) return p.domPlayer.src;
                    }
                }
                return null;
            })()
            """,
            # All video elements on page
            """
            (() => {
                for (const v of document.querySelectorAll('video')) {
                    const s = v.src || v.currentSrc;
                    if (s && s.startsWith('http')) return s;
                }
                return null;
            })()
            """,
            # Blob URL check (some players use blob: URLs with HLS.js)
            """
            (() => {
                for (const v of document.querySelectorAll('video')) {
                    const s = v.src || v.currentSrc;
                    if (s && s.startsWith('blob:')) return s;
                }
                return null;
            })()
            """,
        ]

        for script in probe_scripts:
            try:
                result = await page.evaluate(script)
                if result and (result.startswith("http") or result.startswith("blob:")):
                    logger.info("Found source via JS probe: %s", result)
                    captured_url = result
                    break
            except Exception as e:
                logger.debug("JS probe failed: %s", e)

    # ── Phase 4: last resort – fetch the encrypted data and try to
    # decode it ourselves if we still have nothing ────────────────
    if not captured_url:
        try:
            next_data = await page.evaluate("""
                (() => {
                    const el = document.getElementById('__NEXT_DATA__');
                    if (!el) return null;
                    try {
                        return JSON.parse(el.textContent);
                    } catch { return null; }
                })()
            """)
            if next_data and next_data.get("props", {}).get("pageProps", {}).get("data"):
                encrypted = next_data["props"]["pageProps"]["data"]
                logger.info("Got encrypted data string (len=%d). Decryption not yet implemented.", len(encrypted))
                # TODO: implement decryption here once algorithm is known
        except Exception as e:
            logger.debug("Encrypted data extraction failed: %s", e)

    await asyncio.sleep(1)
    await context.close()
    if own_browser:
        await browser.close()
        await p.stop()

    if not captured_url:
        logger.warning("Could not extract any video source for %s", embed_url)
        return None

    # ── Manifest fetch & quality parsing ─────────────────────────
    sources = []
    cdn_headers = cdn_headers or {}

    try:
        import httpx

        async with httpx.AsyncClient(
            headers=cdn_headers,
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            resp = await client.get(captured_url)
            if not resp.is_success:
                logger.warning("Failed to fetch master manifest: %s", captured_url)
                return [{"url": captured_url, "quality": "Auto", "resolution": 0, "bandwidth": 0}]

            manifest_text = resp.text
            base_url = captured_url.rsplit("/", 1)[0] + "/"

            if "#EXT-X-STREAM-INF" in manifest_text:
                from .hls_parser import parse_master_manifest

                variants = parse_master_manifest(manifest_text, base_url)
                if variants:
                    for v in variants:
                        sources.append({
                            "url": v.url,
                            "quality": v.quality_label,
                            "resolution": v.resolution_height,
                            "bandwidth": v.bandwidth,
                        })
                    logger.info(
                        "Parsed %d quality variants: %s",
                        len(sources),
                        [s["quality"] for s in sources],
                    )
                    return sources

            sources.append({"url": captured_url, "quality": "Auto", "resolution": 0, "bandwidth": 0})
            return sources

    except Exception as e:
        logger.warning("Failed to parse master manifest: %s", e)
        return [{"url": captured_url, "quality": "Auto", "resolution": 0, "bandwidth": 0}]
