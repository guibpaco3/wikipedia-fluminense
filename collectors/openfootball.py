"""Coletor openfootball (github.com/openfootball) — dados em domínio público (CC0).

Formato "Football.TXT":

    = Copa Libertadores 2023
    ▪ Finals, Final
      Sat Nov 4
        17:00  CA Boca Juniors (ARG)   v Fluminense FC (BRA)      1-2 a.e.t. (1-1, 0-1)

Placar: "1-2 a.e.t. (1-1, 0-1)" = 1-2 após a prorrogação (1-1 no tempo normal, 0-1 no intervalo);
"2-4 pen. (1-1, 0-1)" = 2-4 nos pênaltis após 1-1. O placar gravado é o do fim do jogo com bola
rolando (prorrogação incluída); pênaltis em campo próprio.

País da partida: nas copas continentais é inferido do país do mandante (status "inferido");
finais em jogo único (Libertadores e Sul-Americana desde 2019) e o Mundial de Clubes são em
sede neutra — o país só é gravado quando a fonte diz qual é (aqui, apenas para o Mundial, cuja
sede é a do torneio e consta do cabeçalho do arquivo). Sem estádio/árbitro/uniforme nessa fonte.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass

from collectors.base import run_collector
from collectors.data_validation import validate_match
from collectors.http import PoliteClient
from collectors.teams import FIFA_ISO2, TeamNamer, is_fluminense
from core import config
from database.connection import Conn
from database.models import EventRecord, MatchRecord
from database.repository import upsert_match

SOURCE = "openfootball"
RAW = "https://raw.githubusercontent.com/openfootball/{repo}/master/{path}"
WEB = "https://github.com/openfootball/{repo}/blob/master/{path}"

log = config.get_logger("openfootball")

# (repositório, caminho, competição, categoria, temporada, país-sede quando neutro)
FILES = [
    ("south-america", "brazil/2025_br1.txt", "Campeonato Brasileiro Série A", "nacional", "2025", None),
    ("south-america", "brazil/2026_br1.txt", "Campeonato Brasileiro Série A", "nacional", "2026", None),
    ("south-america", "brazil/2025_brcup.txt", "Copa do Brasil de Futebol", "nacional", "2025", None),
    *[("south-america", f"copa-libertadores/{y}_copal.txt", "Copa Libertadores", "continental", str(y), None)
      for y in range(2012, 2027)],
    *[("south-america", f"copa-libertadores/{y}_copas.txt", "Copa Sul-Americana", "continental", str(y), None)
      for y in range(2012, 2026)],
    ("club-world-cup", "2023/clubworldcup.txt", "Copa do Mundo de Clubes da FIFA", "mundial", "2023", "SA"),
    ("club-world-cup", "2025/clubworldcup.txt", "Copa do Mundo de Clubes da FIFA", "mundial", "2025", "US"),
]
NATIONAL = {"Campeonato Brasileiro Série A", "Copa do Brasil de Futebol"}

_DOW = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
_MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                                       "Nov", "Dec"], 1)}
RX_DATE = re.compile(rf"^\s*(?:{_DOW}\s+)?(?P<mon>[A-Z][a-z]{{2}})/?\s*(?P<day>\d{{1,2}})(?:\s+(?P<year>\d{{4}}))?\s*$")
RX_MATCH = re.compile(
    r"^\s*(?:(?P<time>\d{1,2}[:.]\d{2})\s+)?(?:@\s*\S.*?\s{2,})?(?P<home>\S.*?)\s+v(?:s\.?)?\s+(?P<away>\S.*?)\s{2,}"
    r"(?P<score>\d+-\d+)\s*(?P<kind>a\.e\.t\.|pen\.)?\s*(?:\((?P<inner>[^)]*)\))?(?P<rest>.*)$")
RX_STAGE = re.compile(r"^\s*▪\s*(?P<stage>.+?)\s*$")
RX_YEAR = re.compile(r"\b(20\d\d|19\d\d)\b")


@dataclass
class OFMatch:
    date: str
    kickoff: str | None
    home: str
    away: str
    home_goals: int
    away_goals: int
    ht: tuple[int, int] | None
    pens: tuple[int, int] | None
    stage: str | None
    round: str | None


def _score(s: str) -> tuple[int, int]:
    a, b = s.split("-")
    return int(a), int(b)


def parse(text: str, default_year: int) -> list[OFMatch]:
    year = default_year
    head = RX_YEAR.search(next((l for l in text.splitlines() if l.startswith("=")), ""))
    stage = rnd = None
    cur_date: str | None = None
    last_month: int | None = None
    out: list[OFMatch] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line.startswith("="):
            continue
        sm = RX_STAGE.match(line)
        if sm:
            st = sm.group("stage")
            md = re.match(r"(?i)^(?:matchday|round|rodada)\s*(\d+)$", st)
            if md:
                stage, rnd = None if stage and stage.lower().startswith("matchday") else stage, md.group(1)
            else:
                stage, rnd = st, None
            continue
        dm = RX_DATE.match(line)
        if dm and dm.group("mon") in _MONTHS:
            m = _MONTHS[dm.group("mon")]
            if dm.group("year"):
                year = int(dm.group("year"))
            elif last_month and m < last_month - 5:       # virou o ano
                year += 1
            last_month = m
            cur_date = f"{year:04d}-{m:02d}-{int(dm.group('day')):02d}"
            continue
        mm = RX_MATCH.match(line)
        if not mm or not cur_date:
            continue
        hg, ag = _score(mm.group("score"))
        inner = [p.strip() for p in (mm.group("inner") or "").split(",") if re.fullmatch(r"\s*\d+-\d+\s*", p)]
        ht = pens = None
        kind = mm.group("kind")
        if kind == "pen.":
            pens = (hg, ag)
            if not inner:
                continue                       # placar do tempo normal ausente: não dá para gravar
            hg, ag = _score(inner[0])          # placar com bola rolando (inclui prorrogação, se houve)
            ht = _score(inner[-1]) if len(inner) > 1 else None
        elif kind == "a.e.t.":
            ht = _score(inner[-1]) if len(inner) > 1 else None
        else:
            ht = _score(inner[0]) if inner else None
        out.append(OFMatch(cur_date, mm.group("time"), mm.group("home").strip(), mm.group("away").strip(),
                           hg, ag, ht, pens, stage, rnd))
    _ = head
    return out


def build_records(c: Conn, text: str, repo: str, path: str, competition: str, category: str, season: str,
                  host: str | None, namer: TeamNamer) -> list[MatchRecord]:
    recs = []
    url = WEB.format(repo=repo, path=path)
    for m in parse(text, int(season)):
        if not (is_fluminense(m.home) or is_fluminense(m.away)):
            continue
        intl = competition not in NATIONAL
        home, hs, hc = namer.canonical(m.home, country=None if intl else "BR", international=intl)
        away, as_, ac = namer.canonical(m.away, country=None if intl else "BR", international=intl)
        single_final = (competition in ("Copa Libertadores", "Copa Sul-Americana") and int(season) >= 2019
                        and (m.stage or "").lower().endswith("final") and "semi" not in (m.stage or "").lower()
                        and "quarter" not in (m.stage or "").lower())
        neutral = bool(host) or single_final
        if competition in NATIONAL:
            country, cstatus = "BR", "inferido"
        elif host:
            country, cstatus = host, "inferido"
        elif single_final:
            country, cstatus = None, "nao_verificado"
        else:
            country, cstatus = hc, "inferido"
        raw = repr((path, m))
        recs.append(MatchRecord(
            source_code=SOURCE, source_ref=f"{path}#{m.date}|{home}|{away}", date=m.date, kickoff=m.kickoff,
            home_team=home, away_team=away, home_state=hs, away_state=as_, home_country=hc, away_country=ac,
            home_goals=m.home_goals, away_goals=m.away_goals,
            home_goals_ht=m.ht[0] if m.ht else None, away_goals_ht=m.ht[1] if m.ht else None,
            home_penalties=m.pens[0] if m.pens else None, away_penalties=m.pens[1] if m.pens else None,
            competition=competition, competition_category=category, season=season,
            stage=m.stage, round=m.round, neutral=neutral, country_iso2=country, country_status=cstatus,
            url=url, reliability="media", row_hash=hashlib.sha1(raw.encode()).hexdigest()))
    return recs


def collect(files: list[tuple] | None = None, texts: dict[str, str] | None = None) -> dict:
    """Baixa os arquivos (ou usa `texts`, para testes) e funde as partidas do Fluminense."""
    files = files or FILES

    def work(c: Conn, counts: Counter, messages: list[str]) -> None:
        client = PoliteClient(delay=1.0, cache_dir=config.CACHE_DIR / "openfootball")
        namer = TeamNamer.from_db(c)
        for repo, path, comp, cat, season, host in files:
            try:
                text = texts[path] if texts and path in texts else \
                    client.get_bytes(RAW.format(repo=repo, path=path)).decode("utf-8")
            except Exception as e:  # noqa: BLE001 — arquivo ausente não derruba a coleta
                messages.append(f"{path}: não baixado ({e})")
                continue
            recs = build_records(c, text, repo, path, comp, cat, season, host, namer)
            for rec in recs:
                v = validate_match(rec)
                if not v.ok:
                    counts["rejected"] += 1
                    messages.append(f"[{rec.source_ref}] rejeitado: {'; '.join(v.errors)}")
                    continue
                status, _ = upsert_match(c, rec)
                counts[status] += 1
            messages.append(f"{path}: {len(recs)} partidas do Fluminense")
    return run_collector("openfootball", SOURCE, work)


__all__ = ["collect", "parse", "FILES", "FIFA_ISO2", "EventRecord"]
