"""Resultados da busca global, por categoria."""
from __future__ import annotations

import streamlit as st

from modules.search import CATEGORIES, search

TARGET = {"match": "views/match.py", "player": "views/players.py", "coach": "views/coaches.py",
          "person": "views/players.py", "competition": "views/competitions.py", "title": "views/titles.py",
          "stadium": "views/stadiums.py", "team": "views/advanced_search.py", "article": "views/history.py",
          "referee": "views/referees_kits.py"}
ICON = {"match": "⚽", "player": "👟", "coach": "📋", "person": "👤", "competition": "🗂️", "title": "🏆",
        "stadium": "🏟️", "team": "🛡️", "article": "📜", "referee": "🧑‍⚖️"}

st.title("🔎 Busca")
q = st.text_input("Pesquisar na enciclopédia", value=st.query_params.get("q", ""),
                  placeholder="Ex.: Fred, Washington, Maracanã, Campeonato Brasileiro 2012, Flamengo")
if not q:
    st.caption("Digite um nome, clube, estádio, competição ou ano.")
    st.stop()
st.query_params["q"] = q

results = search(q)
if not results:
    st.warning(f"Nada encontrado para “{q}”. A base ainda não cobre toda a história do clube; "
               "veja **Fontes e cobertura**.")
    st.stop()
st.caption(f"Resultados para “{q}” — {sum(len(v) for v in results.values())} itens")
for cat, rows in results.items():
    st.markdown(f"#### {CATEGORIES[cat]} ({len(rows)})")
    for r in rows:
        param = {"adv": str(r["entity_id"])} if cat == "team" else {"id": str(r["entity_id"])}
        st.page_link(TARGET[cat], label=f"{r['title']}  ·  {r['subtitle'] or ''}", query_params=param, icon=ICON[cat])
