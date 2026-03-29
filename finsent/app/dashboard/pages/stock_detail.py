from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Stock Detail", className="hero-kicker"),
                    html.H1(id="stock-page-title", className="page-title"),
                    html.P(
                        "A deeper read on price action, sentiment behavior, confidence, and the core company context behind the signal.",
                        className="page-subtitle",
                    ),
                    html.Div(id="stock-badge-row", className="badge-row"),
                ],
                className="section-shell page-header-shell mb-3",
            ),
            dbc.Row(id="stock-metric-row", className="g-3 mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Primary Chart", className="section-kicker"),
                                html.Div(
                                    [
                                        html.H3("Focused Detail", className="section-title mb-0"),
                                        dcc.Dropdown(
                                            id="stock-chart-mode",
                                            options=[
                                                {"label": "Price Timeline", "value": "price"},
                                                {"label": "Price vs Sentiment", "value": "overlay"},
                                            ],
                                            value="price",
                                            clearable=False,
                                            searchable=False,
                                            className="finsent-dropdown chart-mode-dropdown",
                                        ),
                                    ],
                                    className="chart-card-header",
                                ),
                                dcc.Graph(id="stock-main-chart"),
                            ],
                            className="chart-card",
                        ),
                        lg=8,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div("Company Snapshot", className="section-kicker"),
                                        html.H3("Key Stats", className="section-title"),
                                        html.Div(id="stock-summary-panel", className="summary-stack"),
                                    ],
                                    className="section-shell mb-3",
                                ),
                                html.Div(
                                    [
                                        html.Div("Model Readout", className="section-kicker"),
                                        html.H3("Signal Interpretation", className="section-title"),
                                        html.Div(id="stock-ai-explanation", className="explanation-box compact"),
                                    ],
                                    className="section-shell explanation-shell",
                                ),
                            ],
                            className="stack-shell",
                        ),
                        lg=4,
                    ),
                ],
                className="g-3 mb-4",
            ),
        ],
        className="analysis-page",
    )
