# DataIntel — Automated Data Intelligence Platform

A full-stack data scraping, processing, and analytics platform that automatically collects data from websites, processes it through a cleaning pipeline, stores it in a structured database, and presents it in a professional dashboard with real-time price monitoring and alerts.

Built as a portfolio project to demonstrate end-to-end software engineering capability across data engineering, backend development, and frontend development.

---

## Live Demo

> Run locally following the setup instructions below.
> Demo video: [coming soon]

---

## Screenshots

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### Items Detail View
![Items](docs/screenshots/items.png)

### Scrape Runs History
![Runs](docs/screenshots/runs.png)

### Price Alerts
![Alerts](docs/screenshots/alerts.png)

---

## What This Platform Does

This platform simulates real business use cases:

- **Competitor price tracking** — monitor product prices across multiple websites automatically
- **Market intelligence** — collect and analyze data from any website on a schedule
- **Price alert system** — get notified when prices drop below or rise above your thresholds
- **Business automation** — replace manual data collection with an automated pipeline

---

## Features

### Backend
- Automated web scraping with BeautifulSoup and Playwright
- Anti-detection techniques — rotating User-Agents, polite delays, robots.txt compliance, exponential backoff retries
- 4-stage data processing pipeline — validate, clean, deduplicate, normalize
- Historical price tracking — append-only snapshot table for trend analytics
- APScheduler — automatic scraping on configurable intervals
- Price alert system — fires and records alerts after every scrape run
- Email notifications via SMTP when alerts trigger
- Full REST API with pagination, filtering, and search
- Job health monitoring — every scrape run logged with timing and outcome

### Frontend
- Live dashboard with summary cards pulling real data from the API
- Searchable, filterable, paginated data table
- Price trend charts with historical data points
- Multi-source filtering with dynamic category detection
- Price change badges — visual indicators for price drops and increases
- Live "Scrape Now" button with real-time feedback
- Scrape runs history page with status badges and duration
- Price alerts page — create, view, and delete monitoring rules
- Bell indicator on items that have active alerts
- Item detail panel — full metadata, tags, author, price history chart

---

## Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| Python 3.11 | Core language |
| FastAPI | REST API framework |
| SQLAlchemy 2.0 (async) | ORM and database layer |
| PostgreSQL | Primary database |
| asyncpg | Async PostgreSQL driver |
| httpx | Async HTTP client for scraping |
| BeautifulSoup4 | HTML parsing |
| Playwright | JavaScript-rendered page scraping |
| Pandas | Data processing pipeline |
| APScheduler | Job scheduling |
| Pydantic v2 | Data validation and settings |

### Frontend
| Technology | Purpose |
|---|---|
| React 18 | UI framework |
| Vite | Build tool and dev server |
| Recharts | Price trend charts |
| Axios | API client |
| React Router | Navigation |

### Infrastructure
| Technology | Purpose |
|---|---|
| Docker | PostgreSQL containerization |
| Git | Version control |

---

## Architecture
```
Scheduler (APScheduler)
    ↓
Scraper Engine (BeautifulSoup / Playwright)
    ↓
Processing Pipeline (validate → clean → deduplicate → normalize)
    ↓
PostgreSQL Database (items + price_snapshots + scrape_runs + alerts)
    ↓
FastAPI REST API
    ↓
React Dashboard
```

### Database Schema

- **sources** — registered data sources (websites)
- **items** — one row per tracked entity with current state
- **price_snapshots** — append-only time-series, one row per scrape per item
- **scrape_runs** — metadata for every job execution
- **alerts** — user-configured monitoring rules
- **alert_events** — fired alert history

---

## Data Sources

| Source | Type | Items | Update Frequency |
|---|---|---|---|
| books.toscrape.com | Product prices | 320 | Every 6 hours |
| quotes.toscrape.com | Quote content | 100 | Every 6 hours |

New sources can be added by creating a single Python file in `backend/scrapers/sources/` and registering it in the scheduler.

---

## Project Structure
```
data-intelligence-platform/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app with lifespan
│   │   └── routes/
│   │       ├── items.py         # Item endpoints
│   │       ├── analytics.py     # Dashboard analytics
│   │       └── scrape_alerts.py # Scrape trigger + alerts
│   ├── database/
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic response schemas
│   │   ├── crud.py              # All DB operations
│   │   └── session.py           # Async engine + session factory
│   ├── scrapers/
│   │   ├── base_scraper.py      # Abstract base + ScrapedItem
│   │   ├── static_scraper.py    # httpx + BeautifulSoup
│   │   ├── dynamic_scraper.py   # Playwright browser automation
│   │   └── sources/
│   │       ├── books_toscrape.py
│   │       └── quotes_toscrape.py
│   ├── processing/
│   │   └── pipeline.py          # 4-stage processing pipeline
│   ├── scheduler/
│   │   ├── scheduler.py         # APScheduler setup
│   │   └── jobs.py              # Scrape + alert jobs
│   └── config.py                # Pydantic settings
├── frontend/
│   └── src/
│       ├── api/client.js        # Axios API client
│       ├── components/
│       │   ├── SummaryCards.jsx
│       │   ├── DataTable.jsx
│       │   ├── PriceChart.jsx
│       │   ├── ScrapeButton.jsx
│       │   └── AlertModal.jsx
│       └── pages/
│           ├── Dashboard.jsx
│           ├── Items.jsx
│           ├── Runs.jsx
│           └── Alerts.jsx
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Local Setup

### Prerequisites
- Python 3.11
- Node.js 18+
- Docker Desktop

### Backend Setup
```bash
# Clone the repository
git clone https://github.com/BadrDyane/data-intelligence-platform.git
cd data-intelligence-platform

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Start PostgreSQL
docker compose up -d postgres

# Copy environment file
cp .env.example .env

# Start the API
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### First Scrape

Once both servers are running, go to `http://localhost:8000/docs` and call:
```
POST /api/v1/scrape
{"source": "books_toscrape"}
```

Or click the **Scrape Now** button in the dashboard.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/v1/items | Paginated items with filters |
| GET | /api/v1/items/{id} | Single item detail |
| GET | /api/v1/items/{id}/trend | Price history for charts |
| GET | /api/v1/analytics/summary | Dashboard summary numbers |
| GET | /api/v1/analytics/runs | Scrape run history |
| POST | /api/v1/scrape | Trigger manual scrape |
| GET | /api/v1/alerts | List active alerts |
| POST | /api/v1/alerts | Create price alert |
| DELETE | /api/v1/alerts/{id} | Delete alert |

Full interactive documentation available at `http://localhost:8000/docs`

---

## Adding a New Data Source

1. Create `backend/scrapers/sources/your_source.py`
2. Extend `StaticScraper` or `DynamicScraper`
3. Implement `scrape_page()` and `scrape_all()`
4. Register in `backend/scheduler/jobs.py`

The scraping engine, processing pipeline, database, API, and dashboard all work automatically with any new source.

---

## Business Use Cases

This platform can be adapted for:

- **E-commerce** — monitor competitor prices across Amazon, eBay, or any online store
- **Real estate** — track property listing prices by neighborhood
- **Job market** — aggregate job listings and salary data
- **Lead generation** — collect business contact information from directories
- **Market research** — track product availability and pricing trends

---

## Author

Badr Dyane — [GitHub](https://github.com/BadrDyane)

---

## License

MIT