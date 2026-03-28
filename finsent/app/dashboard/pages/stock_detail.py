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
                        "Deep-dive view for one stock: sentiment, price movement, confidence, and explainable signals.",
                        className="page-subtitle",
                    ),
                    html.Div(id="stock-badge-row", className="badge-row"),
                ],
                className="section-shell mb-3",
            ),
            dbc.Row(id="stock-metric-row", className="g-3 mb-3"),
            dbc.Row(
                [dbc.Col(html.Div(dcc.Graph(id="stock-overlay-chart"), className="chart-card"), md=12)],
                className="g-3 mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(html.Div(dcc.Graph(id="stock-sentiment-timeline"), className="chart-card"), md=6),
                    dbc.Col(html.Div(dcc.Graph(id="stock-price-chart"), className="chart-card"), md=6),
                ],
                className="g-3 mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("AI Explanation Box", className="section-kicker"),
                                html.H3("Why The Model Is Leaning This Way", className="section-title"),
                                html.Div(id="stock-ai-explanation", className="explanation-box"),
                            ],
                            className="section-shell explanation-shell",
                        ),
                        md=7,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Ticker Summary", className="section-kicker"),
                                html.H3("Key Stats", className="section-title"),
                                html.Div(id="stock-summary-panel", className="summary-stack"),
                            ],
                            className="section-shell",
                        ),
                        md=5,
                    ),
                ],
                className="g-3 mb-4",
            ),
        ]
    )
