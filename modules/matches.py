"""Página individual da partida: todos os dados + proveniência."""
from __future__ import annotations

import pandas as pd

from database.connection import query_df, query_one


def get(match_id: int) -> dict | None:
    return query_one("SELECT * FROM v_matches WHERE id = ?", (match_id,))


def events(match_id: int) -> pd.DataFrame:
    return query_df(
        "SELECT e.event_type, e.minute, e.for_fluminense, e.player_name, e.person_id, s.name AS source "
        "FROM match_events e LEFT JOIN sources s ON s.id = e.source_id WHERE e.match_id = ? "
        "ORDER BY e.minute IS NULL, e.minute", (match_id,))


def lineup(match_id: int) -> pd.DataFrame:
    return query_df(
        "SELECT p.id AS person_id, p.name, l.starter, l.shirt_number FROM match_lineups l "
        "JOIN people p ON p.id = l.person_id WHERE l.match_id = ? ORDER BY l.starter DESC, l.shirt_number",
        (match_id,))


def officials(match_id: int) -> pd.DataFrame:
    return query_df("SELECT o.role, r.name FROM match_officials o JOIN referees r ON r.id = o.referee_id "
                    "WHERE o.match_id = ?", (match_id,))


def provenance(match_id: int) -> pd.DataFrame:
    return query_df(
        "SELECT f.field AS Campo, f.value AS Valor, s.name AS Fonte, f.url AS URL, f.collected_at AS Coletado, "
        "f.reliability AS Confiabilidade, f.status AS Status FROM field_sources f "
        "JOIN sources s ON s.id = f.source_id WHERE f.entity_type = 'match' AND f.entity_id = ? "
        "ORDER BY f.field, s.name", (match_id,))


def source_refs(match_id: int) -> pd.DataFrame:
    return query_df("SELECT s.name AS Fonte, r.source_ref AS Referência, r.url AS URL, r.collected_at AS Coletado "
                    "FROM match_source_refs r JOIN sources s ON s.id = r.source_id WHERE r.match_id = ?",
                    (match_id,))


def discrepancies(match_id: int) -> pd.DataFrame:
    return query_df(
        "SELECT d.field AS Campo, d.current_value AS 'Valor atual', d.new_value AS 'Valor divergente', "
        "s.name AS 'Fonte divergente', d.status AS Situação FROM discrepancies d "
        "LEFT JOIN sources s ON s.id = d.new_source_id WHERE d.entity_type='match' AND d.entity_id = ?",
        (match_id,))


def neighbors(match_id: int, date: str) -> tuple[int | None, int | None]:
    prev = query_one("SELECT id FROM matches WHERE (date < ?) OR (date = ? AND id < ?) "
                     "ORDER BY date DESC, id DESC LIMIT 1", (date, date, match_id))
    nxt = query_one("SELECT id FROM matches WHERE (date > ?) OR (date = ? AND id > ?) "
                    "ORDER BY date, id LIMIT 1", (date, date, match_id))
    return (prev or {}).get("id"), (nxt or {}).get("id")
