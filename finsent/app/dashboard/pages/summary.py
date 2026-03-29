from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Summary", className="hero-kicker"),
                    html.H1(id="summary-page-title", className="page-title"),
                    html.P(
                        "A clean snapshot of the selected stock's sentiment, confidence, and short-term price reaction.",
                        className="page-subtitle",
                    ),
                    html.Div(id="summary-badge-row", className="badge-row"),
                ],
                className="section-shell page-header-shell mb-3",
            ),
            dbc.Row(id="summary-metric-row", className="g-3 mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Sentiment Timeline", className="section-kicker"),
                                html.H3("Recent Tone", className="section-title"),
                                dcc.Graph(id="summary-sentiment-chart"),
                            ],
                            className="chart-card",
                        ),
                        lg=8,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("AI Explanation", className="section-kicker"),
                                html.H3("Why The Signal Looks This Way", className="section-title"),
                                html.Div(id="summary-ai-explanation", className="explanation-box compact"),
                            ],
                            className="section-shell explanation-shell",
                        ),
                        lg=4,
                    ),
                ],
                className="g-3 mb-3",
            ),
        ],
        className="analysis-page",
    )
