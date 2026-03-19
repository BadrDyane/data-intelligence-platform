"""
Books to Scrape — books.toscrape.com

A legal, purpose-built scraping sandbox. Used as the primary demo source
because it has real price data, categories, ratings, and 50 pages of content.

Demonstrates:
  - Pagination (50 pages of 20 items each)
  - Price parsing (British pounds with encoding quirks)
  - Category extraction
  - Rating extraction
  - Availability detection

This is the source you use in all demos and load tests.
"""

import asyncio
from bs4 import BeautifulSoup

from backend.scrapers.static_scraper import StaticScraper
from backend.scrapers.base_scraper import ScrapedItem, ScrapeResult

BASE_URL     = "https://books.toscrape.com"
CATALOGUE    = f"{BASE_URL}/catalogue"
START_URL    = f"{CATALOGUE}/page-1.html"
MAX_PAGES    = 50   # Site has exactly 50 pages

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


class BooksToScrapeScraper(StaticScraper):

    def __init__(self, max_pages: int = MAX_PAGES):
        super().__init__(
            source_name="books_toscrape",
            base_url=BASE_URL,
        )
        self.max_pages = max_pages

    # ── Core parsing ───────────────────────────────────────────────────────────

    def _parse_article(self, article: BeautifulSoup) -> ScrapedItem:
        """Extract a single book from an <article class='product_pod'> element."""

        # Title + URL
        a = article.select_one("h3 a")
        title = a["title"]
        href  = a["href"].replace("../", "")
        url   = f"{CATALOGUE}/{href}"

        # Price — site uses "Â£" encoding quirk for £
        raw_price = article.select_one(".price_color").get_text(strip=True)
        price, currency, _ = self.parse_price(raw_price)

        # Star rating (stored as word in the class name: "star-rating Three")
        rating_el   = article.select_one(".star-rating")
        rating_word = rating_el["class"][1] if rating_el else "Zero"
        rating      = RATING_WORDS.get(rating_word, 0)

        # Availability
        avail_text = article.select_one(".availability")
        available  = "in stock" in avail_text.get_text(strip=True).lower() if avail_text else True

        return ScrapedItem(
            external_id  = self.make_id("books_toscrape", href),
            source       = self.source_name,
            title        = title,
            url          = url,
            price        = price,
            currency     = currency,
            raw_price    = raw_price,
            is_available = available,
            category     = None,    # Populated in scrape_page() from page context
            raw_data     = {
                "rating":        rating,
                "rating_label":  rating_word,
                "href":          href,
            },
        )

    def _parse_category(self, soup: BeautifulSoup) -> str:
        """Extract the category name from a listing page's breadcrumb."""
        breadcrumbs = soup.select("ul.breadcrumb li")
        # Breadcrumb: Home > Books > [Category] > (if on category page)
        if len(breadcrumbs) >= 3:
            return breadcrumbs[2].get_text(strip=True)
        return "General"

    # ── BaseScraper implementation ─────────────────────────────────────────────

    async def scrape_page(self, url: str, page_num: int = 1) -> list[ScrapedItem]:
        html = await self._get(url)
        if not html:
            return []

        soup     = self.parse_html(html)
        category = self._parse_category(soup)
        articles = soup.select("article.product_pod")

        items = []
        for article in articles:
            try:
                item = self._parse_article(article)
                item.category = category
                items.append(item)
            except Exception as e:
                self.logger.warning(f"Failed to parse article on page {page_num}: {e}")

        self.log_page(page_num, url, len(items))
        return items

    async def scrape_all(self) -> ScrapeResult:
        result = ScrapeResult(source=self.source_name)

        for page_num in range(1, self.max_pages + 1):
            url = f"{CATALOGUE}/page-{page_num}.html"
            try:
                items = await self.scrape_page(url, page_num)
                if not items:
                    # Empty page = we've gone past the last page
                    self.logger.info(f"No items on page {page_num}. Stopping.")
                    break
                result.items.extend(items)
                result.pages_scraped += 1
            except Exception as e:
                result.add_error(url, str(e))

        self.logger.info(
            f"Completed: {len(result.items)} items across {result.pages_scraped} pages "
            f"({result.error_count} errors)"
        )
        return result