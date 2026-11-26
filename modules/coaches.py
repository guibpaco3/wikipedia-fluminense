"""Treinadores: passagens (Wikidata/manual) e retrospecto calculado das partidas."""
from __future__ import annotations

import pandas as pd

from core.text import norm
from database.connection import query_df, query_one


def listing() -> pd.DataFrame:
    return query_df("""
        SELECT p.id, p.name AS Técnico,
               (SELECT MIN(start_date) FROM coach_spells s WHERE s.person_id = p.id) AS 'Início (registro)',
               (SELECT MAX(end_date) FROM coach_spells s WHERE s.person_id = p.id) AS 'Fim (registro)',
               COUNT(m.id) AS Jogos, SUM(m.result='V') AS V, SUM(m.result='E') AS E, SUM(m.result='D') AS D,
               ROUND(100.0 * (3*SUM(m.result='V') + SUM(m.result='E')) / NULLIF(3*COUNT(m.result), 0), 1)
                   AS 'Aproveitamento %',
               MIN(m.date) AS 'Primeiro jogo na base', MAX(m.date) AS 'Último jogo na base'
        FROM people p LEFT JOIN v_matches m ON m.flu_coach_id = p.id
        WHERE EXISTS (SELECT 1 FROM coach_spells s WHERE s.person_id = p.id)
           OR EXISTS (SELECT 1 FROM matches x WHERE x.flu_coach_id = p.id)
        GROUP BY p.id ORDER BY MAX(m.date) DESC""")


def get(person_id: int) -> dict | None:
    return query_one("SELECT * FROM people WHERE id = ?", (person_id,))


def spells(person_id: int) -> pd.DataFrame:
    return query_df("SELECT start_date AS Início, end_date AS Fim, interim AS Interino, notes AS Fonte "
                    "FROM coach_spells WHERE person_id = ? ORDER BY start_date", (person_id,))


def merge_suggestions() -> pd.DataFrame:
    """Sugere unir técnicos com nome abreviado (dataset) a cadastros completos (Wikidata),
    quando os jogos do primeiro caem no período do segundo e o sobrenome coincide.
    Apenas sugestão: a união exige confirmação no painel."""
    spells = query_df("SELECT s.person_id, p.name, s.start_date, s.end_date FROM coach_spells s "
                      "JOIN people p ON p.id = s.person_id")
    games = query_df("SELECT flu_coach_id AS pid, coach, MIN(date) AS first, MAX(date) AS last, COUNT(*) AS n "
                     "FROM v_matches WHERE flu_coach_id IS NOT NULL GROUP BY flu_coach_id")
    out = []
    for g in games.itertuples():
        g_tokens = set(norm(g.coach).split()) - {"de", "da", "do", "dos"}
        for s in spells.itertuples():
            if s.person_id == g.pid:
                continue
            start = (s.start_date or "0000")[:10]
            end = (s.end_date or "9999")[:10]
            in_period = start[:4] <= g.last[:4] and g.first[:4] <= end[:4]
            common = g_tokens & (set(norm(s.name).split()) - {"de", "da", "do", "dos"})
            if in_period and any(len(t) > 3 for t in common):
                out.append({"Manter (completo)": s.name, "keep_id": s.person_id,
                            "Unir (como no dataset)": g.coach, "drop_id": g.pid, "Jogos": g.n,
                            "Período dos jogos": f"{g.first} → {g.last}"})
    return pd.DataFrame(out).drop_duplicates(subset=["keep_id", "drop_id"]) if out else pd.DataFrame()
