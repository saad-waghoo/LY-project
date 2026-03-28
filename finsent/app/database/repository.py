from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from finsent.app.database.entities import NewsArticle, PriceBar
from finsent.app.models.schemas import ScrapedNewsItem, SentimentResult


class NewsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_news_with_sentiment(
        self,
        item: ScrapedNewsItem,
        sentiment: SentimentResult,
    ) -> NewsArticle:
        article = self.session.execute(
            select(NewsArticle).where(NewsArticle.url == item.url)
        ).scalar_one_or_none()

        if article is None:
            article = NewsArticle(
                ticker=item.ticker,
                source=item.source,
                title=item.title,
                summary=item.summary,
                url=item.url,
                published_at=item.published_at,
            )
            self.session.add(article)

        article.ticker = item.ticker
        article.source = item.source
        article.title = item.title
        article.summary = item.summary
        article.published_at = item.published_at
        article.sentiment_label = sentiment.label
        article.sentiment_score = sentiment.score
        article.positive_score = sentiment.positive
        article.negative_score = sentiment.negative
        article.neutral_score = sentiment.neutral
        self.session.flush()
        return article

    def list_news_df(self, ticker: str | None = None) -> pd.DataFrame:
        stmt = select(NewsArticle).order_by(NewsArticle.published_at.asc())
        if ticker:
            stmt = stmt.where(NewsArticle.ticker == ticker.upper())
        rows = self.session.execute(stmt).scalars().all()
        return pd.DataFrame(
            [
                {
                    "id": row.id,
                    "ticker": row.ticker,
                    "source": row.source,
                    "title": row.title,
                    "summary": row.summary,
                    "url": row.url,
                    "published_at": row.published_at,
                    "sentiment_label": row.sentiment_label,
                    "sentiment_score": row.sentiment_score,
                    "positive_score": row.positive_score,
                    "negative_score": row.negative_score,
                    "neutral_score": row.neutral_score,
                }
                for row in rows
            ]
        )


class PriceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_price_bars(self, ticker: str, price_frame: pd.DataFrame) -> None:
        ticker = ticker.upper()
        for timestamp, row in price_frame.iterrows():
            price_bar = self.session.execute(
                select(PriceBar).where(
                    PriceBar.ticker == ticker,
                    PriceBar.timestamp == timestamp.to_pydatetime(),
                )
            ).scalar_one_or_none()
            if price_bar is None:
                price_bar = PriceBar(ticker=ticker, timestamp=timestamp.to_pydatetime())
                self.session.add(price_bar)

            price_bar.open = float(row["Open"])
            price_bar.high = float(row["High"])
            price_bar.low = float(row["Low"])
            price_bar.close = float(row["Close"])
            price_bar.volume = float(row["Volume"])

        self.session.flush()

    def list_price_df(self, ticker: str) -> pd.DataFrame:
        rows = self.session.execute(
            select(PriceBar)
            .where(PriceBar.ticker == ticker.upper())
            .order_by(PriceBar.timestamp.asc())
        ).scalars().all()
        return pd.DataFrame(
            [
                {
                    "ticker": row.ticker,
                    "timestamp": row.timestamp,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": row.volume,
                }
                for row in rows
            ]
        )
