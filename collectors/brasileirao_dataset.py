"""Coletor do Brasileirão Dataset (github.com/adaoduque/Brasileirao_Dataset).

Cobertura: Campeonato Brasileiro Série A, 2003 em diante.
Usa três arquivos: partidas (full), gols e cartões.

Incremental: cada linha gera um hash (partida + gols + cartões). Linhas cujo hash
não mudou desde a última coleta são ignoradas.

Derivações (registradas como tal, nunca como fato confirmado):
- Temporada: o arquivo não traz a temporada; ela é obtida pela sequência das rodadas
  (a rodada volta a 1 quando começa um novo campeonato). Ex.: jogos de jan–fev/2021
  pertencem ao campeonato de 2020.
- País = Brasil com status "inferido" (competição nacional disputada no Brasil).
"""
from __future__ import annotations

import csv
import hashlib
import io
from collections import Counter, defaultdict
from datetime import datetime

from collectors.base import run_collector
from collectors.data_validation import validate_match
from collectors.http import PoliteClient
from collectors.normalization import parse_int, stadium_display, team_display
from core import config
from core.text import norm
from database.connection import Conn
from database.models import EventRecord, MatchRecord
from database.repository import upsert_match

SOURCE = "brasileirao_dataset"
RAW = "https://raw.githubusercontent.com/adaoduque/Brasileirao_Dataset/master/"
FILES = {"matches": "campeonato-brasileiro-full.csv", "goals": "campeonato-brasileiro-gols.csv",
         "cards": "campeonato-brasileiro-cartoes.csv"}
REPO_URL = "https://github.com/adaoduque/Brasileirao_Dataset/blob/master/"
COMPETITION = "Campeonato Brasileiro Série A"
WIKIDATA_ID = "Q206813"

log = config.get_logger("brasileirao")


def _read_csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))


def download(client: PoliteClient | None = None) -> dict[str, list[dict]]:
    client = client or PoliteClient(delay=1.0)
    return {k: _read_csv(client.get_bytes(RAW + f).decode("utf-8")) for k, f in FILES.items()}


def assign_seasons(rows: list[dict]) -> dict[str, str]:
    """ID da partida -> temporada, a partir do reinício da numeração das rodadas."""
    ordered = sorted(rows, key=lambda r: int(r["ID"]))
    seasons: dict[str, str] = {}
    season_year = None
    last_round = None
    for r in ordered:
        rnd = parse_int(r.get("rodata") or r.get("rodada"))
        year = datetime.strptime(r["data"].strip(), "%d/%m/%Y").year
        # Novo campeonato: rodada despenca (ex.: 38 -> 1). Pequenos recuos (jogos adiados) não contam.
        new_block = season_year is None or (rnd is not None and last_round is not None
                                            and rnd < last_round - 20)
        if new_block:
            season_year = year  # ano do primeiro jogo do campeonato
        if rnd is not None:
            last_round = rnd
        seasons[r["ID"]] = str(season_year)
    return seasons


def build_records(data: dict[str, list[dict]]) -> list[MatchRecord]:
    flu = norm(config.FLUMINENSE_NAME)
    goals = defaultdict(list)
    for g in data["goals"]:
        goals[g["partida_id"]].append(g)
    cards = defaultdict(list)
    for c in data["cards"]:
        cards[c["partida_id"]].append(c)
    seasons = assign_seasons(data["matches"])
    out: list[MatchRecord] = []
    for r in data["matches"]:
        if flu not in (norm(r["mandante"]), norm(r["visitante"])):
            continue
        mid = r["ID"]
        home, away = team_display(r["mandante"]), team_display(r["visitante"])
        home_n = norm(r["mandante"])
        events: list[EventRecord] = []
        for g in sorted(goals[mid], key=lambda x: parse_int(x.get("minuto")) or 0):
            kind = (g.get("tipo_de_gol") or "").strip().lower()
            etype = "gol_contra" if "contra" in kind else "gol_penalti" if "nalti" in kind else "gol"
            side = "home" if norm(g["clube"]) == home_n else "away"
            events.append(EventRecord(etype, side, g.get("atleta"), parse_int(g.get("minuto"))))
        for cd in cards[mid]:
            etype = "vermelho" if "verm" in (cd.get("cartao") or "").lower() else "amarelo"
            side = "home" if norm(cd["clube"]) == home_n else "away"
            events.append(EventRecord(etype, side, cd.get("atleta"), parse_int(cd.get("minuto"))))
        raw = repr((sorted(r.items()), [sorted(g.items()) for g in goals[mid]],
                    [sorted(c.items()) for c in cards[mid]]))
        out.append(MatchRecord(
            source_code=SOURCE, source_ref=mid,
            date=datetime.strptime(r["data"].strip(), "%d/%m/%Y").date().isoformat(),
            kickoff=(r.get("hora") or "").strip() or None,
            home_team=home, away_team=away,
            home_state=(r.get("mandante_Estado") or "").strip() or None,
            away_state=(r.get("visitante_Estado") or "").strip() or None,
            home_country="BR", away_country="BR",
            home_goals=parse_int(r.get("mandante_Placar")), away_goals=parse_int(r.get("visitante_Placar")),
            competition=COMPETITION, competition_category="nacional", season=seasons.get(mid),
            round=(r.get("rodata") or r.get("rodada") or "").strip() or None,
            stadium=stadium_display(r.get("arena")),
            country_iso2="BR", country_status="inferido",
            home_coach=(r.get("tecnico_mandante") or "").strip() or None,
            away_coach=(r.get("tecnico_visitante") or "").strip() or None,
            home_formation=(r.get("formacao_mandante") or "").strip() or None,
            away_formation=(r.get("formacao_visitante") or "").strip() or None,
            url=REPO_URL + FILES["matches"], reliability="media", events=events,
            row_hash=hashlib.sha1(raw.encode()).hexdigest(),
        ))
    return out


def ingest(c: Conn, records: list[MatchRecord], counts: Counter, messages: list[str]) -> None:
    for rec in records:
        v = validate_match(rec)
        if not v.ok:
            counts["rejected"] += 1
            messages.append(f"[{rec.source_ref} {rec.date}] rejeitado: {'; '.join(v.errors)}")
            continue
        for w in v.warnings:
            messages.append(f"[{rec.source_ref} {rec.date}] aviso: {w}")
        status, _ = upsert_match(c, rec)
        counts[status] += 1


def collect(data: dict[str, list[dict]] | None = None) -> dict:
    def work(c: Conn, counts: Counter, messages: list[str]) -> None:
        d = data or download()
        records = build_records(d)
        messages.append(f"{len(records)} partidas do Fluminense encontradas no arquivo.")
        ingest(c, records, counts, messages)
        # Mesma competição no Wikidata (Q206813), para unificar títulos e partidas.
        c.execute("UPDATE competitions SET wikidata_id = ? WHERE name = ? AND wikidata_id IS NULL "
                  "AND NOT EXISTS (SELECT 1 FROM competitions WHERE wikidata_id = ?)",
                  (WIKIDATA_ID, COMPETITION, WIKIDATA_ID))
    return run_collector("brasileirao_dataset", SOURCE, work)
