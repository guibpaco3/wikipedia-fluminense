"""Página inicial: apresentação, indicadores, globo 3D e calendário histórico."""
from __future__ import annotations

from datetime import date

import streamlit as st

from components import data
from components.calendar_component import MONTHS, matches_per_month_chart, month_grid, year_heatmap
from components.cards import coverage_note, fmt_date, fmt_int, matches_table, note, stat_cards
from components.globe_component import render_globe
from modules.filters import MatchFilter
from modules.globe import country_detail
from modules.statistics import summarize

st.markdown("""
<div class="wf-hero">
  <h1>Wikipédia do Fluminense FC</h1>
  <p>Uma enciclopédia digital da história, das conquistas e da trajetória do Fluminense Football Club.</p>
  <div class="stripe">FFC</div>
</div>""", unsafe_allow_html=True)

st.markdown(
    "Esta plataforma reúne partidas, títulos, jogadores, treinadores, estádios e a história institucional "
    "do Fluminense em uma base de dados pesquisável. **Cada número é calculado a partir das partidas "
    "cadastradas** e cada informação registra sua fonte, data de coleta e grau de confiabilidade. "
    "O que ainda não foi verificado aparece sinalizado.")
coverage_note(data.coverage_text())

# ------------------------------------------------------------------ indicadores
all_matches = data.matches(MatchFilter())
rec = summarize(all_matches)
wt = data.world_totals()
n_comps = int(data.df("SELECT COUNT(*) AS n FROM competitions").iloc[0, 0])
n_comps_with_matches = int(data.df("SELECT COUNT(DISTINCT competition_id) AS n FROM matches").iloc[0, 0])
stat_cards([
    ("Partidas cadastradas", fmt_int(rec.matches), "", "g"),
    ("Vitórias", fmt_int(rec.wins), "", "g"),
    ("Empates", fmt_int(rec.draws), "", "n0"),
    ("Derrotas", fmt_int(rec.losses), "", "r"),
    ("Gols marcados", fmt_int(rec.goals_for), "", "g"),
    ("Gols sofridos", fmt_int(rec.goals_against), "", "r"),
    ("Países com jogos", fmt_int(wt["countries"]), f"{wt['unknown']} jogos sem país" if wt["unknown"] else "", "g"),
    ("Continentes", fmt_int(wt["continents"]), "", "g"),
    ("Competições cadastradas", fmt_int(n_comps), f"{n_comps_with_matches} com partidas na base", "r"),
])

# ------------------------------------------------------------------ globo
st.markdown("## 🌍 O Fluminense pelo mundo")
points = data.globe_points()
g1, g2, g3 = st.columns(3)
g1.metric("Partidas internacionais na base", fmt_int(wt["international"]))
g2.metric("Países visitados", fmt_int(wt["countries"]))
g3.metric("Continentes visitados", fmt_int(wt["continents"]))
if wt["international"] == 0:
    note("Por enquanto a base contém apenas jogos disputados no Brasil (Brasileirão Série A). "
         "Partidas internacionais aparecerão no globo assim que forem cadastradas pelo painel ou por CSV.")

sel = st.session_state.get("globe_country")
focus = None
if sel:
    p = next((p for p in points if p["iso2"] == sel), None)
    if p:
        focus = {"lat": p["lat"], "lon": p["lon"]}
col_globe, col_panel = st.columns([3, 2], gap="large")
with col_globe:
    clicked = render_globe(points, sel, focus, height=560)
    if clicked and clicked != sel:
        st.session_state["globe_country"] = clicked
        st.rerun()
with col_panel:
    if not sel:
        st.markdown("#### Clique em um país")
        st.write("Os países em verde têm partidas cadastradas. O painel mostrará retrospecto, "
                 "cidades, estádios e o histórico cronológico.")
        if points:
            st.dataframe([{"País": p["name"], "Partidas": p["total"], "V": p["v"], "E": p["e"], "D": p["d"]}
                          for p in points], hide_index=True, width="stretch")
    else:
        det = country_detail(sel)
        c = det["country"]
        st.markdown(f"### {c.get('name_pt', sel)}")
        if st.button("✕ Limpar seleção", key="clear_globe"):
            st.session_state.pop("globe_country", None)
            st.rerun()
        r = det["record"]
        if not r.matches:
            st.info("Nenhuma partida do Fluminense registrada neste país na base atual. "
                    "Isso não significa que o clube nunca tenha jogado aqui.")
        else:
            st.caption(f"Continente: {c.get('continent') or '—'}")
            stat_cards([("Partidas", r.matches, "", "g"), ("V-E-D", f"{r.wins}-{r.draws}-{r.losses}", "", "g"),
                        ("Gols", f"{r.goals_for}:{r.goals_against}", "pró : contra", "r")])
            st.write(f"**Primeira partida:** {fmt_date(r.first['date'])} — {r.first['opponent']}")
            st.write(f"**Última partida:** {fmt_date(r.last['date'])} — {r.last['opponent']}")
            if det["inferred"]:
                st.caption(f"⚠️ Em {det['inferred']} jogo(s) o país foi inferido pela competição "
                           "(nacional), não por registro do local.")
            st.write(f"**Cidades:** {', '.join(det['cities']) or 'não informadas na base'}")
            with st.expander(f"Estádios ({len(det['stadiums'])})"):
                st.dataframe(det["stadiums"].rename("Jogos").reset_index().rename(columns={"stadium": "Estádio"}),
                             hide_index=True, width="stretch")
if sel:
    st.markdown(f"#### Histórico cronológico — {country_detail(sel)['country'].get('name_pt', sel)}")
    matches_table(data.matches(MatchFilter(countries=[sel])), key="globe_matches", height=360)

# ------------------------------------------------------------------ calendário
st.markdown("## 📅 Calendário histórico de partidas")
if all_matches.empty:
    st.info("Sem partidas na base.")
    st.stop()
years = sorted(all_matches["year"].unique().tolist())
mode = st.segmented_control("Pesquisar por", ["Ano", "Mês", "Dia"], default="Ano", key="cal_mode")
f = MatchFilter()
grid_year = grid_month = None
if mode == "Ano":
    y = st.selectbox("Ano", years[::-1], key="cal_year")
    f = MatchFilter(year_from=y, year_to=y)
elif mode == "Mês":
    c1, c2 = st.columns([1, 2])
    month = c1.selectbox("Mês", range(1, 13), format_func=lambda m: MONTHS[m - 1], key="cal_month",
                         index=date.today().month - 1)
    scope = c2.radio("Período", ["Um ano", "Intervalo de anos", "Toda a história disponível"], horizontal=True,
                     key="cal_scope")
    if scope == "Um ano":
        y = st.selectbox("Ano", years[::-1], key="cal_month_year")
        f = MatchFilter(months=[month], year_from=y, year_to=y)
        grid_year, grid_month = y, month
    elif scope == "Intervalo de anos":
        y0, y1 = st.slider("Anos", min(years), max(years), (min(years), max(years)), key="cal_range")
        f = MatchFilter(months=[month], year_from=y0, year_to=y1)
    else:
        f = MatchFilter(months=[month])
else:
    kind = st.radio("Tipo", ["Dia e mês (todos os anos)", "Data completa"], horizontal=True, key="cal_day_kind")
    if kind == "Data completa":
        d = st.date_input("Data", value=date.fromisoformat(all_matches["date"].max()),
                          min_value=date(1902, 7, 21), max_value=date.today(), format="DD/MM/YYYY",
                          key="cal_date")
        f = MatchFilter(date_from=d.isoformat(), date_to=d.isoformat())
        grid_year, grid_month = d.year, d.month
    else:
        c1, c2 = st.columns(2)
        dd = c1.number_input("Dia", 1, 31, value=date.today().day, key="cal_dd")
        mm = c2.selectbox("Mês", range(1, 13), format_func=lambda m: MONTHS[m - 1], key="cal_mm",
                          index=date.today().month - 1)
        f = MatchFilter(months=[mm], day=int(dd))

found = data.matches(f)
r = summarize(found)
st.markdown(f"**{r.matches} partida(s) encontrada(s)**" +
            (f" · {r.wins}V {r.draws}E {r.losses}D · gols {r.goals_for}:{r.goals_against}" if r.matches else ""))
tab_list, tab_visual = st.tabs(["Lista cronológica", "Calendário visual"])
with tab_list:
    matches_table(found, key="cal_table")
with tab_visual:
    if mode == "Ano":
        st.plotly_chart(year_heatmap(found, int(f.year_from)), width="stretch", config={"displayModeBar": False})
        months_with = sorted(found["month"].unique().tolist()) if not found.empty else []
        if months_with:
            m = st.selectbox("Ver mês", months_with, format_func=lambda m: MONTHS[m - 1], key="cal_vis_month")
            month_grid(int(f.year_from), int(m), found)
    elif grid_year:
        month_grid(grid_year, grid_month, data.matches(MatchFilter(year_from=grid_year, year_to=grid_year,
                                                                   months=[grid_month])))
    elif not found.empty:
        st.caption("Distribuição por ano das partidas encontradas")
        st.bar_chart(found.groupby("year").size().rename("Partidas"), color="#006B3F")
    if mode == "Ano" and not found.empty:
        st.caption("Partidas por mês no ano")
        st.plotly_chart(matches_per_month_chart(found), width="stretch", config={"displayModeBar": False})
