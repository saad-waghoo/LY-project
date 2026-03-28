from __future__ import annotations

from dash import dcc, html

from finsent.app.dashboard.components import build_filter_bar, build_footer, build_landing_search, build_navbar


def build_app_layout(default_ticker: str) -> html.Div:
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            dcc.Store(
                id="selection-store",
                storage_type="session",
                data={
                    "focus_ticker": default_ticker,
                    "compare_tickers": ["MSFT", "NVDA"],
                    "horizon": "medium",
                    "start_date": None,
                    "end_date": None,
                    "alert_threshold": 40,
                },
            ),
            build_navbar(),
            html.Div(build_landing_search(default_ticker), id="landing-controls-container"),
            html.Div(
                build_filter_bar(
                    focus_ticker=default_ticker,
                    compare_tickers=["MSFT", "NVDA"],
                    horizon="medium",
                    start_date=None,
                    end_date=None,
                    alert_threshold=40,
                ),
                id="top-controls-container",
            ),
            html.Div(id="page-container"),
            build_footer(),
        ],
        className="dashboard-shell",
    )
