"""Jogadores: cadastro, passagens e números calculados a partir das partidas da base."""
from __future__ import annotations

import pandas as pd

from database.connection import query_df, query_one

GOAL_TYPES = "('gol', 'gol_penalti')"


def listing(search: str = "") -> pd.DataFrame:
    """Pessoas que são jogadores (passagem registrada, gol, cartão ou escalação)."""
    like = f"%{search.strip()}%"
    return query_df(f"""
        SELECT p.id, p.name AS Nome, c.name_pt AS Nacionalidade, p.position AS Posição, p.birth_date AS Nascimento,
               (SELECT MIN(start_date) FROM player_spells s WHERE s.person_id = p.id) AS 'Início',
               (SELECT MAX(end_date) FROM player_spells s WHERE s.person_id = p.id) AS 'Fim',
               (SELECT COUNT(*) FROM match_events e WHERE e.person_id = p.id AND e.for_fluminense = 1
                  AND e.event_type IN {GOAL_TYPES}) AS 'Gols na base',
               (SELECT COUNT(*) FROM match_lineups l WHERE l.person_id = p.id) AS 'Jogos escalados'
        FROM people p LEFT JOIN countries c ON c.iso2 = p.nationality_iso2
        WHERE (EXISTS (SELECT 1 FROM player_spells s WHERE s.person_id = p.id)
               OR EXISTS (SELECT 1 FROM match_events e WHERE e.person_id = p.id AND e.for_fluminense = 1)
               OR EXISTS (SELECT 1 FROM match_lineups l WHERE l.person_id = p.id))
          AND (p.name LIKE ? OR p.full_name LIKE ? OR p.name_norm LIKE ?)
        ORDER BY "Gols na base" DESC, p.name""", (like, like, like.lower()))


def get(person_id: int) -> dict | None:
    return query_one("SELECT p.*, c.name_pt AS nationality FROM people p "
                     "LEFT JOIN countries c ON c.iso2 = p.nationality_iso2 WHERE p.id = ?", (person_id,))


def spells(person_id: int) -> pd.DataFrame:
    return query_df("SELECT start_date AS Início, end_date AS Fim, notes AS Fonte FROM player_spells "
                    "WHERE person_id = ? ORDER BY start_date", (person_id,))


def stats(person_id: int) -> dict:
    row = query_one(f"""
        SELECT SUM(event_type IN {GOAL_TYPES}) AS goals, SUM(event_type = 'gol_penalti') AS penalties,
               SUM(event_type = 'amarelo') AS yellow, SUM(event_type = 'vermelho') AS red,
               COUNT(DISTINCT CASE WHEN event_type IN {GOAL_TYPES} THEN match_id END) AS matches_scored
        FROM match_events WHERE person_id = ? AND for_fluminense = 1""", (person_id,)) or {}
    row["lineups"] = query_one("SELECT COUNT(*) AS n FROM match_lineups WHERE person_id = ?", (person_id,))["n"]
    return {k: int(v or 0) for k, v in row.items()}


def goals_by_season(person_id: int) -> pd.DataFrame:
    return query_df(f"""
        SELECT m.season AS Temporada, m.competition AS Competição, COUNT(*) AS Gols
        FROM match_events e JOIN v_matches m ON m.id = e.match_id
        WHERE e.person_id = ? AND e.for_fluminense = 1 AND e.event_type IN {GOAL_TYPES}
        GROUP BY m.season, m.competition ORDER BY m.season""", (person_id,))


def top_scorers(limit: int = 20) -> pd.DataFrame:
    return query_df(f"""
        SELECT p.id, p.name AS Jogador, COUNT(*) AS Gols, MIN(m.year) AS 'De', MAX(m.year) AS 'Até'
        FROM match_events e JOIN people p ON p.id = e.person_id JOIN v_matches m ON m.id = e.match_id
        WHERE e.for_fluminense = 1 AND e.event_type IN {GOAL_TYPES}
        GROUP BY p.id ORDER BY Gols DESC LIMIT ?""", (limit,))


def compare(ids: list[int]) -> pd.DataFrame:
    rows = []
    for pid in ids:
        p = get(pid)
        if not p:
            continue
        s = stats(pid)
        rows.append({"Jogador": p["name"], "Gols na base": s["goals"], "Pênaltis": s["penalties"],
                     "Jogos com gol": s["matches_scored"], "Amarelos": s["yellow"], "Vermelhos": s["red"],
                     "Jogos escalados": s["lineups"]})
    return pd.DataFrame(rows)
