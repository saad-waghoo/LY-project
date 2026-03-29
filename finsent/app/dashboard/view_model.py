from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from hashlib import md5
from pathlib import Path
from typing import TYPE_CHECKING

import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
from dash import html
from plotly import graph_objects as go
from plotly.subplots import make_subplots

from finsent.app.analysis.market_impact import align_news_with_prices, build_daily_impact_summary
from finsent.app.database.base import SessionLocal, init_db
from finsent.app.database.repository import NewsRepository, PriceRepository
from finsent.app.services.kaggle_data import load_company_universe

if TYPE_CHECKING:
    from finsent.app.services.pipeline import FinSentPipeline


WATCHLIST = [
    {"ticker": "AAPL", "name": "Apple", "sector": "Technology"},
    {"ticker": "AMZN", "name": "Amazon", "sector": "Consumer"},
    {"ticker": "MSFT", "name": "Microsoft", "sector": "Technology"},
    {"ticker": "NVDA", "name": "NVIDIA", "sector": "Technology"},
    {"ticker": "TSLA", "name": "Tesla", "sector": "Consumer"},
    {"ticker": "JPM", "name": "JPMorgan", "sector": "Finance"},
    {"ticker": "GS", "name": "Goldman Sachs", "sector": "Finance"},
    {"ticker": "XOM", "name": "ExxonMobil", "sector": "Energy"},
    {"ticker": "CVX", "name": "Chevron", "sector": "Energy"},
    {"ticker": "PFE", "name": "Pfizer", "sector": "Healthcare"},
]

WATCHLIST_MAP = {item["ticker"]: item for item in WATCHLIST}
HORIZON_DAYS = {"short": 3, "medium": 7, "long": 30}
PALETTE = {
    "bg": "#07111f",
    "paper": "#0c1729",
    "ink": "#e8eefb",
    "muted": "#9aa8c7",
    "accent": "#2dd4bf",
    "accent_2": "#fb923c",
    "bull": "#34d399",
    "bear": "#f87171",
    "neutral": "#fbbf24",
    "line": "#60a5fa",
    "grid": "#22314e",
}


@dataclass(slots=True)
class DashboardState:
    news_df: pd.DataFrame
    price_df: pd.DataFrame
    event_df: pd.DataFrame
    daily_summary_df: pd.DataFrame
    compare_df: pd.DataFrame
    sector_df: pd.DataFrame
    demo_mode: bool
    data_status: str


@lru_cache(maxsize=1)
def get_pipeline() -> FinSentPipeline:
    from finsent.app.services.pipeline import FinSentPipeline

    return FinSentPipeline()


def get_ticker_options() -> list[dict[str, str]]:
    companies = load_company_universe()
    if companies:
        return [
            {
                "label": f"{company.ticker}  |  {company.name}",
                "value": company.ticker,
            }
            for company in companies
        ]

    return [{"label": f'{item["ticker"]}  |  {item["name"]}', "value": item["ticker"]} for item in WATCHLIST]


def get_company_name(ticker: str) -> str:
    normalized = ticker.upper()
    for company in load_company_universe():
        if company.ticker == normalized:
            return company.name
    return WATCHLIST_MAP.get(ticker.upper(), {}).get("name", ticker.upper())


def build_dashboard_state(
    focus_ticker: str,
    compare_tickers: list[str] | None,
    horizon: str,
    start_date: str | None,
    end_date: str | None,
) -> DashboardState:
    selected = normalize_tickers([focus_ticker, *(compare_tickers or [])])
    news_df, price_df = load_live_data(selected)
    demo_mode = False
    data_status = (
        "Live mode active: dashboard is rendering stored pipeline data."
        if not news_df.empty or not price_df.empty
        else "No live data is stored yet for the selected ticker and window."
    )

    news_df, price_df = filter_to_window(news_df, price_df, horizon, start_date, end_date)
    event_df = build_event_frame(news_df, price_df)
    daily_summary_df = build_grouped_daily_summary(event_df)
    compare_df = build_compare_frame(news_df, price_df, event_df)
    sector_df = build_sector_frame(compare_df)

    return DashboardState(
        news_df=news_df,
        price_df=price_df,
        event_df=event_df,
        daily_summary_df=daily_summary_df,
        compare_df=compare_df,
        sector_df=sector_df,
        demo_mode=demo_mode,
        data_status=data_status,
    )


def normalize_tickers(raw_tickers: list[str | None]) -> list[str]:
    values: list[str] = []
    for ticker in raw_tickers:
        if not ticker:
            continue
        normalized = ticker.upper().strip()
        if normalized and normalized not in values:
            values.append(normalized)
    return values


def load_live_data(tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    init_db()
    news_frames: list[pd.DataFrame] = []
    price_frames: list[pd.DataFrame] = []

    with SessionLocal() as session:
        news_repo = NewsRepository(session)
        price_repo = PriceRepository(session)
        for ticker in tickers:
            news_df = news_repo.list_news_df(ticker=ticker)
            price_df = price_repo.list_price_df(ticker=ticker)
            if not news_df.empty:
                news_frames.append(news_df)
            if not price_df.empty:
                price_frames.append(price_df)

    news_df = pd.concat(news_frames, ignore_index=True) if news_frames else pd.DataFrame()
    price_df = pd.concat(price_frames, ignore_index=True) if price_frames else pd.DataFrame()

    if not news_df.empty:
        news_df["published_at"] = pd.to_datetime(news_df["published_at"])
    if not price_df.empty:
        price_df["timestamp"] = pd.to_datetime(price_df["timestamp"])

    return news_df, price_df


def needs_live_refresh(ticker: str) -> bool:
    init_db()
    with SessionLocal() as session:
        news_df = NewsRepository(session).list_news_df(ticker=ticker)
        price_df = PriceRepository(session).list_price_df(ticker=ticker)

    if news_df.empty or price_df.empty:
        return True

    latest_news = pd.to_datetime(news_df["published_at"]).max()
    latest_price = pd.to_datetime(price_df["timestamp"]).max()
    now = pd.Timestamp.now().tz_localize(None)
    if (now - latest_news) > pd.Timedelta(hours=24):
        return True
    if (now - latest_price) > pd.Timedelta(hours=24):
        return True
    return False


def ensure_live_data(tickers: list[str]) -> None:
    for ticker in normalize_tickers(tickers):
        if not needs_live_refresh(ticker):
            continue
        try:
            get_pipeline().run(ticker=ticker, limit=20)
        except Exception:
            # The dashboard can still fall back to stored/demo data if live fetch fails.
            continue


def filter_to_window(
    news_df: pd.DataFrame,
    price_df: pd.DataFrame,
    horizon: str,
    start_date: str | None,
    end_date: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if news_df.empty and price_df.empty:
        return news_df, price_df

    if start_date or end_date:
        start_ts = pd.to_datetime(start_date) if start_date else None
        end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1) if end_date else None
        window_days = max(int(((end_ts or start_ts) - (start_ts or end_ts)).days), 1) if (start_ts is not None and end_ts is not None) else 30
    else:
        anchor = None
        if not news_df.empty:
            anchor = news_df["published_at"].max()
        elif not price_df.empty:
            anchor = price_df["timestamp"].max()
        lookback_days = HORIZON_DAYS.get(horizon, 7)
        window_days = lookback_days
        start_ts = anchor - pd.Timedelta(days=lookback_days) if anchor is not None else None
        end_ts = anchor + pd.Timedelta(days=1) if anchor is not None else None

    original_price_df = price_df.copy()

    if start_ts is not None and not news_df.empty:
        news_df = news_df[news_df["published_at"] >= start_ts]
    if end_ts is not None and not news_df.empty:
        news_df = news_df[news_df["published_at"] <= end_ts]
    if start_ts is not None and not price_df.empty:
        price_df = price_df[price_df["timestamp"] >= start_ts]
    if end_ts is not None and not price_df.empty:
        price_df = price_df[price_df["timestamp"] <= end_ts]

    if price_df.empty and not original_price_df.empty:
        fallback_frames: list[pd.DataFrame] = []
        for ticker in sorted(original_price_df["ticker"].dropna().unique()):
            ticker_prices = original_price_df[original_price_df["ticker"] == ticker].copy()
            if ticker_prices.empty:
                continue
            latest_timestamp = ticker_prices["timestamp"].max()
            fallback_start = latest_timestamp - pd.Timedelta(days=window_days)
            fallback_subset = ticker_prices[ticker_prices["timestamp"] >= fallback_start]
            if not fallback_subset.empty:
                fallback_frames.append(fallback_subset)
        if fallback_frames:
            price_df = pd.concat(fallback_frames, ignore_index=True)

    return news_df.copy(), price_df.copy()


def build_event_frame(news_df: pd.DataFrame, price_df: pd.DataFrame) -> pd.DataFrame:
    if news_df.empty or price_df.empty:
        return pd.DataFrame()

    events: list[pd.DataFrame] = []
    for ticker in sorted(news_df["ticker"].dropna().unique()):
        ticker_news = news_df[news_df["ticker"] == ticker]
        ticker_prices = price_df[price_df["ticker"] == ticker]
        if ticker_news.empty or ticker_prices.empty:
            continue
        joined = align_news_with_prices(ticker_news, ticker_prices, return_window_minutes=60)
        if not joined.empty:
            joined["confidence_pct"] = (
                joined[["positive_score", "negative_score", "neutral_score"]].max(axis=1).fillna(0.0) * 100.0
            )
            joined["impact_pct"] = joined["forward_return"].fillna(0.0) * 100.0
            events.append(joined)
    return pd.concat(events, ignore_index=True) if events else pd.DataFrame()


def build_grouped_daily_summary(event_df: pd.DataFrame) -> pd.DataFrame:
    if event_df.empty:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for ticker in sorted(event_df["ticker"].dropna().unique()):
        ticker_df = event_df[event_df["ticker"] == ticker]
        summary = build_daily_impact_summary(ticker_df)
        if not summary.empty:
            summary["ticker"] = ticker
            frames.append(summary)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_compare_frame(news_df: pd.DataFrame, price_df: pd.DataFrame, event_df: pd.DataFrame) -> pd.DataFrame:
    tickers = sorted(set(news_df.get("ticker", pd.Series(dtype=str)).dropna().tolist()) | set(price_df.get("ticker", pd.Series(dtype=str)).dropna().tolist()))
    rows: list[dict[str, object]] = []

    for ticker in tickers:
        ticker_news = news_df[news_df["ticker"] == ticker]
        ticker_prices = price_df[price_df["ticker"] == ticker]
        ticker_events = event_df[event_df["ticker"] == ticker] if not event_df.empty else pd.DataFrame()
        if ticker_prices.empty:
            continue

        first_close = float(ticker_prices["close"].iloc[0])
        last_close = float(ticker_prices["close"].iloc[-1])
        day_change_pct = ((last_close - first_close) / first_close) * 100 if first_close else 0.0
        avg_sentiment = float(ticker_news["sentiment_score"].mean()) if not ticker_news.empty else 0.0
        avg_confidence = (
            float(ticker_news[["positive_score", "negative_score", "neutral_score"]].max(axis=1).mean() * 100.0)
            if not ticker_news.empty
            else 0.0
        )
        rows.append(
            {
                "ticker": ticker,
                "name": WATCHLIST_MAP.get(ticker, {}).get("name", ticker),
                "sector": WATCHLIST_MAP.get(ticker, {}).get("sector", "Other"),
                "last_close": last_close,
                "pct_change": day_change_pct,
                "news_volume": int(len(ticker_news)),
                "avg_sentiment": avg_sentiment,
                "avg_confidence": avg_confidence,
                "avg_impact_pct": float(ticker_events["impact_pct"].mean()) if not ticker_events.empty else 0.0,
                "volume": float(ticker_prices["volume"].iloc[-1]) if "volume" in ticker_prices else 0.0,
            }
        )

    return pd.DataFrame(rows)


def build_sector_frame(compare_df: pd.DataFrame) -> pd.DataFrame:
    if compare_df.empty:
        return pd.DataFrame()
    return (
        compare_df.groupby("sector", as_index=False)
        .agg(
            sentiment=("avg_sentiment", "mean"),
            performance=("pct_change", "mean"),
            confidence=("avg_confidence", "mean"),
        )
        .sort_values("sentiment", ascending=False)
    )


def generate_demo_data(tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    now = pd.Timestamp.now().floor("h")
    news_rows: list[dict[str, object]] = []
    price_rows: list[dict[str, object]] = []
    article_id = 1

    themes = [
        ("earnings beat expectations", 0.58),
        ("analyst upgrade lifts outlook", 0.46),
        ("guidance cut triggers caution", -0.55),
        ("partnership expands revenue visibility", 0.38),
        ("margin pressure worries investors", -0.42),
        ("product launch draws strong demand", 0.34),
        ("regulatory headline adds uncertainty", -0.29),
    ]

    for ticker in tickers:
        seed = int(md5(ticker.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        sector = WATCHLIST_MAP.get(ticker, {}).get("sector", "Other")
        base_price = float(rng.uniform(80, 320))
        timestamps = pd.date_range(end=now, periods=30 * 7, freq="4h")
        drift = rng.normal(0.0008, 0.012, len(timestamps)).cumsum()
        closes = base_price * (1 + drift)

        for idx, ts in enumerate(timestamps):
            close = max(10.0, float(closes[idx]))
            open_price = close * (1 + rng.normal(0.0, 0.002))
            high = max(open_price, close) * (1 + rng.uniform(0.001, 0.01))
            low = min(open_price, close) * (1 - rng.uniform(0.001, 0.01))
            volume = float(rng.integers(800_000, 12_000_000))
            price_rows.append(
                {
                    "ticker": ticker,
                    "timestamp": ts.to_pydatetime(),
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(close, 2),
                    "volume": volume,
                }
            )

        headline_times = pd.date_range(end=now, periods=18, freq="40h")
        for ts in headline_times:
            theme, score = themes[int(rng.integers(0, len(themes)))]
            score = float(np.clip(score + rng.normal(0.0, 0.12), -0.95, 0.95))
            label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
            confidence = float(np.clip(0.62 + abs(score) * 0.28 + rng.normal(0.0, 0.05), 0.52, 0.96))
            if label == "positive":
                positive, negative, neutral = confidence, (1 - confidence) * 0.25, (1 - confidence) * 0.75
            elif label == "negative":
                negative, positive, neutral = confidence, (1 - confidence) * 0.25, (1 - confidence) * 0.75
            else:
                neutral, positive, negative = confidence, (1 - confidence) * 0.5, (1 - confidence) * 0.5

            news_rows.append(
                {
                    "id": article_id,
                    "ticker": ticker,
                    "source": "Demo Feed",
                    "title": f"Demo: {ticker} {theme}",
                    "summary": f"Placeholder frontend data for {ticker} in the {sector} sector.",
                    "url": f"https://demo.local/{ticker.lower()}/{article_id}",
                    "published_at": ts.to_pydatetime(),
                    "sentiment_label": label,
                    "sentiment_score": round(score, 4),
                    "positive_score": round(positive, 4),
                    "negative_score": round(negative, 4),
                    "neutral_score": round(neutral, 4),
                }
            )
            article_id += 1

    news_df = pd.DataFrame(news_rows)
    price_df = pd.DataFrame(price_rows)
    news_df["published_at"] = pd.to_datetime(news_df["published_at"])
    price_df["timestamp"] = pd.to_datetime(price_df["timestamp"])
    return news_df, price_df


def compute_market_mood(compare_df: pd.DataFrame) -> tuple[str, int, str]:
    if compare_df.empty:
        return "Neutral", 50, "Insufficient data for a market-wide reading."

    mood_value = int(np.clip(((compare_df["avg_sentiment"].mean() + 1.0) / 2.0) * 100.0, 0, 100))
    if mood_value >= 60:
        return "Bullish", mood_value, "Broad sentiment is leaning positive across the tracked names."
    if mood_value <= 40:
        return "Bearish", mood_value, "Risk-off tone is dominating the tracked names."
    return "Balanced", mood_value, "Signals are mixed and the market tone is currently neutral."


def build_ai_explanation(focus_ticker: str, news_df: pd.DataFrame, compare_df: pd.DataFrame) -> list[str]:
    ticker_news = news_df[news_df["ticker"] == focus_ticker].sort_values("published_at", ascending=False)
    if ticker_news.empty:
        return [
            f"{focus_ticker} has no stored headlines in the selected window.",
            "Run the live pipeline for this ticker so the dashboard can plot real sentiment and price history.",
        ]

    avg_sentiment = float(ticker_news["sentiment_score"].mean())
    latest = ticker_news.head(3)["title"].tolist()
    confidence = float(ticker_news[["positive_score", "negative_score", "neutral_score"]].max(axis=1).mean() * 100.0)

    direction = "bullish" if avg_sentiment > 0.15 else "bearish" if avg_sentiment < -0.15 else "neutral"
    explanation = [
        f"{focus_ticker} currently reads as {direction} based on the recent headline mix.",
        f"Average model confidence is {confidence:.0f}%, which suggests the signal is reasonably consistent.",
    ]
    if latest:
        explanation.append(f"Recent drivers: {latest[0]}")
    if len(latest) > 1:
        explanation.append(f"Supporting context: {latest[1]}")

    if not compare_df.empty and "avg_sentiment" in compare_df.columns and "ticker" in compare_df.columns:
        peer_rank = compare_df.sort_values("avg_sentiment", ascending=False).reset_index(drop=True)
        if focus_ticker in peer_rank["ticker"].tolist():
            rank = int(peer_rank.index[peer_rank["ticker"] == focus_ticker][0]) + 1
            explanation.append(f"Peer position: ranked {rank} on sentiment across the compared tickers.")
    return explanation


def build_alerts(compare_df: pd.DataFrame, event_df: pd.DataFrame, alert_threshold: int) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []

    for _, row in compare_df.iterrows():
        sentiment_index = int(np.clip(((row["avg_sentiment"] + 1.0) / 2.0) * 100.0, 0, 100))
        if sentiment_index < alert_threshold:
            alerts.append(
                {
                    "title": f'{row["ticker"]} sentiment dropped below {alert_threshold}',
                    "detail": f'Market mood proxy is {sentiment_index} with {row["pct_change"]:.2f}% price change.',
                }
            )
        if row["pct_change"] <= -2.0:
            alerts.append(
                {
                    "title": f'{row["ticker"]} price pressure detected',
                    "detail": f'Price moved {row["pct_change"]:.2f}% over the selected window.',
                }
            )
        if row["news_volume"] >= 12:
            alerts.append(
                {
                    "title": f'{row["ticker"]} has elevated news volume',
                    "detail": f'{int(row["news_volume"])} headlines were captured in the current window.',
                }
            )

    if not event_df.empty:
        negative_events = event_df.sort_values("impact_pct").head(2)
        for _, row in negative_events.iterrows():
            alerts.append(
                {
                    "title": f'Headline impact watch: {row["ticker"]}',
                    "detail": f'{row["title"]} | estimated 1h impact {row["impact_pct"]:.2f}%',
                }
            )

    deduped: list[dict[str, str]] = []
    seen_titles: set[str] = set()
    for alert in alerts:
        if alert["title"] in seen_titles:
            continue
        deduped.append(alert)
        seen_titles.add(alert["title"])
    return deduped[:6]


def build_top_panel(compare_df: pd.DataFrame, column: str, ascending: bool, value_fmt: str) -> list[dbc.ListGroupItem]:
    if compare_df.empty:
        return [dbc.ListGroupItem("No data available for this panel.")]

    rows = compare_df.sort_values(column, ascending=ascending).head(4)
    items: list[dbc.ListGroupItem] = []
    for _, row in rows.iterrows():
        items.append(
            dbc.ListGroupItem(
                [
                    html.Div(row["ticker"], className="panel-symbol"),
                    html.Div(row["name"], className="panel-name"),
                    html.Div(value_fmt.format(row[column]), className="panel-value"),
                ],
                className="panel-item",
            )
        )
    return items


def build_metric_cards(compare_df: pd.DataFrame, event_df: pd.DataFrame) -> list[dbc.Col]:
    mood_label, mood_score, mood_note = compute_market_mood(compare_df)
    avg_confidence = float(compare_df["avg_confidence"].mean()) if not compare_df.empty else 0.0
    avg_return = float(compare_df["pct_change"].mean()) if not compare_df.empty else 0.0
    event_corr = float(event_df["sentiment_score"].corr(event_df["forward_return"])) if not event_df.empty else np.nan

    metrics = [
        ("Market Mood Index", f"{mood_score}", mood_label),
        ("Model Confidence", f"{avg_confidence:.0f}%", "FinBERT signal reliability"),
        ("Average Window Return", f"{avg_return:.2f}%", "Compared stocks"),
        (
            "Sentiment / Return Corr",
            f"{event_corr:.2f}" if pd.notna(event_corr) else "n/a",
            mood_note,
        ),
    ]

    return [
        dbc.Col(
            html.Div(
                [
                    html.Div(title, className="metric-label"),
                    html.Div(value, className="metric-value"),
                    html.Div(note, className="metric-note"),
                ],
                className="metric-card",
            ),
            md=3,
        )
        for title, value, note in metrics
    ]


def build_sentiment_timeline(news_df: pd.DataFrame) -> go.Figure:
    return build_sentiment_timeline_with_title(news_df, "Sentiment Timeline")


def build_sentiment_timeline_with_title(news_df: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    sparse_series = False
    if not news_df.empty:
        work = news_df.copy()
        work["day"] = work["published_at"].dt.floor("D")
        grouped = (
            work.groupby(["ticker", "day"], as_index=False)
            .agg(
                sentiment=("sentiment_score", "mean"),
                confidence=("positive_score", "mean"),
                headline_count=("title", "count"),
            )
        )
        for ticker in sorted(grouped["ticker"].unique()):
            subset = grouped[grouped["ticker"] == ticker]
            if len(subset) <= 3:
                sparse_series = True
                fig.add_trace(
                    go.Bar(
                        x=subset["day"],
                        y=subset["sentiment"],
                        name=ticker,
                        marker_color=np.where(
                            subset["sentiment"] >= 0,
                            PALETTE["bull"],
                            PALETTE["bear"],
                        ),
                        opacity=0.8,
                        customdata=subset[["headline_count"]],
                        hovertemplate=(
                            "<b>%{x|%d %b %Y}</b><br>"
                            "Sentiment: %{y:.2f}<br>"
                            "Headlines: %{customdata[0]}<extra>"
                            + ticker
                            + "</extra>"
                        ),
                    )
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=subset["day"],
                        y=subset["sentiment"],
                        mode="lines+markers",
                        name=ticker,
                        line={"width": 3},
                        customdata=subset[["headline_count"]],
                        hovertemplate=(
                            "<b>%{x|%d %b %Y}</b><br>"
                            "Sentiment: %{y:.2f}<br>"
                            "Headlines: %{customdata[0]}<extra>"
                            + ticker
                            + "</extra>"
                        ),
                    )
                )

    fig.update_layout(
        title=title,
        paper_bgcolor=PALETTE["paper"],
        plot_bgcolor=PALETTE["paper"],
        font={"color": PALETTE["ink"]},
        margin={"l": 32, "r": 24, "t": 56, "b": 28},
        legend={"orientation": "h", "y": 1.12},
        barmode="group",
        xaxis={"title": "", "gridcolor": PALETTE["grid"]},
        yaxis={"title": "Sentiment Score", "gridcolor": PALETTE["grid"], "zerolinecolor": PALETTE["grid"]},
    )
    if sparse_series:
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=1,
            y=1.16,
            showarrow=False,
            xanchor="right",
            text="Sparse data shown as daily bars",
            font={"size": 12, "color": PALETTE["muted"]},
        )
    return fig


def build_overlay_chart(focus_ticker: str, price_df: pd.DataFrame, news_df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    ticker_prices = price_df[price_df["ticker"] == focus_ticker]
    ticker_news = news_df[news_df["ticker"] == focus_ticker]

    if not ticker_prices.empty:
        fig.add_trace(
            go.Scatter(
                x=ticker_prices["timestamp"],
                y=ticker_prices["close"],
                mode="lines",
                name=f"{focus_ticker} Price",
                line={"color": PALETTE["line"], "width": 3},
            ),
            secondary_y=False,
        )
    if not ticker_news.empty:
        fig.add_trace(
            go.Bar(
                x=ticker_news["published_at"],
                y=ticker_news["sentiment_score"],
                name="Headline Sentiment",
                marker_color=np.where(
                    ticker_news["sentiment_score"] >= 0,
                    PALETTE["bull"],
                    PALETTE["bear"],
                ),
                opacity=0.55,
                hovertext=ticker_news["title"],
            ),
            secondary_y=True,
        )

    fig.update_layout(
        title=f"Price vs Sentiment Overlay • {focus_ticker}",
        paper_bgcolor=PALETTE["paper"],
        plot_bgcolor=PALETTE["paper"],
        font={"color": PALETTE["ink"]},
        margin={"l": 32, "r": 24, "t": 56, "b": 28},
        legend={"orientation": "h", "y": 1.1},
    )
    fig.update_xaxes(gridcolor=PALETTE["grid"])
    fig.update_yaxes(title_text="Price", secondary_y=False, gridcolor=PALETTE["grid"])
    fig.update_yaxes(title_text="Sentiment", secondary_y=True, showgrid=False)
    return fig


def build_impact_scatter(event_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not event_df.empty:
        for ticker in sorted(event_df["ticker"].unique()):
            subset = event_df[event_df["ticker"] == ticker]
            fig.add_trace(
                go.Scatter(
                    x=subset["sentiment_score"],
                    y=subset["impact_pct"],
                    mode="markers",
                    name=ticker,
                    marker={"size": np.clip(subset["confidence_pct"], 10, 26), "opacity": 0.75},
                    text=subset["title"],
                )
            )

    fig.update_layout(
        title="Sentiment vs Estimated Impact",
        paper_bgcolor=PALETTE["paper"],
        plot_bgcolor=PALETTE["paper"],
        font={"color": PALETTE["ink"]},
        margin={"l": 32, "r": 24, "t": 56, "b": 28},
        xaxis={"title": "Sentiment Score", "gridcolor": PALETTE["grid"]},
        yaxis={"title": "Estimated 1H Impact %", "gridcolor": PALETTE["grid"]},
    )
    return fig


def build_sector_heatmap(sector_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not sector_df.empty:
        fig.add_trace(
            go.Heatmap(
                z=[sector_df["sentiment"].tolist()],
                x=sector_df["sector"].tolist(),
                y=["Sector Mood"],
                text=[[f'{row["sector"]}<br>Sentiment {row["sentiment"]:.2f}<br>Return {row["performance"]:.2f}%'
                       for _, row in sector_df.iterrows()]],
                hoverinfo="text",
                colorscale=[[0.0, "#c0392b"], [0.5, "#f3d9a6"], [1.0, "#148f77"]],
                zmin=-1,
                zmax=1,
            )
        )

    fig.update_layout(
        title="Sector Heatmap",
        paper_bgcolor=PALETTE["paper"],
        plot_bgcolor=PALETTE["paper"],
        font={"color": PALETTE["ink"]},
        margin={"l": 24, "r": 24, "t": 56, "b": 28},
    )
    return fig


def build_compare_chart(compare_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not compare_df.empty:
        ordered = compare_df.sort_values("pct_change", ascending=False)
        fig.add_trace(
            go.Bar(
                x=ordered["ticker"],
                y=ordered["avg_sentiment"],
                name="Sentiment",
                marker_color=PALETTE["bull"],
            )
        )
        fig.add_trace(
            go.Bar(
                x=ordered["ticker"],
                y=ordered["pct_change"],
                name="Return %",
                marker_color=PALETTE["accent_2"],
            )
        )
        fig.add_trace(
            go.Scatter(
                x=ordered["ticker"],
                y=ordered["avg_confidence"],
                name="Confidence %",
                mode="lines+markers",
                line={"color": PALETTE["line"], "width": 3},
                marker={"size": 10},
                yaxis="y2",
            )
        )

    fig.update_layout(
        title="Signal Snapshot",
        barmode="group",
        paper_bgcolor=PALETTE["paper"],
        plot_bgcolor=PALETTE["paper"],
        font={"color": PALETTE["ink"]},
        margin={"l": 32, "r": 24, "t": 56, "b": 28},
        xaxis={"title": "", "gridcolor": PALETTE["grid"]},
        yaxis={"title": "Sentiment / Return %", "gridcolor": PALETTE["grid"]},
        yaxis2={"title": "Confidence %", "overlaying": "y", "side": "right", "showgrid": False, "range": [0, 100]},
        legend={"orientation": "h", "y": 1.12},
    )
    return fig


def build_price_timeline(
    price_df: pd.DataFrame,
    focus_ticker: str | None = None,
    title: str = "Price Timeline",
    normalize: bool = False,
) -> go.Figure:
    fig = go.Figure()
    work = price_df.copy()
    if focus_ticker:
        work = work[work["ticker"] == focus_ticker]
    if not work.empty:
        for ticker in sorted(work["ticker"].unique()):
            subset = work[work["ticker"] == ticker]
            y_values = subset["close"]
            if normalize and not subset.empty:
                start_close = float(subset["close"].iloc[0])
                if start_close:
                    y_values = (subset["close"] / start_close) * 100.0
            fig.add_trace(
                go.Scatter(
                    x=subset["timestamp"],
                    y=y_values,
                    mode="lines",
                    name=ticker,
                    line={"width": 3},
                )
            )

    fig.update_layout(
        title=title,
        paper_bgcolor=PALETTE["paper"],
        plot_bgcolor=PALETTE["paper"],
        font={"color": PALETTE["ink"]},
        margin={"l": 32, "r": 24, "t": 56, "b": 28},
        legend={"orientation": "h", "y": 1.12},
        xaxis={"title": "", "gridcolor": PALETTE["grid"]},
        yaxis={"title": "Indexed Close (100 = start)" if normalize else "Close Price", "gridcolor": PALETTE["grid"]},
    )
    return fig


def build_metric_grid(items: list[tuple[str, str, str]], column_size: int = 3) -> list[dbc.Col]:
    return [
        dbc.Col(
            html.Div(
                [
                    html.Div(title, className="metric-label"),
                    html.Div(value, className="metric-value"),
                    html.Div(note, className="metric-note"),
                ],
                className="metric-card",
            ),
            md=6,
            lg=column_size,
        )
        for title, value, note in items
    ]


def build_empty_figure(title: str, message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        paper_bgcolor=PALETTE["paper"],
        plot_bgcolor=PALETTE["paper"],
        font={"color": PALETTE["ink"]},
        margin={"l": 32, "r": 24, "t": 56, "b": 28},
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 14, "color": PALETTE["muted"]},
            }
        ],
    )
    return fig


def build_summary_list(items: list[tuple[str, str]]) -> list[html.Div]:
    return [
        html.Div(
            [
                html.Div(label, className="summary-label"),
                html.Div(value, className="summary-value"),
            ],
            className="summary-item",
        )
        for label, value in items
    ]


def build_news_table(event_df: pd.DataFrame, news_df: pd.DataFrame) -> pd.DataFrame:
    if not event_df.empty:
        work = event_df.sort_values("published_at", ascending=False).copy()
        work["confidence_pct"] = work["confidence_pct"].round(1)
        work["impact_pct"] = work["impact_pct"].round(2)
        work["published_at"] = pd.to_datetime(work["published_at"]).dt.strftime("%Y-%m-%d %H:%M")
        work["source"] = work.get("source", "Unknown")
        work["explanation"] = np.where(
            work["sentiment_score"] > 0.2,
            "Positive catalyst cluster",
            np.where(work["sentiment_score"] < -0.2, "Negative catalyst cluster", "Mixed or neutral tone"),
        )
        return work[
            ["published_at", "ticker", "source", "title", "sentiment_label", "confidence_pct", "impact_pct", "explanation"]
        ].rename(
            columns={
                "published_at": "Time",
                "ticker": "Ticker",
                "source": "Source",
                "title": "Headline",
                "sentiment_label": "Sentiment",
                "confidence_pct": "Confidence %",
                "impact_pct": "Impact %",
                "explanation": "Explanation",
            }
        )

    if news_df.empty:
        return pd.DataFrame(columns=["Time", "Ticker", "Source", "Headline", "Sentiment", "Confidence %", "Impact %", "Explanation"])

    fallback = news_df.sort_values("published_at", ascending=False).copy()
    fallback["Time"] = pd.to_datetime(fallback["published_at"]).dt.strftime("%Y-%m-%d %H:%M")
    fallback["Source"] = fallback.get("source", "Unknown")
    fallback["Confidence %"] = (
        fallback[["positive_score", "negative_score", "neutral_score"]].max(axis=1).fillna(0.0) * 100.0
    ).round(1)
    fallback["Impact %"] = "n/a"
    fallback["Explanation"] = "Price linkage unavailable for this headline in the current window."
    return fallback[["Time", "ticker", "Source", "title", "sentiment_label", "Confidence %", "Impact %", "Explanation"]].rename(
        columns={"ticker": "Ticker", "title": "Headline", "sentiment_label": "Sentiment"}
    )


def build_alert_panel(alerts: list[dict[str, str]], demo_mode: bool) -> list[dbc.ListGroupItem]:
    if not alerts:
        label = "No watchlist alerts in the selected window."
        return [dbc.ListGroupItem(label)]

    return [
        dbc.ListGroupItem(
            [html.Div(alert["title"], className="alert-title"), html.Div(alert["detail"], className="alert-detail")],
            className="alert-item",
        )
        for alert in alerts
    ]


def build_research_card() -> html.Div:
    return html.Div(
        [
            html.Div("Research Grounding", className="section-kicker"),
            html.H4("Why This Dashboard Has Academic Weight", className="section-title"),
            html.Ul(
                [
                    html.Li("FinBERT: domain-specific financial sentiment modeling."),
                    html.Li("Financial PhraseBank: benchmark dataset behind financial sentiment labeling."),
                    html.Li("News Sentiment for Stock Prediction: validates sentiment-driven price analysis."),
                    html.Li("Investor Sentiment and Stock Returns: theoretical support for market impact effects."),
                ],
                className="research-list",
            ),
            html.P(
                "Paper selection is anchored on financial NLP, sentiment-price correlation, and scalable analytics visualization.",
                className="research-note",
            ),
        ],
        className="research-card",
    )


def get_assets_folder() -> str:
    return str(Path(__file__).with_name("assets"))
