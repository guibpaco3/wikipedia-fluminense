"""Migrações versionadas.

Cada arquivo `database/migrations/NNN_nome.sql` é aplicado uma única vez, em ordem,
e registrado em `schema_migrations`. Para evoluir o esquema basta adicionar um novo
arquivo — nunca editar um já aplicado.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from core import config
from database.connection import Conn, connect, is_sqlite

log = config.get_logger("migrations")


def _fts5_available(c: Conn) -> bool:
    try:
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts_probe USING fts5(x)")
        c.execute("DROP TABLE _fts_probe")
        return True
    except Exception:
        return False


def _ensure_search_index(c: Conn) -> None:
    """Índice de busca global (FTS5, sem acentos). Recriado sem custo se já existir."""
    if not is_sqlite():  # pragma: no cover
        return
    if _fts5_available(c):
        c.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5("
            "entity_type UNINDEXED, entity_id UNINDEXED, title, subtitle, body, "
            "tokenize = 'unicode61 remove_diacritics 2')"
        )
    else:
        c.execute(
            "CREATE TABLE IF NOT EXISTS search_index (entity_type TEXT, entity_id INTEGER, "
            "title TEXT, subtitle TEXT, body TEXT)"
        )


def _seed_reference(c: Conn) -> None:
    """Dados de referência geográfica (Natural Earth, domínio público)."""
    if c.scalar("SELECT COUNT(*) FROM countries"):
        return
    data = json.loads((config.REFERENCE_DIR / "countries.json").read_text(encoding="utf-8"))
    c.executemany(
        "INSERT INTO countries (iso2, iso3, name_pt, name_en, continent, lat, lon) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(d["iso2"], d["iso3"], d["name_pt"], d["name_en"], d["continent"], d["lat"], d["lon"])
         for d in data.values()],
    )


def migrate() -> list[str]:
    """Aplica as migrações pendentes. Retorna os nomes aplicados."""
    applied: list[str] = []
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT)")
        done = {r["name"] for r in c.all("SELECT name FROM schema_migrations")}
        for path in sorted(config.MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            log.info("Aplicando migração %s", path.name)
            c.executescript(path.read_text(encoding="utf-8"))
            c.execute("INSERT INTO schema_migrations VALUES (?, ?)",
                      (path.name, datetime.now(timezone.utc).isoformat(timespec="seconds")))
            applied.append(path.name)
        _ensure_search_index(c)
        _seed_reference(c)
    return applied


if __name__ == "__main__":
    print(migrate() or "Banco já atualizado.")
