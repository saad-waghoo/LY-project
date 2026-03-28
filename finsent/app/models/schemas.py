from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ScrapedNewsItem:
    ticker: str
    source: str
    title: str
    url: str
    published_at: datetime
    summary: str | None = None


@dataclass(slots=True)
class SentimentResult:
    label: str
    score: float
    positive: float
    negative: float
    neutral: float
