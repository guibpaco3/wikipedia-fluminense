"""Coletor do Wikidata (CC0) via SPARQL e API de busca.

Tudo o que vem daqui entra com confiabilidade "média" e status "não verificado":
o Wikidata é colaborativo e deve ser revisado no painel.

Coletas:
- titles():   edições de competições cujo vencedor (P1346) é o Fluminense (Q80987).
- players():  pessoas com vínculo "membro do time esportivo" (P54) com o clube.
- coaches():  técnicos (P286) registrados no item do clube, com período.
- stadiums(): geolocalização (cidade, coordenadas, capacidade) dos estádios da base.
"""
from __future__ import annotations

import re
from collections import Counter

from collectors.base import run_collector
from collectors.http import PoliteClient
from core import config
from core.text import norm
from database.connection import Conn
from database.repository import (record_field, resolve_city, resolve_competition, resolve_edition,
                                 resolve_person, source_id)

SOURCE = "wikidata"
SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
CLUB = config.FLUMINENSE_WIKIDATA
ENTITY = "https://www.wikidata.org/wiki/"

log = config.get_logger("wikidata")
_client: PoliteClient | None = None


def client() -> PoliteClient:
    global _client
    if _client is None:
        _client = PoliteClient(delay=1.0)
    return _client


def sparql(query: str) -> list[dict]:
    data = client().get_json(SPARQL, params={"query": query, "format": "json"},
                             headers={"Accept": "application/sparql-results+json"})
    return [{k: v["value"] for k, v in row.items()} for row in data["results"]["bindings"]]


def qid(uri: str | None) -> str | None:
    return uri.rsplit("/", 1)[-1] if uri else None


def day(ts: str | None) -> str | None:
    """'1984-05-27T00:00:00Z' -> '1984-05-27' (datas só com ano viram 'AAAA')."""
    if not ts:
        return None
    m = re.match(r"^(-?\d{4})-(\d{2})-(\d{2})", ts)
    if not m:
        return None
    y, mo, d = m.groups()
    if mo == "01" and d == "01":
        return y  # Wikidata usa 01-01 para precisão anual; não inventamos dia/mês
    return f"{y}-{mo}-{d}"


LABEL = 'SERVICE wikibase:label { bd:serviceParam wikibase:language "pt-br,pt,en". }'

YOUTH = re.compile(r"j[úu]nior|juniores|sub-?\d+|juvenil|base|feminin|women|u-?\d{2}\b", re.I)


def categorize(name: str) -> str:
    n = norm(name)
    if any(k in n for k in ("libertadores", "sul americana", "recopa", "conmebol", "copa mercosul",
                             "supercopa")):
        return "continental"
    if any(k in n for k in ("mundial", "intercontinental", "copa do mundo de clubes", "rio cup",
                             "torneio internacional")):
        return "mundial"
    if any(k in n for k in ("brasileir", "copa do brasil", "taca brasil", "torneio roberto gomes pedrosa",
                             "rio sao paulo", "serie c")):
        return "nacional"
    if any(k in n for k in ("carioca", "guanabara", "taca rio", "fluminense de futebol", "metropolitano")):
        return "estadual"
    if "amistos" in n or "verao" in n:
        return "amistoso"
    return "outro"


def competition_name(edition_label: str, series_label: str | None) -> str:
    if series_label:
        return series_label
    name = re.sub(r"\b(de|of)?\s*\d{4}(\s*[-–/]\s*\d{2,4})?\b", "", edition_label).strip(" -–")
    return re.sub(r"\s{2,}", " ", name)


# ---------------------------------------------------------------- títulos
def titles(c: Conn, counts: Counter, messages: list[str]) -> None:
    rows = sparql(f"""
SELECT ?s ?sLabel ?series ?seriesLabel ?sport ?point ?start ?end WHERE {{
  ?s wdt:P1346 wd:{CLUB} .
  OPTIONAL {{ ?s wdt:P3450 ?series }}
  OPTIONAL {{ ?s wdt:P641 ?sport }}
  OPTIONAL {{ ?s wdt:P585 ?point }} OPTIONAL {{ ?s wdt:P580 ?start }} OPTIONAL {{ ?s wdt:P582 ?end }}
  {LABEL}
}}""")
    src = source_id(c, SOURCE)
    seen = set()
    for r in rows:
        wid = qid(r["s"])
        if wid in seen:
            continue
        seen.add(wid)
        label = r.get("sLabel", wid)
        if re.match(r"^(Final|Finais|Partida final)\s", label, re.I):
            counts["ignored_final_item"] += 1  # item da partida final, não do título
            continue
        if r.get("sport") and qid(r["sport"]) != "Q2736":  # Q2736 = futebol
            counts["ignored_other_sport"] += 1
            continue
        comp = competition_name(label, r.get("seriesLabel"))
        years = re.findall(r"\b(1[89]\d{2}|20\d{2})\b", label)
        season = years[0] if years else (day(r.get("end") or r.get("point") or r.get("start")) or "")[:4]
        scope = "base" if YOUTH.search(label) else "profissional"
        series = qid(r.get("series"))
        comp_id = c.scalar("SELECT id FROM competitions WHERE wikidata_id = ?", (series,)) if series else None
        if comp_id is None:
            comp_id = resolve_competition(c, comp, categorize(comp))
        c.execute("UPDATE competitions SET scope = ?, wikidata_id = COALESCE(wikidata_id, ?) WHERE id = ?",
                  (scope, series, comp_id))
        ed_id = resolve_edition(c, comp_id, season) if season else None
        if ed_id:
            c.execute("UPDATE competition_editions SET name = COALESCE(name, ?), wikidata_id = ? WHERE id = ?",
                      (label, wid, ed_id))
        existing = c.scalar("SELECT id FROM titles WHERE wikidata_id = ?", (wid,))
        if existing:
            c.execute("UPDATE titles SET name=?, competition_id=?, edition_id=?, season=? WHERE id=?",
                      (label, comp_id, ed_id, season, existing))
            counts["updated"] += 1
            tid = existing
        else:
            tid = c.insert("INSERT INTO titles (competition_id, edition_id, season, name, wikidata_id, "
                           "reliability) VALUES (?, ?, ?, ?, ?, 'media')",
                           (comp_id, ed_id, season, label, wid))
            counts["inserted"] += 1
        record_field(c, "title", tid, "winner", "Fluminense", src, wid, ENTITY + wid)
    messages.append(f"Títulos: {len(seen)} registros (P1346) lidos.")


# ---------------------------------------------------------------- jogadores
def players(c: Conn, counts: Counter, messages: list[str]) -> None:
    rows = sparql(f"""
SELECT ?p ?pLabel ?start ?end ?birth ?death ?iso ?posLabel ?img WHERE {{
  ?p p:P54 ?st . ?st ps:P54 wd:{CLUB} .
  OPTIONAL {{ ?st pq:P580 ?start }} OPTIONAL {{ ?st pq:P582 ?end }}
  OPTIONAL {{ ?p wdt:P569 ?birth }} OPTIONAL {{ ?p wdt:P570 ?death }}
  OPTIONAL {{ ?p wdt:P1532 ?sportNat . ?sportNat wdt:P297 ?iso }}
  OPTIONAL {{ ?p wdt:P27 ?nat . ?nat wdt:P297 ?iso }}
  OPTIONAL {{ ?p wdt:P413 ?pos }}
  OPTIONAL {{ ?p wdt:P18 ?img }}
  {LABEL}
}}""")
    src = source_id(c, SOURCE)
    by_person: dict[str, dict] = {}
    for r in rows:
        wid = qid(r["p"])
        d = by_person.setdefault(wid, {"name": r.get("pLabel", wid), "spells": set(), "pos": set(),
                                       "birth": r.get("birth"), "death": r.get("death"),
                                       "iso": r.get("iso"), "img": r.get("img")})
        d["spells"].add((day(r.get("start")), day(r.get("end"))))
        if r.get("posLabel"):
            d["pos"].add(r["posLabel"])
    for wid, d in by_person.items():
        if re.fullmatch(r"Q\d+", d["name"]):
            continue  # sem rótulo legível
        pid = resolve_person(c, d["name"], "jogador", wikidata_id=wid)
        row = c.one("SELECT wikidata_id FROM people WHERE id = ?", (pid,))
        if row["wikidata_id"] not in (None, wid):
            # homônimo já ligado a outro item: cria cadastro próprio
            pid = c.insert("INSERT INTO people (name, name_norm, wikidata_id) VALUES (?, ?, ?)",
                           (d["name"], norm(d["name"]), wid))
        iso = d["iso"] if d["iso"] and c.scalar("SELECT 1 FROM countries WHERE iso2 = ?", (d["iso"],)) else None
        c.execute(
            "UPDATE people SET wikidata_id = COALESCE(wikidata_id, ?), birth_date = COALESCE(birth_date, ?), "
            "death_date = COALESCE(death_date, ?), nationality_iso2 = COALESCE(nationality_iso2, ?), "
            "position = COALESCE(position, ?), photo_url = COALESCE(photo_url, ?) WHERE id = ?",
            (wid, day(d["birth"]), day(d["death"]), iso, ", ".join(sorted(d["pos"])) or None, d["img"], pid))
        for start, end in d["spells"]:
            c.execute("INSERT OR IGNORE INTO player_spells (person_id, start_date, end_date, notes) "
                      "VALUES (?, ?, ?, 'Wikidata')", (pid, start, end))
        record_field(c, "person", pid, "player_spell", "Fluminense", src, wid, ENTITY + wid)
        counts["players"] += 1
    messages.append(f"Jogadores: {len(by_person)} pessoas com vínculo P54.")


# ---------------------------------------------------------------- técnicos
def coaches(c: Conn, counts: Counter, messages: list[str]) -> None:
    rows = sparql(f"""
SELECT ?p ?pLabel ?start ?end ?birth ?iso WHERE {{
  wd:{CLUB} p:P286 ?st . ?st ps:P286 ?p .
  OPTIONAL {{ ?st pq:P580 ?start }} OPTIONAL {{ ?st pq:P582 ?end }}
  OPTIONAL {{ ?p wdt:P569 ?birth }} OPTIONAL {{ ?p wdt:P27 ?nat . ?nat wdt:P297 ?iso }}
  {LABEL}
}}""")
    src = source_id(c, SOURCE)
    for r in rows:
        wid = qid(r["p"])
        pid = resolve_person(c, r.get("pLabel", wid), "tecnico", wikidata_id=wid)
        c.execute("UPDATE people SET wikidata_id = COALESCE(wikidata_id, ?), birth_date = COALESCE(birth_date, ?) "
                  "WHERE id = ?", (wid, day(r.get("birth")), pid))
        c.execute("INSERT OR IGNORE INTO coach_spells (person_id, start_date, end_date, notes) "
                  "VALUES (?, ?, ?, 'Wikidata')", (pid, day(r.get("start")), day(r.get("end"))))
        record_field(c, "person", pid, "coach_spell", f"{day(r.get('start'))}–{day(r.get('end'))}",
                     src, wid, ENTITY + wid)
        counts["coaches"] += 1
    messages.append(f"Técnicos: {len(rows)} passagens (P286).")


# ---------------------------------------------------------------- estádios
STADIUM_CLASSES = "wd:Q483110 wd:Q1076486 wd:Q19882233 wd:Q24742964"  # estádio, recinto esportivo...


def _search(name: str) -> list[str]:
    data = client().get_json(API, params={"action": "wbsearchentities", "search": name, "language": "pt",
                                          "uselang": "pt", "type": "item", "limit": 5, "format": "json"})
    return [e["id"] for e in data.get("search", [])]


def stadiums(c: Conn, counts: Counter, messages: list[str], limit: int | None = None) -> None:
    pending = c.all("SELECT id, name, country_iso2 FROM stadiums WHERE wikidata_id IS NULL ORDER BY id")
    if limit:
        pending = pending[:limit]
    src = source_id(c, SOURCE)
    for st in pending:
        query_name = re.sub(r"\s*[-|(].*$", "", st["name"]).strip() or st["name"]
        candidates = _search(query_name)
        if not candidates and not query_name.lower().startswith("est"):
            candidates = _search("Estádio " + query_name)
        if not candidates:
            counts["stadium_not_found"] += 1
            continue
        values = " ".join(f"wd:{q}" for q in candidates)
        rows = sparql(f"""
SELECT ?s ?sLabel ?coord ?iso ?city ?cityLabel ?cap WHERE {{
  VALUES ?s {{ {values} }}
  ?s wdt:P31/wdt:P279* ?cls . VALUES ?cls {{ {STADIUM_CLASSES} }}
  ?s wdt:P625 ?coord .
  OPTIONAL {{ ?s wdt:P17 ?ctry . ?ctry wdt:P297 ?iso }}
  OPTIONAL {{ ?s wdt:P131 ?city }}
  OPTIONAL {{ ?s wdt:P1083 ?cap }}
  {LABEL}
}}""")
        order = {q: i for i, q in enumerate(candidates)}
        rows = [r for r in rows if not st["country_iso2"] or r.get("iso") in (None, st["country_iso2"])]
        if not rows:
            counts["stadium_not_found"] += 1
            continue
        best = min(rows, key=lambda r: order.get(qid(r["s"]), 99))
        m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", best["coord"])
        lon, lat = (float(m.group(1)), float(m.group(2))) if m else (None, None)
        wid = qid(best["s"])
        if c.scalar("SELECT id FROM stadiums WHERE wikidata_id = ? AND id <> ?", (wid, st["id"])):
            # outro nome do mesmo estádio já resolvido: vira apelido dele
            keep = c.scalar("SELECT id FROM stadiums WHERE wikidata_id = ?", (wid,))
            c.execute("UPDATE stadium_aliases SET stadium_id = ? WHERE stadium_id = ?", (keep, st["id"]))
            c.execute("UPDATE matches SET stadium_id = ? WHERE stadium_id = ?", (keep, st["id"]))
            c.execute("DELETE FROM stadiums WHERE id = ?", (st["id"],))
            counts["stadium_merged"] += 1
            c.commit()
            continue
        city_id = None
        if best.get("cityLabel") and not re.fullmatch(r"Q\d+", best["cityLabel"]):
            city_id = resolve_city(c, best["cityLabel"], None, best.get("iso") or st["country_iso2"],
                                   wikidata_id=qid(best.get("city")))
        cap = None
        try:
            cap = int(float(best["cap"])) if best.get("cap") else None
        except ValueError:
            pass
        c.execute("UPDATE stadiums SET official_name=?, wikidata_id=?, lat=?, lon=?, city_id=COALESCE(city_id, ?), "
                  "capacity=COALESCE(capacity, ?), country_iso2=COALESCE(country_iso2, ?), "
                  "geo_status='nao_verificado' WHERE id=?",
                  (best.get("sLabel"), wid, lat, lon, city_id, cap, best.get("iso"), st["id"]))
        record_field(c, "stadium", st["id"], "geo", f"{lat},{lon}", src, wid, ENTITY + wid)
        counts["stadium_geocoded"] += 1
        c.commit()
    messages.append(f"Estádios: {len(pending)} consultados.")


def collect(parts: tuple[str, ...] = ("titles", "players", "coaches", "stadiums")) -> dict:
    fns = {"titles": titles, "players": players, "coaches": coaches, "stadiums": stadiums}

    def work(c: Conn, counts: Counter, messages: list[str]) -> None:
        for p in parts:
            fns[p](c, counts, messages)
    return run_collector("wikidata:" + ",".join(parts), SOURCE, work)
