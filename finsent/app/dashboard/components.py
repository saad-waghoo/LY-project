from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from finsent.app.dashboard.view_model import get_ticker_options


ANALYSIS_NAV_ITEMS = [
    ("Summary", "/summary"),
    ("News Impact", "/news-impact"),
    ("Compare", "/compare"),
    ("Alerts", "/alerts"),
]


def build_navbar() -> html.Div:
    return html.Div(
        [
            dcc.Link(
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
                href="/",
                className="brand-wrap",
            ),
            html.Div(id="nav-links", className="nav-links"),
            html.Div(
                [
                    dcc.Link("Back to Landing", href="/", id="nav-home-link", className="nav-home-link"),
                    html.Div(id="nav-mode-badge", className="nav-mode-badge"),
                ],
                className="nav-actions",
            ),
        ],
        className="top-nav",
    )


def build_nav_links(pathname: str | None, analysis_ready: bool) -> list[dcc.Link]:
    if not analysis_ready or (pathname or "/") == "/":
        return []

    active_path = pathname or "/summary"
    links: list[dcc.Link] = []
    for label, path in ANALYSIS_NAV_ITEMS:
        class_name = "nav-link-item is-active" if active_path == path else "nav-link-item"
        links.append(dcc.Link(label, href=path, className=class_name))
    return links


def build_workspace_bar(
    focus_ticker: str,
    compare_tickers: list[str] | None,
    horizon: str,
    date_window: str,
    alert_threshold: int,
) -> html.Div:
    ticker_options = get_ticker_options()
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Selected Ticker", className="control-label"),
                            dcc.Dropdown(
                                id="global-focus-ticker",
                                options=ticker_options,
                                value=focus_ticker,
                                clearable=False,
                                searchable=True,
                                className="finsent-dropdown workspace-dropdown",
                            ),
                        ],
                        className="workspace-primary-block",
                    ),
                    html.Div(
                        [
                            html.Div("Focused workspace", className="workspace-disclosure-label"),
                            html.Div("Keep the top clean and expand filters only when needed.", className="workspace-disclosure-copy"),
                        ],
                        className="workspace-disclosure-copy-wrap",
                    ),
                ],
                className="workspace-primary-row",
            ),
            dbc.Accordion(
                [
                    dbc.AccordionItem(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("Time Horizon", className="control-label"),
                                            dcc.Dropdown(
                                                id="global-horizon-toggle",
                                                options=[
                                                    {"label": "Short", "value": "short"},
                                                    {"label": "Medium", "value": "medium"},
                                                    {"label": "Long", "value": "long"},
                                                ],
                                                value=horizon,
                                                clearable=False,
                                                searchable=False,
                                                className="finsent-dropdown workspace-dropdown",
                                            ),
                                        ],
                                        id="horizon-toolbar-control",
                                        className="control-card workspace-filter-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Date Window", className="control-label"),
                                            dcc.Dropdown(
                                                id="global-date-window",
                                                options=[
                                                    {"label": "Last 7 Days", "value": "7d"},
                                                    {"label": "Last 30 Days", "value": "30d"},
                                                    {"label": "Last 90 Days", "value": "90d"},
                                                    {"label": "All Stored Data", "value": "all"},
                                                ],
                                                value=date_window,
                                                clearable=False,
                                                searchable=False,
                                                className="finsent-dropdown workspace-dropdown date-window-dropdown",
                                            ),
                                        ],
                                        id="date-toolbar-control",
                                        className="control-card workspace-filter-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Peer Tickers", className="control-label"),
                                            dcc.Dropdown(
                                                id="global-compare-tickers",
                                                options=ticker_options,
                                                value=compare_tickers or [],
                                                multi=True,
                                                searchable=True,
                                                placeholder="Add up to 2 peers",
                                                className="finsent-dropdown workspace-dropdown",
                                            ),
                                            html.Div(
                                                "Choose up to 2 peers, then press Compare.",
                                                className="control-helper",
                                            ),
                                            html.Button(
                                                "Compare",
                                                id="global-compare-apply",
                                                n_clicks=0,
                                                className="workspace-action-button",
                                            ),
                                        ],
                                        id="compare-toolbar-control",
                                        className="control-card workspace-filter-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div("Alert Threshold", className="control-label"),
                                            dcc.Dropdown(
                                                id="global-alert-threshold",
                                                options=[
                                                    {"label": "20", "value": 20},
                                                    {"label": "30", "value": 30},
                                                    {"label": "40", "value": 40},
                                                    {"label": "50", "value": 50},
                                                    {"label": "60", "value": 60},
                                                    {"label": "70", "value": 70},
                                                    {"label": "80", "value": 80},
                                                ],
                                                value=alert_threshold,
                                                clearable=False,
                                                searchable=False,
                                                className="finsent-dropdown workspace-dropdown",
                                            ),
                                        ],
                                        id="alert-toolbar-control",
                                        className="control-card workspace-filter-card",
                                    ),
                                ],
                                className="workspace-filter-grid",
                            )
                        ],
                        title="More filters",
                        item_id="workspace-filters",
                    )
                ],
                start_collapsed=True,
                always_open=False,
                className="workspace-accordion",
            ),
        ],
        className="workspace-shell",
    )


def build_landing_search(default_ticker: str) -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Financial News Sentiment & Market Impact Analyzer", className="hero-kicker"),
                    html.H1("Search A Stock. Let FinSent Do The Rest.", className="hero-title landing-title"),
                    html.P(
                        "Pick one ticker to open a focused analysis workspace with summary, detail, news impact, compare, and alerts.",
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
            html.Div("The rest of the workspace unlocks only after you load a ticker.", className="landing-footnote"),
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


def build_empty_state(title: str, message: str) -> html.Div:
    return html.Div(
        [
            html.Div(title, className="empty-state-title"),
            html.Div(message, className="empty-state-copy"),
        ],
        className="empty-state-card",
    )
