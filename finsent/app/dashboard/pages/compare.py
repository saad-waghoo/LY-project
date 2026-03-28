from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html


def layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Compare Stocks", className="hero-kicker"),
                    html.H1("Side-by-Side Signal Comparison", className="page-title"),
                    html.P(
                        "Compare stocks across sentiment, return, news volume, and confidence.",
                        className="page-subtitle",
                    ),
                ],
                className="section-shell mb-3",
            ),
            dbc.Row(id="compare-metric-row", className="g-3 mb-3"),
            dbc.Row(
                [dbc.Col(html.Div(dcc.Graph(id="compare-main-chart"), className="chart-card"), md=12)],
                className="g-3 mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(html.Div(dcc.Graph(id="compare-sentiment-chart"), className="chart-card"), md=6),
                    dbc.Col(html.Div(dcc.Graph(id="compare-price-chart"), className="chart-card"), md=6),
                ],
                className="g-3 mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                dash_table.DataTable(
                                    id="compare-table",
                                    page_size=6,
                                    style_table={"overflowX": "auto"},
                                    style_cell={
                                        "textAlign": "left",
                                        "padding": "10px 12px",
                                        "fontFamily": "Trebuchet MS, sans-serif",
                                        "backgroundColor": "#0c1729",
                                        "color": "#e8eefb",
                                        "border": "1px solid #22314e",
                                    },
                                    style_header={
                                        "backgroundColor": "#13213a",
                                        "fontWeight": "700",
                                        "color": "#dce7ff",
                                        "border": "1px solid #22314e",
                                    },
                                ),
                            ],
                            className="section-shell",
                        ),
                        md=7,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("AI Comparison Summary", className="section-kicker"),
                                html.H3("Who Leads This Window", className="section-title"),
                                html.Div(id="compare-ai-summary", className="summary-stack"),
                            ],
                            className="section-shell explanation-shell",
                        ),
                        md=5,
                    ),
                ],
                className="g-3 mb-4",
            ),
        ]
    )
