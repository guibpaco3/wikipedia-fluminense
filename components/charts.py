"""Gráficos interativos (Plotly) com a paleta do clube."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from components.theme import GARNET, GREEN, RESULT_COLORS, RESULT_LABELS

LAYOUT = dict(margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="#fff", paper_bgcolor="rgba(0,0,0,0)",
              font=dict(family="Inter", color="#2B302E"), legend=dict(orientation="h", y=-0.18))


def results_by_season(df: pd.DataFrame, col: str = "season") -> go.Figure:
    d = df.dropna(subset=["result"])
    tab = d.groupby([col, "result"]).size().unstack(fill_value=0).reindex(columns=["V", "E", "D"], fill_value=0)
    fig = go.Figure()
    for r in ("V", "E", "D"):
        fig.add_bar(x=tab.index.astype(str), y=tab[r], name=RESULT_LABELS[r], marker_color=RESULT_COLORS[r])
    fig.update_layout(barmode="stack", height=320, **LAYOUT)
    return fig


def points_pct_by_season(df: pd.DataFrame, col: str = "season") -> go.Figure:
    d = df.dropna(subset=["result"])
    g = d.groupby(col)["result"].agg(lambda s: 100 * (3 * (s == "V").sum() + (s == "E").sum()) / (3 * len(s)))
    fig = go.Figure(go.Scatter(x=g.index.astype(str), y=g.values.round(1), mode="lines+markers",
                               line=dict(color=GREEN, width=3), marker=dict(color=GARNET, size=8)))
    fig.update_layout(height=300, yaxis_title="Aproveitamento %", yaxis_range=[0, 100], **LAYOUT)
    return fig


def results_donut(wins: int, draws: int, losses: int) -> go.Figure:
    fig = go.Figure(go.Pie(labels=["Vitórias", "Empates", "Derrotas"], values=[wins, draws, losses], hole=.62,
                           marker_colors=[RESULT_COLORS["V"], RESULT_COLORS["E"], RESULT_COLORS["D"]],
                           sort=False, textinfo="percent"))
    fig.update_layout(height=280, showlegend=True, **LAYOUT)
    return fig


def compare_bars(table: pd.DataFrame, label_col: str) -> go.Figure:
    """Comparação lado a lado (árbitros, uniformes, adversários...)."""
    fig = go.Figure()
    for r, col in (("V", "V"), ("E", "E"), ("D", "D")):
        fig.add_bar(y=table[label_col].astype(str), x=table[col], name=RESULT_LABELS[r], orientation="h",
                    marker_color=RESULT_COLORS[r])
    fig.update_layout(barmode="stack", height=max(240, 40 * len(table) + 80), **LAYOUT)
    fig.update_yaxes(autorange="reversed")
    return fig
