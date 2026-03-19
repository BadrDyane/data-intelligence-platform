"""
FastAPI application entry point.

Wires together:
  - Database initialization
  - Scheduler startup / shutdown
  - All API routers
  - CORS middleware
  - Health check endpoint
  - Global exception handler

Run with:
    uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.database.session import init_db
from backend.database.schemas import HealthOut
from backend.scheduler.scheduler import scheduler
from backend.scheduler.jobs import register_all_jobs
from backend.api.routes.items import router as items_router
from backend.api.routes.analytics import router as analytics_router
from backend.api.routes.scrape_alerts import scrape_router, alerts_router

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown logic.

    Startup:
      1. Create DB tables (idempotent)
      2. Seed the default source record if it doesn't exist
      3. Start the scheduler
      4. Register recurring scrape jobs

    Shutdown:
      1. Stop the scheduler cleanly
    """
    logger.info("=== Starting Data Intelligence Platform ===")

    # 1. Init database
    await init_db()
    logger.info("Database tables initialized")

    # 2. Seed default source
    await _seed_sources()

    # 3. Start scheduler
    if settings.SCHEDULER_ENABLED:
        scheduler.start()
        register_all_jobs()
        logger.info("Scheduler started")
    else:
        logger.info("Scheduler disabled via config")

    logger.info(f"API ready at http://0.0.0.0:8000{settings.API_PREFIX}")
    logger.info(f"Docs at     http://0.0.0.0:8000/docs")

    yield  # ← App runs here

    # Shutdown
    if settings.SCHEDULER_ENABLED and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    logger.info("=== Data Intelligence Platform shut down ===")


async def _seed_sources() -> None:
    """
    Insert the default source records if they don't already exist.
    This way the DB is always in a usable state after first startup.
    """
    from backend.database.session import AsyncSessionLocal
    from backend.database import crud

    async with AsyncSessionLocal() as db:
        existing = await crud.get_source(db, "books_toscrape")
        if not existing:
            await crud.create_source(
                db,
                name="books_toscrape",
                display_name="Books to Scrape",
                base_url="https://books.toscrape.com",
                scraper_class="BooksToScrapeScraper",
                is_active=True,
                scrape_interval_hours=6,
            )
            await db.commit()
            logger.info("Seeded source: books_toscrape")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Automated Data Intelligence Platform — scrapes, processes, "
        "and serves structured market data with trend analytics."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs."},
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(items_router,    prefix=settings.API_PREFIX)
app.include_router(analytics_router,prefix=settings.API_PREFIX)
app.include_router(scrape_router,   prefix=settings.API_PREFIX)
app.include_router(alerts_router,   prefix=settings.API_PREFIX)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthOut, tags=["system"])
async def health_check():
    """
    Lightweight health probe.
    Used by Docker health checks and uptime monitors.
    Returns DB reachability so you catch connection issues early.
    """
    db_ok = False
    try:
        from backend.database.session import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.warning(f"Health check DB ping failed: {e}")

    return HealthOut(
        status="healthy" if db_ok else "degraded",
        version=settings.APP_VERSION,
        db_reachable=db_ok,
    )


@app.get("/", tags=["system"])
async def root():
    return {
        "name":    settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs":    "/docs",
        "health":  "/health",
    }