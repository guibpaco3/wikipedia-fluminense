"""Página inicial: marca, sala de troféus e as abas Fluzão no globo, Lendas do Clube, Técnicos,
Presidentes e Competições — seguidas do calendário histórico."""
from __future__ import annotations

import html
from datetime import date

import pandas as pd
import streamlit as st

from components import brand, data
from components.calendar_component import MONTHS, matches_per_month_chart, month_grid, year_heatmap
from components.cards import coverage_note, fmt_date, fmt_int, matches_table, note, stat_cards
from components.globe_component import render_globe
from modules import frontpage as fp
from modules import wiki_lists as wl
from modules.filters import MatchFilter
from modules.globe import country_detail
from modules.statistics import summarize

E = html.escape


# ----------------------------------------------------------------------------- dados (cache)
@st.cache_data(ttl=3600, show_spinner=False)
def _m():
    return fp.all_matches()


@st.cache_data(ttl=3600, show_spinner=False)
def _coaches():
    return fp.coaches_table(_m())


@st.cache_data(ttl=3600, show_spinner=False)
def _presidents():
    return fp.presidents_table(_m())


@st.cache_data(ttl=3600, show_spinner=False)
def _competitions():
    return fp.competitions_table(_m())


@st.cache_data(ttl=3600, show_spinner=False)
def _idols():
    return wl.idols()


def d(x) -> str:
    return x.strftime("%d/%m/%Y") if x else "atual"


def cite(name: str, label: str | None = None) -> str:
    s = wl.source(name)
    return (f'<a href="{s["url"]}" target="_blank">{E(label or s["title"])}</a> (revisão {s["revid"]})'
            if s["url"] else E(label or name))


def rec_html(j, v, e, dd) -> str:
    if not j:
        return ""
    pb = "".join(f'<span style="width:{100 * x / j:.1f}%"></span>' for x in (v, e, dd))
    return (f'<div class="rec"><div><b>{j}</b><small>J</small></div><div class="v"><b>{v}</b><small>V</small></div>'
            f'<div><b>{e}</b><small>E</small></div><div class="d"><b>{dd}</b><small>D</small></div></div>'
            f'<div class="wf-pbar">{pb}</div>')


def chip(t: dict) -> str:
    icon = next((ic for name, _, ic in fp.TROPHY_PANEL if name == t["title"]), "seriec")
    return f'<span class="wf-chip">{brand.trophy_svg(icon)}{E(t["short"])} {t["year"]}</span>'


# ----------------------------------------------------------------------------- topo: marca
st.markdown(f'<div class="wf-topbar">{brand.lockup("light", "lg")}'
            f'<div class="tag">{E(brand.TAGLINE)}<span>Desde 21 de julho de 1902</span></div></div>',
            unsafe_allow_html=True)

# ----------------------------------------------------------------------------- sala de troféus
items, total = fp.trophy_panel()
cats = {}
for t in wl.main_titles():
    if t.category not in ("Honrarias", "Total"):
        cats[t.category] = cats.get(t.category, 0) + t.count
cat_txt = ", ".join(f"{n} {c.lower()}" for c, n in cats.items())
tiles = "".join(
    f'<div class="wf-t" title="{E(", ".join(map(str, it["years"])))}">'
    f'<div class="top"><span class="ic">{brand.trophy_svg(it["icon"])}</span><span class="num">{it["count"]}</span></div>'
    f'<div class="lbl">{E(it["label"])}</div><div class="bar"><span style="width:38px"></span></div>'
    f'<div class="yrs">{E(", ".join(map(str, it["years"][-3:])))}{" …" if len(it["years"]) > 3 else ""}</div></div>'
    for it in items)
photo = brand.image_b64("hero_recopa_2024.jpg")
st.markdown(
    '<section class="wf-room">'
    f'<div class="photo" style="background-image:url(data:image/jpeg;base64,{photo})">'
    '<div class="cap"><b>Campeão da Recopa Sul-Americana 2024</b>Maracanã, 29/02/2024 · Fluminense 2 × 0 LDU</div></div>'
    '<div class="panel"><div class="kicker">Sala de troféus</div><h2>Nossas conquistas</h2>'
    f'<div class="wf-tgrid">{tiles}</div>'
    f'<div class="total"><span><b>{total or "—"}</b>conquistas oficiais ({E(cat_txt)})</span>'
    '<a href="titulos" target="_self">Ver todos os títulos →</a></div></div></section>'
    f'<div class="wf-src">Contagem de títulos: Wikipédia, {cite("titulos")}. Silhuetas estilizadas dos troféus '
    'em seus modelos atuais; passe o mouse sobre um troféu para ver todos os anos.</div>',
    unsafe_allow_html=True)

# ----------------------------------------------------------------------------- abas
TABS = ["Fluzão no globo", "Lendas do Clube", "Técnicos", "Presidentes", "Competições"]
tabs = st.tabs(TABS, key="home_tabs", on_change="rerun")


def section_head(title: str, sub: str) -> None:
    st.markdown(f'<div class="wf-sec-h"><div class="t">{E(title)}</div><span>{E(sub)}</span></div>', unsafe_allow_html=True)


def tab_globe() -> None:
    wt = data.world_totals()
    section_head("O Fluminense pelo mundo", "Todos os lugares do planeta onde o Flu jogou (partidas na base)")
    points = data.globe_points()
    g1, g2, g3 = st.columns(3)
    g1.metric("Partidas internacionais na base", fmt_int(wt["international"]))
    g2.metric("Países visitados", fmt_int(wt["countries"]))
    g3.metric("Continentes visitados", fmt_int(wt["continents"]))
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
    coverage_note(data.coverage_text())


def tab_legends() -> None:
    idols = _idols()
    section_head("Lendas do Clube", "Os 30 maiores ídolos da história, eleitos por 30 jornalistas (O Globo/Extra, 2020)")
    cards = []
    for i in idols:
        pos = (i.position or "").replace("ex-", "").replace("treinador, ", "").replace(" treinador", "")
        meta = " · ".join(x for x in [pos.capitalize() if pos else "", i.years or ""] if x)
        img = (f'<img src="{E(i.photo)}" alt="{E(i.name)}" loading="lazy">' if i.photo
               else f'<span class="ini">{E("".join(w[0] for w in i.name.split()[:2]))}</span>')
        mark = {"recordes": "¹", "artigo": "²"}

        def stat(v, src, label):
            val = fmt_int(v) if v is not None else "—"
            return f'<div><b>{val}<sup>{mark.get(src, "")}</sup></b><small>{label}</small></div>'
        cards.append(
            f'<div class="wf-leg"><div class="ph">{img}<span class="rk">{i.rank}º</span></div>'
            f'<div class="bd"><div class="nm">{E(i.name)}</div><div class="meta">{E(meta) or "&nbsp;"}</div></div>'
            f'<div class="st">{stat(i.games, i.games_src, "Jogos")}{stat(i.goals, i.goals_src, "Gols")}</div></div>')
    st.markdown(f'<div class="wf-legends">{"".join(cards)}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="wf-src">Lista: Wikipédia, {cite("clube", "Fluminense Football Club — Maiores ídolos")}. '
        f'¹ Ranking oficial do clube (20 que mais jogaram / 20 maiores artilheiros), via {cite("recordes")}. '
        '² Caixa de informações do artigo de cada jogador na Wikipédia (pode estar desatualizada ou somar só '
        'jogos oficiais). — = não informado nas fontes. Fotos: miniaturas dos artigos na Wikimedia Commons '
        '(licença indicada na página de cada arquivo).</div>', unsafe_allow_html=True)


def tab_coaches() -> None:
    df = _coaches()
    section_head("Técnicos", f"{len(df)} passagens, em ordem cronológica")
    df = df.copy()
    df["dec_start"] = df["Início"].map(lambda x: x.year // 10 * 10)
    df["dec_end"] = df["Fim"].map(lambda x: (date.today() if pd.isna(x) else x).year // 10 * 10)
    decades = list(range(int(df["dec_start"].min()), int(df["dec_end"].max()) + 1, 10))
    labels = {dd: f"{dd}–{dd + 9}" for dd in decades}
    choice = st.segmented_control("Década a década", decades, default=decades[-1], format_func=labels.get,
                                  key="coach_decade", required=True)
    sub = df[(df["dec_start"] <= choice) & (df["dec_end"] >= choice)]
    cards = []
    for _, r in sub.iterrows():
        fim = None if pd.isna(r["Fim"]) else r["Fim"]
        cur = fim is None
        dest = "" if pd.isna(r["Destaques"]) else str(r["Destaques"])
        kind = "cur" if cur else ("int" if r["_interim"] else "")
        j = 0 if pd.isna(r["J"]) else int(r["J"])
        body = (rec_html(j, int(r["V"]), int(r["E"]), int(r["D"])) +
                f'<div class="ft"><span>Aproveitamento <b>{r["Aprov. %"]:.1f}%</b></span><span>Gols <b>{r["Gols"]}</b></span></div>'
                if j else '<div class="none">Sem partidas deste período na base.</div>')
        wiki = (f'<div class="ft"><span>Wikipédia, todas as passagens: <b>{int(r["Wiki J"])}</b> J · '
                f'{int(r["Wiki V"])}V {int(r["Wiki E"])}E {int(r["Wiki D"])}D · {r["Wiki %"]:.1f}%</span></div>'
                if not pd.isna(r["Wiki J"]) else "")
        hl = f'<div class="hl">{E(dest)}</div>' if dest else ""
        tag = " · interino" if r["_interim"] else (" · no cargo" if cur else "")
        cards.append(f'<div class="wf-item {kind}"><div class="hd"><div><div class="nm">'
                     f'{E(r["Treinador"].replace(" (interino)", ""))}</div><div class="pd">{d(r["Início"])} – '
                     f'{d(fim)}{tag}</div></div><div class="no">{int(r["Nº"])}</div></div>{body}{wiki}{hl}</div>')
    st.markdown(f'<div class="wf-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    with st.expander("Tabela completa (todas as passagens)"):
        st.dataframe(df.drop(columns=["_interim", "dec_start", "dec_end"]), hide_index=True, width="stretch",
                     column_config={"Início": st.column_config.DateColumn(format="DD/MM/YYYY"),
                                    "Fim": st.column_config.DateColumn(format="DD/MM/YYYY")})
    st.markdown(
        f'<div class="wf-src">Períodos e destaques: Wikipédia, {cite("treinadores")}. J/V/E/D de cada card: '
        'calculados das partidas cadastradas na base dentro do período (a base ainda não tem todos os jogos, '
        'sobretudo amistosos e anos antigos). A linha "Wikipédia" soma todas as passagens do técnico, segundo '
        'a tabela de estatísticas da mesma lista.</div>', unsafe_allow_html=True)


def tab_presidents() -> None:
    rows = _presidents()
    section_head("Presidentes", f"{len(rows)} mandatos desde a fundação")
    cards = []
    for row in rows:
        p, r, won = row["p"], row["rec"], row["titles"]
        cur = p.end is None
        body = (rec_html(r.j, r.v, r.e, r.d) +
                f'<div class="ft"><span>Aproveitamento <b>{r.pct:.1f}%</b></span><span>Gols <b>{r.gp}:{r.gc}</b></span></div>'
                if r.j else '<div class="none">Sem partidas deste período na base.</div>')
        tit = (f'<div class="wf-ttl">{brand.trophy_svg("libertadores")}{len(won)} título(s) relevante(s)</div>'
               f'<div class="wf-chips">{"".join(chip(t) for t in won)}</div>' if won
               else '<div class="none">Nenhum título de primeira linha no mandato.</div>')
        cards.append(f'<div class="wf-item {"cur" if cur else ""}"><div class="hd"><div><div class="nm">{E(p.name)}</div>'
                     f'<div class="pd">{d(p.start)} – {d(p.end)}{" · no cargo" if cur else ""}</div></div>'
                     f'<div class="no">{p.order}</div></div>{body}{tit}</div>')
    st.markdown(f'<div class="wf-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="wf-src">Mandatos: Wikipédia, {cite("presidentes")}. Títulos considerados: Libertadores, Recopa, '
        'Copa Rio, Brasileiro, Copa do Brasil, Série C, Rio-São Paulo e Carioca (lista completa no verbete Títulos), '
        f'segundo {cite("titulos")}; cada título vai para o presidente no cargo na data do último jogo da campanha '
        'registrado na base (ou 1º de julho do ano, quando a base não tem o jogo). Retrospecto: partidas cadastradas '
        'na base dentro do mandato.</div>', unsafe_allow_html=True)


def tab_competitions() -> None:
    df = _competitions()
    section_head("Competições", f"{len(df)} competições com partidas na base")
    cards = []
    for _, r in df.iterrows():
        n_t = r["Títulos"]
        ttl = (f'<div class="wf-ttl">{brand.trophy_svg("seriec")}{int(n_t)} título(s)</div>' if n_t
               else '<div class="none">Sem título nesta competição.</div>')
        cards.append(
            f'<div class="wf-item"><div class="hd"><div><div class="nm">{E(r["Competição"])}</div>'
            f'<div class="pd">{E(str(r["Âmbito"]).capitalize())} · {int(r["Temporadas"])} temporada(s) · '
            f'{E(str(r["Primeira"]))}–{E(str(r["Última"]))}</div></div></div>'
            f'{rec_html(int(r["J"]), int(r["V"]), int(r["E"]), int(r["D"]))}'
            f'<div class="ft"><span>Aproveitamento <b>{r["Aprov. %"]:.1f}%</b></span>'
            f'<span>Gols <b>{int(r["GP"])}:{int(r["GC"])}</b></span></div>{ttl}</div>')
    st.markdown(f'<div class="wf-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    in_base = {"Copa Libertadores da América", "Recopa Sul-Americana", "Campeonato Brasileiro", "Copa do Brasil",
               "Campeonato Brasileiro - Série C", "Campeonato Carioca"}
    missing = [t.name for t in wl.main_titles() if t.category not in ("Honrarias", "Total") and t.name not in in_base]
    note("Títulos: contagem da Wikipédia. O Brasileiro de 1970 aparece no Torneio Roberto Gomes Pedrosa, "
         "como foi disputado. Competições vencidas pelo Flu que ainda não têm partidas na base: "
         + ", ".join(missing) + ".")
    with st.expander("Tabela"):
        st.dataframe(df.drop(columns=["id"]), hide_index=True, width="stretch")


for tab, fn in zip(tabs, [tab_globe, tab_legends, tab_coaches, tab_presidents, tab_competitions]):
    if tab.open:
        with tab:
            fn()

# ----------------------------------------------------------------------------- calendário
st.markdown("## 📅 Calendário histórico de partidas")
all_matches = data.matches(MatchFilter())
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
        dt = st.date_input("Data", value=date.fromisoformat(all_matches["date"].max()),
                           min_value=date(1902, 7, 21), max_value=date.today(), format="DD/MM/YYYY",
                           key="cal_date")
        f = MatchFilter(date_from=dt.isoformat(), date_to=dt.isoformat())
        grid_year, grid_month = dt.year, dt.month
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
