"""Estádios."""
from __future__ import annotations

import streamlit as st

from components import data
from components.cards import entity_table, fmt_int, matches_table, note, record_block
from components.theme import status_badge
from modules import stadiums
from modules.filters import MatchFilter
from modules.statistics import summarize

sid = st.query_params.get("id")
if sid:
    s = stadiums.get(int(sid))
    if not s:
        st.error("Estádio não encontrado.")
        st.stop()
    st.page_link("views/stadiums.py", label="← Todos os estádios")
    st.title(f"🏟️ {s['name']}")
    if s["official_name"] and s["official_name"] != s["name"]:
        st.caption(s["official_name"])
    st.markdown(f"**Cidade:** {s['city'] or 'não informada'} · **País:** {s['country'] or 'não informado'} · "
                f"**Capacidade:** {fmt_int(s['capacity']) if s['capacity'] else 'não informada'} · "
                f"Geolocalização: {status_badge(s['geo_status'])}", unsafe_allow_html=True)
    if s["lat"] is not None:
        st.map(data.df("SELECT lat, lon FROM stadiums WHERE id = ?", (int(sid),)), zoom=12, height=260)
    df = data.matches(MatchFilter(stadiums=[int(sid)]))
    record_block(summarize(df), "Retrospecto do Fluminense no estádio (base)")
    matches_table(df.sort_values("date", ascending=False), key="st_matches")
    st.stop()

st.title("🏟️ Estádios")
note("Nomes como registrados nas fontes; grafias diferentes do mesmo estádio podem ser unidas no painel. "
     "Cidade, coordenadas e capacidade vêm da geolocalização via Wikidata (a executar no painel).")
entity_table(stadiums.listing(), key="st_table", page="views/stadiums.py", height=560)
pts = stadiums.map_points()
if not pts.empty:
    st.map(pts, latitude="lat", longitude="lon", size="jogos", color="#006B3F")
