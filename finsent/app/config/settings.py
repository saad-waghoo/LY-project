from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/finsent.db")
    news_source_base_url: str = os.getenv("NEWS_SOURCE_BASE_URL", "https://finance.yahoo.com")
    default_ticker: str = os.getenv("DEFAULT_TICKER", "AAPL")
    default_news_limit: int = int(os.getenv("DEFAULT_NEWS_LIMIT", "20"))
    default_return_window_minutes: int = int(os.getenv("DEFAULT_RETURN_WINDOW_MINUTES", "60"))
    model_name: str = os.getenv("MODEL_NAME", "ProsusAI/finbert")


settings = Settings()
