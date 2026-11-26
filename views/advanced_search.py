"""PESQUISA AVANÇADA — filtros combináveis com estatísticas recalculadas."""
from __future__ import annotations

import streamlit as st

from components import data
from components.cards import coverage_note, matches_table, note, record_block
from components.charts import compare_bars, results_by_season
from modules.filters import KIT_UNIDENTIFIED, MatchFilter
from modules.statistics import by_group, summarize

st.title("🧭 Pesquisa avançada")
st.write("Combine os filtros livremente: todas as estatísticas são recalculadas a partir das partidas da base.")
coverage_note(data.coverage_text())

KEYS = ["adv_opp", "adv_opp_country", "adv_ref", "adv_ref_unconf", "adv_kit", "adv_comp", "adv_comp_cat",
        "adv_season", "adv_years", "adv_side", "adv_result", "adv_country", "adv_cont", "adv_intl",
        "adv_stadium", "adv_coach"]

# Pré-seleção vinda de outra página (?adv=<id do adversário>)
_adv = st.query_params.get("adv")
if _adv and st.session_state.get("_adv_applied") != _adv:
    try:
        st.session_state["adv_opp"] = [int(_adv)]
    except ValueError:
        pass
    st.session_state["_adv_applied"] = _adv

if st.button("🧹 Limpar todos os filtros"):
    for k in KEYS:
        st.session_state.pop(k, None)
    st.query_params.clear()
    st.rerun()

opp = data.options("SELECT t.id, t.name FROM teams t WHERE t.is_fluminense = 0 "
                   "AND EXISTS (SELECT 1 FROM matches m WHERE m.opponent_id = t.id) ORDER BY t.name")
refs = data.options("SELECT id, name FROM referees ORDER BY name")
kits = data.options("SELECT id, name || ' (' || category || ')' FROM kits ORDER BY category, name")
kits = {KIT_UNIDENTIFIED: "Uniforme não identificado", **kits}
comps = data.options("SELECT id, name FROM competitions WHERE id IN (SELECT competition_id FROM matches) ORDER BY name")
seasons = data.df("SELECT DISTINCT season FROM v_matches WHERE season IS NOT NULL ORDER BY season")["season"].tolist()
countries = data.options("SELECT DISTINCT c.iso2, c.name_pt FROM countries c JOIN matches m ON m.country_iso2 = c.iso2 "
                         "ORDER BY c.name_pt")
opp_countries = data.options("SELECT DISTINCT c.iso2, c.name_pt FROM countries c JOIN teams t ON t.country_iso2 = c.iso2 "
                             "WHERE t.is_fluminense = 0 ORDER BY c.name_pt")
continents = data.df("SELECT DISTINCT continent FROM v_matches WHERE continent IS NOT NULL")["continent"].tolist()
stadiums = data.options("SELECT id, name FROM stadiums WHERE id IN (SELECT stadium_id FROM matches) ORDER BY name")
coaches = data.options("SELECT DISTINCT p.id, p.name FROM people p JOIN matches m ON m.flu_coach_id = p.id ORDER BY p.name")
yr = data.df("SELECT MIN(year) a, MAX(year) b FROM v_matches").iloc[0]

t1, t2, t3, t4, t5 = st.tabs(["⚔️ Adversário", "🧑‍⚖️ Árbitro", "🎽 Uniforme", "🏆 Competição", "📍 Período, local e outros"])
with t1:
    sel_opp = st.multiselect("Clubes adversários", list(opp), format_func=opp.get, key="adv_opp",
                             placeholder="Ex.: Flamengo, Vasco da Gama, Botafogo…")
    sel_opp_c = st.multiselect("País do adversário", list(opp_countries), format_func=opp_countries.get,
                               key="adv_opp_country", help="Ex.: todos os confrontos contra clubes argentinos.")
with t2:
    if not refs:
        note("Nenhum árbitro cadastrado ainda. As fontes automáticas disponíveis não trazem arbitragem; "
             "o cadastro é feito no painel administrativo, com fonte.")
    sel_ref = st.multiselect("Árbitros", list(refs), format_func=refs.get, key="adv_ref")
    unconf = st.checkbox("Incluir partidas com árbitro não confirmado", key="adv_ref_unconf",
                         help="Por padrão só entram partidas cuja arbitragem está confirmada.")
with t3:
    if len(kits) == 1:
        note("Nenhum uniforme cadastrado ainda. O uniforme nunca é presumido pelo mando de campo: cada partida "
             "precisa de associação manual com evidência (foto, registro). Até lá, todas aparecem como "
             "<b>Uniforme não identificado</b>.")
    sel_kit = st.multiselect("Uniformes", list(kits), format_func=kits.get, key="adv_kit")
with t4:
    sel_comp = st.multiselect("Competições", list(comps), format_func=comps.get, key="adv_comp")
    sel_cat = st.multiselect("Tipo de competição", ["nacional", "estadual", "continental", "mundial", "amistoso", "outro"],
                             key="adv_comp_cat")
    sel_season = st.multiselect("Temporadas", seasons, key="adv_season")
with t5:
    c1, c2 = st.columns(2)
    years = c1.slider("Anos", int(yr["a"]), int(yr["b"]), (int(yr["a"]), int(yr["b"])), key="adv_years") \
        if yr["a"] else (None, None)
    sel_side = c2.multiselect("Mando", ["mandante", "visitante", "neutro"], key="adv_side")
    sel_res = c2.multiselect("Resultado", ["V", "E", "D"], key="adv_result",
                             format_func={"V": "Vitória", "E": "Empate", "D": "Derrota"}.get)
    c3, c4 = st.columns(2)
    sel_country = c3.multiselect("País da partida", list(countries), format_func=countries.get, key="adv_country")
    sel_cont = c3.multiselect("Continente", continents, key="adv_cont")
    intl = c3.radio("Âmbito geográfico", ["Todos", "Só internacionais", "Só no Brasil"], horizontal=True, key="adv_intl")
    sel_stad = c4.multiselect("Estádios", list(stadiums), format_func=stadiums.get, key="adv_stadium")
    sel_coach = c4.multiselect("Técnico do Fluminense", list(coaches), format_func=coaches.get, key="adv_coach")

full_range = yr["a"] and years == (int(yr["a"]), int(yr["b"]))
f = MatchFilter(
    opponents=sel_opp, opponent_countries=sel_opp_c, referees=sel_ref, include_unconfirmed_referees=unconf,
    kits=sel_kit, competitions=sel_comp, competition_categories=sel_cat, seasons=sel_season,
    year_from=None if full_range else years[0], year_to=None if full_range else years[1],
    sides=sel_side, results=sel_res, countries=sel_country, continents=sel_cont,
    international={"Todos": None, "Só internacionais": True, "Só no Brasil": False}[intl],
    stadiums=sel_stad, coaches=sel_coach,
)

found = data.matches(f)
active = [n for n, v in (("adversário", sel_opp or sel_opp_c), ("árbitro", sel_ref), ("uniforme", sel_kit),
                          ("competição", sel_comp or sel_cat or sel_season), ("período", not full_range),
                          ("mando/resultado", sel_side or sel_res), ("local", sel_country or sel_cont or sel_stad or intl != "Todos"),
                          ("técnico", sel_coach)) if v]
st.markdown("---")
st.markdown(f"### Resultado {'— filtros: ' + ', '.join(active) if active else '— toda a base'}")
rec = summarize(found)
record_block(rec)

if not found.empty:
    tab_hist, tab_cmp, tab_evo = st.tabs(["Histórico de partidas", "Comparar", "Evolução"])
    with tab_hist:
        matches_table(found.sort_values("date", ascending=False), key="adv_table", height=480)
        st.download_button("⬇️ Baixar resultado (CSV)", found.to_csv(index=False).encode("utf-8"),
                           "pesquisa_fluminense.csv", "text/csv")
    with tab_cmp:
        dim = st.selectbox("Comparar por", ["Adversário", "Árbitro", "Uniforme", "Competição", "Temporada",
                                            "Estádio", "Técnico", "Mando"], key="adv_dim")
        col = {"Adversário": "opponent", "Árbitro": "referee", "Uniforme": "kit", "Competição": "competition",
               "Temporada": "season", "Estádio": "stadium", "Técnico": "coach", "Mando": "flu_side"}[dim]
        d = found.copy()
        if col == "referee":
            d = d[d["referee_status"] == "confirmado"] if not unconf else d
        if col == "kit":
            d.loc[d["kit_status"] != "confirmado", "kit"] = "Uniforme não identificado"
        table = by_group(d, col, dim)
        st.dataframe(table, hide_index=True, width="stretch")
        top = table.head(15)
        if not top.empty:
            st.plotly_chart(compare_bars(top, dim), width="stretch", config={"displayModeBar": False})
    with tab_evo:
        if found["season"].notna().any():
            st.plotly_chart(results_by_season(found), width="stretch", config={"displayModeBar": False})
        else:
            st.plotly_chart(results_by_season(found, "year"), width="stretch", config={"displayModeBar": False})
