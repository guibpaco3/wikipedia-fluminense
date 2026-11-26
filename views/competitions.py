"""Competições e edições."""
from __future__ import annotations

import streamlit as st

from components import data
from components.cards import entity_table, matches_table, note, record_block
from components.charts import points_pct_by_season, results_by_season
from modules import competitions
from modules.filters import MatchFilter
from modules.statistics import summarize

cid = st.query_params.get("id")
if cid:
    c = competitions.get(int(cid))
    if not c:
        st.error("Competição não encontrada.")
        st.stop()
    st.page_link("views/competitions.py", label="← Todas as competições")
    st.title(c["name"])
    st.caption(f"Categoria: {c['category']} · Âmbito: {c['scope']}")
    df = data.matches(MatchFilter(competitions=[int(cid)]))
    eds = competitions.editions(int(cid))
    n_titles = int((eds["Título"] == "🏆").sum()) if not eds.empty else 0
    st.markdown(f"**Participações com partidas na base:** {int((eds['Jogos'] > 0).sum()) if not eds.empty else 0} · "
                f"**Títulos registrados:** {n_titles}")
    record_block(summarize(df), "Retrospecto na base")
    best = competitions.best_campaign(int(cid))
    if best:
        st.write(f"**Melhor campanha (aproveitamento, na base):** {best['Temporada']} — "
                 f"{best['V']}V {best['E']}E {best['D']}D, {best['Aproveitamento %']}%")
    st.markdown("#### Edições")
    st.dataframe(eds, hide_index=True, width="stretch")
    if not df.empty:
        a, b = st.columns(2)
        a.plotly_chart(results_by_season(df), width="stretch", config={"displayModeBar": False})
        b.plotly_chart(points_pct_by_season(df), width="stretch", config={"displayModeBar": False})
        season = st.selectbox("Ver jogos da temporada", ["Todas"] + sorted(df["season"].dropna().unique().tolist(), reverse=True))
        matches_table(df if season == "Todas" else df[df["season"] == season], key="comp_matches")
    st.stop()

st.title("🗂️ Competições")
note("Competições com partidas na base e competições conhecidas apenas pelos títulos registrados.")
entity_table(competitions.listing(), key="comp_table", page="views/competitions.py", height=560)
