"""Lista de todas as partidas da base, com busca por texto."""
from __future__ import annotations

import streamlit as st

from components import data
from components.cards import coverage_note, matches_table
from components.charts import points_pct_by_season, results_by_season
from modules.filters import MatchFilter

st.title("⚽ Partidas")
coverage_note(data.coverage_text())
df = data.matches(MatchFilter())
q = st.text_input("Filtrar por texto (adversário, estádio, competição, técnico)", key="ml_q")
if q:
    mask = df[["opponent", "stadium", "competition", "coach"]].fillna("").apply(
        lambda s: s.str.contains(q, case=False, regex=False)).any(axis=1)
    df = df[mask]
matches_table(df.sort_values("date", ascending=False), key="ml_table", height=520)
if not df.empty:
    c1, c2 = st.columns(2)
    c1.plotly_chart(results_by_season(df), width="stretch", config={"displayModeBar": False})
    c2.plotly_chart(points_pct_by_season(df), width="stretch", config={"displayModeBar": False})
