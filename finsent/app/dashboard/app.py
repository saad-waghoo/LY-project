from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate

from finsent.app.dashboard.layout import build_app_layout
from finsent.app.dashboard.pages import alerts, compare, news_impact, overview, stock_detail
from finsent.app.dashboard.view_model import (
    build_ai_explanation,
    build_alert_panel,
    build_alerts,
    build_compare_chart,
    build_dashboard_state,
    build_impact_scatter,
    build_metric_cards,
    build_metric_grid,
    build_news_table,
    build_overlay_chart,
    build_price_timeline,
    build_sector_heatmap,
    build_sentiment_timeline,
    build_summary_list,
    build_top_panel,
    compute_market_mood,
    ensure_live_data,
    get_assets_folder,
)


def _selection(data: dict | None) -> dict:
    base = {
        "focus_ticker": "AAPL",
        "compare_tickers": ["MSFT", "NVDA"],
        "horizon": "medium",
        "start_date": None,
        "end_date": None,
        "alert_threshold": 40,
    }
    if data:
        base.update(data)
    return base


def create_app(default_ticker: str = "AAPL") -> dash.Dash:
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        assets_folder=get_assets_folder(),
        suppress_callback_exceptions=True,
    )
    app.layout = build_app_layout(default_ticker)

    @app.callback(
        Output("page-container", "children"),
        Input("url", "pathname"),
        Input("selection-store", "data"),
    )
    def render_page(pathname: str | None, selection_data: dict | None):
        selection = _selection(selection_data)
        routes = {
            "/": lambda: overview.layout(selection["focus_ticker"]),
            "/stock-detail": stock_detail.layout,
            "/news-impact": news_impact.layout,
            "/compare": compare.layout,
            "/alerts": alerts.layout,
        }
        return routes.get(pathname or "/", lambda: overview.layout(selection["focus_ticker"]))()

    @app.callback(
        Output("top-controls-container", "style"),
        Output("landing-controls-container", "style"),
        Input("url", "pathname"),
    )
    def toggle_top_controls(pathname: str | None):
        if (pathname or "/") == "/":
            return {"display": "none"}, {"display": "block"}
        return {"display": "block"}, {"display": "none"}

    @app.callback(
        Output("landing-ticker-search", "value"),
        Output("global-focus-ticker", "value"),
        Output("global-compare-tickers", "value"),
        Output("global-horizon-toggle", "value"),
        Output("global-date-range", "start_date"),
        Output("global-date-range", "end_date"),
        Output("global-alert-threshold", "value"),
        Input("selection-store", "data"),
    )
    def sync_controls_from_selection(selection_data: dict | None):
        selection = _selection(selection_data)
        return (
            selection["focus_ticker"],
            selection["focus_ticker"],
            selection["compare_tickers"],
            selection["horizon"],
            selection["start_date"],
            selection["end_date"],
            selection["alert_threshold"],
        )

    @app.callback(
        Output("selection-store", "data", allow_duplicate=True),
        Output("url", "pathname"),
        Input("landing-search-button", "n_clicks"),
        State("landing-ticker-search", "value"),
        State("selection-store", "data"),
        prevent_initial_call=True,
    )
    def update_selection_from_landing(
        landing_clicks: int | None,
        landing_ticker: str | None,
        selection_data: dict | None,
    ):
        if not landing_clicks:
            raise PreventUpdate

        selection = _selection(selection_data)
        if not landing_ticker:
            return no_update, no_update

        selection["focus_ticker"] = landing_ticker
        ensure_live_data([landing_ticker])
        return selection, "/stock-detail"

    @app.callback(
        Output("selection-store", "data", allow_duplicate=True),
        Input("global-focus-ticker", "value"),
        Input("global-compare-tickers", "value"),
        Input("global-horizon-toggle", "value"),
        Input("global-date-range", "start_date"),
        Input("global-date-range", "end_date"),
        Input("global-alert-threshold", "value"),
        State("selection-store", "data"),
        prevent_initial_call=True,
    )
    def update_selection_from_filters(
        global_focus_ticker: str | None,
        global_compare_tickers: list[str] | None,
        global_horizon: str | None,
        global_start_date: str | None,
        global_end_date: str | None,
        global_alert_threshold: int | None,
        selection_data: dict | None,
    ):
        trigger = ctx.triggered_id
        if trigger is None:
            raise PreventUpdate

        selection = _selection(selection_data)

        if trigger == "global-focus-ticker" and global_focus_ticker:
            selection["focus_ticker"] = global_focus_ticker
            ensure_live_data([global_focus_ticker])
        elif trigger == "global-compare-tickers":
            selection["compare_tickers"] = global_compare_tickers or []
            ensure_live_data(selection["compare_tickers"])
        elif trigger == "global-horizon-toggle" and global_horizon:
            selection["horizon"] = global_horizon
        elif trigger == "global-date-range":
            selection["start_date"] = global_start_date
            selection["end_date"] = global_end_date
        elif trigger == "global-alert-threshold" and global_alert_threshold is not None:
            selection["alert_threshold"] = global_alert_threshold
        else:
            raise PreventUpdate

        return selection

    @app.callback(
        Output("nav-mode-badge", "children"),
        Input("selection-store", "data"),
    )
    def update_nav_badge(selection_data: dict | None):
        selection = _selection(selection_data)
        state = build_dashboard_state(
            selection["focus_ticker"],
            selection["compare_tickers"],
            selection["horizon"],
            selection["start_date"],
            selection["end_date"],
        )
        return "Demo Mode" if state.demo_mode else "Live Data"

    @app.callback(
        Output("stock-page-title", "children"),
        Output("stock-badge-row", "children"),
        Output("stock-metric-row", "children"),
        Output("stock-overlay-chart", "figure"),
        Output("stock-sentiment-timeline", "figure"),
        Output("stock-price-chart", "figure"),
        Output("stock-ai-explanation", "children"),
        Output("stock-summary-panel", "children"),
        Input("selection-store", "data"),
    )
    def refresh_stock_detail(selection_data: dict | None):
        selection = _selection(selection_data)
        focus_ticker = selection["focus_ticker"]
        if not focus_ticker:
            raise PreventUpdate
        state = build_dashboard_state(
            focus_ticker,
            selection["compare_tickers"],
            selection["horizon"],
            selection["start_date"],
            selection["end_date"],
        )
        ticker_news = state.news_df[state.news_df["ticker"] == focus_ticker]
        ticker_prices = state.price_df[state.price_df["ticker"] == focus_ticker]
        ticker_events = state.event_df[state.event_df["ticker"] == focus_ticker] if not state.event_df.empty else pd.DataFrame()
        avg_sentiment = float(ticker_news["sentiment_score"].mean()) if not ticker_news.empty else 0.0
        avg_confidence = (
            float(ticker_news[["positive_score", "negative_score", "neutral_score"]].max(axis=1).mean() * 100.0)
            if not ticker_news.empty
            else 0.0
        )
        price_change = 0.0
        if len(ticker_prices) >= 2:
            first_close = float(ticker_prices["close"].iloc[0])
            last_close = float(ticker_prices["close"].iloc[-1])
            price_change = ((last_close - first_close) / first_close) * 100.0 if first_close else 0.0
        latest_label = ticker_news["sentiment_label"].iloc[-1].title() if not ticker_news.empty else "Neutral"
        avg_impact = float(ticker_events["impact_pct"].mean()) if not ticker_events.empty else 0.0
        badges = [
            html.Div(f"Sentiment: {latest_label}", className="pill-badge"),
            html.Div(f"Confidence: {avg_confidence:.0f}%", className="pill-badge"),
            html.Div(f"Impact: {avg_impact:.2f}%", className="pill-badge"),
        ]
        metrics = build_metric_grid(
            [
                ("Current Sentiment", f"{avg_sentiment:.2f}", latest_label),
                ("Confidence Score", f"{avg_confidence:.0f}%", "FinBERT confidence"),
                ("News Volume", str(len(ticker_news)), "Captured headlines"),
                ("Price Change", f"{price_change:.2f}%", "Selected window"),
            ]
        )
        summary = build_summary_list(
            [
                (
                    "Sector",
                    state.compare_df[state.compare_df["ticker"] == focus_ticker]["sector"].iloc[0]
                    if focus_ticker in state.compare_df.get("ticker", pd.Series(dtype=str)).tolist()
                    else "n/a",
                ),
                ("Articles", str(len(ticker_news))),
                ("Last Update", ticker_news["published_at"].max().strftime("%Y-%m-%d %H:%M") if not ticker_news.empty else "n/a"),
                ("Average Impact", f"{avg_impact:.2f}%"),
                ("Correlation", f'{ticker_events["sentiment_score"].corr(ticker_events["forward_return"]):.2f}' if len(ticker_events) >= 2 else "n/a"),
            ]
        )
        return (
            f"{focus_ticker} Detail View",
            badges,
            metrics,
            build_overlay_chart(focus_ticker, state.price_df, state.news_df),
            build_sentiment_timeline(ticker_news if not ticker_news.empty else state.news_df.head(0)),
            build_price_timeline(ticker_prices if not ticker_prices.empty else state.price_df.head(0), title=f"{focus_ticker} Price Timeline"),
            [html.Div(line, className="explanation-line") for line in build_ai_explanation(focus_ticker, state.news_df, state.compare_df)],
            summary,
        )

    @app.callback(
        Output("news-impact-scatter", "figure"),
        Output("news-impact-summary", "children"),
        Output("news-impact-table", "data"),
        Output("news-impact-table", "columns"),
        Input("selection-store", "data"),
    )
    def refresh_news_impact(selection_data: dict | None):
        selection = _selection(selection_data)
        focus_ticker = selection["focus_ticker"]
        if not focus_ticker:
            raise PreventUpdate
        state = build_dashboard_state(
            focus_ticker,
            selection["compare_tickers"],
            selection["horizon"],
            selection["start_date"],
            selection["end_date"],
        )
        table_df = build_news_table(state.event_df, state.news_df)
        summary = build_summary_list(
            [
                ("Headlines", str(len(table_df))),
                ("Average Impact", f'{state.event_df["impact_pct"].mean():.2f}%' if not state.event_df.empty else "n/a"),
                ("Highest Positive", f'{state.event_df["impact_pct"].max():.2f}%' if not state.event_df.empty else "n/a"),
                ("Highest Negative", f'{state.event_df["impact_pct"].min():.2f}%' if not state.event_df.empty else "n/a"),
            ]
        )
        return (
            build_impact_scatter(state.event_df),
            summary,
            table_df.to_dict("records"),
            [{"name": col, "id": col} for col in table_df.columns],
        )

    @app.callback(
        Output("compare-metric-row", "children"),
        Output("compare-main-chart", "figure"),
        Output("compare-sentiment-chart", "figure"),
        Output("compare-price-chart", "figure"),
        Output("compare-table", "data"),
        Output("compare-table", "columns"),
        Output("compare-ai-summary", "children"),
        Input("selection-store", "data"),
    )
    def refresh_compare(selection_data: dict | None):
        selection = _selection(selection_data)
        focus_ticker = selection["focus_ticker"]
        if not focus_ticker:
            raise PreventUpdate
        state = build_dashboard_state(
            focus_ticker,
            selection["compare_tickers"],
            selection["horizon"],
            selection["start_date"],
            selection["end_date"],
        )
        compare_df = state.compare_df.copy()
        compare_table = compare_df.rename(
            columns={
                "ticker": "Ticker",
                "avg_sentiment": "Avg Sentiment",
                "avg_confidence": "Confidence %",
                "pct_change": "Price Change %",
                "news_volume": "News Volume",
                "avg_impact_pct": "Avg Impact %",
            }
        )
        metrics = build_metric_grid(
            [
                ("Best Sentiment", compare_df.sort_values("avg_sentiment", ascending=False)["ticker"].iloc[0] if not compare_df.empty else "n/a", "Top ranked"),
                ("Best Return", compare_df.sort_values("pct_change", ascending=False)["ticker"].iloc[0] if not compare_df.empty else "n/a", "Strongest price move"),
                ("Highest News Volume", compare_df.sort_values("news_volume", ascending=False)["ticker"].iloc[0] if not compare_df.empty else "n/a", "Most coverage"),
                ("Strongest Confidence", compare_df.sort_values("avg_confidence", ascending=False)["ticker"].iloc[0] if not compare_df.empty else "n/a", "Most reliable signal"),
            ]
        )
        summary_lines: list[html.Div] = []
        if not compare_df.empty:
            leader = compare_df.sort_values("avg_sentiment", ascending=False).iloc[0]
            laggard = compare_df.sort_values("pct_change", ascending=True).iloc[0]
            noisy = compare_df.sort_values("news_volume", ascending=False).iloc[0]
            summary_lines = [
                html.Div(f'{leader["ticker"]} leads on sentiment with a score of {leader["avg_sentiment"]:.2f}.', className="explanation-line"),
                html.Div(f'{laggard["ticker"]} is the weakest price performer in the selected window.', className="explanation-line"),
                html.Div(f'{noisy["ticker"]} has the heaviest news flow and deserves closer inspection.', className="explanation-line"),
            ]
        return (
            metrics,
            build_compare_chart(compare_df),
            build_sentiment_timeline(state.news_df),
            build_price_timeline(state.price_df, title="Price Performance Comparison"),
            compare_table.to_dict("records"),
            [{"name": col, "id": col} for col in compare_table.columns],
            summary_lines,
        )

    @app.callback(
        Output("alerts-feed", "children"),
        Output("alerts-summary-panel", "children"),
        Output("alerts-sector-heatmap", "figure"),
        Output("alerts-shift-chart", "figure"),
        Input("selection-store", "data"),
    )
    def refresh_alerts(selection_data: dict | None):
        selection = _selection(selection_data)
        focus_ticker = selection["focus_ticker"]
        if not focus_ticker:
            raise PreventUpdate
        state = build_dashboard_state(
            focus_ticker,
            selection["compare_tickers"],
            selection["horizon"],
            selection["start_date"],
            selection["end_date"],
        )
        alerts_data = build_alerts(state.compare_df, state.event_df, selection["alert_threshold"])
        bearish = int((state.compare_df["avg_sentiment"] < 0).sum()) if not state.compare_df.empty else 0
        summary = build_summary_list(
            [
                ("Active Alerts", str(len(alerts_data))),
                ("Bearish Tickers", str(bearish)),
                ("Strongest Mover", state.compare_df.sort_values("pct_change", ascending=False)["ticker"].iloc[0] if not state.compare_df.empty else "n/a"),
                ("Latest Shift", state.news_df.sort_values("published_at", ascending=False)["ticker"].iloc[0] if not state.news_df.empty else "n/a"),
            ]
        )
        return (
            build_alert_panel(alerts_data, state.demo_mode),
            summary,
            build_sector_heatmap(state.sector_df),
            build_sentiment_timeline(state.news_df),
        )

    return app
