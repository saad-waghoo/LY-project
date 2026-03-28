# FinSent

FinSent is a local end-to-end prototype for analyzing financial news sentiment and short-term market impact.

## V1 Features

- Yahoo Finance scraping with `requests` + `BeautifulSoup`
- FinBERT sentiment inference using `ProsusAI/finbert`
- Historical price data via `yfinance`
- SQLite storage through SQLAlchemy
- News-to-market alignment and short-term return analysis
- Plotly Dash dashboard for interactive exploration

## Project Structure

```text
finsent/
  app/
    analysis/
    config/
    dashboard/
    database/
    models/
    scrapers/
    services/
    utils/
  scripts/
  data/
  tests/
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run Pipeline

```bash
python -m finsent.scripts.run_pipeline --ticker AAPL --limit 15
```

This command scrapes recent Yahoo Finance news, runs FinBERT sentiment, stores the results, fetches market data, and computes a simple impact analysis table.

## Run Dashboard

```bash
python -m finsent.scripts.run_dashboard
```

Open `http://127.0.0.1:8050`.

## Notes

- Yahoo Finance markup can change, so the scraper is defensive and easy to swap.
- The first FinBERT run downloads model weights from Hugging Face.
- SQLite is used for the local prototype; the storage layer is structured so PostgreSQL can be introduced later with a `DATABASE_URL` change.
