from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html


def layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div("News Impact", className="hero-kicker"),
                    html.H1("Headline-Level Explainability", className="page-title"),
                    html.P(
                        "Focus on how individual headlines were classified, how confident the model was, and what short-term impact each item may have had.",
                        className="page-subtitle",
                    ),
                ],
                className="section-shell page-header-shell mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Impact Map", className="section-kicker"),
                                html.H3("Sentiment vs Estimated Impact", className="section-title"),
                                dcc.Graph(id="news-impact-scatter"),
                            ],
                            className="chart-card",
                        ),
                        lg=8,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("Impact Summary", className="section-kicker"),
                                html.H3("Current Window", className="section-title"),
                                html.Div(id="news-impact-summary", className="summary-stack"),
                            ],
                            className="section-shell",
                        ),
                        lg=4,
                    ),
                ],
                className="g-3 mb-3",
            ),
            dbc.Accordion(
                [
                    dbc.AccordionItem(
                        [
                            dash_table.DataTable(
                                id="news-impact-table",
                                page_size=8,
                                sort_action="native",
                                filter_action="native",
                                style_table={"overflowX": "auto"},
                                style_cell={
                                    "textAlign": "left",
                                    "padding": "10px 12px",
                                    "fontFamily": "Trebuchet MS, sans-serif",
                                    "backgroundColor": "#0c1729",
                                    "color": "#e8eefb",
                                    "border": "1px solid #22314e",
                                    "whiteSpace": "normal",
                                    "height": "auto",
                                },
                                style_header={
                                    "backgroundColor": "#13213a",
                                    "fontWeight": "700",
                                    "color": "#dce7ff",
                                    "border": "1px solid #22314e",
                                },
                            ),
                        ],
                        title="Headline table",
                        item_id="headline-table",
                    )
                ],
                start_collapsed=False,
                always_open=False,
                className="page-accordion mb-4",
            ),
        ],
        className="analysis-page",
    )
