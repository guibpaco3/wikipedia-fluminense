"""Estádios onde o Fluminense jogou (a partir das partidas)."""
from __future__ import annotations

import pandas as pd

from database.connection import query_df, query_one


def listing() -> pd.DataFrame:
    return query_df("""
        SELECT s.id, s.name AS Estádio, ci.name AS Cidade, co.name_pt AS País, s.capacity AS Capacidade,
               COUNT(m.id) AS Jogos, SUM(m.result='V') AS V, SUM(m.result='E') AS E, SUM(m.result='D') AS D,
               ROUND(100.0 * (3*SUM(m.result='V') + SUM(m.result='E')) / NULLIF(3*COUNT(m.result), 0), 1)
                   AS 'Aproveitamento %',
               MIN(m.date) AS 'Primeiro jogo', MAX(m.date) AS 'Último jogo', s.geo_status AS 'Geolocalização'
        FROM stadiums s LEFT JOIN cities ci ON ci.id = s.city_id
        LEFT JOIN countries co ON co.iso2 = COALESCE(s.country_iso2, ci.country_iso2)
        LEFT JOIN v_matches m ON m.stadium_id = s.id
        GROUP BY s.id ORDER BY Jogos DESC""")


def get(sid: int) -> dict | None:
    return query_one("""SELECT s.*, ci.name AS city, co.name_pt AS country FROM stadiums s
                        LEFT JOIN cities ci ON ci.id = s.city_id
                        LEFT JOIN countries co ON co.iso2 = COALESCE(s.country_iso2, ci.country_iso2)
                        WHERE s.id = ?""", (sid,))


def aliases(sid: int) -> list[str]:
    return query_df("SELECT alias_norm FROM stadium_aliases WHERE stadium_id = ?", (sid,))["alias_norm"].tolist()


def map_points() -> pd.DataFrame:
    return query_df("""SELECT s.id, s.name, s.lat, s.lon, COUNT(m.id) AS jogos FROM stadiums s
                       JOIN matches m ON m.stadium_id = s.id WHERE s.lat IS NOT NULL GROUP BY s.id""")
