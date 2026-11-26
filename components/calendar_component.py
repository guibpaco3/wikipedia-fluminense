"""Calendário visual: grade mensal com os dias de jogo destacados e mapa anual de calor."""
from __future__ import annotations

import calendar
import html
from urllib.parse import urlencode

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.theme import GREEN, RESULT_COLORS

WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MONTHS = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro",
          "Outubro", "Novembro", "Dezembro"]


def month_grid(year: int, month: int, df: pd.DataFrame) -> None:
    """Grade do mês; cada jogo vira um link para a página da partida."""
    by_day: dict[int, list[dict]] = {}
    for m in df.to_dict("records"):
        if m["year"] == year and m["month"] == month:
            by_day.setdefault(int(m["day"]), []).append(m)
    cells = [f'<div class="h">{d}</div>' for d in WEEKDAYS]
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
        for d in week:
            if d == 0:
                cells.append('<div class="d e"></div>')
                continue
            games = by_day.get(d, [])
            links = "".join(
                f'<a target="_self" href="partida?{urlencode({"id": int(g["id"])})}" '
                f'style="background:{RESULT_COLORS.get(g["result"], "#8A8F8C")}" '
                f'title="{html.escape(_title(g))}">'
                f'{int(g["flu_goals"]) if pd.notna(g["flu_goals"]) else "?"}x'
                f'{int(g["opp_goals"]) if pd.notna(g["opp_goals"]) else "?"} {html.escape(g["opponent"])}</a>'
                for g in games)
            cls = "d m" if games else "d"
            cells.append(f'<div class="{cls}"><span class="n">{d}</span>{links}</div>')
    st.markdown(f"**{MONTHS[month - 1]} de {year}**")
    st.markdown(f'<div class="wf-cal">{"".join(cells)}</div>', unsafe_allow_html=True)
    st.caption("Placar sempre do ponto de vista do Fluminense (gols do Flu x gols do adversário). "
               "🟩 vitória · ⬜ empate · 🟥 derrota")


def _title(g: dict) -> str:
    return f"{g['date']} · {g['opponent']} · {g['competition'] or ''}"


def year_heatmap(df: pd.DataFrame, year: int) -> go.Figure:
    """Mapa anual estilo 'contribuições': um quadrado por dia, colorido pelo resultado."""
    days = pd.date_range(f"{year}-01-01", f"{year}-12-31")
    res = {}
    for m in df[df["year"] == year].to_dict("records"):
        res[m["date"]] = m
    x, y, z, text = [], [], [], []
    for d in days:
        iso = d.date().isoformat()
        x.append(int(d.strftime("%W")))
        y.append(d.weekday())
        m = res.get(iso)
        z.append({"V": 3, "E": 2, "D": 1}.get(m["result"], 0.5) if m else 0)
        text.append(f"{d:%d/%m/%Y}<br>{m['opponent']} ({m['flu_goals']}x{m['opp_goals']})" if m else f"{d:%d/%m/%Y}")
    colors = [[0, "#EEF1EF"], [0.12, "#EEF1EF"], [0.13, "#B8BEBB"], [0.34, "#B8BEBB"],
              [0.35, RESULT_COLORS["D"]], [0.6, RESULT_COLORS["D"]], [0.61, RESULT_COLORS["E"]],
              [0.85, RESULT_COLORS["E"]], [0.86, RESULT_COLORS["V"]], [1, RESULT_COLORS["V"]]]
    fig = go.Figure(go.Heatmap(x=x, y=y, z=z, text=text, hoverinfo="text", colorscale=colors, zmin=0, zmax=3,
                               showscale=False, xgap=3, ygap=3))
    fig.update_yaxes(tickvals=list(range(7)), ticktext=WEEKDAYS, autorange="reversed", showgrid=False)
    month_starts = [int(pd.Timestamp(f"{year}-{m:02d}-01").strftime("%W")) for m in range(1, 13)]
    fig.update_xaxes(tickvals=month_starts, ticktext=[m[:3] for m in MONTHS], showgrid=False)
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="#fff",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#333"))
    return fig


def matches_per_month_chart(df: pd.DataFrame) -> go.Figure:
    counts = df.groupby("month").size().reindex(range(1, 13), fill_value=0)
    fig = go.Figure(go.Bar(x=[m[:3] for m in MONTHS], y=counts.values, marker_color=GREEN))
    fig.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="#fff",
                      paper_bgcolor="rgba(0,0,0,0)", yaxis_title="Partidas")
    return fig
