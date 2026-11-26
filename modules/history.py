"""História institucional: artigos, linha do tempo, presidentes, árbitros e uniformes."""
from __future__ import annotations

import pandas as pd

from database.connection import query_df, query_one


def articles(category: str | None = None) -> pd.DataFrame:
    if category:
        return query_df("SELECT * FROM articles WHERE category = ? ORDER BY title", (category,))
    return query_df("SELECT * FROM articles ORDER BY category, title")


def article(slug_or_id) -> dict | None:
    return query_one("SELECT * FROM articles WHERE slug = ? OR id = ?", (str(slug_or_id), slug_or_id))


def timeline() -> pd.DataFrame:
    return query_df("SELECT * FROM timeline_events ORDER BY date")


def presidents() -> pd.DataFrame:
    return query_df("""SELECT pr.id, p.id AS person_id, p.name AS Presidente, pr.start_date AS Início,
                              pr.end_date AS Fim, pr.highlights AS 'Principais acontecimentos'
                       FROM presidencies pr JOIN people p ON p.id = pr.person_id ORDER BY pr.start_date""")


def titles_in_period(start: str | None, end: str | None) -> pd.DataFrame:
    """Títulos (registrados) cuja temporada cai no período informado."""
    return query_df("""SELECT t.season AS Ano, t.name AS Título FROM titles t
                       WHERE t.verification_status <> 'rejeitado'
                         AND t.season >= COALESCE(?, '0000') AND t.season <= COALESCE(?, '9999')
                       ORDER BY t.season""", ((start or "")[:4] or None, (end or "")[:4] or None))


def referees() -> pd.DataFrame:
    return query_df("""SELECT r.id, r.name AS Árbitro, r.country_iso2 AS País, r.federation AS Federação,
                              SUM(m.referee_status = 'confirmado') AS 'Jogos confirmados',
                              COUNT(m.id) AS 'Jogos (inclui não confirmados)'
                       FROM referees r LEFT JOIN matches m ON m.referee_id = r.id
                       GROUP BY r.id ORDER BY "Jogos confirmados" DESC, r.name""")


def kits() -> pd.DataFrame:
    return query_df("""SELECT k.id, k.name AS Uniforme, k.category AS Categoria, k.season AS Temporada,
                              k.description AS Descrição, k.image_url,
                              SUM(m.kit_status = 'confirmado') AS 'Jogos confirmados'
                       FROM kits k LEFT JOIN matches m ON m.flu_kit_id = k.id
                       GROUP BY k.id ORDER BY k.category, k.season""")
