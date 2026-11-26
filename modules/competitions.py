"""Competições, edições e títulos."""
from __future__ import annotations

import pandas as pd

from database.connection import query_df, query_one


def listing() -> pd.DataFrame:
    return query_df("""
        SELECT c.id, c.name AS Competição, c.category AS Categoria, c.scope AS Âmbito,
               (SELECT COUNT(*) FROM matches m WHERE m.competition_id = c.id) AS 'Partidas na base',
               (SELECT COUNT(DISTINCT m.edition_id) FROM matches m WHERE m.competition_id = c.id) AS 'Edições com jogos',
               (SELECT COUNT(*) FROM titles t WHERE t.competition_id = c.id
                  AND t.verification_status <> 'rejeitado') AS 'Títulos registrados'
        FROM competitions c ORDER BY "Partidas na base" DESC, c.name""")


def get(cid: int) -> dict | None:
    return query_one("SELECT * FROM competitions WHERE id = ?", (cid,))


def editions(cid: int) -> pd.DataFrame:
    """Campanhas por edição, calculadas a partir das partidas da base."""
    return query_df("""
        SELECT e.season AS Temporada, e.fluminense_result AS 'Resultado final',
               COUNT(m.id) AS Jogos, SUM(m.result='V') AS V, SUM(m.result='E') AS E, SUM(m.result='D') AS D,
               SUM(m.flu_goals) AS GP, SUM(m.opp_goals) AS GC,
               ROUND(100.0 * (3*SUM(m.result='V') + SUM(m.result='E')) / NULLIF(3*COUNT(m.result), 0), 1)
                   AS 'Aproveitamento %',
               CASE WHEN EXISTS (SELECT 1 FROM titles t WHERE t.edition_id = e.id
                                 AND t.verification_status <> 'rejeitado') THEN '🏆' ELSE '' END AS Título
        FROM competition_editions e LEFT JOIN v_matches m ON m.edition_id = e.id
        WHERE e.competition_id = ? GROUP BY e.id ORDER BY e.season DESC""", (cid,))


def titles(include_youth: bool = False) -> pd.DataFrame:
    scope = "" if include_youth else "AND c.scope = 'profissional'"
    return query_df(f"""
        SELECT t.id, t.season AS Ano, t.name AS Título, c.name AS Competição, c.category AS Categoria,
               c.scope AS Âmbito, t.official AS Oficial, t.reliability AS Confiabilidade,
               t.verification_status AS Status, t.wikidata_id, t.edition_id, t.competition_id, t.final_match_id
        FROM titles t LEFT JOIN competitions c ON c.id = t.competition_id
        WHERE t.verification_status <> 'rejeitado' {scope}
        ORDER BY t.season""")


def title_detail(tid: int) -> dict | None:
    return query_one("""SELECT t.*, c.name AS competition, p.name AS coach FROM titles t
                        LEFT JOIN competitions c ON c.id = t.competition_id
                        LEFT JOIN people p ON p.id = t.coach_id WHERE t.id = ?""", (tid,))


def best_campaign(cid: int) -> dict | None:
    df = editions(cid)
    df = df[df["Jogos"] > 0]
    if df.empty:
        return None
    return df.sort_values(["Aproveitamento %", "Jogos"], ascending=False).iloc[0].to_dict()
