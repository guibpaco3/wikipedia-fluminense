"""Coletor RSSSF / RSSSF Brasil (www.rsssf.org e www.rsssfbrasil.com).

Política: páginas estáticas, sem robots.txt restritivo; o aviso de cada página permite copiar
"no todo ou em parte, desde que seja dado o devido crédito ao autor". O crédito fica no campo
URL de cada partida (página de origem) e na página "Fontes e cobertura". Downloads com 3 s de
intervalo e cache em disco — cada página é baixada uma única vez.

As páginas são texto livre com formatos que variam ao longo dos anos; a leitura fica em
`rsssf_parser.py`, que só aceita formatos reconhecidos com segurança. Lacunas nunca são
preenchidas por suposição:
- partida sem data exata na página não é importada (fica no relatório da coleta);
- estádio só quando a página informa; árbitro e uniforme não são lidos dessas páginas;
- autores de gols só quando a contagem de nomes bate com o placar.

País da partida: competições brasileiras -> Brasil (inferido); copas continentais -> país do
mandante (inferido), quando o país do clube é conhecido (código na própria página ou cadastro).
"""
from __future__ import annotations

import hashlib
import html
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from collectors.base import run_collector
from collectors.data_validation import validate_match
from collectors.http import PoliteClient
from collectors.rsssf_parser import ParsedMatch, parse_page
from collectors.teams import TeamNamer
from core import config
from core.text import norm
from database.connection import Conn
from database.models import EventRecord, MatchRecord
from database.repository import upsert_match

SOURCE = "rsssf"
log = config.get_logger("rsssf")

CARIOCA = "Campeonato Carioca de Futebol"
SERIE_A = "Campeonato Brasileiro Série A"
SERIE_B = "Campeonato Brasileiro Série B"
SERIE_C = "Campeonato Brasileiro Série C"
TACA_BRASIL = "Taça Brasil"
ROBERTAO = "Torneio Roberto Gomes Pedrosa"
COPA_BR = "Copa do Brasil de Futebol"
LIBERTADORES = "Copa Libertadores"
SULAMERICANA = "Copa Sul-Americana"
RECOPA = "Recopa Sul-Americana"
CATEGORY = {CARIOCA: "estadual", SERIE_A: "nacional", SERIE_B: "nacional", SERIE_C: "nacional",
            TACA_BRASIL: "nacional", ROBERTAO: "nacional", COPA_BR: "nacional", LIBERTADORES: "continental",
            SULAMERICANA: "continental", RECOPA: "continental"}
INTERNATIONAL = {LIBERTADORES, SULAMERICANA, RECOPA}

ORG = "https://www.rsssf.org/"
BRA = "https://www.rsssfbrasil.com/"

_client: PoliteClient | None = None


def client() -> PoliteClient:
    global _client
    if _client is None:
        _client = PoliteClient(delay=3.0, cache_dir=config.CACHE_DIR / "rsssf")
    return _client


def decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


# Algumas páginas da RSSSF Brasil (Carioca 2001-2006) trazem o caractere de substituição U+FFFD no
# lugar de letras acentuadas — defeito do próprio arquivo publicado. Só se restauram palavras com
# uma única leitura possível.
_FFFD_WORDS = {"Am\ufffdrica": "América", "S\ufffdo": "São", "Crist\ufffdv\ufffdo": "Cristóvão",
               "Petr\ufffdpolis": "Petrópolis", "Igua\ufffdu": "Iguaçu", "J\ufffdlio": "Júlio",
               "C\ufffdsar": "César", "F\ufffdbio": "Fábio", "al\ufffdm": "além", "Ta\ufffda": "Taça"}


def to_text(page: str) -> str:
    """HTML -> texto: remove scripts/estilos e tags, decodifica entidades."""
    page = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", page)
    page = re.sub(r"(?i)<br\s*/?>|</?(p|div|tr|li|h\d|pre|table|hr)\b[^>]*>", "\n", page)
    page = re.sub(r"<[^>]+>", "", page)
    page = html.unescape(page).replace("\r", "").replace("\xa0", " ").lstrip("﻿")
    if "\ufffd" in page:
        page = re.sub(r"\w*\ufffd[\w\ufffd]*", lambda m: _FFFD_WORDS.get(m.group(0), m.group(0)), page)
    return page


def fetch_text(url: str) -> str:
    return to_text(decode(client().get_bytes(url, use_cache=True)))


# --------------------------------------------------------------------------- páginas
@dataclass(frozen=True)
class Page:
    url: str
    year: int
    competition: str                 # competição padrão da página
    default_state: str | None = None
    sections: str | None = None      # regra de seções: "brasileiro" | "cup_only" | "a_and_cup"
    season_from_dates: bool = False  # Recopa: temporada = ano em que foi disputada


def _yy(y: int) -> str:
    return f"{y % 100:02d}"


def pages(parts: set[str] | None = None) -> list[Page]:
    want = parts or {"carioca", "brasileiro", "copa_do_brasil", "libertadores", "sulamericana", "recopa"}
    out: list[Page] = []
    if "carioca" in want:
        out += [Page(f"{BRA}tablesr/rj{y}.htm", y, CARIOCA, "RJ") for y in range(1906, 2025)]
        out.append(Page(f"{BRA}tablesr/rj1979s.htm", 1979, CARIOCA, "RJ"))
    if "brasileiro" in want:
        out += [Page(f"{ORG}tablesb/brazcup{_yy(y)}.html", y, TACA_BRASIL) for y in range(1959, 1969)]
        out += [Page(f"{ORG}tablesb/braz{_yy(y)}.html", y, ROBERTAO) for y in range(1967, 1971)]
        out += [Page(f"{ORG}tablesb/braz{_yy(y)}.html", y, SERIE_A, sections="brasileiro")
                for y in range(1971, 2003) if y != 2000]
        out.append(Page(f"{ORG}tablesb/braz-joao00.html", 2000, SERIE_A, sections="brasileiro"))
        out.append(Page(f"{ORG}tablesb/braz3-99.html", 1999, SERIE_C))
        out.append(Page(f"{ORG}tablesb/braz2025.html", 2025, SERIE_A, sections="a_only"))
    if "copa_do_brasil" in want:
        out += [Page(f"{ORG}tablesb/brazcup{_yy(y)}.html", y, COPA_BR) for y in range(1989, 2010)]
        out += [Page(f"{ORG}tablesb/braz{y}.html", y, COPA_BR, sections="cup_only") for y in range(2010, 2026)]
    if "libertadores" in want:
        out += [Page(f"{ORG}sacups/copa{_yy(y)}.html", y, LIBERTADORES) for y in range(1960, 2010)]
        out += [Page(f"{ORG}sacups/copa{y}.html", y, LIBERTADORES) for y in (2010, 2011)]
    if "sulamericana" in want:
        out += [Page(f"{ORG}sacups/sudamcup{_yy(y)}.html", y, SULAMERICANA) for y in range(2002, 2010)]
        out += [Page(f"{ORG}sacups/sudamcup{y}.html", y, SULAMERICANA) for y in (2010, 2011)]
    if "recopa" in want:
        old = [1970, 1988, 1989, 1991, 1992, 1993, 1994, 1995, 1996]
        out += [Page(f"{ORG}sacups/recopa{_yy(y)}.html", y, RECOPA, season_from_dates=True) for y in old]
        out += [Page(f"{ORG}sacups/recopa{_yy(y)}.html", y, RECOPA, season_from_dates=True)
                for y in range(2002, 2010)]
        out += [Page(f"{ORG}sacups/recopa{y}.html", y, RECOPA, season_from_dates=True) for y in range(2010, 2026)]
    return out


# --------------------------------------------------------------------------- seções
_H_SKIP = re.compile(r"(?i)libertadores|conmebol|mercosu[lr]|sul-?americana|sudamericana|supercopa|"
                     r"copa dos campe|qualification|torneio in[ií]cio|playoff for|relegation playoff")
_H_A_FORCE = re.compile(r"(?i)ta[cç]a de ouro|copa jo[ãa]o havelange|m[óo]dulo (azul|verde)")
_H_B = re.compile(r"(?i)second (division|level)|2nd (division|level)|s[ée]rie b\b|ta[cç]a de prata|segunda divis|"
                  r"m[óo]dulo amarelo")
_H_C = re.compile(r"(?i)third (division|level)|3rd (division|level)|s[ée]rie c\b|terceira divis")
_H_CUP = re.compile(r"(?i)\bcup\b|copa do brasil")
_H_A = re.compile(r"(?i)championship\b|s[ée]rie a\b|first (division|level)|1st (division|level)|campeonato brasileiro")


# Frases explicativas ("Teams qualified from Taça de Prata...", "X were promoted to Série A") não são títulos.
_H_SENTENCE = re.compile(r"(?i)\b(were|was|are|is|will|qualif\w*|classified|relegat\w*|rebaixad\w*|promoted|"
                         r"eliminated|selected|disqualified|losers|winners?|champions|teams?|clubs?|berths?|"
                         r"due to|for second|whose|th in)\b")


def _heading_kind(line: str) -> str | None:
    if line[:1] in " \t":                     # recuado: texto corrido ou item de lista, não título
        return None
    s = line.strip()
    if not s or len(s) > 80 or re.search(r"\d+\s?-\s?\d+", s) or s[:1] in "[(":
        return None
    if re.match(r"(?i)^(list of|overview|\d{4}\s*\()", s) or s.endswith("."):
        return None
    core = s.lstrip("* ").strip()
    if not core or core[:1].islower() or re.match(r"^\d+\s*[.)]", core) or _H_SENTENCE.search(core):
        return None
    if _H_SKIP.search(s):
        return "skip"
    if _H_A_FORCE.search(s):
        return "A"
    if _H_B.search(s):
        return "B"
    if _H_C.search(s):
        return "C"
    if _H_CUP.search(s):
        return "CUP"
    if _H_A.search(s):
        return "A"
    return None


def flu_division(year: int) -> str:
    """Divisão do Campeonato Brasileiro em que o Fluminense jogou (fato histórico, até 2002):
    Série A em todas as edições, exceto 1998 (Série B) e 1999 (Série C). Usado para descartar
    seções de outras divisões — onde jogam homônimos como o Fluminense de Feira de Santana-BA."""
    return {1998: SERIE_B, 1999: SERIE_C}.get(year, SERIE_A)


def split_sections(text: str, rule: str | None, default: str, year: int | None = None) -> list[tuple[str, str]]:
    """Divide a página em (competição, texto). Seções sem competição definida são descartadas.
    Com `year` (regra "brasileiro"), só a seção da divisão do Fluminense naquele ano é mantida."""
    if rule is None:
        return [(default, text)]
    comp_for = {"brasileiro": {"A": SERIE_A, "B": SERIE_B, "C": SERIE_C, "CUP": None, "skip": None},
                "cup_only": {"A": None, "B": None, "C": None, "CUP": COPA_BR, "skip": None},
                "a_only": {"A": SERIE_A, "B": None, "C": None, "CUP": None, "skip": None}}[rule]
    current = default if rule == "brasileiro" else None
    out: list[tuple[str | None, list[str]]] = [(current, [])]
    for line in text.split("\n"):
        kind = _heading_kind(line)
        if kind == "skip" and rule != "brasileiro":
            kind = None          # nas páginas de copa, menção à Libertadores não encerra a seção
        if kind:
            current = comp_for[kind]
            out.append((current, []))
        out[-1][1].append(line)
    merged: dict[str, list[str]] = defaultdict(list)
    keep = flu_division(year) if (rule == "brasileiro" and year and year <= 2002) else None
    for comp, lines in out:
        if comp and (keep is None or comp == keep):
            merged[comp].extend(lines + [""])
    return [(comp, "\n".join(lines)) for comp, lines in merged.items()]


# --------------------------------------------------------------------------- registros
_COUNTRY_NAMES: dict[str, str] | None = None


def _country_code(name: str | None) -> str | None:
    """'Brazil' / 'Ecuador' (como escrito na página) -> ISO2, pela tabela de países do banco."""
    global _COUNTRY_NAMES
    if not name:
        return None
    if _COUNTRY_NAMES is None:
        from database.connection import query_all
        _COUNTRY_NAMES = {}
        for r in query_all("SELECT iso2, name_en, name_pt FROM countries"):
            for n in (r["name_en"], r["name_pt"]):
                if n:
                    _COUNTRY_NAMES[norm(n)] = r["iso2"]
        _COUNTRY_NAMES.update({"usa": "US", "england": "GB", "scotland": "GB", "korea republic": "KR",
                               "south korea": "KR", "uae": "AE", "holland": "NL"})
    return _COUNTRY_NAMES.get(norm(name))


_TABLE_QUAL =re.compile(r"^\s*\d{1,2}\s*[.-]\s*([^\d()\n]+?)\s*\(([^()\d\n]{2,40})\)\s+\d")


def page_qualifiers(text: str) -> dict[str, str]:
    """Nome curto -> nome com cidade, a partir das tabelas da própria página.

    Ex.: " 3.Nacional (Montevideo)   6  2 ..." -> {"Nacional": "Nacional (Montevideo)"}. Usado para
    identificar clubes estrangeiros homônimos nas copas internacionais.
    """
    out: dict[str, str] = {}
    for line in text.split("\n"):
        m = _TABLE_QUAL.match(line)
        if m:
            out.setdefault(m.group(1).strip(), f"{m.group(1).strip()} ({m.group(2).strip()})")
    return out


# "AMÉRICA Futebol Clube (Rio de Janeiro-GB)", "Clube Atlético BRAGANTINO (Bragança Paulista-SP)",
# "FLUMINENSE Futebol Clube (Rio de Janeiro RJ)"
_PARTICIPANT = re.compile(r"^\s*(?:[A-Za-zÀ-ÿ'.]+\s+)*?([A-ZÀ-Ý][A-ZÀ-Ý'.]{2,}(?:\s+(?:DE|DA|DO|DOS|[A-ZÀ-Ý][A-ZÀ-Ý'.]+))*)"
                          r"(?:\s+[^()\n]*)?\s*\([^()\n]*?[-,\s]\s*([A-Z]{2})\s*\)\s*$")


def national_qualifiers(text: str) -> dict[str, str]:
    """Clubes que a página escreve sem estado ("América") mas identifica na lista de participantes
    ("AMÉRICA Futebol Clube (Rio de Janeiro-GB)"). Só vale quando a lista aponta um único estado para
    aquele nome. A classificação não serve de prova: nela "Internacional" (RS) convive com
    "Internacional-SP". -> {nome normalizado: UF}"""
    from collectors.teams import UFS
    part: dict[str, set[str]] = defaultdict(set)
    for line in text.split("\n"):
        pm = _PARTICIPANT.match(line)
        if pm:
            uf = "RJ" if pm.group(2) == "GB" else pm.group(2)       # GB: estado da Guanabara (1960-1975)
            if uf in UFS:
                part[norm(pm.group(1))].add(uf)
    if part.get("fluminense") != {"RJ"}:
        return {}          # lista parcial (ex.: só os promovidos da Taça de Prata) não identifica ninguém
    return {k: next(iter(v)) for k, v in part.items() if len(v) == 1}


def _canon(namer: TeamNamer, raw: str, state: str | None, country: str | None, intl: bool,
           quals: dict[str, str], nquals: dict[str, str] | None = None) -> tuple[str, str | None, str | None]:
    if nquals and not intl and state is None:
        from collectors.teams import split_name
        if split_name(raw)[1] is None and (uf := nquals.get(norm(raw.strip()))):
            raw = f"{raw.strip()}-{uf}"
    if intl and country is None and raw.strip() in quals:
        name, uf, cc = namer.canonical(quals[raw.strip()], None, None, international=True)
        if cc and cc != "BR":
            return name, uf, cc
    return namer.canonical(raw, state, country, international=intl)


def to_record(pm: ParsedMatch, page: Page, comp: str, namer: TeamNamer,
              quals: dict[str, str] | None = None, nquals: dict[str, str] | None = None) -> MatchRecord:
    intl = comp in INTERNATIONAL
    state = None if intl else page.default_state
    quals = quals or {}
    home, hs, hc = _canon(namer, pm.home, state, pm.home_country or (None if intl else "BR"), intl, quals, nquals)
    away, as_, ac = _canon(namer, pm.away, state, pm.away_country or (None if intl else "BR"), intl, quals, nquals)
    venue_cc = _country_code(pm.venue_country)
    if venue_cc:
        # A página informa o país do local (ex.: "Second leg [Feb 29, Maracanã, Rio de Janeiro, Brazil, ...]").
        country, cstatus = venue_cc, "nao_verificado"
    elif intl:
        # País da partida = país do mandante (inferido); desconhecido se o país do clube não é conhecido.
        country, cstatus = (hc, "inferido") if hc else (None, "nao_verificado")
    else:
        country, cstatus = "BR", "inferido"
    season = pm.date[:4] if page.season_from_dates else str(page.year)
    events = [EventRecord("gol_contra" if k == "gol_contra" else k, side, name, minute)
              for side, name, minute, k in pm.scorers]
    raw = repr((comp, pm.date, home, away, pm.home_goals, pm.away_goals, pm.home_pens, pm.away_pens,
                pm.stadium, pm.city, pm.referee, pm.attendance, pm.venue_country, pm.stage, pm.round, pm.scorers))
    return MatchRecord(
        source_code=SOURCE, source_ref=f"{page.url}#{pm.date}|{home}|{away}", date=pm.date,
        home_team=home, away_team=away, home_state=hs, away_state=as_, home_country=hc, away_country=ac,
        home_goals=pm.home_goals, away_goals=pm.away_goals,
        home_penalties=pm.home_pens, away_penalties=pm.away_pens,
        competition=comp, competition_category=CATEGORY[comp], season=season,
        stage=pm.stage, round=pm.round, stadium=pm.stadium, city=pm.city, attendance=pm.attendance,
        # Árbitro só quando a ficha do jogo na página o nomeia explicitamente.
        referee=pm.referee, referee_status="confirmado" if pm.referee else "nao_identificado",
        country_iso2=country, country_status=cstatus, url=page.url, reliability="media",
        events=events, row_hash=hashlib.sha1(raw.encode()).hexdigest())


@dataclass
class PageReport:
    page: Page
    records: list[MatchRecord]
    undated: list[str]
    unparsed: list[str]
    ambiguous: list[str]
    error: str | None = None


def _flu_score(r: MatchRecord) -> tuple[int | None, int | None]:
    """(gols do Fluminense, gols do adversário) — independe de quem a linha pôs como mandante."""
    return (r.home_goals, r.away_goals) if r.home_team == "Fluminense" else (r.away_goals, r.home_goals)


def _same_match_key(recs: list[MatchRecord], rec: MatchRecord) -> MatchRecord | None:
    """Registro da mesma página contra o mesmo adversário, mesma competição, até 3 dias de diferença."""
    from datetime import date as _d
    opp = rec.away_team if rec.home_team == "Fluminense" else rec.home_team
    d0 = _d.fromisoformat(rec.date)
    near = [r for r in recs if r.competition == rec.competition
            and (r.away_team if r.home_team == "Fluminense" else r.home_team) == opp
            and abs((_d.fromisoformat(r.date) - d0).days) <= 3]
    return near[0] if len(near) == 1 else None


def read_page(page: Page, namer: TeamNamer) -> PageReport:
    try:
        text = fetch_text(page.url)
    except Exception as e:  # noqa: BLE001 — página ausente (404) não derruba a coleta
        return PageReport(page, [], [], [], [], error=f"{type(e).__name__}: {e}"[:200])
    recs: list[MatchRecord] = []
    und: list[str] = []
    unp: list[str] = []
    amb: list[str] = []
    seen: set[str] = set()
    quals = page_qualifiers(text)
    # "Recopa 2023 — NB: played 2024": o ano-base das datas é o da disputa.
    played = re.search(r"(?i)\bNB\s*:?\s*played\s+((?:19|20)\d\d)\b", text[:800])
    base_year = int(played.group(1)) if played else page.year
    for comp, chunk in split_sections(text, page.sections, page.competition, page.year):
        nquals = national_qualifiers(chunk) if page.default_state is None else {}
        res = parse_page(chunk, base_year, page.default_state, national=comp not in INTERNATIONAL
                         and comp != CARIOCA)
        und += res.undated
        unp += res.unparsed
        amb += res.ambiguous
        for pm in res.matches:
            rec = to_record(pm, page, comp, namer, quals, nquals)
            prev = None
            if rec.source_ref in seen:          # mesmo jogo listado duas vezes na página (lista + ficha)
                prev = next(r for r in recs if r.source_ref == rec.source_ref)
            else:
                prev = _same_match_key(recs, rec)
                if prev is not None and not (pm.from_sheet and _flu_score(prev) == _flu_score(rec)):
                    prev = None
                elif prev is not None and prev.date != rec.date:
                    # Ficha e lista da mesma página com datas próximas e mesmo placar: um só jogo.
                    # Fica a data da lista; a divergência é registrada para conferência.
                    amb.append(f"lista e ficha divergem na data: {prev.date} × {rec.date} "
                               f"({prev.home_team} x {prev.away_team}); mantida a da lista")
            if prev is not None:
                if _flu_score(prev) == _flu_score(rec):
                    for f in ("stadium", "city", "referee", "attendance", "events", "stage", "round",
                              "home_penalties", "away_penalties"):
                        if not getattr(prev, f) and getattr(rec, f):
                            setattr(prev, f, getattr(rec, f))
                    if rec.referee:
                        prev.referee_status = rec.referee_status
                    if rec.country_status == "nao_verificado" and rec.country_iso2:   # país dito pela página
                        prev.country_iso2, prev.country_status = rec.country_iso2, rec.country_status
                    prev.row_hash = hashlib.sha1((prev.row_hash + rec.row_hash).encode()).hexdigest()
                    continue
                amb.append(f"placares diferentes na mesma página: {prev.home_goals}-{prev.away_goals} × "
                           f"{rec.home_goals}-{rec.away_goals} ({rec.date} {rec.home_team} x {rec.away_team})")
                continue
            seen.add(rec.source_ref)
            recs.append(rec)
    return PageReport(page, recs, und, unp, amb)


def dry_run(parts: set[str] | None = None, namer: TeamNamer | None = None) -> list[PageReport]:
    """Lê as páginas sem gravar nada (para conferência)."""
    from database.connection import connect
    if namer is None:
        with connect() as c:
            namer = TeamNamer.from_db(c)
    return [read_page(p, namer) for p in pages(parts)]


def collect(parts: set[str] | None = None) -> dict:
    def work(c: Conn, counts: Counter, messages: list[str]) -> None:
        namer = TeamNamer.from_db(c)
        for page in pages(parts):
            rep = read_page(page, namer)
            if rep.error:
                if "404" not in rep.error:
                    messages.append(f"{page.url}: {rep.error}")
                continue
            for rec in rep.records:
                v = validate_match(rec)
                if not v.ok:
                    counts["rejected"] += 1
                    messages.append(f"[{rec.source_ref}] rejeitado: {'; '.join(v.errors)}")
                    continue
                status, _ = upsert_match(c, rec)
                counts[status] += 1
            counts["sem_data"] += len(rep.undated)
            for line in rep.undated[:3]:
                messages.append(f"{page.url}: sem data exata — {line.strip()[:90]}")
            for line in rep.unparsed[:3]:
                messages.append(f"{page.url}: linha não reconhecida — {line.strip()[:90]}")
            c.commit()
    return run_collector("rsssf", SOURCE, work)
