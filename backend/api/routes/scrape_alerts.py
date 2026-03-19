"""
Scrape routes — manually trigger scrape jobs via the API.
Alert routes — create and manage price/availability alerts.

POST /scrape                — trigger a full scrape for a source
GET  /scrape/sources        — list available sources
POST /alerts                — create a new alert
GET  /alerts                — list all alerts
DELETE /alerts/{id}         — delete an alert
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_db
from backend.database import crud
from backend.database.schemas import AlertCreate, AlertOut, TriggerScrapeRequest
from backend.scheduler.jobs import SCRAPER_REGISTRY, run_scrape_job

logger = logging.getLogger(__name__)

scrape_router = APIRouter(prefix="/scrape", tags=["scrape"])
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])


# ── Scrape ────────────────────────────────────────────────────────────────────

@scrape_router.get("/sources")
async def list_scrape_sources():
    """
    List all registered scraper sources.
    Used by the dashboard's 'Trigger Scrape' dropdown.
    """
    return {"sources": list(SCRAPER_REGISTRY.keys())}


@scrape_router.post("")
async def trigger_scrape(
    body: TriggerScrapeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger a scrape for a source.

    Runs in the background so the response returns immediately.
    Poll GET /analytics/runs to track progress.

    This is what powers the 'Scrape Now' button in the dashboard.
    """
    if body.source not in SCRAPER_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source '{body.source}'. Available: {list(SCRAPER_REGISTRY)}",
        )

    background_tasks.add_task(run_scrape_job, body.source, "manual")
    logger.info(f"Manual scrape triggered for source={body.source!r}")

    return {
        "message": f"Scrape started for '{body.source}'",
        "source":  body.source,
        "tip":     "Poll GET /api/v1/analytics/runs to track progress",
    }


# ── Alerts ────────────────────────────────────────────────────────────────────

@alerts_router.post("", response_model=AlertOut)
async def create_alert(body: AlertCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new price/availability alert on a specific item.

    Conditions:
      - price_below   : fire when current_price < threshold
      - price_above   : fire when current_price > threshold
      - price_drop    : fire when price drops by threshold% or more
      - new_item      : fire when a new item appears in the source
    """
    item = await crud.get_item(db, body.item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {body.item_id} not found")

    alert = await crud.create_alert(
        db,
        item_id=body.item_id,
        condition=body.condition,
        threshold=body.threshold,
        notify_email=body.notify_email,
        label=body.label,
    )
    await db.commit()
    return AlertOut.model_validate(alert)


@alerts_router.get("", response_model=list[AlertOut])
async def list_alerts(db: AsyncSession = Depends(get_db)):
    """All active alerts."""
    alerts = await crud.get_active_alerts(db)
    return [AlertOut.model_validate(a) for a in alerts]


@alerts_router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Soft-delete an alert by setting status=DELETED."""
    from backend.database.models import Alert, AlertStatus
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    alert.status = AlertStatus.DELETED
    await db.commit()
    return {"deleted": alert_id}