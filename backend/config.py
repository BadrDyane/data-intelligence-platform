"""
Central configuration — all environment variables loaded here.
Every module imports from config, never reads os.environ directly.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────────
    APP_NAME: str = "Data Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # ── Database ───────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://dip_user:dip_pass@localhost:5432/dip_db"
    DB_ECHO_SQL: bool = False          # Set True to log all SQL queries

    # ── Scraping ───────────────────────────────────────────────────────
    SCRAPE_DELAY_MIN: float = 1.5      # Seconds between requests (min)
    SCRAPE_DELAY_MAX: float = 3.5      # Seconds between requests (max)
    SCRAPE_TIMEOUT: int = 30           # HTTP timeout in seconds
    SCRAPE_MAX_RETRIES: int = 3        # Retry attempts on failure
    PLAYWRIGHT_HEADLESS: bool = True   # False to watch browser during dev

    # ── Scheduler ─────────────────────────────────────────────────────
    SCHEDULER_ENABLED: bool = True
    DEFAULT_SCRAPE_INTERVAL_HOURS: int = 6

    # ── Alerts ────────────────────────────────────────────────────────
    ALERT_EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""

    # ── CORS ──────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton — imports never create multiple Settings objects."""
    return Settings()


settings = get_settings()