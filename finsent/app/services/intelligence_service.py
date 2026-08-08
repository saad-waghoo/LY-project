from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pandas as pd

from finsent.app.config.settings import settings
from finsent.app.database.base import SessionLocal, init_db
from finsent.app.database.repository import (
    AnalysisRepository,
    NewsRepository,
    PriceRepository,
    QuoteSnapshotRepository,
    SignalSnapshotRepository,
)
from finsent.app.services.llm_analyzers import AggregateAnalysis, ArticleAnalysis, build_llm_analyzer, heuristic_article_analysis
from finsent.app.services.market_providers import QuoteSnapshot, build_market_provider
from finsent.app.services.news_providers import NormalizedNewsArticle, build_news_provider
from finsent.app.services.signal_engine import CompositeSignal, CompositeSignalEngine
from finsent.app.services.symbol_registry import SymbolRecord, registry


@dataclass(slots=True)
class IntelligenceSnapshot:
    symbol: SymbolRecord
    quote: QuoteSnapshot
    articles: list[NormalizedNewsArticle]
    analyses: list[ArticleAnalysis]
    aggregate: AggregateAnalysis
    signal: CompositeSignal
    price_history: pd.DataFrame


class IntelligenceService:
    def __init__(self) -> None:
        self.signal_engine = CompositeSignalEngine()
        self.llm = build_llm_analyzer()

    def run(self, symbol: SymbolRecord) -> IntelligenceSnapshot:
        init_db()
        market_provider = build_market_provider(symbol)
        news_provider = build_news_provider(symbol)
        quote = market_provider.fetch_quote_snapshot(symbol)
        end = datetime.now(timezone.utc).replace(tzinfo=None)
        start = end - timedelta(days=30)
        price_history = market_provider.fetch_price_bars(symbol, start=start, end=end, interval=settings.default_price_interval)

        articles = self._dedupe(news_provider.fetch_news(symbol, limit=settings.default_news_limit))
        analyses: list[ArticleAnalysis] = []
        uncached_remote_analyses = 0

        with SessionLocal() as session:
            news_repo = NewsRepository(session)
            price_repo = PriceRepository(session)
            quote_repo = QuoteSnapshotRepository(session)
            analysis_repo = AnalysisRepository(session)
            signal_repo = SignalSnapshotRepository(session)

            quote_repo.upsert_quote_snapshot(symbol, quote)
            for article in articles:
                cached = analysis_repo.get_by_article_hash(article.dedupe_hash)
                if cached is not None:
                    analysis = cached
                else:
                    if uncached_remote_analyses < settings.llm_analysis_limit:
                        analysis = self.llm.analyze_article(symbol, article)
                        uncached_remote_analyses += 1
                    else:
                        analysis = heuristic_article_analysis(
                            symbol,
                            article,
                            provider=self.llm.provider_name,
                            parse_status="heuristic_budget_fallback",
                            reason="LLM analysis budget reached for this refresh; local heuristic analysis used.",
                        )
                    analysis_repo.upsert_article_analysis(symbol, article, analysis)
                analyses.append(analysis)
                news_repo.upsert_normalized_news(symbol, article, analysis)

            article_pairs = list(zip(articles, analyses))
            aggregate = self.llm.aggregate(symbol, article_pairs)
            signal = self.signal_engine.compute(quote, article_pairs, aggregate)
            if not price_history.empty:
                price_repo.upsert_price_bars(self.storage_ticker(symbol), price_history)
            signal_repo.upsert_signal_snapshot(symbol, quote, aggregate, signal)
            session.commit()

        return IntelligenceSnapshot(symbol, quote, articles, analyses, aggregate, signal, price_history)

    @staticmethod
    def _dedupe(articles: list[NormalizedNewsArticle]) -> list[NormalizedNewsArticle]:
        seen: set[str] = set()
        ordered: list[NormalizedNewsArticle] = []
        for article in sorted(articles, key=lambda item: item.published_at, reverse=True):
            if article.dedupe_hash in seen:
                continue
            ordered.append(article)
            seen.add(article.dedupe_hash)
        return ordered

    @staticmethod
    def article_hash(title: str, url: str) -> str:
        return sha256(f"{title}|{url}".encode()).hexdigest()

    @staticmethod
    def storage_ticker(symbol: SymbolRecord) -> str:
        if symbol.exchange == "NSE":
            return f"{symbol.ticker}.NS"
        if symbol.exchange == "BSE":
            return f"{symbol.ticker}.BO"
        return symbol.ticker


intelligence_service = IntelligenceService()
