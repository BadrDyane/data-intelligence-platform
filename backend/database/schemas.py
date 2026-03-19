"""
Pydantic v2 schemas — the contract between the API and the outside world.

Naming convention:
  - *Base    : shared fields
  - *Create  : fields required to create a resource (POST body)
  - *Update  : fields allowed to update a resource (PATCH body)
  - *Out     : what the API returns (response model)
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from backend.database.models import AlertCondition, AlertStatus, ScrapeStatus


# ── Source ────────────────────────────────────────────────────────────────────

class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                    int
    name:                  str
    display_name:          str
    base_url:              str
    scraper_class:         str
    is_active:             bool
    scrape_interval_hours: int
    created_at:            datetime


# ── Item ──────────────────────────────────────────────────────────────────────

class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    external_id:      str
    source:           str
    title:            str
    url:              str
    category:         Optional[str]
    current_price:    Optional[float]
    previous_price:   Optional[float]
    price_currency:   str
    price_change_pct: Optional[float]
    is_available:     bool
    extra_data:       dict
    first_seen_at:    datetime
    last_seen_at:     datetime
    last_scraped_at:  Optional[datetime]


class ItemListOut(BaseModel):
    """Paginated item list response."""
    items:       list[ItemOut]
    total:       int
    page:        int
    page_size:   int
    total_pages: int


# ── PriceSnapshot ─────────────────────────────────────────────────────────────

class PriceSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           int
    item_id:      int
    price:        Optional[float]
    currency:     str
    is_available: bool
    scraped_at:   datetime


class PriceTrendOut(BaseModel):
    """Time-series data for a single item — used by the chart."""
    item_id:       int
    item_title:    str
    snapshots:     list[PriceSnapshotOut]
    min_price:     Optional[float]
    max_price:     Optional[float]
    avg_price:     Optional[float]
    current_price: Optional[float]
    price_change_pct: Optional[float]   # Change from first to last snapshot


# ── ScrapeRun ─────────────────────────────────────────────────────────────────

class ScrapeRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    source:           str
    status:           ScrapeStatus
    triggered_by:     str
    started_at:       datetime
    completed_at:     Optional[datetime]
    duration_seconds: Optional[float]
    items_found:      int
    items_new:        int
    items_updated:    int
    items_unchanged:  int
    pages_scraped:    int
    error_count:      int
    error_log:        list


class TriggerScrapeRequest(BaseModel):
    source: str = Field(..., description="Source name to scrape, e.g. 'books_toscrape'")
    pages:  Optional[int] = Field(None, description="Max pages to scrape (None = all)")


# ── Alert ─────────────────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    item_id:      int
    condition:    AlertCondition
    threshold:    Optional[float] = None
    notify_email: Optional[str]   = None
    label:        Optional[str]   = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            int
    item_id:       int
    condition:     AlertCondition
    threshold:     Optional[float]
    status:        AlertStatus
    notify_email:  Optional[str]
    label:         Optional[str]
    created_at:    datetime
    last_fired_at: Optional[datetime]
    fire_count:    int


# ── Analytics ─────────────────────────────────────────────────────────────────

class SourceStatsOut(BaseModel):
    """Per-source statistics for the dashboard summary cards."""
    source:           str
    display_name:     str
    total_items:      int
    avg_price:        Optional[float]
    min_price:        Optional[float]
    max_price:        Optional[float]
    items_with_drop:  int      # Items whose price decreased since last scrape
    last_scraped_at:  Optional[datetime]


class DashboardSummaryOut(BaseModel):
    """Top-level numbers for the dashboard hero section."""
    total_items:        int
    total_sources:      int
    active_alerts:      int
    total_scrape_runs:  int
    last_run_at:        Optional[datetime]
    sources:            list[SourceStatsOut]


# ── Health ────────────────────────────────────────────────────────────────────

class HealthOut(BaseModel):
    status:      str
    version:     str
    db_reachable: bool