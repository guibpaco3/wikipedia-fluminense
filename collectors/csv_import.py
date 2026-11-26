"""Importação de partidas por CSV padronizado.

Caminho para todas as fontes que não permitem coleta automática (RSSSF, Transfermarkt,
oGol, livros, jornais): o administrador transcreve e CADA LINHA informa sua fonte.

Colunas (cabeçalho obrigatório; vazias são permitidas, exceto as marcadas com *):
  data*            AAAA-MM-DD ou DD/MM/AAAA
  mandante*, visitante*
  gols_mandante, gols_visitante, gols_mandante_intervalo, gols_visitante_intervalo
  horario, competicao, categoria_competicao, temporada, fase, rodada, neutro (sim/não)
  estadio, cidade, pais_iso2, pais_status (verificado/nao_verificado), publico
  arbitro, arbitro_status (confirmado/nao_confirmado)
  tecnico_mandante, tecnico_visitante
  gols   -> "mandante|Fred|23;visitante|Fulano|51;mandante|Contra: Beltrano|70"
  fonte_codigo*    código de uma fonte cadastrada (rsssf, transfermarkt, ogol, manual...)
  fonte_url, confiabilidade (alta/media/baixa), ref (identificador opcional)
"""
from __future__ import annotations

import csv
import hashlib
import io
from collections import Counter
from datetime import datetime

from collectors.base import run_collector
from collectors.data_validation import validate_match
from collectors.normalization import parse_int
from core.text import clean
from database.connection import Conn
from database.models import EventRecord, MatchRecord
from database.repository import upsert_match

COLUMNS = ["data", "horario", "mandante", "visitante", "gols_mandante", "gols_visitante",
           "gols_mandante_intervalo", "gols_visitante_intervalo", "competicao", "categoria_competicao",
           "temporada", "fase", "rodada", "neutro", "estadio", "cidade", "pais_iso2", "pais_status", "publico",
           "arbitro", "arbitro_status", "tecnico_mandante", "tecnico_visitante", "gols",
           "fonte_codigo", "fonte_url", "confiabilidade", "ref"]
REQUIRED = ("data", "mandante", "visitante", "fonte_codigo")


def template() -> str:
    return ",".join(COLUMNS) + "\n"


def _date(v: str) -> str:
    v = v.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"data inválida: {v!r}")


def _events(spec: str | None) -> list[EventRecord]:
    out = []
    for part in (spec or "").split(";"):
        bits = [b.strip() for b in part.split("|")]
        if len(bits) < 2 or not bits[1]:
            continue
        side = "home" if bits[0].lower().startswith("m") else "away"
        name = bits[1]
        etype = "gol"
        if name.lower().startswith("contra:"):
            etype, name = "gol_contra", name.split(":", 1)[1].strip()
        elif name.lower().startswith("pênalti:") or name.lower().startswith("penalti:"):
            etype, name = "gol_penalti", name.split(":", 1)[1].strip()
        out.append(EventRecord(etype, side, name, parse_int(bits[2]) if len(bits) > 2 else None))
    return out


def parse(text: str) -> tuple[list[MatchRecord], list[str]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
    if missing:
        return [], [f"Colunas obrigatórias ausentes: {', '.join(missing)}"]
    records, errors = [], []
    for i, r in enumerate(reader, start=2):
        g = lambda k: clean(r.get(k))  # noqa: E731
        try:
            if not all(g(k) for k in REQUIRED):
                raise ValueError("campos obrigatórios vazios")
            d = _date(g("data"))
            ref = g("ref") or f"{d}|{g('mandante')}|{g('visitante')}"
            rec = MatchRecord(
                source_code=g("fonte_codigo"), source_ref=ref, date=d, kickoff=g("horario"),
                home_team=g("mandante"), away_team=g("visitante"),
                home_goals=parse_int(g("gols_mandante")), away_goals=parse_int(g("gols_visitante")),
                home_goals_ht=parse_int(g("gols_mandante_intervalo")),
                away_goals_ht=parse_int(g("gols_visitante_intervalo")),
                competition=g("competicao"), competition_category=g("categoria_competicao") or "outro",
                season=g("temporada"), stage=g("fase"), round=g("rodada"),
                neutral=(g("neutro") or "").lower() in ("sim", "s", "1", "true"),
                stadium=g("estadio"), city=g("cidade"),
                country_iso2=(g("pais_iso2") or "").upper() or None,
                country_status=g("pais_status") or "nao_verificado",
                attendance=parse_int(g("publico")), referee=g("arbitro"),
                referee_status=g("arbitro_status") or "nao_confirmado",
                home_coach=g("tecnico_mandante"), away_coach=g("tecnico_visitante"),
                url=g("fonte_url"), reliability=g("confiabilidade") or "media", events=_events(g("gols")),
            )
            rec.row_hash = hashlib.sha1(repr(sorted(r.items())).encode()).hexdigest()
            records.append(rec)
        except Exception as exc:
            errors.append(f"Linha {i}: {exc}")
    return records, errors


def import_csv(text: str, username: str = "cli") -> dict:
    def work(c: Conn, counts: Counter, messages: list[str]) -> None:
        records, errors = parse(text)
        counts["rejected"] += len(errors)
        messages.extend(errors)
        known = {r["code"] for r in c.all("SELECT code FROM sources")}
        for rec in records:
            if rec.source_code not in known:
                counts["rejected"] += 1
                messages.append(f"[{rec.date}] fonte desconhecida: {rec.source_code}")
                continue
            v = validate_match(rec)
            if not v.ok:
                counts["rejected"] += 1
                messages.append(f"[{rec.date} {rec.home_team} x {rec.away_team}] {'; '.join(v.errors)}")
                continue
            messages.extend(f"[{rec.date}] aviso: {w}" for w in v.warnings)
            status, _ = upsert_match(c, rec)
            counts[status] += 1
    return run_collector(f"csv_import:{username}", "csv_import", work)
