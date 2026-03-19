import asyncio
import logging
import random
from typing import Optional
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from backend.config import settings
from backend.scrapers.base_scraper import BaseScraper, ScrapedItem, ScrapeResult

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.6049.204 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
]


class StaticScraper(BaseScraper):

    def __init__(self, source_name: str, base_url: str):
        super().__init__(source_name)
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None
        self._robots: Optional[RobotFileParser] = None
        self._robots_loaded = False

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(settings.SCRAPE_TIMEOUT),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _load_robots(self) -> None:
        if self._robots_loaded:
            return
        try:
            robots_url = urljoin(self.base_url, "/robots.txt")
            resp = await self.client.get(robots_url, headers=self._headers())
            self._robots = RobotFileParser()
            self._robots.parse(resp.text.splitlines())
        except Exception as e:
            logger.warning(f"Could not load robots.txt: {e}")
            self._robots = None
        finally:
            self._robots_loaded = True

    def _can_fetch(self, url: str) -> bool:
        if self._robots is None:
            return True
        return self._robots.can_fetch("*", url)

    def _headers(self) -> dict:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
        }

    async def _get(self, url: str) -> Optional[str]:
        await self._load_robots()

        if not self._can_fetch(url):
            logger.warning(f"robots.txt disallows: {url}")
            return None

        await asyncio.sleep(random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX))

        for attempt in range(1, settings.SCRAPE_MAX_RETRIES + 1):
            try:
                resp = await self.client.get(url, headers=self._headers())

                if resp.status_code == 429:
                    wait = 2 ** attempt * random.uniform(1.0, 2.0)
                    logger.warning(f"Rate limited on {url}. Waiting {wait:.1f}s")
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code == 404:
                    return None

                resp.raise_for_status()
                return resp.text

            except httpx.TimeoutException:
                logger.warning(f"Timeout on {url} (attempt {attempt})")
                if attempt < settings.SCRAPE_MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                if attempt < settings.SCRAPE_MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)

        return None

    def parse_html(self, html: str) -> BeautifulSoup:
        try:
            return BeautifulSoup(html, "lxml")
        except Exception:
            return BeautifulSoup(html, "html.parser")

    def abs_url(self, path: str) -> str:
        return urljoin(self.base_url, path)

    async def scrape_page(self, url: str, page_num: int = 1) -> list[ScrapedItem]:
        raise NotImplementedError("Implement scrape_page() in your source subclass.")

    async def scrape_all(self) -> ScrapeResult:
        raise NotImplementedError("Implement scrape_all() in your source subclass.")