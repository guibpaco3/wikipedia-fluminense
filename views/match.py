"""Página individual de uma partida (/partida?id=N)."""
from __future__ import annotations

import html
from datetime import date

import pandas as pd
import streamlit as st

from components.cards import fmt_date, fmt_int
from components.theme import badge, status_badge
from database.models import LABELS
from modules import matches

WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
EVENT_LABEL = {"gol": "⚽ Gol", "gol_penalti": "⚽ Gol (pênalti)", "gol_contra": "⚽ Gol contra",
               "amarelo": "🟨 Amarelo", "vermelho": "🟥 Vermelho"}

try:
    mid = int(st.query_params.get("id", 0))
except ValueError:
    mid = 0
m = matches.get(mid) if mid else None
if not m:
    st.error("Partida não encontrada. Use a busca, o calendário ou a pesquisa avançada.")
    st.page_link("views/match_list.py", label="Ver todas as partidas", icon="⚽")
    st.stop()

prev_id, next_id = matches.neighbors(m["id"], m["date"])
c1, _, c3 = st.columns([1, 4, 1])
if prev_id:
    c1.page_link("views/match.py", label="← Partida anterior", query_params={"id": prev_id})
if next_id:
    c3.page_link("views/match.py", label="Próxima partida →", query_params={"id": next_id})

d = date.fromisoformat(m["date"])
home, away = m["home_team"], m["away_team"]
# Lado do Fluminense pelo mandante listado (em campo neutro o mandante listado pode ser o adversário).
flu_home = m["away_team"] == m["opponent"]
hg, ag = (m["flu_goals"], m["opp_goals"]) if flu_home else (m["opp_goals"], m["flu_goals"])
hht, aht = (m["flu_goals_ht"], m["opp_goals_ht"]) if flu_home else (m["opp_goals_ht"], m["flu_goals_ht"])
hp, ap = (m["flu_penalties"], m["opp_penalties"]) if flu_home else (m["opp_penalties"], m["flu_penalties"])
score = f"{'?' if hg is None else hg} x {'?' if ag is None else ag}"
ht = f" · intervalo {hht} x {aht}" if hht is not None and aht is not None else ""
if hp is not None and ap is not None:
    ht += f" · pênaltis {hp} x {ap}"
comp = " · ".join(x for x in (m["competition"], m["season"], m["stage"],
                               m["round"] and f"Rodada {m['round']}") if x)
st.markdown(f"""
<div class="wf-scoreboard">
  <div class="t">{html.escape(home)}</div><div class="s">{score}</div><div class="t r">{html.escape(away)}</div>
  <div class="meta">{html.escape(comp or 'Competição não informada')}<br>
  {WEEKDAYS[d.weekday()]}, {d:%d/%m/%Y}{' · ' + m['kickoff'] if m['kickoff'] else ''}{ht}</div>
</div>""", unsafe_allow_html=True)

res = {"V": ("Vitória do Fluminense", "ok"), "E": ("Empate", ""), "D": ("Derrota do Fluminense", "bad")}.get(
    m["result"], ("Resultado não informado", "warn"))
st.markdown(badge(res[0], res[1]) + badge(f"Fluminense {m['flu_side']}") +
            " Confiabilidade: " + badge(LABELS.get(m["reliability"], m["reliability"])) +
            " Status: " + status_badge(m["verification_status"]), unsafe_allow_html=True)


def row(label: str, value, status: str | None = None) -> None:
    v = value if value not in (None, "") and not (isinstance(value, float) and pd.isna(value)) else \
        "<i style='color:#8a938f'>Não informado</i>"
    extra = " " + status_badge(status) if status else ""
    st.markdown(f"**{label}:** {v}{extra}", unsafe_allow_html=True)


st.markdown("### Ficha da partida")
a, b = st.columns(2)
with a:
    row("Data", f"{d:%d/%m/%Y}")
    row("Horário", m["kickoff"])
    row("Competição", m["competition"])
    row("Temporada / edição", m["season"])
    row("Fase", m["stage"])
    row("Rodada", m["round"])
    row("Mandante", home)
    row("Visitante", away)
    row("Placar do intervalo", f"{hht} x {aht}" if hht is not None and aht is not None else None)
with b:
    row("Estádio", m["stadium"])
    row("Cidade", m["city"])
    row("País", m["country"], m["country_status"] if m["country"] else None)
    row("Continente", m["continent"])
    row("Público", fmt_int(m["attendance"]) if m["attendance"] else None)
    row("Árbitro", m["referee"] if m["referee_status"] != "nao_identificado" else "Não identificado",
        m["referee_status"])
    row("Uniforme do Fluminense", m["kit"] if m["kit_status"] == "confirmado" else "Uniforme não identificado",
        m["kit_status"])
    row("Técnico do Fluminense", m["coach"])
    row("Técnico do adversário", m["opp_coach"])

off = matches.officials(m["id"])
if not off.empty:
    st.markdown("**Arbitragem auxiliar:** " + ", ".join(f"{r.name} ({r.role})" for r in off.itertuples()))

ev = matches.events(m["id"])
st.markdown("### Gols e cartões")
if ev.empty:
    st.caption("Nenhum evento (gols/cartões) detalhado na base para esta partida.")
else:
    ev = ev.assign(Equipe=ev["for_fluminense"].map({1: "Fluminense", 0: m["opponent"]}),
                   Evento=ev["event_type"].map(EVENT_LABEL),
                   Minuto=ev["minute"].map(lambda x: f"{int(x)}'" if pd.notna(x) else "—"))
    goals = ev[ev["event_type"].str.startswith("gol")]
    cards = ev[~ev["event_type"].str.startswith("gol")]
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Gols**")
        for r in goals.itertuples():
            st.write(f"{r.Minuto} {r.Evento} — **{r.player_name or 'autor não informado'}** ({r.Equipe})")
        if goals.empty:
            st.caption("Sem gols." if (m["flu_goals"] or 0) + (m["opp_goals"] or 0) == 0 else "Autores não informados.")
    with g2:
        st.markdown("**Cartões**")
        if cards.empty:
            st.caption("Sem cartões registrados.")
        else:
            st.dataframe(cards[["Minuto", "Evento", "player_name", "Equipe"]].rename(columns={"player_name": "Jogador"}),
                         hide_index=True, width="stretch")
    scorers = goals.dropna(subset=["person_id"])
    if not scorers.empty:
        st.caption("Páginas dos autores dos gols do Fluminense:")
        cols = st.columns(min(4, len(scorers)))
        for i, r in enumerate(scorers.drop_duplicates("person_id").itertuples()):
            cols[i % len(cols)].page_link("views/players.py", label=r.player_name,
                                          query_params={"id": int(r.person_id)}, icon="👟")

lu = matches.lineup(m["id"])
st.markdown("### Escalação do Fluminense")
if lu.empty:
    st.caption("Escalação não cadastrada.")
else:
    for r in lu.itertuples():
        st.page_link("views/players.py", label=f"{'' if r.starter else '(reserva) '}{r.name}",
                     query_params={"id": int(r.person_id)})

st.markdown("### Fontes e verificação")
refs = matches.source_refs(m["id"])
st.dataframe(refs, hide_index=True, width="stretch",
             column_config={"URL": st.column_config.LinkColumn("URL")})
disc = matches.discrepancies(m["id"])
if not disc.empty:
    st.warning("Há divergências entre fontes para esta partida:")
    st.dataframe(disc, hide_index=True, width="stretch")
with st.expander("Proveniência detalhada de cada campo"):
    st.dataframe(matches.provenance(m["id"]), hide_index=True, width="stretch",
                 column_config={"URL": st.column_config.LinkColumn("URL")})

st.markdown("### Navegue a partir desta partida")
n1, n2, n3 = st.columns(3)
n1.page_link("views/advanced_search.py", label=f"Todos os jogos contra {m['opponent']}",
             query_params={"adv": str(m["opponent_id"])}, icon="🧭")
if m["competition_id"]:
    n2.page_link("views/competitions.py", label=f"{m['competition']}",
                 query_params={"id": int(m["competition_id"])}, icon="🗂️")
if m["stadium_id"]:
    n3.page_link("views/stadiums.py", label=f"{m['stadium']}", query_params={"id": int(m["stadium_id"])},
                 icon="🏟️")
if m["flu_coach_id"]:
    st.page_link("views/coaches.py", label=f"Técnico: {m['coach']}", query_params={"id": int(m["flu_coach_id"])},
                 icon="📋")
