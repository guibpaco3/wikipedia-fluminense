"""Dados do globo: agregação das partidas por país (somente países confirmados/inferidos)."""
from __future__ import annotations

import pandas as pd

from database.connection import query_df
from modules.filters import MatchFilter, fetch_matches
from modules.statistics import summarize


def country_points() -> list[dict]:
    df = query_df(
        "SELECT c.iso2, c.name_pt AS name, c.continent, c.lat, c.lon, COUNT(*) AS total, "
        "SUM(m.result='V') AS v, SUM(m.result='E') AS e, SUM(m.result='D') AS d "
        "FROM v_matches m JOIN countries c ON c.iso2 = m.country_iso2 "
        "WHERE m.country_iso2 IS NOT NULL GROUP BY c.iso2 ORDER BY total DESC")
    return [{k: (None if pd.isna(v) else (int(v) if k in ("total", "v", "e", "d") else v))
             for k, v in r.items()} for r in df.to_dict("records")]


def world_totals() -> dict:
    df = query_df("SELECT COUNT(*) AS n, COUNT(DISTINCT country_iso2) AS countries, "
                  "COUNT(DISTINCT continent) AS continents, "
                  "SUM(CASE WHEN country_iso2 <> 'BR' THEN 1 ELSE 0 END) AS international, "
                  "SUM(CASE WHEN country_iso2 IS NULL THEN 1 ELSE 0 END) AS unknown "
                  "FROM v_matches")
    return {k: int(v or 0) for k, v in df.iloc[0].to_dict().items()}


def country_detail(iso2: str) -> dict:
    df = fetch_matches(MatchFilter(countries=[iso2]))
    info = query_df("SELECT * FROM countries WHERE iso2 = ?", (iso2,))
    stadiums = (df.dropna(subset=["stadium"]).groupby("stadium").size().sort_values(ascending=False)
                if not df.empty else pd.Series(dtype=int))
    cities = sorted(df["city"].dropna().unique().tolist()) if not df.empty else []
    return {"country": info.iloc[0].to_dict() if not info.empty else {"iso2": iso2, "name_pt": iso2},
            "record": summarize(df), "matches": df, "stadiums": stadiums, "cities": cities,
            "inferred": int((df["country_status"] == "inferido").sum()) if not df.empty else 0}
