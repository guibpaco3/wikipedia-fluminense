"""Cobertura histórica: o que a base contém de fato e quando foi atualizada.

Toda página com estatísticas mostra este resumo, para que números parciais nunca
sejam lidos como a história completa do clube.
"""
from __future__ import annotations

import pandas as pd

from database.connection import query_df, query_one


def summary() -> dict:
    row = query_one("SELECT COUNT(*) AS n, MIN(date) AS first, MAX(date) AS last, "
                    "COUNT(DISTINCT competition_id) AS comps FROM matches") or {}
    last = query_one("SELECT value FROM meta WHERE key = 'last_update'")
    row["last_update"] = last["value"] if last else None
    return row


def by_competition() -> pd.DataFrame:
    return query_df(
        "SELECT competition AS Competição, COUNT(*) AS Partidas, MIN(season) AS 'Primeira temporada', "
        "MAX(season) AS 'Última temporada', MIN(date) AS 'Primeiro jogo', MAX(date) AS 'Último jogo' "
        "FROM v_matches GROUP BY competition ORDER BY Partidas DESC")


def by_source() -> pd.DataFrame:
    return query_df(
        "SELECT s.name AS Fonte, COUNT(DISTINCT r.match_id) AS Partidas, MAX(r.collected_at) AS 'Última coleta' "
        "FROM match_source_refs r JOIN sources s ON s.id = r.source_id GROUP BY s.id ORDER BY Partidas DESC")


def field_completeness() -> pd.DataFrame:
    """Percentual de partidas com cada informação preenchida."""
    row = query_one(
        "SELECT COUNT(*) AS total, COUNT(kickoff) AS horario, COUNT(stadium_id) AS estadio, "
        "COUNT(flu_goals_ht) AS intervalo, COUNT(attendance) AS publico, "
        "SUM(referee_status = 'confirmado') AS arbitro, SUM(kit_status = 'confirmado') AS uniforme, "
        "COUNT(flu_coach_id) AS tecnico, "
        "(SELECT COUNT(DISTINCT match_id) FROM match_events) AS eventos, "
        "(SELECT COUNT(DISTINCT match_id) FROM match_lineups) AS escalacao, "
        "SUM(verification_status = 'verificado') AS verificadas FROM matches")
    total = row.pop("total") or 0
    labels = {"horario": "Horário", "estadio": "Estádio", "intervalo": "Placar do intervalo",
              "publico": "Público", "arbitro": "Árbitro confirmado", "uniforme": "Uniforme confirmado",
              "tecnico": "Técnico do Flu", "eventos": "Gols/cartões detalhados",
              "escalacao": "Escalação", "verificadas": "Partida verificada manualmente"}
    return pd.DataFrame([{"Informação": labels[k], "Partidas": int(v or 0),
                          "Cobertura %": round(100 * (v or 0) / total, 1) if total else 0.0}
                         for k, v in row.items()])


def coverage_sentence() -> str:
    s = summary()
    if not s.get("n"):
        return "A base ainda não contém partidas. Execute a atualização no painel administrativo."
    from datetime import date
    f = date.fromisoformat(s["first"]).strftime("%d/%m/%Y")
    l_ = date.fromisoformat(s["last"]).strftime("%d/%m/%Y")
    comps = query_df("SELECT DISTINCT competition FROM v_matches WHERE competition IS NOT NULL")["competition"]
    comp_txt = ", ".join(comps.tolist()[:4]) + ("…" if len(comps) > 4 else "")
    return (f"Base com {s['n']:,} partidas entre {f} e {l_} ({comp_txt}). "
            "Não representa toda a história do clube.").replace(",", ".")
