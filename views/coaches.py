"""Treinadores."""
from __future__ import annotations

import streamlit as st

from components import data
from components.cards import entity_table, matches_table, note, record_block
from components.charts import results_by_season
from modules import coaches
from modules.filters import MatchFilter
from modules.history import titles_in_period
from modules.statistics import by_group, summarize

cid = st.query_params.get("id")
if cid:
    p = coaches.get(int(cid))
    if not p:
        st.error("Treinador não encontrado.")
        st.stop()
    st.page_link("views/coaches.py", label="← Todos os treinadores")
    st.title(p["name"])
    sp = coaches.spells(int(cid))
    st.markdown("#### Períodos no comando (registro)")
    if sp.empty:
        st.caption("Período formal não registrado; abaixo, o intervalo dos jogos da base.")
    else:
        st.dataframe(sp, hide_index=True, width="stretch")
    df = data.matches(MatchFilter(coaches=[int(cid)]))
    record_block(summarize(df), "Retrospecto nas partidas da base")
    if not df.empty:
        st.markdown("#### Campanhas por competição")
        camp = by_group(df.assign(camp=df["competition"].fillna("") + " " + df["season"].fillna("")), "camp", "Campanha")
        st.dataframe(camp, hide_index=True, width="stretch")
        t = titles_in_period(df["date"].min(), df["date"].max())
        st.markdown("#### Títulos registrados no período dos seus jogos")
        st.caption("Coincidência de período; a atribuição do título ao técnico deve ser confirmada no verbete do título.")
        if t.empty:
            st.caption("Nenhum.")
        else:
            st.dataframe(t, hide_index=True, width="stretch")
        st.plotly_chart(results_by_season(df), width="stretch", config={"displayModeBar": False})
        matches_table(df.sort_values("date", ascending=False), key="co_matches")
    st.stop()

st.title("📋 Treinadores")
note("Retrospectos calculados pelas partidas da base. Os nomes do Brasileirão Dataset vêm abreviados "
     "(ex.: “L. Venker de Menezes”); a unificação com o cadastro completo é feita no painel administrativo.")
entity_table(coaches.listing(), key="co_table", page="views/coaches.py", height=560)
