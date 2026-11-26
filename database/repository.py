"""Operações de escrita: resolução de entidades, upsert de partidas com
proveniência por campo, detecção de divergências, auditoria e metadados."""
from __future__ import annotations

import json
from datetime import date as date_cls
from datetime import datetime, timedelta, timezone
from typing import Any

from core import config
from core.text import clean, norm
from database.connection import Conn
from database.models import MatchRecord

log = config.get_logger("repository")

MANUAL_SOURCE = "manual"

# Campos da partida cuja origem é rastreada.
TRACKED_FIELDS = (
    "date", "kickoff", "competition_id", "edition_id", "round", "stage",
    "home_team_id", "away_team_id", "flu_goals", "opp_goals", "flu_goals_ht", "opp_goals_ht",
    "flu_penalties", "opp_penalties", "stadium_id", "city_id", "country_iso2", "attendance", "referee_id", "flu_coach_id",
    "opp_coach", "flu_formation",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- metadados
def set_meta(c: Conn, key: str, value: str) -> None:
    c.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
              "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))


def get_meta(c: Conn, key: str) -> str | None:
    return c.scalar("SELECT value FROM meta WHERE key = ?", (key,))


def audit(c: Conn, username: str, action: str, entity_type: str | None = None,
          entity_id: int | None = None, details: Any = None) -> None:
    c.execute(
        "INSERT INTO audit_log (at, username, action, entity_type, entity_id, details) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (now(), username, action, entity_type, entity_id,
         json.dumps(details, ensure_ascii=False, default=str) if details is not None else None),
    )


# ---------------------------------------------------------------- fontes
def ensure_source(c: Conn, code: str, name: str, kind: str, base_url: str | None = None,
                  license: str | None = None, reliability: str = "media",
                  automated: bool = False, notes: str | None = None) -> int:
    row = c.one("SELECT id FROM sources WHERE code = ?", (code,))
    if row:
        c.execute("UPDATE sources SET name=?, kind=?, base_url=?, license=?, default_reliability=?, "
                  "automated=?, notes=? WHERE id=?",
                  (name, kind, base_url, license, reliability, int(automated), notes, row["id"]))
        return row["id"]
    return c.insert(
        "INSERT INTO sources (code, name, kind, base_url, license, default_reliability, automated, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (code, name, kind, base_url, license, reliability, int(automated), notes))


def manual_source_id(c: Conn) -> int:
    return ensure_source(c, MANUAL_SOURCE, "Cadastro manual (painel administrativo)", "manual",
                         reliability="alta",
                         notes="Informação inserida/corrigida por administrador, com referência informada.")


def source_id(c: Conn, code: str) -> int:
    sid = c.scalar("SELECT id FROM sources WHERE code = ?", (code,))
    if sid is None:
        if code == MANUAL_SOURCE:
            return manual_source_id(c)
        raise KeyError(f"Fonte não cadastrada: {code}")
    return sid


def start_run(c: Conn, source: int, collector: str) -> int:
    return c.insert("INSERT INTO collection_runs (source_id, collector, started_at) VALUES (?, ?, ?)",
                    (source, collector, now()))


def finish_run(c: Conn, run_id: int, status: str, counts: dict[str, int], message: str = "") -> None:
    c.execute(
        "UPDATE collection_runs SET finished_at=?, status=?, inserted=?, updated=?, unchanged=?, "
        "rejected=?, message=? WHERE id=?",
        (now(), status, counts.get("inserted", 0), counts.get("updated", 0),
         counts.get("unchanged", 0), counts.get("rejected", 0), message[:4000], run_id))


def record_field(c: Conn, entity_type: str, entity_id: int, field: str, value: Any, source: int,
                 source_ref: str | None = None, url: str | None = None,
                 reliability: str = "media", status: str = "nao_verificado") -> None:
    c.execute(
        "INSERT INTO field_sources (entity_type, entity_id, field, value, source_id, source_ref, url, "
        "collected_at, reliability, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(entity_type, entity_id, field, source_id) DO UPDATE SET "
        "value=excluded.value, source_ref=excluded.source_ref, url=excluded.url, "
        "collected_at=excluded.collected_at, reliability=excluded.reliability, status=excluded.status",
        (entity_type, entity_id, field, None if value is None else str(value), source, source_ref, url,
         now(), reliability, status))


def add_discrepancy(c: Conn, entity_type: str, entity_id: int, field: str, current: Any,
                    current_source: int | None, new: Any, new_source: int, url: str | None) -> None:
    exists = c.scalar(
        "SELECT id FROM discrepancies WHERE entity_type=? AND entity_id=? AND field=? AND new_value=? "
        "AND new_source_id=? AND status='aberta'",
        (entity_type, entity_id, field, str(new), new_source))
    if exists:
        return
    c.execute(
        "INSERT INTO discrepancies (entity_type, entity_id, field, current_value, current_source_id, "
        "new_value, new_source_id, new_url, detected_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (entity_type, entity_id, field, None if current is None else str(current), current_source,
         str(new), new_source, url, now()))


# ---------------------------------------------------------------- entidades
def resolve_team(c: Conn, name: str, state: str | None = None, country: str | None = None,
                 create: bool = True) -> int | None:
    name = clean(name) or ""
    key = norm(name)
    tid = c.scalar("SELECT team_id FROM team_aliases WHERE alias_norm = ?", (key,))
    if tid or not create:
        return tid
    tid = c.scalar("SELECT id FROM teams WHERE name = ?", (name,))
    if tid is None:
        is_flu = int(key == norm(config.FLUMINENSE_NAME))
        tid = c.insert("INSERT INTO teams (name, state, country_iso2, is_fluminense) VALUES (?, ?, ?, ?)",
                       (name, state, country, is_flu))
    c.execute("INSERT OR IGNORE INTO team_aliases (alias_norm, team_id) VALUES (?, ?)", (key, tid))
    return tid


def fluminense_id(c: Conn) -> int:
    tid = c.scalar("SELECT id FROM teams WHERE is_fluminense = 1")
    return tid or resolve_team(c, config.FLUMINENSE_NAME, "RJ", "BR")


def add_team_alias(c: Conn, alias: str, team_id: int) -> None:
    c.execute("INSERT INTO team_aliases (alias_norm, team_id) VALUES (?, ?) "
              "ON CONFLICT(alias_norm) DO UPDATE SET team_id = excluded.team_id", (norm(alias), team_id))


def resolve_competition(c: Conn, name: str, category: str = "outro",
                        country: str | None = None) -> int:
    name = clean(name) or "Competição não identificada"
    cid = c.scalar("SELECT id FROM competitions WHERE name = ?", (name,))
    if cid:
        return cid
    return c.insert("INSERT INTO competitions (name, category, country_iso2) VALUES (?, ?, ?)",
                    (name, category, country))


def resolve_edition(c: Conn, competition_id: int, season: str) -> int:
    eid = c.scalar("SELECT id FROM competition_editions WHERE competition_id = ? AND season = ?",
                   (competition_id, season))
    if eid:
        return eid
    return c.insert("INSERT INTO competition_editions (competition_id, season) VALUES (?, ?)",
                    (competition_id, season))


def resolve_stadium(c: Conn, name: str, country: str | None = None, create: bool = True) -> int | None:
    name = clean(name)
    if not name:
        return None
    key = norm(name)
    sid = c.scalar("SELECT stadium_id FROM stadium_aliases WHERE alias_norm = ?", (key,))
    if sid or not create:
        return sid
    sid = c.scalar("SELECT id FROM stadiums WHERE name = ?", (name,))
    if sid is None:
        sid = c.insert("INSERT INTO stadiums (name, country_iso2) VALUES (?, ?)", (name, country))
    c.execute("INSERT OR IGNORE INTO stadium_aliases (alias_norm, stadium_id) VALUES (?, ?)", (key, sid))
    return sid


def resolve_city(c: Conn, name: str, state: str | None, country: str | None,
                 lat: float | None = None, lon: float | None = None,
                 wikidata_id: str | None = None) -> int:
    row = c.one("SELECT id FROM cities WHERE name = ? AND COALESCE(state,'') = COALESCE(?, '') "
                "AND COALESCE(country_iso2,'') = COALESCE(?, '')", (name, state, country))
    if row:
        return row["id"]
    return c.insert("INSERT INTO cities (name, state, country_iso2, lat, lon, wikidata_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (name, state, country, lat, lon, wikidata_id))


def resolve_person(c: Conn, name: str, context: str = "geral", create: bool = True,
                   wikidata_id: str | None = None) -> int | None:
    name = clean(name)
    if not name:
        return None
    if wikidata_id:
        pid = c.scalar("SELECT id FROM people WHERE wikidata_id = ?", (wikidata_id,))
        if pid:
            return pid
    key = norm(name)
    pid = c.scalar("SELECT person_id FROM person_aliases WHERE alias_norm = ? AND context IN (?, 'geral') "
                   "ORDER BY context = 'geral'", (key, context))
    if pid or not create:
        return pid
    pid = c.insert("INSERT INTO people (name, name_norm, wikidata_id) VALUES (?, ?, ?)",
                   (name, key, wikidata_id))
    c.execute("INSERT OR IGNORE INTO person_aliases (alias_norm, person_id, context) VALUES (?, ?, ?)",
              (key, pid, context))
    return pid


def resolve_referee(c: Conn, name: str) -> int | None:
    name = clean(name)
    if not name:
        return None
    rid = c.scalar("SELECT id FROM referees WHERE name = ?", (name,))
    return rid or c.insert("INSERT INTO referees (name) VALUES (?)", (name,))


def merge_people(c: Conn, keep_id: int, drop_id: int, username: str) -> None:
    """Une dois cadastros da mesma pessoa (ex.: nome abreviado × nome completo)."""
    if keep_id == drop_id:
        return
    for table, col in (("match_events", "person_id"), ("matches", "flu_coach_id"),
                       ("titles", "coach_id")):
        c.execute(f"UPDATE {table} SET {col} = ? WHERE {col} = ?", (keep_id, drop_id))
    c.execute("UPDATE OR IGNORE match_lineups SET person_id = ? WHERE person_id = ?", (keep_id, drop_id))
    for table in ("player_spells", "coach_spells", "presidencies", "person_aliases"):
        c.execute(f"UPDATE OR IGNORE {table} SET person_id = ? WHERE person_id = ?", (keep_id, drop_id))
    keep = c.one("SELECT * FROM people WHERE id = ?", (keep_id,))
    drop = c.one("SELECT * FROM people WHERE id = ?", (drop_id,))
    for col in ("full_name", "birth_date", "death_date", "nationality_iso2", "position", "photo_url",
                "wikidata_id", "bio"):
        if keep and drop and not keep[col] and drop[col]:
            if col == "wikidata_id":
                c.execute("UPDATE people SET wikidata_id = NULL WHERE id = ?", (drop_id,))
            c.execute(f"UPDATE people SET {col} = ? WHERE id = ?", (drop[col], keep_id))
    c.execute("DELETE FROM people WHERE id = ?", (drop_id,))
    audit(c, username, "mesclar_pessoas", "person", keep_id, {"removido": drop_id})


# ---------------------------------------------------------------- partidas
def natural_key(date: str, opponent_id: int) -> str:
    return f"{date}|{opponent_id}"


def _field_sources(c: Conn, match_id: int, field: str) -> set[int]:
    return {r["source_id"] for r in c.all(
        "SELECT source_id FROM field_sources WHERE entity_type='match' AND entity_id=? AND field=?",
        (match_id, field))}


def upsert_match(c: Conn, rec: MatchRecord) -> tuple[str, int]:
    """Funde uma partida vinda de uma fonte na base.

    Retorna (situação, id) com situação em: inserted | updated | unchanged.
    - Mesmo registro da mesma fonte com o mesmo hash -> unchanged (atualização incremental).
    - Campo vazio na base -> preenchido.
    - Campo divergente já confirmado por OUTRA fonte -> mantém o atual e registra divergência.
    """
    src = source_id(c, rec.source_code)
    ref = c.one("SELECT match_id, row_hash FROM match_source_refs WHERE source_id=? AND source_ref=?",
                (src, rec.source_ref))
    if ref and rec.row_hash and ref["row_hash"] == rec.row_hash:
        return "unchanged", ref["match_id"]

    flu = fluminense_id(c)
    home = resolve_team(c, rec.home_team, rec.home_state, rec.home_country)
    away = resolve_team(c, rec.away_team, rec.away_state, rec.away_country)
    if flu not in (home, away):
        raise ValueError(f"Partida sem o Fluminense: {rec.home_team} x {rec.away_team}")
    flu_home = home == flu
    opponent = away if flu_home else home
    side = "neutro" if rec.neutral else ("mandante" if flu_home else "visitante")

    comp_id = resolve_competition(c, rec.competition, rec.competition_category) if rec.competition else None
    edition_id = resolve_edition(c, comp_id, rec.season) if comp_id and rec.season else None
    stadium_id = resolve_stadium(c, rec.stadium, rec.country_iso2) if rec.stadium else None
    referee_id = resolve_referee(c, rec.referee) if rec.referee else None
    coach_name = rec.home_coach if flu_home else rec.away_coach
    coach_id = resolve_person(c, coach_name, "tecnico") if coach_name else None
    city_id = None
    if rec.city:
        city_id = resolve_city(c, rec.city, None, rec.country_iso2)

    def pick(h, a):
        return h if flu_home else a

    values: dict[str, Any] = {
        "date": rec.date, "kickoff": rec.kickoff, "competition_id": comp_id, "edition_id": edition_id,
        "round": rec.round, "stage": rec.stage, "home_team_id": home, "away_team_id": away,
        "flu_goals": pick(rec.home_goals, rec.away_goals), "opp_goals": pick(rec.away_goals, rec.home_goals),
        "flu_goals_ht": pick(rec.home_goals_ht, rec.away_goals_ht),
        "opp_goals_ht": pick(rec.away_goals_ht, rec.home_goals_ht),
        "flu_penalties": pick(rec.home_penalties, rec.away_penalties),
        "opp_penalties": pick(rec.away_penalties, rec.home_penalties),
        "stadium_id": stadium_id, "city_id": city_id, "country_iso2": rec.country_iso2,
        "attendance": rec.attendance, "referee_id": referee_id, "flu_coach_id": coach_id,
        "opp_coach": pick(rec.away_coach, rec.home_coach),
        "flu_formation": pick(rec.home_formation, rec.away_formation),
    }
    key = natural_key(rec.date, opponent)
    existing = None
    if ref:
        existing = c.one("SELECT * FROM matches WHERE id = ?", (ref["match_id"],))
    if existing is None:
        existing = c.one("SELECT * FROM matches WHERE natural_key = ?", (key,))
    if existing is None and comp_id:
        # Mesma partida com data diferente em outra fonte (jogo adiado, erro de digitação):
        # mesmo adversário e competição a até 3 dias -> é a mesma; a data entra como divergência.
        d0 = date_cls.fromisoformat(rec.date)
        near = c.all("SELECT * FROM matches WHERE opponent_id = ? AND competition_id = ? AND date BETWEEN ? AND ?",
                     (opponent, comp_id, (d0 - timedelta(days=3)).isoformat(),
                      (d0 + timedelta(days=3)).isoformat()))
        if len(near) == 1 and not c.scalar("SELECT 1 FROM match_source_refs WHERE match_id = ? AND source_id = ?",
                                           (near[0]["id"], src)):
            existing = near[0]

    ts = now()
    if existing is None:
        cols = dict(values)
        cols.update(natural_key=key, opponent_id=opponent, flu_side=side,
                    country_status=rec.country_status if rec.country_iso2 else "nao_verificado",
                    referee_status=rec.referee_status if referee_id else "nao_identificado",
                    reliability=rec.reliability, created_at=ts, updated_at=ts)
        names = ", ".join(cols)
        marks = ", ".join("?" for _ in cols)
        match_id = c.insert(f"INSERT INTO matches ({names}) VALUES ({marks})", list(cols.values()))
        status = "inserted"
        for f, v in values.items():
            if v is not None:
                record_field(c, "match", match_id, f, v, src, rec.source_ref, rec.url, rec.reliability)
    else:
        match_id = existing["id"]
        changes: dict[str, Any] = {}
        for f, v in values.items():
            if v is None:
                continue
            cur = existing[f]
            if cur is None or str(cur) == str(v):
                if cur is None:
                    changes[f] = v
                record_field(c, "match", match_id, f, v, src, rec.source_ref, rec.url, rec.reliability)
                continue
            others = _field_sources(c, match_id, f) - {src}
            if others:
                add_discrepancy(c, "match", match_id, f, cur, min(others), v, src, rec.url)
                record_field(c, "match", match_id, f, v, src, rec.source_ref, rec.url, rec.reliability,
                             status="divergente")
                c.execute("UPDATE matches SET verification_status='divergente' WHERE id=? "
                          "AND verification_status <> 'verificado'", (match_id,))
            else:  # a própria fonte corrigiu o valor
                changes[f] = v
                record_field(c, "match", match_id, f, v, src, rec.source_ref, rec.url, rec.reliability)
        if rec.referee and "referee_id" in changes:
            changes["referee_status"] = rec.referee_status
        if rec.country_iso2 and "country_iso2" in changes:
            changes["country_status"] = rec.country_status
        if changes:
            changes["updated_at"] = ts
            sets = ", ".join(f"{k} = ?" for k in changes)
            c.execute(f"UPDATE matches SET {sets} WHERE id = ?", [*changes.values(), match_id])
        status = "updated"

    c.execute(
        "INSERT INTO match_source_refs (match_id, source_id, source_ref, url, row_hash, collected_at) "
        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(source_id, source_ref) DO UPDATE SET "
        "match_id=excluded.match_id, url=excluded.url, row_hash=excluded.row_hash, "
        "collected_at=excluded.collected_at",
        (match_id, src, rec.source_ref, rec.url, rec.row_hash, ts))

    if rec.events:
        c.execute("DELETE FROM match_events WHERE match_id = ? AND source_id = ?", (match_id, src))
        for ev in rec.events:
            for_flu = (ev.side == "home") == flu_home
            person = None
            if for_flu and ev.event_type != "gol_contra" and ev.player_name:
                person = resolve_person(c, ev.player_name, "jogador")
            c.execute(
                "INSERT OR IGNORE INTO match_events (match_id, event_type, minute, for_fluminense, "
                "person_id, player_name, source_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (match_id, ev.event_type, ev.minute, int(for_flu), person, clean(ev.player_name), src))
    return status, match_id
