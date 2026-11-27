"""Dados da página inicial: retrospecto por técnico, por presidente e por competição.

Os períodos (técnicos, presidentes) e a lista de títulos vêm das cópias da Wikipédia
(modules/wiki_lists.py). Os retrospectos são calculados das partidas cadastradas no banco —
portanto refletem a cobertura da base, que é sinalizada na tela.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from database.connection import query_df
from modules import wiki_lists as w

# Competição do banco → (nome do título na lista da Wikipédia, anos considerados)
# O Brasileiro de 1970 foi disputado como Torneio Roberto Gomes Pedrosa (id 21).
_BR = "Campeonato Brasileiro"
COMP_TITLE = {
    1: (_BR, lambda y: y != 1970),
    21: (_BR, lambda y: y == 1970),
    2: ("Copa do Brasil", None),
    6: ("Campeonato Brasileiro - Série C", None),
    4: ("Campeonato Carioca", None),
    16: ("Copa Libertadores da América", None),
    17: ("Recopa Sul-Americana", None),
}
# títulos com peso para a aba Presidentes (os torneios menores ficam no verbete Títulos)
RELEVANT = ["Copa Libertadores da América", "Recopa Sul-Americana", "Copa Rio Internacional",
            _BR, "Copa do Brasil", "Campeonato Brasileiro - Série C", "Torneio Rio-São Paulo",
            "Campeonato Carioca"]
SHORT = {"Copa Libertadores da América": "Libertadores", "Recopa Sul-Americana": "Recopa",
         "Copa Rio Internacional": "Copa Rio", _BR: "Brasileiro", "Copa do Brasil": "Copa do Brasil",
         "Campeonato Brasileiro - Série C": "Série C", "Torneio Rio-São Paulo": "Rio-São Paulo",
         "Campeonato Carioca": "Carioca"}


def all_matches() -> pd.DataFrame:
    d = query_df("SELECT date, result, flu_goals, opp_goals, competition_id, season FROM v_matches "
                 "WHERE date IS NOT NULL ORDER BY date")
    d["d"] = pd.to_datetime(d["date"], errors="coerce")
    return d.dropna(subset=["d"])


@dataclass
class Rec:
    j: int = 0
    v: int = 0
    e: int = 0
    d: int = 0
    gp: int = 0
    gc: int = 0

    @property
    def pct(self) -> float | None:
        return round(100 * (3 * self.v + self.e) / (3 * self.j), 1) if self.j else None


def _rec(sub: pd.DataFrame) -> Rec:
    if sub.empty:
        return Rec()
    r = sub["result"]
    return Rec(len(sub), int((r == "V").sum()), int((r == "E").sum()), int((r == "D").sum()),
               int(sub["flu_goals"].fillna(0).sum()), int(sub["opp_goals"].fillna(0).sum()))


def _periods(items, m: pd.DataFrame, today: date | None = None) -> list[Rec]:
    """Retrospecto em [início, fim]; se o próximo período começa no dia em que este termina,
    o jogo desse dia fica com o próximo (evita contar duas vezes)."""
    today = today or date.today()
    out = []
    for i, it in enumerate(items):
        if not it.start:
            out.append(Rec())
            continue
        end = it.end or today
        nxt = items[i + 1].start if i + 1 < len(items) else None
        if nxt and nxt <= end:
            end = nxt - timedelta(days=1)
        mask = (m["d"] >= pd.Timestamp(it.start)) & (m["d"] <= pd.Timestamp(end))
        out.append(_rec(m[mask]))
    return out


def coaches_table(m: pd.DataFrame) -> pd.DataFrame:
    spells = w.coaches()
    recs = _periods(spells, m)
    rows = []
    for s, r in zip(spells, recs):
        wr = s.wiki_record or {}
        rows.append({
            "Nº": s.order, "Treinador": s.name + (" (interino)" if s.interim else ""),
            "Início": s.start, "Fim": s.end, "J": r.j or None, "V": r.v if r.j else None,
            "E": r.e if r.j else None, "D": r.d if r.j else None,
            "Gols": f"{r.gp}:{r.gc}" if r.j else None, "Aprov. %": r.pct,
            "Wiki J": wr.get("J"), "Wiki V": wr.get("V"), "Wiki E": wr.get("E"), "Wiki D": wr.get("D"),
            "Wiki %": wr.get("pct"), "Destaques": s.highlights or None, "_interim": s.interim})
    return pd.DataFrame(rows)


def title_dates(m: pd.DataFrame) -> list[dict]:
    """Títulos relevantes com a data de conquista (último jogo da campanha na base, se houver;
    senão 1º de julho do ano, marcado como aproximado)."""
    last = m.groupby(["competition_id", "season"])["d"].max()
    by_name: dict[str, list[int]] = {}
    for cid, (name, flt) in COMP_TITLE.items():
        by_name.setdefault(name, []).append(cid)
    out = []
    for t in w.main_titles():
        if t.name not in RELEVANT:
            continue
        for y in t.years:
            when, exact = None, False
            for cid in by_name.get(t.name, []):
                key = (cid, str(y))
                if key in last.index:
                    when, exact = last[key].date(), True
            out.append({"title": t.name, "short": SHORT.get(t.name, t.name), "year": y,
                        "date": when or date(y, 7, 1), "exact": exact})
    return sorted(out, key=lambda x: x["date"])


def presidents_table(m: pd.DataFrame) -> list[dict]:
    pres = w.presidents()
    recs = _periods(pres, m)
    tds = title_dates(m)
    rows = []
    for i, (p, r) in enumerate(zip(pres, recs)):
        end = p.end or date.today()
        nxt = pres[i + 1].start if i + 1 < len(pres) else None
        if nxt and nxt <= end:
            end = nxt - timedelta(days=1)
        won = [t for t in tds if p.start and p.start <= t["date"] <= end]
        rows.append({"p": p, "rec": r, "titles": won})
    return rows


def competitions_table(m: pd.DataFrame) -> pd.DataFrame:
    comps = query_df("SELECT id, name, category FROM competitions")
    titles = {t.name: t for t in w.main_titles()}
    rows = []
    for _, c in comps.iterrows():
        sub = m[m["competition_id"] == c["id"]]
        if sub.empty:
            continue
        r = _rec(sub)
        n_t = None
        if c["id"] in COMP_TITLE:
            name, flt = COMP_TITLE[c["id"]]
            t = titles.get(name)
            if t:
                yrs = [y for y in t.years if flt is None or flt(y)]
                n_t = len(yrs)
        else:
            n_t = 0
        seasons = sorted(sub["season"].dropna().unique().tolist())
        rows.append({"id": int(c["id"]), "Competição": c["name"], "Âmbito": c["category"],
                     "Temporadas": len(seasons), "Primeira": seasons[0] if seasons else None,
                     "Última": seasons[-1] if seasons else None, "J": r.j, "V": r.v, "E": r.e,
                     "D": r.d, "GP": r.gp, "GC": r.gc, "Aprov. %": r.pct, "Títulos": n_t})
    return pd.DataFrame(rows).sort_values("J", ascending=False)


# Painel de troféus (estilo "sala de troféus"): ordem de importância, contagem da Wikipédia.
TROPHY_PANEL = [
    ("Copa Libertadores da América", "Libertadores", "libertadores"),
    ("Recopa Sul-Americana", "Recopa Sul-Americana", "recopa"),
    ("Copa Rio Internacional", "Copa Rio Internacional", "copario"),
    (_BR, "Campeonato Brasileiro", "brasileiro"),
    ("Copa do Brasil", "Copa do Brasil", "copadobrasil"),
    ("Campeonato Brasileiro - Série C", "Brasileiro Série C", "seriec"),
    ("Torneio Rio-São Paulo", "Torneio Rio-São Paulo", "riosp"),
    ("Campeonato Carioca", "Campeonato Carioca", "carioca"),
]


def trophy_panel() -> tuple[list[dict], int | None]:
    titles = {t.name: t for t in w.main_titles()}
    items = []
    for name, label, icon in TROPHY_PANEL:
        t = titles.get(name)
        if t:
            items.append({"label": label, "count": t.count, "years": t.years, "icon": icon})
    total = next((t.count for t in w.main_titles() if t.name == "Conquistas oficiais"), None)
    return items, total
