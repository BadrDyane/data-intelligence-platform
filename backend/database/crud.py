"""
CRUD layer — all database read/write operations.

Design principles:
  - Routes never write SQL. They call functions here.
  - All functions accept an AsyncSession and return ORM objects or dicts.
  - Upsert logic for items uses ON CONFLICT to handle re-scrapes cleanly.
  - Analytics queries use window functions for trend computation.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import select, func, text, update, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.database.models import (
    Alert, AlertCondition, AlertEvent, AlertStatus,
    Item, PriceSnapshot, ScrapeRun, ScrapeStatus, Source,
)
from backend.scrapers.base_scraper import ScrapedItem

logger = logging.getLogger(__name__)


# ── Sources ───────────────────────────────────────────────────────────────────

async def get_all_sources(db: AsyncSession) -> list[Source]:
    result = await db.execute(select(Source).where(Source.is_active == True))
    return result.scalars().all()


async def get_source(db: AsyncSession, name: str) -> Optional[Source]:
    result = await db.execute(select(Source).where(Source.name == name))
    return result.scalar_one_or_none()


async def create_source(db: AsyncSession, **kwargs) -> Source:
    source = Source(**kwargs)
    db.add(source)
    await db.flush()
    return source


# ── Items ─────────────────────────────────────────────────────────────────────

async def upsert_item(db: AsyncSession, scraped: ScrapedItem) -> tuple[Item, bool]:
    """
    Insert or update an item. Returns (item, is_new).
    """
    from sqlalchemy import select

    # Check if item already exists
    result = await db.execute(
        select(Item).where(
            Item.source == scraped.source,
            Item.external_id == scraped.external_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        # Brand new item
        item = Item(
            external_id=scraped.external_id,
            source=scraped.source,
            title=scraped.title,
            url=scraped.url,
            category=scraped.category,
            description=scraped.description,
            image_url=scraped.image_url,
            current_price=scraped.price,
            previous_price=None,
            price_currency=scraped.currency,
            price_change_pct=None,
            is_available=scraped.is_available,
            extra_data=scraped.raw_data,
            last_scraped_at=datetime.now(timezone.utc),
        )
        db.add(item)
        await db.flush()
        return item, True

    else:
        # Update existing item
        previous = existing.current_price

        # Compute price change percentage safely in Python
        if previous and previous != 0 and scraped.price is not None:
            change_pct = round((scraped.price - previous) / previous * 100, 2)
        else:
            change_pct = None

        existing.title = scraped.title
        existing.current_price = scraped.price
        existing.previous_price = previous
        existing.price_change_pct = change_pct
        existing.is_available = scraped.is_available
        existing.extra_data = scraped.raw_data
        existing.last_scraped_at = datetime.now(timezone.utc)

        await db.flush()
        return existing, False


async def get_items(
    db: AsyncSession,
    source: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Item], int]:
    """Returns (items, total_count) for pagination."""
    q = select(Item)

    if source:
        q = q.where(Item.source == source)
    if category:
        q = q.where(Item.category.ilike(f"%{category}%"))
    if search:
        q = q.where(Item.title.ilike(f"%{search}%"))
    if min_price is not None:
        q = q.where(Item.current_price >= min_price)
    if max_price is not None:
        q = q.where(Item.current_price <= max_price)

    # Total count (before pagination)
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginated result
    q = q.order_by(desc(Item.last_seen_at)).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(q)).scalars().all()

    return items, total


async def get_item(db: AsyncSession, item_id: int) -> Optional[Item]:
    return await db.get(Item, item_id)


# ── Price Snapshots ───────────────────────────────────────────────────────────

async def insert_snapshot(
    db: AsyncSession,
    item_id: int,
    price: Optional[float],
    is_available: bool,
    raw_price: Optional[str] = None,
    run_id: Optional[int] = None,
    currency: str = "USD",
) -> PriceSnapshot:
    snapshot = PriceSnapshot(
        item_id=item_id,
        run_id=run_id,
        price=price,
        currency=currency,
        is_available=is_available,
        raw_price=raw_price,
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


async def get_price_history(
    db: AsyncSession,
    item_id: int,
    limit: int = 90,
) -> list[PriceSnapshot]:
    """Last N snapshots for a single item, ordered oldest→newest for charting."""
    result = await db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.item_id == item_id)
        .order_by(PriceSnapshot.scraped_at.desc())
        .limit(limit)
    )
    # Reverse so the chart gets chronological order
    return list(reversed(result.scalars().all()))


# ── Scrape Runs ───────────────────────────────────────────────────────────────

async def create_run(
    db: AsyncSession,
    source: str,
    triggered_by: str = "scheduler",
) -> ScrapeRun:
    run = ScrapeRun(source=source, triggered_by=triggered_by, status=ScrapeStatus.RUNNING)
    db.add(run)
    await db.flush()
    return run


async def complete_run(
    db: AsyncSession,
    run_id: int,
    status: ScrapeStatus,
    items_found: int = 0,
    items_new: int = 0,
    items_updated: int = 0,
    items_unchanged: int = 0,
    pages_scraped: int = 0,
    error_count: int = 0,
    error_log: list = None,
) -> ScrapeRun:
    run = await db.get(ScrapeRun, run_id)
    run.status = status
    run.completed_at = datetime.now(timezone.utc)
    run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
    run.items_found = items_found
    run.items_new = items_new
    run.items_updated = items_updated
    run.items_unchanged = items_unchanged
    run.pages_scraped = pages_scraped
    run.error_count = error_count
    run.error_log = error_log or []
    await db.flush()
    return run


async def get_recent_runs(
    db: AsyncSession,
    source: Optional[str] = None,
    limit: int = 20,
) -> list[ScrapeRun]:
    q = select(ScrapeRun).order_by(desc(ScrapeRun.started_at)).limit(limit)
    if source:
        q = q.where(ScrapeRun.source == source)
    result = await db.execute(q)
    return result.scalars().all()


# ── Alerts ────────────────────────────────────────────────────────────────────

async def create_alert(
    db: AsyncSession,
    item_id: int,
    condition: AlertCondition,
    threshold: Optional[float] = None,
    notify_email: Optional[str] = None,
    label: Optional[str] = None,
) -> Alert:
    alert = Alert(
        item_id=item_id,
        condition=condition,
        threshold=threshold,
        notify_email=notify_email,
        label=label,
    )
    db.add(alert)
    await db.flush()
    return alert


async def get_active_alerts(db: AsyncSession) -> list[Alert]:
    result = await db.execute(
        select(Alert).where(Alert.status == AlertStatus.ACTIVE)
    )
    return result.scalars().all()


async def fire_alert(
    db: AsyncSession,
    alert: Alert,
    run_id: Optional[int],
    price: Optional[float],
    message: str,
) -> AlertEvent:
    """Record a fired alert and update the alert's metadata."""
    event = AlertEvent(
        alert_id=alert.id,
        run_id=run_id,
        price_at_fire=price,
        message=message,
        notified=False,
    )
    db.add(event)

    alert.last_fired_at = datetime.now(timezone.utc)
    alert.fire_count += 1
    await db.flush()
    return event


# ── Analytics ─────────────────────────────────────────────────────────────────

async def get_dashboard_summary(db: AsyncSession) -> dict:
    """
    Single query to power the dashboard summary cards.
    Returns aggregated stats across all sources.
    """
    total_items   = (await db.execute(select(func.count(Item.id)))).scalar_one()
    total_sources = (await db.execute(select(func.count(Source.id)).where(Source.is_active))).scalar_one()
    active_alerts = (await db.execute(select(func.count(Alert.id)).where(Alert.status == AlertStatus.ACTIVE))).scalar_one()
    total_runs    = (await db.execute(select(func.count(ScrapeRun.id)))).scalar_one()

    last_run = (await db.execute(
        select(ScrapeRun.started_at).order_by(desc(ScrapeRun.started_at)).limit(1)
    )).scalar_one_or_none()

    return {
        "total_items": total_items,
        "total_sources": total_sources,
        "active_alerts": active_alerts,
        "total_scrape_runs": total_runs,
        "last_run_at": last_run,
    }


async def get_source_stats(db: AsyncSession) -> list[dict]:
    """Per-source price statistics — powers the source comparison cards."""
    result = await db.execute(
        select(
            Item.source,
            func.count(Item.id).label("total_items"),
            func.avg(Item.current_price).label("avg_price"),
            func.min(Item.current_price).label("min_price"),
            func.max(Item.current_price).label("max_price"),
            func.max(Item.last_scraped_at).label("last_scraped_at"),
        )
        .group_by(Item.source)
    )
    rows = result.fetchall()
    stats = []
    for row in rows:
        stats.append({
            "source":          row.source,
            "total_items":     row.total_items,
            "avg_price":       round(row.avg_price, 2) if row.avg_price else None,
            "min_price":       round(row.min_price, 2) if row.min_price else None,
            "max_price":       round(row.max_price, 2) if row.max_price else None,
            "items_with_drop": 0,
            "last_scraped_at": row.last_scraped_at,
        })
    return stats