from __future__ import annotations

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from finsent.app.config.settings import settings
from finsent.app.models.schemas import ScrapedNewsItem
from finsent.app.utils.text import normalize_text
from finsent.app.utils.time import ensure_utc_naive, parse_rfc822_datetime


class YahooFinanceScraper:
    source_name = "Yahoo Finance"
    excluded_titles = {
        "today's news",
        "news",
        "us",
        "politics",
        "world",
        "science",
        "newsletters",
        "more topics",
        "more news",
        "tech news",
    }

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                )
            }
        )

    def fetch_latest(self, ticker: str, limit: int = 20) -> list[ScrapedNewsItem]:
        ticker = ticker.upper()
        response = self._fetch_quote_page(ticker)

        soup = BeautifulSoup(response.text, "html.parser")
        articles: list[ScrapedNewsItem] = []
        seen_urls: set[str] = set()

        for link in soup.select("a[href*='/news/'], a[href*='https://finance.yahoo.com/news/']"):
            title = normalize_text(link.get_text(" ", strip=True))
            href = link.get("href")
            if not href or not title:
                continue

            article_url = urljoin(settings.news_source_base_url, href)
            if not self._is_valid_article_link(title=title, article_url=article_url):
                continue
            if article_url in seen_urls:
                continue

            container = link.find_parent(["li", "div", "section", "article"])
            summary = normalize_text(container.get_text(" ", strip=True)) if container else ""

            time_node = None
            if container:
                time_node = container.find("time")
            published_at = ensure_utc_naive(parse_rfc822_datetime(time_node.get("datetime") if time_node else None))

            articles.append(
                ScrapedNewsItem(
                    ticker=ticker,
                    source=self.source_name,
                    title=title,
                    url=article_url,
                    published_at=published_at,
                    summary=summary[:1200] if summary else None,
                )
            )
            seen_urls.add(article_url)

            if len(articles) >= limit:
                break

        return articles

    def _is_valid_article_link(self, title: str, article_url: str) -> bool:
        normalized_title = title.lower().strip()
        if normalized_title in self.excluded_titles:
            return False
        if len(normalized_title) < 35:
            return False
        lowered_url = article_url.lower().rstrip("/")
        if lowered_url.endswith("/news"):
            return False
        if "/news/" not in lowered_url:
            return False
        return True

    def _fetch_quote_page(self, ticker: str) -> requests.Response:
        candidate_urls = [
            f"{settings.news_source_base_url}/quote/{ticker}?p={ticker}",
            f"{settings.news_source_base_url}/quote/{ticker}",
            f"{settings.news_source_base_url}/quote/{ticker}/news?p={ticker}",
        ]
        last_error: Exception | None = None
        for url in candidate_urls:
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                continue

        if last_error is not None:
            raise last_error
        raise requests.RequestException(f"Failed to fetch Yahoo Finance page for {ticker}")
