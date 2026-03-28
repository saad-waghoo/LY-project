from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from finsent.app.analysis.market_impact import align_news_with_prices, build_daily_impact_summary
from finsent.app.config.settings import settings
from finsent.app.database.base import SessionLocal, init_db
from finsent.app.database.repository import NewsRepository, PriceRepository
from finsent.app.scrapers.yahoo_finance import YahooFinanceScraper
from finsent.app.services.market_data import MarketDataService
from finsent.app.services.sentiment import FinBERTSentimentService


@dataclass(slots=True)
class PipelineResult:
    news_df: pd.DataFrame
    price_df: pd.DataFrame
    event_df: pd.DataFrame
    summary_df: pd.DataFrame


class FinSentPipeline:
    def __init__(self) -> None:
        self.scraper = YahooFinanceScraper()
        self.sentiment_service = FinBERTSentimentService()
        self.market_data_service = MarketDataService()

    def run(
        self,
        ticker: str | None = None,
        limit: int | None = None,
        return_window_minutes: int | None = None,
    ) -> PipelineResult:
        ticker = (ticker or settings.default_ticker).upper()
        limit = limit or settings.default_news_limit
        return_window_minutes = return_window_minutes or settings.default_return_window_minutes

        init_db()

        articles = self.scraper.fetch_latest(ticker=ticker, limit=limit)
        if not articles:
            return PipelineResult(
                news_df=pd.DataFrame(),
                price_df=pd.DataFrame(),
                event_df=pd.DataFrame(),
                summary_df=pd.DataFrame(),
            )

        with SessionLocal() as session:
            news_repo = NewsRepository(session)
            price_repo = PriceRepository(session)

            for article in articles:
                sentiment = self.sentiment_service.predict(article.title)
                news_repo.upsert_news_with_sentiment(article, sentiment)

            session.commit()

            news_df = news_repo.list_news_df(ticker=ticker)
            min_time = pd.to_datetime(news_df["published_at"]).min().to_pydatetime()
            max_time = pd.to_datetime(news_df["published_at"]).max().to_pydatetime()

            price_frame = self.market_data_service.fetch_intraday_prices(
                ticker=ticker,
                start=min_time - timedelta(days=1),
                end=max_time + timedelta(days=1),
            )
            if not price_frame.empty:
                price_repo.upsert_price_bars(ticker=ticker, price_frame=price_frame)
                session.commit()

            price_df = price_repo.list_price_df(ticker=ticker)

        event_df = align_news_with_prices(
            news_df=news_df,
            price_df=price_df,
            return_window_minutes=return_window_minutes,
        )
        summary_df = build_daily_impact_summary(event_df)

        return PipelineResult(
            news_df=news_df,
            price_df=price_df,
            event_df=event_df,
            summary_df=summary_df,
        )
