"""
Database models — designed for historical tracking and trend analytics.

Core design decisions:
  - items           : one row per unique trackable entity (product, job listing, etc.)
  - price_snapshots : append-only time-series — NEVER update, always insert.
                      This is what powers the trend charts.
  - scrape_runs     : job metadata for the operations dashboard.
  - alerts          : user-configured price/availability triggers.
  - alert_events    : fired alert history (for the notification log).
"""

import enum
from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, Float,
    ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


# ── Base ──────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Enums ─────────────────────────────────────────────────────────────────────

class ScrapeStatus(str, enum.Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    FAILED    = "failed"
    PARTIAL   = "partial"      # Completed but with some errors


class AlertCondition(str, enum.Enum):
    PRICE_BELOW   = "price_below"    # Notify when price drops below threshold
    PRICE_ABOVE   = "price_above"    # Notify when price rises above threshold
    PRICE_DROP    = "price_drop"     # Notify on any price decrease (%)
    NEW_ITEM      = "new_item"       # Notify when a new item appears
    AVAILABILITY  = "availability"   # Notify when item comes back in stock


class AlertStatus(str, enum.Enum):
    ACTIVE   = "active"
    FIRED    = "fired"
    PAUSED   = "paused"
    DELETED  = "deleted"


# ── Source ────────────────────────────────────────────────────────────────────

class Source(Base):
    """
    A registered data source (website / feed).
    Scrapers reference this to tag where data came from.
    """
    __tablename__ = "sources"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    name          = Column(String(100), unique=True, nullable=False)  # e.g. "books_toscrape"
    display_name  = Column(String(200), nullable=False)               # e.g. "Books to Scrape"
    base_url      = Column(String(500), nullable=False)
    scraper_class = Column(String(100), nullable=False)               # Python class name
    is_active     = Column(Boolean, default=True, nullable=False)
    scrape_interval_hours = Column(Integer, default=6, nullable=False)
    config        = Column(JSON, default={})                          # Source-specific settings
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    items       = relationship("Item", back_populates="source_rel", lazy="dynamic")
    scrape_runs = relationship("ScrapeRun", back_populates="source_rel", lazy="dynamic")

    def __repr__(self):
        return f"<Source name={self.name!r} active={self.is_active}>"


# ── Item ──────────────────────────────────────────────────────────────────────

class Item(Base):
    """
    A canonical tracked entity — one row per unique thing we monitor.

    external_id is the stable identifier within a source (URL slug, product ID,
    job listing ID). The (source, external_id) pair is unique.

    current_price is denormalized here for fast dashboard queries.
    The full price history lives in price_snapshots.
    """
    __tablename__ = "items"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    external_id   = Column(String(64), nullable=False)   # SHA-256 hash of stable URL/ID
    source        = Column(String(100), ForeignKey("sources.name"), nullable=False)
    title         = Column(String(500), nullable=False)
    url           = Column(String(1000), nullable=False)
    category      = Column(String(200), nullable=True)
    description   = Column(Text, nullable=True)
    image_url     = Column(String(1000), nullable=True)

    # Denormalized current state (updated each scrape)
    current_price      = Column(Float, nullable=True)
    previous_price     = Column(Float, nullable=True)
    price_currency     = Column(String(10), default="USD")
    price_change_pct   = Column(Float, nullable=True)   # Computed: (curr-prev)/prev * 100
    is_available       = Column(Boolean, default=True)

    # Metadata
    extra_data    = Column(JSON, default={})            # Source-specific fields (rating, etc.)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)

    # Constraints & indexes
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_item_source_external"),
        Index("ix_item_source",       "source"),
        Index("ix_item_current_price","current_price"),
        Index("ix_item_last_seen",    "last_seen_at"),
        Index("ix_item_category",     "category"),
    )

    # Relationships
    source_rel      = relationship("Source", back_populates="items", foreign_keys=[source])
    price_snapshots = relationship("PriceSnapshot", back_populates="item",
                                   cascade="all, delete-orphan", lazy="dynamic")
    alerts          = relationship("Alert", back_populates="item",
                                   cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<Item id={self.id} title={self.title[:40]!r} price={self.current_price}>"


# ── PriceSnapshot ─────────────────────────────────────────────────────────────

class PriceSnapshot(Base):
    """
    Append-only time-series table — one row per scrape per item.
    NEVER update rows here. Always insert.

    This is the source of truth for all trend charts and analytics.
    The LAG() window function over this table powers price change detection.
    """
    __tablename__ = "price_snapshots"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    item_id     = Column(BigInteger, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    run_id      = Column(BigInteger, ForeignKey("scrape_runs.id"), nullable=True)
    price       = Column(Float, nullable=True)
    currency    = Column(String(10), default="USD")
    is_available = Column(Boolean, default=True)
    raw_price   = Column(String(50), nullable=True)   # Original string before parsing ("£12.99")
    scraped_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_snapshot_item_time", "item_id", "scraped_at"),   # Critical for trend queries
        Index("ix_snapshot_run",       "run_id"),
        Index("ix_snapshot_scraped_at","scraped_at"),
    )

    # Relationships
    item = relationship("Item", back_populates="price_snapshots")
    run  = relationship("ScrapeRun", back_populates="snapshots")

    def __repr__(self):
        return f"<PriceSnapshot item_id={self.item_id} price={self.price} at={self.scraped_at}>"


# ── ScrapeRun ─────────────────────────────────────────────────────────────────

class ScrapeRun(Base):
    """
    Metadata about each scraping job execution.
    Powers the 'job health' panel in the dashboard — shows clients
    that the system is running reliably and gives full audit history.
    """
    __tablename__ = "scrape_runs"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    source          = Column(String(100), ForeignKey("sources.name"), nullable=False)
    status          = Column(Enum(ScrapeStatus), default=ScrapeStatus.PENDING, nullable=False)
    triggered_by    = Column(String(50), default="scheduler")   # "scheduler" | "manual" | "api"

    # Timing
    started_at      = Column(DateTime(timezone=True), server_default=func.now())
    completed_at    = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Results
    items_found     = Column(Integer, default=0)    # Raw count from scraper
    items_new       = Column(Integer, default=0)    # Brand new items inserted
    items_updated   = Column(Integer, default=0)    # Existing items with changed data
    items_unchanged = Column(Integer, default=0)    # No change detected
    pages_scraped   = Column(Integer, default=0)

    # Error tracking
    error_count     = Column(Integer, default=0)
    error_log       = Column(JSON, default=[])      # List of {url, error, timestamp}
    notes           = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_run_source",     "source"),
        Index("ix_run_status",     "status"),
        Index("ix_run_started_at", "started_at"),
    )

    # Relationships
    source_rel = relationship("Source", back_populates="scrape_runs", foreign_keys=[source])
    snapshots  = relationship("PriceSnapshot", back_populates="run", lazy="dynamic")
    alerts     = relationship("AlertEvent", back_populates="run", lazy="dynamic")

    def __repr__(self):
        return f"<ScrapeRun id={self.id} source={self.source!r} status={self.status}>"


# ── Alert ─────────────────────────────────────────────────────────────────────

class Alert(Base):
    """
    A user-configured monitoring rule on a specific item.
    After each scrape run, the alert checker evaluates these rules
    against the latest price snapshot.
    """
    __tablename__ = "alerts"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    item_id     = Column(BigInteger, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    condition   = Column(Enum(AlertCondition), nullable=False)
    threshold   = Column(Float, nullable=True)      # Price value or % drop
    status      = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False)
    notify_email = Column(String(200), nullable=True)
    label       = Column(String(200), nullable=True)  # User-friendly name for the alert

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    last_fired_at = Column(DateTime(timezone=True), nullable=True)
    fire_count  = Column(Integer, default=0)

    __table_args__ = (
        Index("ix_alert_item",   "item_id"),
        Index("ix_alert_status", "status"),
    )

    # Relationships
    item   = relationship("Item", back_populates="alerts")
    events = relationship("AlertEvent", back_populates="alert", lazy="dynamic")

    def __repr__(self):
        return f"<Alert id={self.id} item_id={self.item_id} condition={self.condition}>"


# ── AlertEvent ────────────────────────────────────────────────────────────────

class AlertEvent(Base):
    """
    A record of every time an alert fired.
    Displayed in the notification log panel.
    """
    __tablename__ = "alert_events"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    alert_id    = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    run_id      = Column(BigInteger, ForeignKey("scrape_runs.id"), nullable=True)
    fired_at    = Column(DateTime(timezone=True), server_default=func.now())
    price_at_fire = Column(Float, nullable=True)
    message     = Column(Text, nullable=True)
    notified    = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_alert_event_alert",  "alert_id"),
        Index("ix_alert_event_fired",  "fired_at"),
    )

    # Relationships
    alert = relationship("Alert", back_populates="events")
    run   = relationship("ScrapeRun", back_populates="alerts")

    def __repr__(self):
        return f"<AlertEvent alert_id={self.alert_id} fired_at={self.fired_at}>"