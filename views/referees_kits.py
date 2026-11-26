"""Árbitros e uniformes."""
from __future__ import annotations

import streamlit as st

from components import data
from components.cards import matches_table, note, record_block
from modules import history
from modules.filters import MatchFilter
from modules.statistics import summarize

rid = st.query_params.get("id")
if rid:
    r = data.df("SELECT * FROM referees WHERE id = ?", (int(rid),))
    if r.empty:
        st.error("Árbitro não encontrado.")
        st.stop()
    st.title(f"🧑‍⚖️ {r.iloc[0]['name']}")
    df = data.matches(MatchFilter(referees=[int(rid)]))
    record_block(summarize(df), "Retrospecto do Fluminense (apenas arbitragens confirmadas)")
    matches_table(df, key="ref_matches")
    st.stop()

st.title("🎽 Árbitros e uniformes")
t1, t2 = st.tabs(["Árbitros", "Uniformes"])
with t1:
    refs = history.referees()
    if refs.empty:
        note("Nenhum árbitro cadastrado. Nenhuma das fontes de coleta automática disponíveis traz a arbitragem; "
             "o cadastro é manual, com fonte, e só partidas com árbitro <b>confirmado</b> entram nas estatísticas.")
    else:
        ev = st.dataframe(refs.drop(columns=["id"]), hide_index=True, on_select="rerun", selection_mode="single-row",
                          width="stretch", key="refs_tbl")
        if ev.selection.rows:
            st.switch_page("views/referees_kits.py", query_params={"id": int(refs.iloc[ev.selection.rows[0]]["id"])})
with t2:
    kits = history.kits()
    total = int(data.df("SELECT COUNT(*) FROM matches").iloc[0, 0])
    confirmed = int(data.df("SELECT COUNT(*) FROM matches WHERE kit_status = 'confirmado'").iloc[0, 0])
    st.metric("Partidas com uniforme confirmado", f"{confirmed} de {total}")
    note("O uniforme usado <b>nunca</b> é presumido por mando de campo. Ele é associado manualmente a cada "
         "partida, com evidência (fotografia, registro histórico). Sem confirmação: “Uniforme não identificado”.")
    if kits.empty:
        st.caption("Nenhum uniforme cadastrado ainda.")
    for k in kits.itertuples():
        c1, c2 = st.columns([1, 4])
        if k.image_url:
            c1.image(k.image_url, width=120)
        c2.markdown(f"**{k.Uniforme}** · {k.Categoria} · {k.Temporada or ''}  \n{k.Descrição or ''}  \n"
                    f"Jogos confirmados: {int(k._7 or 0)}")
