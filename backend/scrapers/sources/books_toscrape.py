"""
Books to Scrape — books.toscrape.com

Updated to scrape by category so every book gets a proper category label
(Mystery, Fiction, Science, etc.) instead of defaulting to 'General'.

Strategy:
  1. Fetch the homepage and extract all category URLs + names
  2. Scrape each category page by page
  3. Tag every item with its category
"""

from bs4 import BeautifulSoup

from backend.scrapers.static_scraper import StaticScraper
from backend.scrapers.base_scraper import ScrapedItem, ScrapeResult

BASE_URL  = "https://books.toscrape.com"
CATALOGUE = f"{BASE_URL}/catalogue"

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

# Limit for demo — set to None to scrape all 50 categories
MAX_CATEGORIES = 10
MAX_PAGES_PER_CATEGORY = 5


class BooksToScrapeScraper(StaticScraper):

    def __init__(self):
        super().__init__(
            source_name="books_toscrape",
            base_url=BASE_URL,
        )

    # ── Step 1: get all category URLs ──────────────────────────────────────

    async def _get_categories(self) -> list[tuple[str, str]]:
        """
        Fetch the homepage and extract all category links.
        Returns a list of (category_name, category_url) tuples.

        Example:
            ("Mystery", "https://books.toscrape.com/catalogue/category/books/mystery_3/index.html")
        """
        html = await self._get(BASE_URL)
        if not html:
            return []

        soup = self.parse_html(html)

        # Category links are in the left sidebar under <ul class="nav nav-list">
        nav = soup.select_one("ul.nav.nav-list")
        if not nav:
            self.logger.warning("Could not find category nav — falling back to General")
            return []

        categories = []
        for a in nav.select("ul li a"):
            name = a.get_text(strip=True)
            href = a["href"].strip()
            # href is relative like "catalogue/category/books/mystery_3/index.html"
            url = f"{BASE_URL}/{href}"
            if name.lower() != "books":   # Skip the top-level "Books" link
                categories.append((name, url))

        self.logger.info(f"Found {len(categories)} categories")
        return categories

    # ── Step 2: parse a single book article ───────────────────────────────

    def _parse_article(
        self, article: BeautifulSoup, category: str
    ) -> ScrapedItem:
        a = article.select_one("h3 a")
        title = a["title"]
        href  = a["href"].replace("../", "").replace("../../", "")
        url   = f"{CATALOGUE}/{href}"

        raw_price = article.select_one(".price_color").get_text(strip=True)
        price, currency, _ = self.parse_price(raw_price)

        rating_el   = article.select_one(".star-rating")
        rating_word = rating_el["class"][1] if rating_el else "Zero"
        rating      = RATING_WORDS.get(rating_word, 0)

        avail_el  = article.select_one(".availability")
        available = (
            "in stock" in avail_el.get_text(strip=True).lower()
            if avail_el else True
        )

        return ScrapedItem(
            external_id  = self.make_id("books_toscrape", href),
            source       = self.source_name,
            title        = title,
            url          = url,
            price        = price,
            currency     = currency,
            raw_price    = raw_price,
            is_available = available,
            category     = category,
            raw_data     = {
                "rating":       rating,
                "rating_label": rating_word,
                "href":         href,
            },
        )

    # ── Step 3: scrape one category page ──────────────────────────────────

    async def scrape_page(
        self, url: str, page_num: int = 1
    ) -> list[ScrapedItem]:
        # Category pages have a "next" button — we pass the category name
        # via a different method, so this just returns items with no category
        html = await self._get(url)
        if not html:
            return []
        soup  = self.parse_html(html)
        items = []
        for article in soup.select("article.product_pod"):
            try:
                items.append(self._parse_article(article, "General"))
            except Exception as e:
                self.logger.warning(f"Parse error on {url}: {e}")
        return items

    async def _scrape_category(
        self, category_name: str, category_url: str
    ) -> tuple[list[ScrapedItem], int]:
        """
        Scrape all pages of a single category.
        Returns (items, pages_scraped).
        """
        all_items = []
        page_num  = 1
        url       = category_url

        while True:
            if MAX_PAGES_PER_CATEGORY and page_num > MAX_PAGES_PER_CATEGORY:
                break

            html = await self._get(url)
            if not html:
                break

            soup     = self.parse_html(html)
            articles = soup.select("article.product_pod")

            if not articles:
                break

            for article in articles:
                try:
                    item = self._parse_article(article, category_name)
                    all_items.append(item)
                except Exception as e:
                    self.logger.warning(
                        f"Parse error [{category_name}] page {page_num}: {e}"
                    )

            self.log_page(page_num, url, len(articles))

            # Check for a "next" button to get the next page URL
            next_btn = soup.select_one("li.next a")
            if not next_btn:
                break

            # Next href is relative to the current page's directory
            next_href = next_btn["href"]
            base_dir  = url.rsplit("/", 1)[0]
            url       = f"{base_dir}/{next_href}"
            page_num += 1

        return all_items, page_num - 1

    # ── Main orchestrator ──────────────────────────────────────────────────

    async def scrape_all(self) -> ScrapeResult:
        result = ScrapeResult(source=self.source_name)

        # Get all categories
        categories = await self._get_categories()
        if not categories:
            self.logger.error("No categories found — aborting")
            return result

        # Limit for demo
        if MAX_CATEGORIES:
            categories = categories[:MAX_CATEGORIES]
            self.logger.info(
                f"Scraping {len(categories)} categories "
                f"(MAX_CATEGORIES={MAX_CATEGORIES})"
            )

        # Scrape each category
        for category_name, category_url in categories:
            self.logger.info(f"Scraping category: {category_name}")
            try:
                items, pages = await self._scrape_category(
                    category_name, category_url
                )
                result.items.extend(items)
                result.pages_scraped += pages
                self.logger.info(
                    f"  {category_name}: {len(items)} items, {pages} pages"
                )
            except Exception as e:
                result.add_error(category_url, str(e))

        self.logger.info(
            f"Completed: {len(result.items)} items across "
            f"{result.pages_scraped} pages "
            f"({result.error_count} errors)"
        )
        return result