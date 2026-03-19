"""
Processing pipeline — transforms raw ScrapedItems into DB-ready clean data.

Pipeline stages (run in order):
  1. Validate    : reject items missing required fields
  2. Clean       : strip whitespace, fix encodings, normalize strings
  3. Deduplicate : remove intra-batch duplicates (same external_id)
  4. Normalize   : standardize categories, currencies, titles

Each stage is a pure function: list[ScrapedItem] → list[ScrapedItem].
The orchestrator (run_pipeline) wires them together and logs results.

Design: No database calls here. The pipeline works purely on ScrapedItem
objects. The CRUD layer handles persistence separately. This keeps the
pipeline testable in isolation with no DB dependency.
"""

import logging
import re
import unicodedata
from typing import Optional

from backend.scrapers.base_scraper import ScrapedItem

logger = logging.getLogger(__name__)


# ── Stage 1: Validate ─────────────────────────────────────────────────────────

def validate(items: list[ScrapedItem]) -> tuple[list[ScrapedItem], int]:
    """
    Reject items that are missing required fields or have clearly bad data.

    Returns (valid_items, rejected_count).
    """
    valid = []
    rejected = 0

    for item in items:
        if not item.external_id:
            logger.debug(f"Rejected: missing external_id — {item.title!r}")
            rejected += 1
            continue
        if not item.title or len(item.title.strip()) < 2:
            logger.debug(f"Rejected: empty/too-short title — {item.url}")
            rejected += 1
            continue
        if not item.url:
            logger.debug(f"Rejected: missing URL — {item.title!r}")
            rejected += 1
            continue
        if not item.source:
            logger.debug(f"Rejected: missing source — {item.title!r}")
            rejected += 1
            continue
        if item.price is not None and item.price < 0:
            logger.debug(f"Rejected: negative price ({item.price}) — {item.title!r}")
            rejected += 1
            continue

        valid.append(item)

    if rejected:
        logger.info(f"Validation: {len(valid)} valid, {rejected} rejected")
    return valid, rejected


# ── Stage 2: Clean ────────────────────────────────────────────────────────────

def clean_string(s: Optional[str]) -> Optional[str]:
    """
    Normalize a string:
      - Unicode NFC normalization (fixes garbled £ → £ encoding)
      - Collapse whitespace
      - Strip leading/trailing whitespace
    """
    if s is None:
        return None
    # NFC normalization fixes "Â£" → "£" and similar encoding artifacts
    s = unicodedata.normalize("NFC", s)
    # Collapse multiple spaces/tabs/newlines into a single space
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def clean_price(price: Optional[float]) -> Optional[float]:
    """Round price to 2 decimal places. Return None if zero (likely a parse error)."""
    if price is None:
        return None
    rounded = round(price, 2)
    return rounded if rounded > 0 else None


def clean(items: list[ScrapedItem]) -> list[ScrapedItem]:
    """Apply string and price cleaning to every item."""
    cleaned = []
    for item in items:
        item.title       = clean_string(item.title) or "Untitled"
        item.description = clean_string(item.description)
        item.category    = clean_string(item.category)
        item.url         = item.url.strip() if item.url else item.url
        item.price       = clean_price(item.price)
        cleaned.append(item)
    return cleaned


# ── Stage 3: Deduplicate ──────────────────────────────────────────────────────

def deduplicate(items: list[ScrapedItem]) -> tuple[list[ScrapedItem], int]:
    """
    Remove intra-batch duplicates using external_id as the key.

    Why this matters: If two pages both list the same product (e.g. pagination
    overlap, or a 'featured' section repeating items from the main listing),
    we only keep the first occurrence in the batch.

    The CRUD upsert handles cross-batch deduplication (same item seen in a
    previous scrape run). This stage handles within-run duplicates.

    Returns (deduped_items, removed_count).
    """
    seen = {}
    removed = 0

    for item in items:
        key = f"{item.source}|{item.external_id}"
        if key in seen:
            removed += 1
            logger.debug(f"Duplicate removed: {item.title!r} ({item.external_id})")
        else:
            seen[key] = item

    if removed:
        logger.info(f"Deduplication: removed {removed} duplicates, {len(seen)} remain")

    return list(seen.values()), removed


# ── Stage 4: Normalize ────────────────────────────────────────────────────────

# Map raw category strings → canonical names
CATEGORY_ALIASES: dict[str, str] = {
    "mystery":         "Mystery",
    "thriller":        "Thriller",
    "science fiction": "Science Fiction",
    "sci-fi":          "Science Fiction",
    "nonfiction":      "Non-Fiction",
    "non fiction":     "Non-Fiction",
    "self help":       "Self-Help",
    "self-help":       "Self-Help",
    "tech":            "Technology",
    "technology":      "Technology",
    "it":              "Technology",
}

SUPPORTED_CURRENCIES = {"USD", "GBP", "EUR", "JPY", "CAD", "AUD"}


def normalize_category(category: Optional[str]) -> Optional[str]:
    if not category:
        return None
    lowered = category.lower().strip()
    return CATEGORY_ALIASES.get(lowered, category.strip().title())


def normalize_currency(currency: str) -> str:
    upper = currency.upper()
    return upper if upper in SUPPORTED_CURRENCIES else "USD"


def normalize_title(title: str) -> str:
    """Truncate excessively long titles (some sites have 500+ char titles)."""
    return title[:495] + "…" if len(title) > 500 else title


def normalize(items: list[ScrapedItem]) -> list[ScrapedItem]:
    """Apply all normalization rules."""
    for item in items:
        item.category = normalize_category(item.category)
        item.currency = normalize_currency(item.currency)
        item.title    = normalize_title(item.title)
    return items


# ── Orchestrator ──────────────────────────────────────────────────────────────

class PipelineResult:
    """Summary of a pipeline run — useful for logging and monitoring."""

    def __init__(self):
        self.input_count:    int = 0
        self.rejected_count: int = 0
        self.duplicate_count:int = 0
        self.output_count:   int = 0

    @property
    def loss_pct(self) -> float:
        if self.input_count == 0:
            return 0.0
        return round((self.input_count - self.output_count) / self.input_count * 100, 1)

    def __str__(self):
        return (
            f"Pipeline: {self.input_count} in → "
            f"{self.rejected_count} rejected → "
            f"{self.duplicate_count} dupes → "
            f"{self.output_count} out "
            f"({self.loss_pct}% loss)"
        )


def run_pipeline(raw_items: list[ScrapedItem]) -> tuple[list[ScrapedItem], PipelineResult]:
    """
    Run the full processing pipeline on a list of raw scraped items.

    Returns (clean_items, PipelineResult).

    Usage:
        result = await scraper.scrape_all()
        clean_items, stats = run_pipeline(result.items)
        logger.info(stats)
        # Now persist clean_items via CRUD
    """
    stats = PipelineResult()
    stats.input_count = len(raw_items)

    # Stage 1: Validate
    items, stats.rejected_count = validate(raw_items)

    # Stage 2: Clean
    items = clean(items)

    # Stage 3: Deduplicate
    items, stats.duplicate_count = deduplicate(items)

    # Stage 4: Normalize
    items = normalize(items)

    stats.output_count = len(items)
    logger.info(str(stats))

    return items, stats