"""
Items routes — CRUD endpoints for tracked items.

GET  /items           — paginated list with filters
GET  /items/{id}      — single item detail
GET  /items/{id}/trend — price history for charting
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_db
from backend.database import crud
from backend.database.schemas import ItemOut, ItemListOut, PriceTrendOut, PriceSnapshotOut

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=ItemListOut)
async def list_items(
    source:    Optional[str]   = Query(None, description="Filter by source name"),
    category:  Optional[str]   = Query(None, description="Filter by category (partial match)"),
    search:    Optional[str]   = Query(None, description="Search by title (partial match)"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    page:      int             = Query(1, ge=1),
    page_size: int             = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Paginated item list with filtering and search.

    All filters are optional and combinable. Results are sorted by
    last_seen_at descending (most recently scraped first).
    """
    items, total = await crud.get_items(
        db,
        source=source,
        category=category,
        search=search,
        min_price=min_price,
        max_price=max_price,
        page=page,
        page_size=page_size,
    )
    return ItemListOut(
        items=[ItemOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    """Single item by ID with all current fields."""
    item = await crud.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return ItemOut.model_validate(item)


@router.get("/{item_id}/trend", response_model=PriceTrendOut)
async def get_price_trend(
    item_id: int,
    days:    int = Query(30, ge=1, le=365, description="Number of days of history"),
    db: AsyncSession = Depends(get_db),
):
    """
    Price history for a single item — used by the line chart in the dashboard.

    Returns snapshots ordered oldest → newest (correct for Chart.js).
    Includes aggregate stats (min, max, avg) pre-computed for the summary card.
    """
    item = await crud.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    # 1 snapshot per day max ≈ days limit (using per-run snapshots, could be more)
    snapshots = await crud.get_price_history(db, item_id, limit=days * 3)

    prices = [s.price for s in snapshots if s.price is not None]

    # Price change from first to last snapshot
    change_pct = None
    if len(prices) >= 2:
        change_pct = round((prices[-1] - prices[0]) / prices[0] * 100, 2) if prices[0] else None

    return PriceTrendOut(
        item_id=item_id,
        item_title=item.title,
        snapshots=[PriceSnapshotOut.model_validate(s) for s in snapshots],
        min_price=round(min(prices), 2) if prices else None,
        max_price=round(max(prices), 2) if prices else None,
        avg_price=round(sum(prices) / len(prices), 2) if prices else None,
        current_price=item.current_price,
        price_change_pct=change_pct,
    )