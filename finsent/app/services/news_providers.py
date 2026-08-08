from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Protocol

import requests

from finsent.app.config.settings import settings
from finsent.app.scrapers.yahoo_finance import YahooFinanceScraper
from finsent.app.services.symbol_registry import SymbolRecord


@dataclass(slots=True)
class NormalizedNewsArticle:
    article_id: str
    ticker: str
    exchange: str
    source: str
    title: str
    summary: str | None
    url: str
    published_at: datetime
    ingested_at: datetime
    provider: str
    dedupe_hash: str
    relevance_score: float | None = None


class NewsProvider(Protocol):
    provider_name: str

    def fetch_news(self, symbol: SymbolRecord, limit: int = 20) -> list[NormalizedNewsArticle]:
        ...


class PolygonNewsProvider:
    provider_name = "polygon"
    provider_tier = "provider-grade"

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.session = requests.Session()

    def fetch_news(self, symbol: SymbolRecord, limit: int = 20) -> list[NormalizedNewsArticle]:
        if symbol.exchange != "US" or not settings.polygon_api_key:
            return []
        response = self.session.get(
            f"{settings.polygon_base_url.rstrip('/')}/v2/reference/news",
            params={
                "ticker": symbol.polygon_symbol or symbol.ticker,
                "limit": min(limit, 50),
                "order": "desc",
                "sort": "published_utc",
                "apiKey": settings.polygon_api_key,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        return [self._normalize(symbol, item) for item in results if isinstance(item, dict)]

    def _normalize(self, symbol: SymbolRecord, item: dict[str, object]) -> NormalizedNewsArticle:
        title = str(item.get("title", "")).strip()
        url = str(item.get("article_url", "")).strip()
        published_at = self._coerce_datetime(item.get("published_utc")) or datetime.now(timezone.utc).replace(tzinfo=None)
        dedupe_hash = hashlib.sha256(f"{title}|{url}".encode()).hexdigest()
        return NormalizedNewsArticle(
            article_id=str(item.get("id") or dedupe_hash),
            ticker=symbol.ticker,
            exchange=symbol.exchange,
            source=str(item.get("publisher", {}).get("name", "Polygon")) if isinstance(item.get("publisher"), dict) else "Polygon",
            title=title,
            summary=str(item.get("description", "")).strip() or None,
            url=url,
            published_at=published_at,
            ingested_at=datetime.now(timezone.utc).replace(tzinfo=None),
            provider=self.provider_name,
            dedupe_hash=dedupe_hash,
            relevance_score=1.0,
        )

    @staticmethod
    def _coerce_datetime(value: object) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)


class CuratedWebNewsProvider:
    provider_name = "fallback_web"
    provider_tier = "fallback-quality"

    def __init__(self) -> None:
        self.scraper = YahooFinanceScraper()

    def fetch_news(self, symbol: SymbolRecord, limit: int = 20) -> list[NormalizedNewsArticle]:
        # Fallback provider for markets without a stronger direct news integration yet.
        raw_articles = self.scraper.fetch_latest(
            ticker=f"{symbol.ticker}.NS" if symbol.exchange == "NSE" else f"{symbol.ticker}.BO" if symbol.exchange == "BSE" else symbol.ticker,
            limit=limit,
        )
        articles: list[NormalizedNewsArticle] = []
        for item in raw_articles:
            dedupe_hash = hashlib.sha256(f"{item.title}|{item.url}".encode()).hexdigest()
            articles.append(
                NormalizedNewsArticle(
                    article_id=dedupe_hash,
                    ticker=symbol.ticker,
                    exchange=symbol.exchange,
                    source=item.source,
                    title=item.title,
                    summary=item.summary,
                    url=item.url,
                    published_at=item.published_at,
                    ingested_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    provider=self.provider_name,
                    dedupe_hash=dedupe_hash,
                    relevance_score=None,
                )
            )
        return articles


class MarketauxNewsProvider:
    provider_name = "marketaux"
    provider_tier = "provider-grade"

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.session = requests.Session()

    def fetch_news(self, symbol: SymbolRecord, limit: int = 20) -> list[NormalizedNewsArticle]:
        if symbol.exchange not in {"NSE", "BSE"} or not settings.marketaux_api_token:
            return []

        articles = self._fetch_by_symbols(symbol, limit=limit)
        if articles:
            return articles
        return self._fetch_by_company_name(symbol, limit=limit)

    def _fetch_by_symbols(self, symbol: SymbolRecord, limit: int) -> list[NormalizedNewsArticle]:
        candidates = self._symbol_candidates(symbol)
        response = self.session.get(
            f"{settings.marketaux_base_url.rstrip('/')}/news/all",
            params={
                "api_token": settings.marketaux_api_token,
                "symbols": ",".join(candidates),
                "filter_entities": "true",
                "language": "en",
                "limit": min(limit, 50),
                "must_have_entities": "true",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("data") or []
        return self._normalize_articles(symbol, results)

    def _fetch_by_company_name(self, symbol: SymbolRecord, limit: int) -> list[NormalizedNewsArticle]:
        response = self.session.get(
            f"{settings.marketaux_base_url.rstrip('/')}/news/all",
            params={
                "api_token": settings.marketaux_api_token,
                "search": symbol.display_name,
                "countries": "in",
                "language": "en",
                "limit": min(limit, 50),
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("data") or []
        return self._normalize_articles(symbol, results)

    def _normalize_articles(self, symbol: SymbolRecord, results: list[object]) -> list[NormalizedNewsArticle]:
        articles: list[NormalizedNewsArticle] = []
        seen: set[str] = set()
        candidates = set(self._symbol_candidates(symbol))

        for item in results:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            if not title or not url:
                continue
            dedupe_hash = hashlib.sha256(f"{title}|{url}".encode()).hexdigest()
            if dedupe_hash in seen:
                continue
            entities = item.get("entities") or []
            relevance = self._relevance_for_symbol(symbol, entities, candidates)
            if relevance <= 0:
                continue
            published_at = self._coerce_datetime(item.get("published_at")) or datetime.now(timezone.utc).replace(tzinfo=None)
            source = str(item.get("source", "Marketaux")).strip() or "Marketaux"
            articles.append(
                NormalizedNewsArticle(
                    article_id=str(item.get("uuid") or dedupe_hash),
                    ticker=symbol.ticker,
                    exchange=symbol.exchange,
                    source=source,
                    title=title,
                    summary=str(item.get("description", "")).strip() or None,
                    url=url,
                    published_at=published_at,
                    ingested_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    provider=self.provider_name,
                    dedupe_hash=dedupe_hash,
                    relevance_score=relevance,
                )
            )
            seen.add(dedupe_hash)
        return articles

    @staticmethod
    def _symbol_candidates(symbol: SymbolRecord) -> list[str]:
        if symbol.exchange == "NSE":
            return [f"{symbol.ticker}.NS", symbol.ticker]
        if symbol.exchange == "BSE":
            return [f"{symbol.ticker}.BO", symbol.ticker]
        return [symbol.ticker]

    @staticmethod
    def _coerce_datetime(value: object) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _relevance_for_symbol(symbol: SymbolRecord, entities: list[object], candidates: set[str]) -> float:
        best = 0.0
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            entity_symbol = str(entity.get("symbol", "")).strip().upper()
            entity_name = str(entity.get("name", "")).strip().lower()
            if entity_symbol and entity_symbol in {candidate.upper() for candidate in candidates}:
                return 1.0
            if entity_name and entity_name == symbol.display_name.strip().lower():
                best = max(best, 0.8)
        return best


def build_news_provider(symbol: SymbolRecord) -> NewsProvider:
    if symbol.exchange == "US":
        return PolygonNewsProvider() if settings.polygon_api_key else CuratedWebNewsProvider()
    if symbol.exchange in {"NSE", "BSE"}:
        return MarketauxNewsProvider() if settings.marketaux_api_token else CuratedWebNewsProvider()
    return CuratedWebNewsProvider()
