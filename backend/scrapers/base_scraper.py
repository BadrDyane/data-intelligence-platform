"""
Base scraper — the contract every scraper must fulfil.

All concrete scrapers (StaticScraper, DynamicScraper) extend this.
The rest of the system (pipeline, API, scheduler) only talks to this interface,
so you can swap or add scrapers without touching anything else.
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScrapedItem:
    """
    The universal transfer object between a scraper and the processing pipeline.

    Every scraper produces a list of these. The pipeline validates, cleans, and
    persists them. No scraper should write to the database directly.
    """
    external_id:  str                     # Deterministic stable ID (hash of URL/product-id)
    source:       str                     # Source name matching sources.name in DB
    title:        str
    url:          str
    price:        Optional[float] = None
    currency:     str = "USD"
    category:     Optional[str] = None
    description:  Optional[str] = None
    image_url:    Optional[str] = None
    is_available: bool = True
    raw_price:    Optional[str] = None    # Original price string before parsing ("£12.99")
    raw_data:     dict = field(default_factory=dict)  # Source-specific bonus fields


@dataclass
class ScrapeResult:
    """
    The outcome of a full scrape_all() call.
    Wraps items + run metadata so the pipeline can log everything in one place.
    """
    source:        str
    items:         list[ScrapedItem] = field(default_factory=list)
    pages_scraped: int = 0
    error_count:   int = 0
    errors:        list[dict] = field(default_factory=list)  # [{url, error, timestamp}]

    def add_error(self, url: str, error: str) -> None:
        import datetime
        self.error_count += 1
        self.errors.append({
            "url": url,
            "error": error,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })
        logger.warning(f"Scrape error [{self.source}] {url}: {error}")


class BaseScraper(ABC):
    """
    Abstract scraper. Every data source gets its own subclass.

    Lifecycle:
        async with MySource() as scraper:      # starts browser if needed
            result = await scraper.scrape_all()
        # browser/client closed automatically

    If your source doesn't need the async context manager (e.g. pure static),
    you can call scrape_all() directly — just call close() manually after.
    """

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = logging.getLogger(f"scraper.{source_name}")

    # ── Abstract interface ─────────────────────────────────────────────────────

    @abstractmethod
    async def scrape_page(self, url: str, page_num: int = 1) -> list[ScrapedItem]:
        """
        Fetch and parse a single page URL.
        Returns a list of ScrapedItem found on that page.
        """

    @abstractmethod
    async def scrape_all(self) -> ScrapeResult:
        """
        Orchestrate the full crawl — pagination, error handling, result collection.
        Returns a ScrapeResult with all items and run metadata.
        """

    async def close(self) -> None:
        """Clean up resources (close HTTP client, browser, etc.). Override if needed."""

    # ── Context manager ────────────────────────────────────────────────────────

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ── Utilities shared by all scrapers ───────────────────────────────────────

    def make_id(self, *parts: str) -> str:
        """
        Generate a deterministic 16-char ID from one or more strings.

        Why: After re-scraping, we need to recognize the same product without
        relying on a database lookup. Hashing the source + stable URL fragment
        gives us a collision-resistant ID that survives restarts.

        Example:
            self.make_id("books_toscrape", "catalogue/a-light-in-the-attic_1000")
            → "3a8f91b4c6e20d17"
        """
        combined = "|".join(str(p) for p in parts)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

    def parse_price(self, raw: str) -> tuple[Optional[float], str, str]:
        """
        Extract a float price from a raw price string.

        Returns (price_float, currency_code, raw_string).

        Handles:
            "£12.99"      → (12.99, "GBP", "£12.99")
            "$1,299.00"   → (1299.0, "USD", "$1,299.00")
            "€ 9,99"      → (9.99, "EUR", "€ 9,99")
            "N/A"         → (None, "USD", "N/A")
            ""            → (None, "USD", "")
        """
        import re

        CURRENCY_SYMBOLS = {"£": "GBP", "$": "USD", "€": "EUR", "¥": "JPY"}

        if not raw:
            return None, "USD", ""

        raw = raw.strip()
        currency = "USD"

        for symbol, code in CURRENCY_SYMBOLS.items():
            if symbol in raw:
                currency = code
                break

        # Strip everything except digits, dots, commas
        digits = re.sub(r"[^\d.,]", "", raw)

        if not digits:
            return None, currency, raw

        # Handle European format: "9,99" → "9.99"
        if "," in digits and "." not in digits:
            digits = digits.replace(",", ".")
        else:
            digits = digits.replace(",", "")

        try:
            return round(float(digits), 2), currency, raw
        except ValueError:
            return None, currency, raw

    def log_page(self, page_num: int, url: str, count: int) -> None:
        self.logger.info(f"Page {page_num} | {url} | {count} items found")