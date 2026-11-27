"""Wikipédia do Fluminense FC — ponto de entrada.

Executar:  streamlit run app.py

Para adicionar um módulo: crie a página em views/ e registre-a em PAGES abaixo.
"""
from __future__ import annotations

import streamlit as st

from components.brand import BRAND_BOTTOM, BRAND_TOP, lockup  # noqa: E402

st.set_page_config(page_title=f"{BRAND_TOP} {BRAND_BOTTOM} · Fluminense FC", page_icon="📗",
                   layout="wide", initial_sidebar_state="expanded")

from components import theme  # noqa: E402
from components.data import coverage_summary  # noqa: E402
from database.migrations import migrate  # noqa: E402


@st.cache_resource(show_spinner="Preparando o banco de dados…")
def _bootstrap() -> bool:
    migrate()
    return True


_bootstrap()
theme.inject()

P = st.Page
PAGES = {
    "Enciclopédia": [
        P("views/home.py", title="Página inicial", icon="🏠", url_path="inicio", default=True),
        P("views/search.py", title="Busca", icon="🔎", url_path="busca"),
        P("views/advanced_search.py", title="Pesquisa avançada", icon="🧭", url_path="pesquisa-avancada"),
        P("views/match_list.py", title="Partidas", icon="⚽", url_path="partidas"),
        P("views/match.py", title="Partida", icon="⚽", url_path="partida", visibility="hidden"),
    ],
    "Verbetes": [
        P("views/history.py", title="História e presidentes", icon="📜", url_path="historia"),
        P("views/titles.py", title="Títulos", icon="🏆", url_path="titulos"),
        P("views/competitions.py", title="Competições", icon="🗂️", url_path="competicoes"),
        P("views/players.py", title="Jogadores", icon="👟", url_path="jogadores"),
        P("views/coaches.py", title="Treinadores", icon="📋", url_path="treinadores"),
        P("views/stadiums.py", title="Estádios", icon="🏟️", url_path="estadios"),
        P("views/referees_kits.py", title="Árbitros e uniformes", icon="🎽", url_path="arbitros-uniformes"),
    ],
    "Sobre os dados": [
        P("views/sources.py", title="Fontes e cobertura", icon="📚", url_path="fontes"),
        P("views/administration.py", title="Administração", icon="🔒", url_path="admin"),
    ],
}
nav = st.navigation(PAGES, position="sidebar")

with st.sidebar:
    st.markdown(lockup("dark"), unsafe_allow_html=True)
    st.write("")
    q = st.text_input("Pesquisa global", placeholder="Fred, Maracanã, Libertadores 2008…",
                      key="global_q", label_visibility="collapsed")
    if q and st.session_state.get("_last_global_q") != q:
        st.session_state["_last_global_q"] = q
        st.switch_page("views/search.py", query_params={"q": q})
    s = coverage_summary()
    if s.get("n"):
        st.caption(f"Base: {s['n']:,} partidas · {s['first'][:4]}–{s['last'][:4]}".replace(",", "."))
    if s.get("last_update"):
        st.caption(f"Atualizada em {s['last_update'][:10]}")

nav.run()
