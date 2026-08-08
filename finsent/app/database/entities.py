from __future__ import annotations

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from finsent.app.database.base import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (UniqueConstraint("url", name="uq_news_articles_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1024))
    published_at: Mapped[DateTime] = mapped_column(DateTime, index=True)
    ingested_at: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True, index=True)
    dedupe_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_label: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    model_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    positive_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    negative_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    neutral_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    bid_ask_spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_sell_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_pressure: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    relevant: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_horizon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    catalyst_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    short_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parse_status: Mapped[str | None] = mapped_column(String(32), nullable=True)


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


class QuoteSnapshotEntity(Base):
    __tablename__ = "quote_snapshots"
    __table_args__ = (UniqueConstraint("ticker", "exchange", "provider", "market_timestamp", name="uq_quote_snapshots_scope"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    exchange: Mapped[str] = mapped_column(String(16), index=True)
    provider_symbol: Mapped[str] = mapped_column(String(64))
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8))
    bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread_absolute: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_timestamp: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True, index=True)
    ingested_at: Mapped[DateTime] = mapped_column(DateTime, index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    freshness_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_status: Mapped[str] = mapped_column(String(32), index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class SignalSnapshotEntity(Base):
    __tablename__ = "signal_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    exchange: Mapped[str] = mapped_column(String(16), index=True)
    ingested_at: Mapped[DateTime] = mapped_column(DateTime, index=True)
    quote_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    analysis_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    composite_label: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    signal_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    overall_sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    action_bias: Mapped[str | None] = mapped_column(String(32), nullable=True)
    net_short_term_view: Mapped[str | None] = mapped_column(String(128), nullable=True)
    final_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_bullets: Mapped[str | None] = mapped_column(Text, nullable=True)
