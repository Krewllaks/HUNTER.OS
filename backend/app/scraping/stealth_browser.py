"""
HUNTER.OS - Multi-Layer Stealth Browser Manager
3-tier anti-detection: CloakBrowser (33 C++ patches) → rebrowser-playwright → vanilla playwright
"""
import asyncio
import logging
import random
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Human-like delay ranges ─────────────────────────────
TYPING_DELAY = (50, 150)       # ms between keystrokes
CLICK_DELAY = (100, 500)       # ms before click
SCROLL_DELAY = (500, 2000)     # ms between scrolls
PAGE_LOAD_WAIT = (2000, 5000)  # ms after navigation

# ── Timezone rotation (matched with locale) ──────────────
TIMEZONE_LOCALES = [
    ("America/New_York", "en-US"),
    ("America/Chicago", "en-US"),
    ("America/Los_Angeles", "en-US"),
    ("Europe/London", "en-GB"),
    ("Europe/Berlin", "de-DE"),
]

# ── User agent rotation pool (Chrome 121-125, 2024-2025) ─
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# ── Viewport randomization ──────────────────────────────
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1366, "height": 768},
    {"width": 2560, "height": 1440},
]

# ── Extra stealth scripts (injected on fallback engines) ─
STEALTH_SCRIPTS = [
    """Object.defineProperty(navigator, 'webdriver', {get: () => undefined});""",
    """Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5].map(() => ({
            name: 'Chrome PDF Plugin',
            filename: 'internal-pdf-viewer',
        }))
    });""",
    """Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});""",
    """window.chrome = { runtime: {} };""",
    """const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);""",
]

# ── Engine detection ─────────────────────────────────────
_ENGINE = None  # "cloak" | "rebrowser" | "vanilla"


def _detect_engine() -> str:
    """Detect best available browser engine at import time."""
    global _ENGINE
    if _ENGINE:
        return _ENGINE

    # Tier 1: CloakBrowser — 33 C++ Chromium source patches
    try:
        import cloakbrowser  # noqa: F401
        _ENGINE = "cloak"
        logger.info("🛡️ StealthBrowser engine: CloakBrowser (33 C++ patches)")
        return _ENGINE
    except ImportError:
        pass

    # Tier 2: rebrowser-playwright — CDP Runtime.Enable leak fix
    try:
        from rebrowser_playwright.async_api import async_playwright  # noqa: F401
        _ENGINE = "rebrowser"
        logger.info("🔧 StealthBrowser engine: rebrowser-playwright (CDP fix)")
        return _ENGINE
    except ImportError:
        pass

    # Tier 3: vanilla playwright
    _ENGINE = "vanilla"
    logger.warning("⚠️ StealthBrowser engine: vanilla playwright (no stealth patches)")
    return _ENGINE


class StealthBrowser:
    """
    Multi-layer stealth browser with automatic engine selection:
    1. CloakBrowser — 33 C++ Chromium patches (canvas, WebGL, audio, font, GPU fingerprint)
    2. rebrowser-playwright — CDP Runtime.Enable leak fix
    3. vanilla playwright — JS stealth scripts only (weakest)

    All engines expose identical Playwright-compatible Page/Browser objects.
    """

    def __init__(self, proxy: Optional[str] = None, session_cookie: Optional[str] = None):
        self.proxy = proxy
        self.session_cookie = session_cookie
        self.engine = _detect_engine()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def __aenter__(self):
        await self.launch()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def launch(self):
        """Launch stealth browser using best available engine."""
        tz, locale = random.choice(TIMEZONE_LOCALES)
        viewport = random.choice(VIEWPORTS)
        user_agent = random.choice(USER_AGENTS)

        if self.engine == "cloak":
            await self._launch_cloak(viewport, user_agent, tz, locale)
        elif self.engine == "rebrowser":
            await self._launch_rebrowser(viewport, user_agent, tz, locale)
        else:
            await self._launch_vanilla(viewport, user_agent, tz, locale)

        # LinkedIn session cookie injection (all engines)
        if self.session_cookie and self._context:
            await self._context.add_cookies([
                {
                    "name": "li_at",
                    "value": self.session_cookie,
                    "domain": ".linkedin.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                }
            ])

        return self._page

    # ── Engine launchers ──────────────────────────────────

    async def _launch_cloak(self, viewport, user_agent, tz, locale):
        """
        CloakBrowser: 33 C++ source-level Chromium patches.
        Patches canvas, WebGL, AudioContext, fonts, GPU, WebRTC, etc.
        Built-in humanization with Bezier mouse curves.
        Returns standard Playwright Browser/Page objects.
        """
        import cloakbrowser

        launch_kwargs = {
            "headless": settings.PLAYWRIGHT_HEADLESS,
            "humanize": True,  # Bezier curve mouse, natural typing
            "timezone": tz,
            "locale": locale,
        }

        if self.proxy:
            launch_kwargs["proxy"] = self.proxy

        self._browser = await cloakbrowser.launch_async(**launch_kwargs)

        # CloakBrowser returns a Playwright Browser — create context + page
        self._context = await self._browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale=locale,
            timezone_id=tz,
            color_scheme="light",
        )
        self._page = await self._context.new_page()
        logger.info(f"🛡️ CloakBrowser launched (headless={settings.PLAYWRIGHT_HEADLESS}, tz={tz})")

    async def _launch_rebrowser(self, viewport, user_agent, tz, locale):
        """rebrowser-playwright: CDP Runtime.Enable leak patched."""
        from rebrowser_playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        launch_args = self._build_chromium_args()

        if self.proxy:
            launch_args["proxy"] = {"server": self.proxy}

        self._browser = await self._playwright.chromium.launch(**launch_args)
        self._context = await self._browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale=locale,
            timezone_id=tz,
            color_scheme="light",
        )

        # Inject JS stealth scripts (rebrowser patches CDP, these patch JS)
        for script in STEALTH_SCRIPTS:
            await self._context.add_init_script(script)

        self._page = await self._context.new_page()
        logger.info(f"🔧 rebrowser-playwright launched (headless={settings.PLAYWRIGHT_HEADLESS}, tz={tz})")

    async def _launch_vanilla(self, viewport, user_agent, tz, locale):
        """Vanilla Playwright with JS stealth scripts only."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        launch_args = self._build_chromium_args()

        if self.proxy:
            launch_args["proxy"] = {"server": self.proxy}

        self._browser = await self._playwright.chromium.launch(**launch_args)
        self._context = await self._browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale=locale,
            timezone_id=tz,
            color_scheme="light",
        )

        for script in STEALTH_SCRIPTS:
            await self._context.add_init_script(script)

        self._page = await self._context.new_page()
        logger.warning(f"⚠️ Vanilla playwright launched — minimal stealth (tz={tz})")

    def _build_chromium_args(self) -> dict:
        """Standard Chromium launch arguments for non-CloakBrowser engines."""
        return {
            "headless": settings.PLAYWRIGHT_HEADLESS,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu",
            ],
        }

    # ── Page access ───────────────────────────────────────

    @property
    def page(self):
        if not self._page:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return self._page

    # ── Human-like actions ────────────────────────────────

    async def human_type(self, selector: str, text: str):
        """Type with random delays between keystrokes."""
        await self.page.click(selector)
        for char in text:
            await self.page.type(selector, char, delay=random.randint(*TYPING_DELAY))
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.3, 0.8))

    async def human_click(self, selector: str):
        """Click with random pre-delay and slight position offset."""
        await asyncio.sleep(random.randint(*CLICK_DELAY) / 1000)
        element = await self.page.query_selector(selector)
        if element:
            box = await element.bounding_box()
            if box:
                x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
                y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
                await self.page.mouse.click(x, y)

    async def human_scroll(self, direction: str = "down", amount: int = 300):
        """Scroll with human-like speed variation."""
        delta = amount if direction == "down" else -amount
        steps = random.randint(3, 7)
        for _ in range(steps):
            await self.page.mouse.wheel(0, delta // steps)
            await asyncio.sleep(random.randint(*SCROLL_DELAY) / 1000)

    async def random_mouse_movement(self):
        """Random mouse wiggle to appear human."""
        viewport = self.page.viewport_size
        if viewport:
            x = random.randint(100, viewport["width"] - 100)
            y = random.randint(100, viewport["height"] - 100)
            await self.page.mouse.move(x, y, steps=random.randint(5, 15))

    async def navigate(self, url: str, wait_for: str = "domcontentloaded") -> str:
        """Navigate with human-like timing."""
        await self.random_mouse_movement()
        await self.page.goto(
            url,
            wait_until=wait_for,
            timeout=settings.SCRAPE_TIMEOUT_MS,
        )
        await asyncio.sleep(random.randint(*PAGE_LOAD_WAIT) / 1000)
        return await self.page.content()

    async def extract_text(self) -> str:
        """Extract all visible text from current page."""
        return await self.page.evaluate("""
            () => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                let text = '';
                while (walker.nextNode()) {
                    const node = walker.currentNode;
                    if (node.parentElement &&
                        getComputedStyle(node.parentElement).display !== 'none' &&
                        getComputedStyle(node.parentElement).visibility !== 'hidden') {
                        text += node.textContent.trim() + ' ';
                    }
                }
                return text.replace(/\\s+/g, ' ').trim();
            }
        """)

    async def screenshot(self, path: str = "debug_screenshot.png"):
        """Take screenshot for debugging."""
        await self.page.screenshot(path=path, full_page=True)

    async def close(self):
        """Clean shutdown — works for all engines."""
        try:
            if self._context:
                await self._context.close()
        except Exception as exc:
            logger.debug("Browser cleanup (context): %s", exc)
        try:
            if self._browser:
                await self._browser.close()
        except Exception as exc:
            logger.debug("Browser cleanup (browser): %s", exc)
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as exc:
            logger.debug("Browser cleanup (playwright): %s", exc)
