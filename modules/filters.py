"""Filtro único de partidas, compartilhado por calendário, globo, pesquisa avançada
e páginas de entidades. Todos os critérios são combináveis (E lógico entre critérios,
OU lógico entre valores de um mesmo critério)."""
from __future__ import annotations

from dataclasses import dataclass, field, fields

import pandas as pd

from database.connection import query_df

KIT_UNIDENTIFIED = -1  # valor especial: "Uniforme não identificado"


@dataclass
class MatchFilter:
    opponents: list[int] = field(default_factory=list)
    opponent_countries: list[str] = field(default_factory=list)
    referees: list[int] = field(default_factory=list)
    include_unconfirmed_referees: bool = False
    kits: list[int] = field(default_factory=list)          # aceita KIT_UNIDENTIFIED
    kit_categories: list[str] = field(default_factory=list)
    competitions: list[int] = field(default_factory=list)
    competition_categories: list[str] = field(default_factory=list)
    seasons: list[str] = field(default_factory=list)
    stadiums: list[int] = field(default_factory=list)
    cities: list[int] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    continents: list[str] = field(default_factory=list)
    international: bool | None = None       # True = fora do Brasil; False = no Brasil
    sides: list[str] = field(default_factory=list)          # mandante/visitante/neutro
    results: list[str] = field(default_factory=list)        # V/E/D
    coaches: list[int] = field(default_factory=list)
    player: int | None = None                # partidas com gol/cartão/escalação do jogador
    date_from: str | None = None
    date_to: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    months: list[int] = field(default_factory=list)
    day: int | None = None
    verified_only: bool = False

    def is_empty(self) -> bool:
        return all(getattr(self, f.name) in (None, False, [], "") for f in fields(self)
                   if f.name != "include_unconfirmed_referees")

    def where(self) -> tuple[str, list]:
        sql: list[str] = []
        params: list = []

        def inn(col: str, values: list) -> None:
            if values:
                sql.append(f"{col} IN ({', '.join('?' for _ in values)})")
                params.extend(values)

        inn("opponent_id", self.opponents)
        inn("opponent_country", self.opponent_countries)
        if self.referees:
            inn("referee_id", self.referees)
            if not self.include_unconfirmed_referees:
                sql.append("referee_status = 'confirmado'")
        if self.kits:
            ids = [k for k in self.kits if k != KIT_UNIDENTIFIED]
            parts = []
            if ids:
                parts.append(f"(flu_kit_id IN ({', '.join('?' for _ in ids)}) AND kit_status = 'confirmado')")
                params.extend(ids)
            if KIT_UNIDENTIFIED in self.kits:
                parts.append("(flu_kit_id IS NULL OR kit_status <> 'confirmado')")
            sql.append("(" + " OR ".join(parts) + ")")
        if self.kit_categories:
            inn("kit_category", self.kit_categories)
            sql.append("kit_status = 'confirmado'")
        inn("competition_id", self.competitions)
        inn("competition_category", self.competition_categories)
        inn("season", self.seasons)
        inn("stadium_id", self.stadiums)
        inn("city_id", self.cities)
        inn("country_iso2", self.countries)
        inn("continent", self.continents)
        if self.international is True:
            sql.append("country_iso2 IS NOT NULL AND country_iso2 <> 'BR'")
        elif self.international is False:
            sql.append("country_iso2 = 'BR'")
        inn("flu_side", self.sides)
        inn("result", self.results)
        inn("flu_coach_id", self.coaches)
        if self.player:
            sql.append("(id IN (SELECT match_id FROM match_events WHERE person_id = ? AND for_fluminense = 1) "
                       "OR id IN (SELECT match_id FROM match_lineups WHERE person_id = ?))")
            params.extend([self.player, self.player])
        if self.date_from:
            sql.append("date >= ?")
            params.append(self.date_from)
        if self.date_to:
            sql.append("date <= ?")
            params.append(self.date_to)
        if self.year_from:
            sql.append("year >= ?")
            params.append(self.year_from)
        if self.year_to:
            sql.append("year <= ?")
            params.append(self.year_to)
        inn("month", self.months)
        if self.day:
            sql.append("day = ?")
            params.append(self.day)
        if self.verified_only:
            sql.append("verification_status = 'verificado'")
        return (" WHERE " + " AND ".join(sql)) if sql else "", params


def fetch_matches(f: MatchFilter | None = None, order: str = "date, kickoff") -> pd.DataFrame:
    where, params = (f or MatchFilter()).where()
    return query_df(f"SELECT * FROM v_matches{where} ORDER BY {order}", params)


def options(sql: str) -> list[tuple]:
    """Lista (id, rótulo) para seletores."""
    df = query_df(sql)
    return list(df.itertuples(index=False, name=None))
