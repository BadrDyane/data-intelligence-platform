"""
Analytics routes — pre-aggregated data for the dashboard.

GET /analytics/summary        — hero numbers (total items, sources, alerts, runs)
GET /analytics/sources        — per-source statistics
GET /analytics/runs           — recent scrape run history
GET /analytics/runs/{run_id}  — single run detail
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_db
from backend.database import crud
from backend.database.schemas import DashboardSummaryOut, ScrapeRunOut, SourceOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=DashboardSummaryOut)
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    """
    Top-level dashboard numbers.

    Designed to power the 4 summary cards at the top of the dashboard:
      - Total items tracked
      - Active sources
      - Active alerts configured
      - Total scrape runs completed

    Also returns per-source stats for the source comparison panel.
    """
    summary = await crud.get_dashboard_summary(db)
    source_stats = await crud.get_source_stats(db)
    sources = await crud.get_all_sources(db)

    # Join display_name from source records into the stats
    source_display = {s.name: s.display_name for s in sources}
    enriched_stats = [
        {**stat, "display_name": source_display.get(stat["source"], stat["source"])}
        for stat in source_stats
    ]

    return DashboardSummaryOut(
        **summary,
        sources=enriched_stats,
    )


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(db: AsyncSession = Depends(get_db)):
    """All registered active sources."""
    sources = await crud.get_all_sources(db)
    return [SourceOut.model_validate(s) for s in sources]


@router.get("/runs", response_model=list[ScrapeRunOut])
async def list_runs(
    source: Optional[str] = Query(None),
    limit:  int           = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Recent scrape run history.

    Used by the 'Job Health' panel — shows clients the system is running
    reliably with full timing and outcome data for each run.
    """
    runs = await crud.get_recent_runs(db, source=source, limit=limit)
    return [ScrapeRunOut.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=ScrapeRunOut)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    """Single run detail — includes full error_log for debugging."""
    from sqlalchemy import select
    from backend.database.models import ScrapeRun
    result = await db.execute(select(ScrapeRun).where(ScrapeRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return ScrapeRunOut.model_validate(run)