from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate

from finsent.app.dashboard.components import build_empty_state, build_nav_links
from finsent.app.dashboard.layout import build_app_layout
from finsent.app.dashboard.pages import alerts, compare, news_impact, stock_detail, summary
from finsent.app.dashboard.view_model import (
    build_ai_explanation,
    build_alert_panel,
    build_alerts,
    build_compare_chart,
    build_dashboard_state,
    build_empty_figure,
    build_impact_scatter,
    build_metric_grid,
    build_news_table,
    build_overlay_chart,
    build_price_timeline,
    build_sector_heatmap,
    build_sentiment_timeline_with_title,
    build_summary_list,
    ensure_live_data,
    get_company_name,
    get_assets_folder,
)


def _selection(data: dict | None) -> dict:
    base = {
        "focus_ticker": "AAPL",
        "compare_tickers": [],
        "horizon": "medium",
        "date_window": "30d",
        "alert_threshold": 40,
        "analysis_ready": False,
    }
    if data:
        base.update(data)
    return base


def _resolve_date_window(selection: dict) -> tuple[str | None, str | None]:
    today = pd.Timestamp.now().normalize()
    date_window = selection.get("date_window", "30d")
    if date_window == "7d":
        return (today - pd.Timedelta(days=7)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    if date_window == "30d":
        return (today - pd.Timedelta(days=30)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    if date_window == "90d":
        return (today - pd.Timedelta(days=90)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    return None, None


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
            "/summary": summary.layout,
            "/stock-detail": stock_detail.layout,
            "/news-impact": news_impact.layout,
            "/compare": compare.layout,
            "/alerts": alerts.layout,
        }
        current_path = pathname or "/"
        if current_path == "/":
            return html.Div()
        if not selection["analysis_ready"]:
            return build_empty_state(
                "Load a ticker first",
                "Start from the landing page, choose a ticker, and then open the analysis workspace.",
            )
        return routes.get(current_path, summary.layout)()

    @app.callback(
        Output("top-controls-container", "style"),
        Output("landing-controls-container", "style"),
        Output("horizon-toolbar-control", "style"),
        Output("date-toolbar-control", "style"),
        Output("compare-toolbar-control", "style"),
        Output("alert-toolbar-control", "style"),
        Input("url", "pathname"),
        Input("selection-store", "data"),
    )
    def toggle_top_controls(pathname: str | None, selection_data: dict | None):
        selection = _selection(selection_data)
        current_path = pathname or "/"
        if current_path == "/" or not selection["analysis_ready"]:
            return {"display": "none"}, {"display": "grid"}, {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "none"}

        horizon_style = {"display": "block"} if current_path in {"/summary", "/stock-detail", "/compare", "/alerts"} else {"display": "none"}
        date_style = {"display": "block"} if current_path in {"/summary", "/news-impact"} else {"display": "none"}
        compare_style = {"display": "block"} if current_path in {"/summary", "/stock-detail", "/news-impact", "/compare", "/alerts"} else {"display": "none"}
        alert_style = {"display": "block"} if current_path == "/alerts" else {"display": "none"}
        return {"display": "block"}, {"display": "none"}, horizon_style, date_style, compare_style, alert_style

    @app.callback(
        Output("landing-ticker-search", "value"),
        Output("global-focus-ticker", "value"),
        Output("global-compare-tickers", "value"),
        Output("global-horizon-toggle", "value"),
        Output("global-date-window", "value"),
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
            selection["date_window"],
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
        selection["analysis_ready"] = True
        ensure_live_data([landing_ticker])
        return selection, "/summary"

    @app.callback(
        Output("selection-store", "data", allow_duplicate=True),
        Input("global-focus-ticker", "value"),
        Input("global-horizon-toggle", "value"),
        Input("global-date-window", "value"),
        Input("global-alert-threshold", "value"),
        State("selection-store", "data"),
        prevent_initial_call=True,
    )
    def update_selection_from_filters(
        global_focus_ticker: str | None,
        global_horizon: str | None,
        global_date_window: str | None,
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
        elif trigger == "global-horizon-toggle" and global_horizon:
            selection["horizon"] = global_horizon
        elif trigger == "global-date-window" and global_date_window:
            selection["date_window"] = global_date_window
        elif trigger == "global-alert-threshold" and global_alert_threshold is not None:
            selection["alert_threshold"] = global_alert_threshold
        else:
            raise PreventUpdate

        return selection

    @app.callback(
        Output("selection-store", "data", allow_duplicate=True),
        Output("url", "pathname", allow_duplicate=True),
        Input("global-compare-apply", "n_clicks"),
        State("global-compare-tickers", "value"),
        State("selection-store", "data"),
        prevent_initial_call=True,
    )
    def apply_compare_selection(
        compare_apply_clicks: int | None,
        global_compare_tickers: list[str] | None,
        selection_data: dict | None,
    ):
        if not compare_apply_clicks:
            raise PreventUpdate

        selection = _selection(selection_data)
        compare_values = [ticker for ticker in (global_compare_tickers or []) if ticker and ticker != selection["focus_ticker"]]
        selection["compare_tickers"] = compare_values[:2]
        return selection, "/compare"

    @app.callback(
        Output("nav-home-link", "style"),
        Output("nav-links", "children"),
        Output("nav-mode-badge", "children"),
        Input("selection-store", "data"),
        Input("url", "pathname"),
    )
    def update_nav_badge(selection_data: dict | None, pathname: str | None):
        selection = _selection(selection_data)
        current_path = pathname or "/"
        nav_links = build_nav_links(pathname, selection["analysis_ready"])
        home_style = {"display": "inline-flex"} if current_path != "/" else {"display": "none"}
        if not selection["analysis_ready"] or current_path == "/":
            return home_style, nav_links, "Select a ticker to begin"

        start_date, end_date = _resolve_date_window(selection)
        state = build_dashboard_state(
            selection["focus_ticker"],
            selection["compare_tickers"],
            selection["horizon"],
            start_date,
            end_date,
        )
        company_name = get_company_name(selection["focus_ticker"])
        data_label = "Demo Mode" if state.demo_mode else "Live Data"
        return home_style, nav_links, f'{selection["focus_ticker"]} • {company_name} • {data_label}'

    @app.callback(
        Output("summary-page-title", "children"),
        Output("summary-badge-row", "children"),
        Output("summary-metric-row", "children"),
        Output("summary-sentiment-chart", "figure"),
        Output("summary-ai-explanation", "children"),
        Input("selection-store", "data"),
    )
    def refresh_summary(selection_data: dict | None):
        selection = _selection(selection_data)
        focus_ticker = selection["focus_ticker"]
        if not selection["analysis_ready"] or not focus_ticker:
            raise PreventUpdate

        start_date, end_date = _resolve_date_window(selection)
        state = build_dashboard_state(
            focus_ticker,
            selection["compare_tickers"],
            selection["horizon"],
            start_date,
            end_date,
        )
        company_name = get_company_name(focus_ticker)
        ticker_news = state.news_df[state.news_df["ticker"] == focus_ticker]
        ticker_prices = state.price_df[state.price_df["ticker"] == focus_ticker]
        avg_sentiment = float(ticker_news["sentiment_score"].mean()) if not ticker_news.empty else 0.0
        avg_confidence = (
            float(ticker_news[["positive_score", "negative_score", "neutral_score"]].max(axis=1).mean() * 100.0)
            if not ticker_news.empty
            else 0.0
        )
        latest_label = ticker_news["sentiment_label"].iloc[-1].title() if not ticker_news.empty else "Neutral"
        current_price = float(ticker_prices["close"].iloc[-1]) if not ticker_prices.empty else 0.0
        price_change = 0.0
        if len(ticker_prices) >= 2:
            first_close = float(ticker_prices["close"].iloc[0])
            last_close = float(ticker_prices["close"].iloc[-1])
            price_change = ((last_close - first_close) / first_close) * 100.0 if first_close else 0.0

        badges = [
            html.Div(f"{latest_label} signal", className="pill-badge"),
            html.Div(f"Price move {price_change:.2f}%", className="pill-badge"),
        ]
        metrics = build_metric_grid(
            [
                ("Current Price", f"${current_price:.2f}" if current_price else "n/a", "Latest stored close"),
                ("Sentiment Score", f"{avg_sentiment:.2f}", "Average headline tone"),
                ("Confidence", f"{avg_confidence:.0f}%", "FinBERT certainty"),
                ("Short-Term Move", f"{price_change:.2f}%", "Selected time window"),
            ],
            column_size=3,
        )
        figure = (
            build_sentiment_timeline_with_title(ticker_news, "Recent Sentiment")
            if not ticker_news.empty
            else build_empty_figure("Recent Sentiment", f"No sentiment history is stored yet for {focus_ticker}.")
        )
        explanation_lines = build_ai_explanation(focus_ticker, state.news_df, state.compare_df)[:3]
        return (
            f"{focus_ticker} | {company_name}",
            badges,
            metrics,
            figure,
            [html.Div(line, className="explanation-line") for line in explanation_lines],
        )

    @app.callback(
        Output("stock-page-title", "children"),
        Output("stock-badge-row", "children"),
        Output("stock-metric-row", "children"),
        Output("stock-main-chart", "figure"),
        Output("stock-ai-explanation", "children"),
        Output("stock-summary-panel", "children"),
        Input("stock-chart-mode", "value"),
        Input("selection-store", "data"),
    )
    def refresh_stock_detail(chart_mode: str | None, selection_data: dict | None):
        selection = _selection(selection_data)
        focus_ticker = selection["focus_ticker"]
        if not selection["analysis_ready"] or not focus_ticker:
            raise PreventUpdate
        start_date, end_date = _resolve_date_window(selection)
        state = build_dashboard_state(
            focus_ticker,
            selection["compare_tickers"],
            selection["horizon"],
            start_date,
            end_date,
        )
        ticker_news = state.news_df[state.news_df["ticker"] == focus_ticker]
        ticker_prices = state.price_df[state.price_df["ticker"] == focus_ticker]
        ticker_events = state.event_df[state.event_df["ticker"] == focus_ticker] if not state.event_df.empty else pd.DataFrame()
        company_name = get_company_name(focus_ticker)
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
        current_price = float(ticker_prices["close"].iloc[-1]) if not ticker_prices.empty else 0.0
        badges = [
            html.Div(f"{latest_label} sentiment", className="pill-badge"),
            html.Div(f"Estimated impact {avg_impact:.2f}%", className="pill-badge"),
        ]
        metrics = build_metric_grid(
            [
                ("Current Price", f"${current_price:.2f}" if current_price else "n/a", "Latest stored close"),
                ("Price Change", f"{price_change:.2f}%", "Selected window"),
                ("Sentiment Score", f"{avg_sentiment:.2f}", latest_label),
                ("Confidence", f"{avg_confidence:.0f}%", "FinBERT confidence"),
            ],
            column_size=3,
        )
        summary = build_summary_list(
            [
                (
                    "Sector",
                    state.compare_df[state.compare_df["ticker"] == focus_ticker]["sector"].iloc[0]
                    if focus_ticker in state.compare_df.get("ticker", pd.Series(dtype=str)).tolist()
                    else "n/a",
                ),
                ("Company", company_name),
                ("News Volume", str(len(ticker_news))),
                ("Articles", str(len(ticker_news))),
                ("Last Update", ticker_news["published_at"].max().strftime("%Y-%m-%d %H:%M") if not ticker_news.empty else "n/a"),
                ("Average Impact", f"{avg_impact:.2f}%"),
                ("Correlation", f'{ticker_events["sentiment_score"].corr(ticker_events["forward_return"]):.2f}' if len(ticker_events) >= 2 else "n/a"),
            ]
        )
        if chart_mode == "overlay":
            main_chart = build_overlay_chart(focus_ticker, state.price_df, state.news_df)
        else:
            main_chart = (
                build_price_timeline(
                    ticker_prices if not ticker_prices.empty else state.price_df.head(0),
                    title=f"{focus_ticker} Price Timeline",
                )
                if not ticker_prices.empty
                else build_empty_figure(f"{focus_ticker} Price Timeline", "No price history is stored for the current window.")
            )
        return (
            f"{focus_ticker} | {company_name}",
            badges,
            metrics,
            main_chart,
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
        if not selection["analysis_ready"] or not focus_ticker:
            raise PreventUpdate
        start_date, end_date = _resolve_date_window(selection)
        state = build_dashboard_state(
            focus_ticker,
            selection["compare_tickers"],
            selection["horizon"],
            start_date,
            end_date,
        )
        ticker_news = state.news_df[state.news_df["ticker"] == focus_ticker]
        ticker_events = state.event_df[state.event_df["ticker"] == focus_ticker] if not state.event_df.empty else pd.DataFrame()
        table_df = build_news_table(ticker_events, ticker_news)
        summary = build_summary_list(
            [
                ("Headlines", str(len(table_df))),
                ("Average Impact", f'{ticker_events["impact_pct"].mean():.2f}%' if not ticker_events.empty else "n/a"),
                ("Highest Positive", f'{ticker_events["impact_pct"].max():.2f}%' if not ticker_events.empty else "n/a"),
                ("Highest Negative", f'{ticker_events["impact_pct"].min():.2f}%' if not ticker_events.empty else "n/a"),
                ("Average Confidence", f'{ticker_events["confidence_pct"].mean():.0f}%' if not ticker_events.empty else "n/a"),
            ]
        )
        return (
            build_impact_scatter(ticker_events)
            if not ticker_events.empty
            else build_empty_figure(
                "Sentiment vs Estimated Impact",
                f"No valid price bars overlap the stored headlines for {focus_ticker} in this window. Import newer prices or switch to All Stored Data.",
            ),
            summary,
            table_df.to_dict("records"),
            [{"name": col, "id": col} for col in table_df.columns],
        )

    @app.callback(
        Output("compare-selection-summary", "children"),
        Output("compare-empty-state", "children"),
        Output("compare-empty-state", "style"),
        Output("compare-content", "style"),
        Output("compare-metric-row", "children"),
        Output("compare-main-chart", "figure"),
        Output("compare-secondary-chart", "figure"),
        Output("compare-ai-summary", "children"),
        Input("selection-store", "data"),
    )
    def refresh_compare(selection_data: dict | None):
        selection = _selection(selection_data)
        focus_ticker = selection["focus_ticker"]
        if not selection["analysis_ready"] or not focus_ticker:
            raise PreventUpdate
        start_date, end_date = _resolve_date_window(selection)
        state = build_dashboard_state(
            focus_ticker,
            selection["compare_tickers"],
            selection["horizon"],
            start_date,
            end_date,
        )
        compare_df = state.compare_df.copy()
        applied_peers = selection["compare_tickers"][:2]
        selection_summary = (
            html.Div(
                [
                    html.Div("Applied Comparison", className="section-kicker"),
                    html.Div(
                        f'{focus_ticker} vs ' + " • ".join(applied_peers),
                        className="compare-selection-value",
                    ),
                ],
                className="section-shell compare-selection-shell",
            )
            if applied_peers
            else html.Div()
        )
        if len(compare_df) < 2:
            return (
                selection_summary,
                build_empty_state(
                    "Add peer tickers to compare",
                    f"Use More filters to choose up to 2 peers, then press Compare. The page will then rank sentiment, returns, and confidence against {focus_ticker}.",
                ),
                {"display": "block"},
                {"display": "none"},
                [],
                build_empty_figure("Peer Comparison", "Peer comparison will appear after you select additional tickers."),
                build_empty_figure("Relative Price Performance", "Choose peer tickers to unlock the secondary comparison view."),
                [html.Div("Comparison insights will appear here once at least two tickers are loaded.", className="explanation-line")],
            )

        metrics = build_metric_grid(
            [
                ("Best Sentiment", compare_df.sort_values("avg_sentiment", ascending=False)["ticker"].iloc[0] if not compare_df.empty else "n/a", "Highest average headline tone"),
                ("Best Return", compare_df.sort_values("pct_change", ascending=False)["ticker"].iloc[0] if not compare_df.empty else "n/a", "Strongest move in stored window"),
                ("Highest News Volume", compare_df.sort_values("news_volume", ascending=False)["ticker"].iloc[0] if not compare_df.empty else "n/a", "Most headline coverage"),
                ("Best Confidence", compare_df.sort_values("avg_confidence", ascending=False)["ticker"].iloc[0] if not compare_df.empty else "n/a", "Most stable signal"),
            ],
            column_size=3,
        )
        summary_lines: list[html.Div] = []
        if not compare_df.empty:
            leader = compare_df.sort_values("avg_sentiment", ascending=False).iloc[0]
            winner = compare_df.sort_values("pct_change", ascending=False).iloc[0]
            laggard = compare_df.sort_values("pct_change", ascending=True).iloc[0]
            reliable = compare_df.sort_values("avg_confidence", ascending=False).iloc[0]
            summary_lines = [
                html.Div(f'{winner["ticker"]} is leading on relative performance at {winner["pct_change"]:.2f}% in the stored comparison window.', className="explanation-line"),
                html.Div(f'{leader["ticker"]} has the strongest sentiment signal with an average score of {leader["avg_sentiment"]:.2f}.', className="explanation-line"),
                html.Div(f'{reliable["ticker"]} has the most reliable model output at {reliable["avg_confidence"]:.0f}% confidence, while {laggard["ticker"]} is the weakest price mover.', className="explanation-line"),
            ]
        return (
            selection_summary,
            [],
            {"display": "none"},
            {"display": "block"},
            metrics,
            build_price_timeline(state.price_df, title="Indexed Price Performance", normalize=True),
            build_compare_chart(compare_df),
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
        if not selection["analysis_ready"] or not focus_ticker:
            raise PreventUpdate
        start_date, end_date = _resolve_date_window(selection)
        state = build_dashboard_state(
            focus_ticker,
            selection["compare_tickers"],
            selection["horizon"],
            start_date,
            end_date,
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
            build_sector_heatmap(state.sector_df)
            if not state.sector_df.empty
            else build_empty_figure("Sector Mood", "Sector-level mood appears when peer data is available."),
            build_sentiment_timeline_with_title(state.news_df, "Recent Sentiment Trend")
            if not state.news_df.empty
            else build_empty_figure("Recent Sentiment Trend", "No stored sentiment series is available in the selected window."),
        )

    return app
