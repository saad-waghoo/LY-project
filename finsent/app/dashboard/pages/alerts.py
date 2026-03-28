from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Alerts & Market Intelligence", className="hero-kicker"),
                    html.H1("Monitoring Layer", className="page-title"),
                    html.P(
                        "Watch negative sentiment drops, unusual news flow, and watchlist movement in one operational view.",
                        className="page-subtitle",
                    ),
                ],
                className="section-shell mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Alert Feed", className="section-kicker"),
                                html.H3("Active Signals", className="section-title"),
                                dbc.ListGroup(id="alerts-feed", flush=True),
                            ],
                            className="section-shell",
                        ),
                        md=7,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Watchlist Summary", className="section-kicker"),
                                html.H3("At A Glance", className="section-title"),
                                html.Div(id="alerts-summary-panel", className="summary-stack"),
                            ],
                            className="section-shell",
                        ),
                        md=5,
                    ),
                ],
                className="g-3 mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(html.Div(dcc.Graph(id="alerts-sector-heatmap"), className="chart-card"), md=6),
                    dbc.Col(html.Div(dcc.Graph(id="alerts-shift-chart"), className="chart-card"), md=6),
                ],
                className="g-3 mb-4",
            ),
        ]
    )
