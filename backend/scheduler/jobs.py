"""
Scheduler jobs — async functions that run on a schedule.

Each job:
  1. Creates a ScrapeRun record (status=RUNNING)
  2. Runs the appropriate scraper
  3. Runs the processing pipeline
  4. Persists items + snapshots to the DB
  5. Updates the ScrapeRun record (status=SUCCESS/FAILED)
  6. Evaluates alerts against new snapshots

The scheduler calls run_scrape_job(source_name) — everything else is internal.
"""

import logging
from datetime import datetime, timezone

from backend.database.session import AsyncSessionLocal
from backend.database import crud
from backend.database.models import ScrapeStatus
from backend.processing.pipeline import run_pipeline
from backend.scrapers.sources.books_toscrape import BooksToScrapeScraper

logger = logging.getLogger(__name__)

# Registry maps source name → scraper class
# Add new sources here when you build them.
SCRAPER_REGISTRY: dict = {
    "books_toscrape": BooksToScrapeScraper,
}


async def run_scrape_job(source_name: str, triggered_by: str = "scheduler") -> dict:
    """
    Full scrape-process-persist pipeline for one source.

    Returns a summary dict for the API response (when triggered manually).
    Raises no exceptions — all errors are logged and recorded in ScrapeRun.
    """
    logger.info(f"Starting scrape job: source={source_name!r} triggered_by={triggered_by!r}")

    if source_name not in SCRAPER_REGISTRY:
        logger.error(f"Unknown source: {source_name!r}. Available: {list(SCRAPER_REGISTRY)}")
        return {"error": f"Unknown source: {source_name}"}

    async with AsyncSessionLocal() as db:
        # ── Step 1: Create the run record ─────────────────────────────────────
        run = await crud.create_run(db, source=source_name, triggered_by=triggered_by)
        await db.commit()
        run_id = run.id
        logger.info(f"ScrapeRun created: id={run_id}")

    # ── Step 2: Scrape ────────────────────────────────────────────────────────
    ScraperClass = SCRAPER_REGISTRY[source_name]
    scrape_result = None

    try:
        async with ScraperClass() as scraper:
            scrape_result = await scraper.scrape_all()
    except Exception as e:
        logger.error(f"Scraper crashed for {source_name!r}: {e}", exc_info=True)
        async with AsyncSessionLocal() as db:
            await crud.complete_run(
                db, run_id,
                status=ScrapeStatus.FAILED,
                error_count=1,
                error_log=[{"url": "scraper_init", "error": str(e)}],
            )
            await db.commit()
        return {"error": str(e), "run_id": run_id}

    # ── Step 3: Process ───────────────────────────────────────────────────────
    clean_items, pipeline_stats = run_pipeline(scrape_result.items)
    logger.info(f"Pipeline complete: {pipeline_stats}")

    # ── Step 4: Persist ───────────────────────────────────────────────────────
    items_new = items_updated = items_unchanged = 0

    async with AsyncSessionLocal() as db:
        for scraped in clean_items:
            try:
                item, is_new = await crud.upsert_item(db, scraped)

                # Always insert a snapshot row — even if price didn't change.
                # The unchanged rows still confirm the item is still live.
                await crud.insert_snapshot(
                    db,
                    item_id=item.id,
                    price=scraped.price,
                    is_available=scraped.is_available,
                    raw_price=scraped.raw_price,
                    run_id=run_id,
                    currency=scraped.currency,
                )

                if is_new:
                    items_new += 1
                elif item.current_price != item.previous_price:
                    items_updated += 1
                else:
                    items_unchanged += 1

            except Exception as e:
                logger.error(f"Failed to persist item {scraped.title!r}: {e}")
                scrape_result.add_error(scraped.url, str(e))

        # ── Step 5: Finalize run record ───────────────────────────────────────
        final_status = (
            ScrapeStatus.SUCCESS if scrape_result.error_count == 0
            else ScrapeStatus.PARTIAL if len(clean_items) > 0
            else ScrapeStatus.FAILED
        )
        await crud.complete_run(
            db, run_id,
            status=final_status,
            items_found=len(scrape_result.items),
            items_new=items_new,
            items_updated=items_updated,
            items_unchanged=items_unchanged,
            pages_scraped=scrape_result.pages_scraped,
            error_count=scrape_result.error_count,
            error_log=scrape_result.errors,
        )
        await db.commit()

    # ── Step 6: Evaluate alerts ───────────────────────────────────────────────
    try:
        await evaluate_alerts(run_id)
    except Exception as e:
        logger.error(f"Alert evaluation failed: {e}", exc_info=True)

    summary = {
        "run_id":           run_id,
        "source":           source_name,
        "status":           final_status.value,
        "items_found":      len(scrape_result.items),
        "items_new":        items_new,
        "items_updated":    items_updated,
        "items_unchanged":  items_unchanged,
        "pages_scraped":    scrape_result.pages_scraped,
        "error_count":      scrape_result.error_count,
    }
    logger.info(f"Scrape job complete: {summary}")
    return summary


async def evaluate_alerts(run_id: int) -> None:
    """
    Check all active alerts against the latest price data.

    Called after every scrape run. Fires alert events for any condition
    that is now met, and logs them for the notification panel.
    """
    from backend.database.models import AlertCondition

    async with AsyncSessionLocal() as db:
        alerts = await crud.get_active_alerts(db)
        if not alerts:
            return

        logger.info(f"Evaluating {len(alerts)} active alerts")

        for alert in alerts:
            item = await crud.get_item(db, alert.item_id)
            if not item or item.current_price is None:
                continue

            fired = False
            message = ""

            if alert.condition == AlertCondition.PRICE_BELOW:
                if item.current_price < alert.threshold:
                    fired = True
                    message = f"Price dropped to {item.current_price} (threshold: {alert.threshold})"

            elif alert.condition == AlertCondition.PRICE_ABOVE:
                if item.current_price > alert.threshold:
                    fired = True
                    message = f"Price rose to {item.current_price} (threshold: {alert.threshold})"

            elif alert.condition == AlertCondition.PRICE_DROP:
                if item.price_change_pct is not None and item.price_change_pct < -(alert.threshold or 0):
                    fired = True
                    pct = abs(item.price_change_pct)
                    message = f"Price dropped {pct:.1f}% to {item.current_price}"

            if fired:
                await crud.fire_alert(db, alert, run_id, item.current_price, message)
                logger.info(f"Alert {alert.id} fired: {message}")

        await db.commit()


def register_all_jobs() -> None:
    """
    Register recurring scrape jobs for all sources.
    Called once on application startup.

    Uses 'replace_existing=True' so restarts don't create duplicate jobs.
    """
    from backend.scheduler.scheduler import scheduler

    for source_name in SCRAPER_REGISTRY:
        job_id = f"scrape_{source_name}"
        scheduler.add_job(
            run_scrape_job,
            trigger="interval",
            hours=settings.DEFAULT_SCRAPE_INTERVAL_HOURS,
            id=job_id,
            name=f"Scrape {source_name}",
            kwargs={"source_name": source_name, "triggered_by": "scheduler"},
            replace_existing=True,
        )
        logger.info(
            f"Scheduled job '{job_id}' every {settings.DEFAULT_SCRAPE_INTERVAL_HOURS}h"
        )


# Import here to avoid circular import
from backend.config import settings