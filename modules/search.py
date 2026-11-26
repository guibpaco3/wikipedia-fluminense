"""Busca global (FTS5, insensível a acentos), com resultados por categoria.

O índice é reconstruído após cada coleta/edição (`rebuild_index`). Em bancos sem
FTS5 a busca cai para LIKE sobre a mesma tabela.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from core import config
from core.text import norm, search_terms
from database.connection import connect, query_all
from modules.statistics import score_text

log = config.get_logger("search")

CATEGORIES = {
    "match": "Partidas", "player": "Jogadores", "coach": "Treinadores", "person": "Pessoas",
    "competition": "Competições", "title": "Títulos", "stadium": "Estádios", "team": "Clubes adversários",
    "article": "Artigos históricos", "referee": "Árbitros",
}

MONTHS = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro",
          "outubro", "novembro", "dezembro"]


def _is_fts(c) -> bool:
    sql = c.scalar("SELECT sql FROM sqlite_master WHERE name = 'search_index'") or ""
    return "fts5" in sql.lower()


def rebuild_index() -> int:
    docs: list[tuple] = []
    scorers: dict[int, str] = {}
    for r in query_all("SELECT match_id, GROUP_CONCAT(player_name, ' ') AS names FROM match_events "
                       "WHERE for_fluminense = 1 AND event_type IN ('gol', 'gol_penalti') GROUP BY match_id"):
        scorers[r["match_id"]] = r["names"] or ""
    for m in query_all("SELECT * FROM v_matches"):
        d = date.fromisoformat(m["date"])
        title = f"{score_text(m)} — {m['competition'] or 'Competição não informada'} {m['season'] or ''}".strip()
        sub = f"{d:%d/%m/%Y} · {m['stadium'] or 'estádio não informado'}"
        body = " ".join(str(x) for x in (m["stage"], m["round"] and f"rodada {m['round']}", m["city"],
                                         m["country"], m["coach"], m["referee"], d.year, MONTHS[d.month - 1],
                                         "final" if (m["stage"] or "").lower().startswith("final") else "",
                                         scorers.get(m["id"]))
                        if x)
        docs.append(("match", m["id"], title, sub, body))
    roles = query_all("""
        SELECT p.id, p.name, p.full_name, p.position,
               EXISTS (SELECT 1 FROM player_spells s WHERE s.person_id = p.id)
               OR EXISTS (SELECT 1 FROM match_events e WHERE e.person_id = p.id AND e.for_fluminense = 1) AS is_player,
               EXISTS (SELECT 1 FROM coach_spells s WHERE s.person_id = p.id)
               OR EXISTS (SELECT 1 FROM matches m WHERE m.flu_coach_id = p.id) AS is_coach,
               EXISTS (SELECT 1 FROM presidencies s WHERE s.person_id = p.id) AS is_president
        FROM people p""")
    for p in roles:
        kind = "coach" if p["is_coach"] else "player" if p["is_player"] else "person"
        tags = [t for t, f in (("jogador", p["is_player"]), ("técnico treinador", p["is_coach"]),
                               ("presidente", p["is_president"])) if f]
        docs.append((kind, p["id"], p["name"], p["position"] or ", ".join(tags), f"{p['full_name'] or ''} {' '.join(tags)}"))
    for r in query_all("SELECT id, name, category FROM competitions"):
        docs.append(("competition", r["id"], r["name"], r["category"], ""))
    for r in query_all("SELECT t.id, t.name, t.season, c.name AS comp FROM titles t "
                       "LEFT JOIN competitions c ON c.id = t.competition_id WHERE t.verification_status <> 'rejeitado'"):
        docs.append(("title", r["id"], r["name"], f"Título · {r['season']}", f"{r['comp'] or ''} campeão título"))
    for r in query_all("SELECT s.id, s.name, s.official_name, ci.name AS city FROM stadiums s "
                       "LEFT JOIN cities ci ON ci.id = s.city_id"):
        docs.append(("stadium", r["id"], r["name"], r["city"] or "", r["official_name"] or ""))
    for r in query_all("SELECT id, name, full_name, state FROM teams WHERE is_fluminense = 0"):
        docs.append(("team", r["id"], r["name"], r["state"] or "", r["full_name"] or ""))
    for r in query_all("SELECT id, title, summary, body_md, category FROM articles"):
        docs.append(("article", r["id"], r["title"], r["summary"] or r["category"], r["body_md"][:5000]))
    for r in query_all("SELECT id, name FROM referees"):
        docs.append(("referee", r["id"], r["name"], "Árbitro", "arbitro"))
    with connect() as c:
        c.execute("DELETE FROM search_index")
        c.executemany("INSERT INTO search_index (entity_type, entity_id, title, subtitle, body) "
                      "VALUES (?, ?, ?, ?, ?)", docs)
    log.info("Índice de busca reconstruído: %s documentos", len(docs))
    return len(docs)


def search(query: str, limit_per_category: int = 15) -> dict[str, list[dict]]:
    terms = search_terms(query)
    if not terms:
        return {}
    with connect() as c:
        if _is_fts(c):
            fts = " AND ".join(f'"{t}"*' for t in terms)
            rows = c.all("SELECT entity_type, entity_id, title, subtitle, bm25(search_index, 0, 0, 8, 2, 1) AS rank "
                         "FROM search_index WHERE search_index MATCH ? ORDER BY rank LIMIT 600", (fts,))
        else:  # pragma: no cover
            conds = " AND ".join("(LOWER(title||' '||subtitle||' '||body) LIKE ?)" for _ in terms)
            rows = c.all(f"SELECT entity_type, entity_id, title, subtitle FROM search_index WHERE {conds} LIMIT 600",
                         [f"%{t}%" for t in terms])
    # Favorece correspondência exata do título (ex.: "Fred" antes de "Frederico ...").
    q = norm(query)
    rows.sort(key=lambda r: (norm(r["title"]) != q, r.get("rank", 0)))
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if len(grouped[r["entity_type"]]) < limit_per_category:
            grouped[r["entity_type"]].append(r)
    order = list(CATEGORIES)
    return {k: grouped[k] for k in sorted(grouped, key=order.index)}
