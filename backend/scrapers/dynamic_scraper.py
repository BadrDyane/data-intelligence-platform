"""
DynamicScraper — for JavaScript-rendered pages.

Uses Playwright (Chromium) with:
  - Stealth patches to mask automation detection
  - Smart wait strategies (selector / networkidle / fixed)
  - XHR/fetch interception for API-driven sites
  - Browser singleton lifecycle (one browser, one page at a time)
  - Full async context manager support

Subclasses override scrape_page() and scrape_all() with source-specific logic.
"""

import asyncio
import json
import logging
import random
from typing import Optional, Any, Callable

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Response,
)

from backend.config import settings
from backend.scrapers.base_scraper import BaseScraper, ScrapedItem, ScrapeResult

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36",
]

# JavaScript injected into every page before any scripts run.
# Masks the most common automation fingerprints.
STEALTH_SCRIPT = """
() => {
    // Remove the webdriver property that Selenium/Playwright expose
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // Fake plugin list (real browsers have plugins, headless doesn't)
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer',  filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
        ],
    });

    // Fake language list
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

    // Fake screen resolution (headless has zero size by default)
    Object.defineProperty(screen, 'availWidth',  { get: () => 1920 });
    Object.defineProperty(screen, 'availHeight', { get: () => 1080 });

    // Pass the Chrome object check
    window.chrome = { runtime: {} };

    // Fake notification permission state
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);
}
"""


class DynamicScraper(BaseScraper):
    """
    Base for all JavaScript-rendered scrapers.

    Lifecycle (preferred — via context manager):
        async with MyDynamicSource() as scraper:
            result = await scraper.scrape_all()

    The browser opens once on __aenter__ and closes on __aexit__.
    Never open a new browser per request — it's ~2s startup and kills memory.
    """

    def __init__(self, source_name: str, base_url: str):
        super().__init__(source_name)
        self.base_url = base_url
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    # ── Browser lifecycle ──────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start Playwright + Chromium. Called by __aenter__."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.PLAYWRIGHT_HEADLESS,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--no-first-run",
                "--disable-infobars",
            ],
        )
        self.logger.info(f"Browser started (headless={settings.PLAYWRIGHT_HEADLESS})")

    async def close(self) -> None:
        """Close browser + Playwright. Called by __aexit__."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self.logger.info("Browser closed")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_):
        await self.close()

    # ── Page management ────────────────────────────────────────────────────────

    async def _new_context(self) -> BrowserContext:
        """Create a fresh browser context with randomized fingerprints."""
        return await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": random.choice([1280, 1366, 1440, 1920]),
                      "height": random.choice([768, 900, 1080])},
            locale="en-US",
            timezone_id="America/New_York",
            java_script_enabled=True,
            accept_downloads=False,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "DNT": "1",
            },
        )

    async def _new_page(self) -> tuple[Page, BrowserContext]:
        """Create a context + page, inject stealth script."""
        context = await self._new_context()
        page = await context.new_page()
        await page.add_init_script(STEALTH_SCRIPT)
        # Block image and font loading for speed (remove if site needs them for JS)
        await page.route(
            "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot}",
            lambda route: route.abort(),
        )
        return page, context

    # ── Navigation strategies ──────────────────────────────────────────────────

    async def fetch_html(
        self,
        url: str,
        *,
        wait_for_selector: Optional[str] = None,
        wait_state: str = "domcontentloaded",
        extra_wait: float = 0.0,
    ) -> Optional[str]:
        """
        Navigate to a URL and return the fully-rendered HTML.

        Args:
            url:                URL to navigate to.
            wait_for_selector:  CSS selector to wait for (most reliable).
                                If provided, overrides wait_state.
            wait_state:         Playwright load state to wait for.
                                Options: 'load', 'domcontentloaded', 'networkidle'.
                                'networkidle' is safest for API-driven pages.
            extra_wait:         Additional fixed delay after content loads (seconds).
                                Use as last resort for lazy-loaded content.

        Returns:
            Fully-rendered HTML string, or None on failure.
        """
        page, context = await self._new_page()
        try:
            self.logger.debug(f"Navigating to {url}")
            await page.goto(url, wait_until=wait_state, timeout=settings.SCRAPE_TIMEOUT * 1000)

            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=15_000)
                    self.logger.debug(f"Selector '{wait_for_selector}' found")
                except Exception:
                    self.logger.warning(f"Selector '{wait_for_selector}' not found on {url}")

            if extra_wait > 0:
                await asyncio.sleep(extra_wait)

            # Polite delay before returning
            await asyncio.sleep(random.uniform(0.5, 1.5))

            return await page.content()

        except Exception as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None

        finally:
            await context.close()

    async def intercept_api(
        self,
        url: str,
        *,
        api_pattern: str,
        wait_state: str = "networkidle",
        timeout: int = 20_000,
    ) -> Optional[dict | list]:
        """
        Intercept XHR/fetch calls made by the page and capture their JSON response.

        This is the most reliable technique for API-driven SPAs.
        Instead of parsing rendered HTML, we capture the raw API response.

        Args:
            url:         Page URL to navigate to.
            api_pattern: URL substring to match (e.g. "/api/products" or "graphql").
            wait_state:  Playwright load state before timing out.
            timeout:     Max ms to wait for the intercepted response.

        Returns:
            Parsed JSON payload from the first matching response, or None.

        Example:
            data = await scraper.intercept_api(
                "https://example.com/products",
                api_pattern="/api/v2/products",
            )
        """
        page, context = await self._new_page()
        captured: list[Any] = []

        async def on_response(response: Response) -> None:
            if api_pattern in response.url and response.status == 200:
                try:
                    payload = await response.json()
                    captured.append(payload)
                    self.logger.debug(f"Intercepted API response from {response.url}")
                except Exception as e:
                    self.logger.warning(f"Could not parse API response JSON: {e}")

        page.on("response", on_response)

        try:
            await page.goto(url, wait_until=wait_state, timeout=timeout)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            return captured[0] if captured else None

        except Exception as e:
            self.logger.error(f"intercept_api failed on {url}: {e}")
            return None

        finally:
            await context.close()

    async def scroll_and_load(
        self,
        url: str,
        *,
        content_selector: str,
        max_scrolls: int = 10,
        scroll_pause: float = 1.5,
    ) -> Optional[str]:
        """
        Handle infinite-scroll pages by repeatedly scrolling to the bottom
        until no new content appears or max_scrolls is reached.

        Args:
            url:              Page URL.
            content_selector: CSS selector for the items being loaded.
            max_scrolls:      Maximum scroll attempts.
            scroll_pause:     Seconds to wait after each scroll.

        Returns:
            Final rendered HTML after all content is loaded.
        """
        page, context = await self._new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=settings.SCRAPE_TIMEOUT * 1000)
            await page.wait_for_selector(content_selector, timeout=15_000)

            prev_count = 0
            for i in range(max_scrolls):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(scroll_pause)

                curr_count = await page.locator(content_selector).count()
                self.logger.debug(f"Scroll {i+1}: {curr_count} items ({prev_count} before)")

                if curr_count == prev_count:
                    self.logger.info(f"No new items after scroll {i+1}. Stopping.")
                    break
                prev_count = curr_count

            return await page.content()

        except Exception as e:
            self.logger.error(f"scroll_and_load failed on {url}: {e}")
            return None

        finally:
            await context.close()

    # ── Abstract: implement in source subclasses ───────────────────────────────

    async def scrape_page(self, url: str, page_num: int = 1) -> list[ScrapedItem]:
        raise NotImplementedError("Implement scrape_page() in your source subclass.")

    async def scrape_all(self) -> ScrapeResult:
        raise NotImplementedError("Implement scrape_all() in your source subclass.")