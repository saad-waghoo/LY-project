from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from finsent.app.dashboard.view_model import get_ticker_options


NAV_ITEMS = [
    ("Overview", "/"),
    ("Stock Detail", "/stock-detail"),
    ("News Impact", "/news-impact"),
    ("Compare", "/compare"),
    ("Alerts", "/alerts"),
]


def build_navbar() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Img(src="/assets/finsent-logo.svg", className="brand-logo", alt="FinSent logo"),
                    html.Div(
                        [
                            html.Div("FinSent", className="brand-mark"),
                            html.Div("Sentiment x Market Intelligence", className="brand-submark"),
                        ],
                        className="brand-copy",
                    ),
                ],
                className="brand-wrap",
            ),
            html.Div(
                [dcc.Link(label, href=path, className="nav-link-item") for label, path in NAV_ITEMS],
                className="nav-links",
            ),
            html.Div(id="nav-mode-badge", className="nav-mode-badge"),
        ],
        className="top-nav",
    )


def build_filter_bar(
    focus_ticker: str,
    compare_tickers: list[str] | None,
    horizon: str,
    start_date: str | None,
    end_date: str | None,
    alert_threshold: int,
) -> html.Div:
    ticker_options = get_ticker_options()
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Ticker", className="control-label"),
                    dcc.Dropdown(
                        id="global-focus-ticker",
                        options=ticker_options,
                        value=focus_ticker,
                        clearable=False,
                        searchable=True,
                        className="finsent-dropdown",
                    ),
                ],
                className="control-card",
            ),
            html.Div(
                [
                    html.Div("Compare", className="control-label"),
                    dcc.Dropdown(
                        id="global-compare-tickers",
                        options=ticker_options,
                        value=compare_tickers or [],
                        multi=True,
                        searchable=True,
                        className="finsent-dropdown",
                    ),
                ],
                className="control-card",
            ),
            html.Div(
                [
                    html.Div("Horizon", className="control-label"),
                    dcc.RadioItems(
                        id="global-horizon-toggle",
                        options=[
                            {"label": "Short", "value": "short"},
                            {"label": "Medium", "value": "medium"},
                            {"label": "Long", "value": "long"},
                        ],
                        value=horizon,
                        className="toggle-group",
                        inputClassName="toggle-input",
                        labelClassName="toggle-label",
                    ),
                ],
                className="control-card",
            ),
            html.Div(
                [
                    html.Div("Date Range", className="control-label"),
                    dcc.DatePickerRange(
                        id="global-date-range",
                        display_format="DD MMM YYYY",
                        start_date=start_date,
                        end_date=end_date,
                        className="date-range",
                    ),
                ],
                className="control-card",
            ),
            html.Div(
                [
                    html.Div("Alert Threshold", className="control-label"),
                    dcc.Slider(
                        id="global-alert-threshold",
                        min=20,
                        max=80,
                        step=5,
                        value=alert_threshold,
                        marks={20: "20", 40: "40", 60: "60", 80: "80"},
                        tooltip={"placement": "bottom"},
                    ),
                ],
                className="control-card control-card-slider",
            ),
        ],
        className="control-grid",
    )


def build_landing_search(default_ticker: str) -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Financial News Sentiment & Market Impact Analyzer", className="hero-kicker"),
                    html.H1("Search A Stock. Let FinSent Do The Rest.", className="hero-title landing-title"),
                    html.P(
                        "Start with a ticker, then explore sentiment, news impact, comparison, and alerts in dedicated tabs.",
                        className="hero-copy landing-copy",
                    ),
                ],
                className="landing-copy-wrap",
            ),
            html.Div(
                [
                    html.Div("Search Company / Ticker", className="control-label"),
                    dcc.Dropdown(
                        id="landing-ticker-search",
                        options=get_ticker_options(),
                        value=default_ticker,
                        clearable=False,
                        searchable=True,
                        className="finsent-dropdown landing-search-dropdown",
                    ),
                    dbc.Button("Load Analysis", id="landing-search-button", className="landing-search-button"),
                ],
                className="landing-search-shell",
            ),
            html.Div(
                [
                    html.Div("The detailed experience lives in the other tabs once you search.", className="landing-footnote"),
                    html.Div("Stock Detail, News Impact, Compare, and Alerts will automatically use your selected ticker.", className="landing-footnote secondary"),
                ],
                className="landing-footnotes",
            ),
        ],
        className="landing-page",
    )


def build_footer() -> html.Div:
    return html.Div(
        "FinBERT | Financial PhraseBank | Sentiment-Price Analytics | Plotly Dash",
        className="footer-strip",
    )


def build_button_link(label: str, href: str, class_name: str = "page-link-button") -> dbc.Button:
    return dbc.Button(label, href=href, class_name=class_name, color="link")
