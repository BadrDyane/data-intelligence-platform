"""
Quotes to Scrape — quotes.toscrape.com

Demonstrates the platform can handle completely different
data structures from different sources.

Data extracted:
  - Quote text
  - Author name
  - Tags
  - Author URL

This proves the scraping engine is generic — not just for products.
"""

from bs4 import BeautifulSoup

from backend.scrapers.static_scraper import StaticScraper
from backend.scrapers.base_scraper import ScrapedItem, ScrapeResult

BASE_URL  = "https://quotes.toscrape.com"
MAX_PAGES = 10


class QuotesToScrapeScraper(StaticScraper):

    def __init__(self):
        super().__init__(
            source_name="quotes_toscrape",
            base_url=BASE_URL,
        )

    def _parse_quote(self, div: BeautifulSoup) -> ScrapedItem:
        # Quote text
        text = div.select_one("span.text")
        quote_text = text.get_text(strip=True) if text else "Unknown"

        # Author
        author_el = div.select_one("small.author")
        author    = author_el.get_text(strip=True) if author_el else "Unknown"

        # Author URL
        author_link = div.select_one("a[href*='author']")
        author_url  = f"{BASE_URL}{author_link['href']}" if author_link else BASE_URL

        # Tags
        tags = [t.get_text(strip=True) for t in div.select("a.tag")]

        # Use quote text as stable ID
        external_id = self.make_id("quotes_toscrape", quote_text[:100])

        return ScrapedItem(
            external_id  = external_id,
            source       = self.source_name,
            title        = f'"{quote_text[:120]}"',
            url          = author_url,
            price        = None,          # Quotes don't have prices
            currency     = "USD",
            category     = tags[0] if tags else "General",
            description  = f"By {author}",
            is_available = True,
            raw_data     = {
                "author":      author,
                "tags":        tags,
                "quote_text":  quote_text,
                "author_url":  author_url,
            },
        )

    async def scrape_page(self, url: str, page_num: int = 1) -> list[ScrapedItem]:
        html = await self._get(url)
        if not html:
            return []

        soup  = self.parse_html(html)
        divs  = soup.select("div.quote")
        items = []

        for div in divs:
            try:
                items.append(self._parse_quote(div))
            except Exception as e:
                self.logger.warning(f"Parse error on page {page_num}: {e}")

        self.log_page(page_num, url, len(items))
        return items

    async def scrape_all(self) -> ScrapeResult:
        result  = ScrapeResult(source=self.source_name)
        page    = 1
        url     = BASE_URL

        while page <= MAX_PAGES:
            try:
                items = await self.scrape_page(url, page)
                if not items:
                    break

                result.items.extend(items)
                result.pages_scraped += 1

                # Check for next page
                html = await self._get(url)
                if not html:
                    break

                soup     = self.parse_html(html)
                next_btn = soup.select_one("li.next a")
                if not next_btn:
                    break

                url  = f"{BASE_URL}{next_btn['href']}"
                page += 1

            except Exception as e:
                result.add_error(url, str(e))
                break

        self.logger.info(
            f"Completed: {len(result.items)} quotes across "
            f"{result.pages_scraped} pages "
            f"({result.error_count} errors)"
        )
        return result