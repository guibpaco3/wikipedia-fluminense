"""Enciclopédia de títulos."""
from __future__ import annotations

import streamlit as st

from components import data
from components.cards import matches_table, note
from components.theme import status_badge
from modules import competitions
from modules.filters import MatchFilter
from modules.statistics import summarize

tid = st.query_params.get("id")
if tid:
    t = competitions.title_detail(int(tid))
    if not t:
        st.error("Título não encontrado.")
        st.stop()
    st.page_link("views/titles.py", label="← Todos os títulos")
    st.title(f"🏆 {t['name']}")
    st.markdown(f"Competição: **{t['competition'] or '—'}** · Ano/temporada: **{t['season'] or '—'}** · "
                f"Status: {status_badge(t['verification_status'])}", unsafe_allow_html=True)
    if t["wikidata_id"]:
        st.caption(f"Fonte: Wikidata [{t['wikidata_id']}](https://www.wikidata.org/wiki/{t['wikidata_id']})")
    st.markdown("#### Contexto histórico")
    st.write(t["context"] or "_Ainda não redigido. Pode ser cadastrado no painel administrativo._")
    st.write(f"**Treinador:** {t['coach'] or 'não registrado'}")
    if t["final_match_id"]:
        st.page_link("views/match.py", label="Ver a final", query_params={"id": t["final_match_id"]}, icon="⚽")
    if t["edition_id"]:
        df = data.matches(MatchFilter(competitions=[t["competition_id"]], seasons=[t["season"]]))
        st.markdown("#### Campanha (partidas da base)")
        if df.empty:
            st.caption("As partidas desta campanha ainda não estão na base.")
        else:
            r = summarize(df)
            st.write(f"{r.matches} jogos · {r.wins}V {r.draws}E {r.losses}D · gols {r.goals_for}:{r.goals_against}")
            st.write("**Adversários:** " + ", ".join(sorted(df["opponent"].unique())))
            matches_table(df, key="title_matches")
    note("Elenco campeão: disponível quando as escalações da campanha forem cadastradas.")
    st.stop()

st.title("🏆 Títulos")
note("Lista montada a partir do Wikidata (edições em que o Fluminense consta como vencedor), "
     "<b>ainda incompleta e não verificada</b> — por exemplo, nem todos os Campeonatos Cariocas conquistados "
     "estão registrados lá. Cada título pode ser verificado, corrigido ou acrescentado no painel.")
youth = st.toggle("Incluir categorias de base", value=False)
df = competitions.titles(include_youth=youth)
st.metric("Títulos registrados na base", len(df))
if not df.empty:
    st.bar_chart(df.groupby("Competição").size().sort_values(ascending=False).rename("Títulos"), color="#7A0019",
                 horizontal=True)
    show = df[["Ano", "Título", "Competição", "Categoria", "Status"]]
    ev = st.dataframe(show, hide_index=True, on_select="rerun", selection_mode="single-row", width="stretch",
                      height=520, key="titles_tbl")
    if ev.selection.rows:
        st.switch_page("views/titles.py", query_params={"id": int(df.iloc[ev.selection.rows[0]]["id"])})
