"""Jogadores: lista pesquisável, página individual (?id=) e comparação."""
from __future__ import annotations

import streamlit as st

from components import data
from components.cards import entity_table, fmt_date, matches_table, note, stat_cards
from modules import players
from modules.filters import MatchFilter

pid = st.query_params.get("id")
if pid:
    p = players.get(int(pid))
    if not p:
        st.error("Pessoa não encontrada.")
        st.stop()
    st.page_link("views/players.py", label="← Todos os jogadores")
    c1, c2 = st.columns([1, 3])
    with c1:
        if p["photo_url"]:
            st.image(p["photo_url"], width=200, caption="Imagem: Wikimedia Commons (via Wikidata)")
    with c2:
        st.title(p["name"])
        if p["full_name"]:
            st.caption(p["full_name"])
        st.write(f"**Nacionalidade:** {p['nationality'] or 'não informada'}  \n"
                 f"**Posição:** {p['position'] or 'não informada'}  \n"
                 f"**Nascimento:** {fmt_date(p['birth_date']) if p['birth_date'] and len(p['birth_date']) == 10 else (p['birth_date'] or 'não informado')}")
        if p["wikidata_id"]:
            st.caption(f"Wikidata: [{p['wikidata_id']}](https://www.wikidata.org/wiki/{p['wikidata_id']})")
        if p["bio"]:
            st.markdown(p["bio"])
    s = players.stats(int(pid))
    stat_cards([("Gols na base", s["goals"], "partidas com autoria registrada", "g"),
                ("Pênaltis", s["penalties"], "", "g"), ("Jogos com gol", s["matches_scored"], "", "g"),
                ("Amarelos", s["yellow"], "", "n0"), ("Vermelhos", s["red"], "", "r"),
                ("Jogos escalados", s["lineups"] or "—", "escalações cadastradas", "g")])
    note("Números calculados apenas sobre as partidas da base com eventos detalhados "
         "(hoje: Brasileirão Série A 2003–2024). <b>Não são totais de carreira no clube.</b> "
         "Assistências ainda não estão disponíveis em nenhuma fonte coletada.")
    sp = players.spells(int(pid))
    st.markdown("#### Passagens pelo clube")
    if sp.empty:
        st.caption("Período não registrado.")
    else:
        st.dataframe(sp, hide_index=True, width="stretch")
    gs = players.goals_by_season(int(pid))
    if not gs.empty:
        st.markdown("#### Gols por temporada (base)")
        st.dataframe(gs, hide_index=True, width="stretch")
    st.markdown("#### Partidas em que aparece (gol, cartão ou escalação)")
    matches_table(data.matches(MatchFilter(player=int(pid))).sort_values("date", ascending=False), key="pl_matches")
    st.stop()

st.title("👟 Jogadores")
st.write("Jogadores com passagem registrada (Wikidata) ou com gols/cartões/escalações nas partidas da base.")
tab_list, tab_top, tab_cmp = st.tabs(["Pesquisar", "Artilheiros na base", "Comparar"])
with tab_list:
    q = st.text_input("Nome", key="pl_q")
    entity_table(players.listing(q), key="pl_table", page="views/players.py", height=520)
with tab_top:
    note("Artilharia restrita às partidas da base com autoria de gols registrada.")
    entity_table(players.top_scorers(30), key="pl_top", page="views/players.py")
with tab_cmp:
    allp = players.listing("")
    opts = dict(zip(allp["id"], allp["Nome"]))
    sel = st.multiselect("Escolha jogadores para comparar", list(opts), format_func=opts.get, max_selections=6)
    if sel:
        st.dataframe(players.compare(sel), hide_index=True, width="stretch")
