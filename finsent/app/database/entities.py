from __future__ import annotations

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from finsent.app.database.base import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (UniqueConstraint("url", name="uq_news_articles_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1024))
    published_at: Mapped[DateTime] = mapped_column(DateTime, index=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    positive_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    negative_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    neutral_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class PriceBar(Base):
    __tablename__ = "price_bars"
    __table_args__ = (UniqueConstraint("ticker", "timestamp", name="uq_price_bars_ticker_timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
