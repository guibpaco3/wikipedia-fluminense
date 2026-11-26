"""Infraestrutura comum: execução de um coletor com registro em `collection_runs`."""
from __future__ import annotations

import traceback
from collections import Counter
from typing import Callable

from core import config
from database.connection import Conn, connect
from database.repository import finish_run, set_meta, source_id, start_run, now
from collectors.sources_registry import register_sources

log = config.get_logger("collector")


def run_collector(name: str, source_code: str, fn: Callable[[Conn, Counter, list[str]], None]) -> dict:
    """Executa `fn(conn, contadores, mensagens)` numa transação, registrando a execução.

    Em caso de erro, os dados parciais são descartados (rollback) e o erro fica registrado.
    """
    with connect() as c:
        register_sources(c)
        run_id = start_run(c, source_id(c, source_code), name)
    counts: Counter = Counter()
    messages: list[str] = []
    status = "ok"
    try:
        with connect() as c:
            fn(c, counts, messages)
            set_meta(c, f"last_update:{source_code}", now())
            set_meta(c, "last_update", now())
    except Exception as exc:
        status = "erro"
        messages.insert(0, f"{type(exc).__name__}: {exc}")
        log.error("Coletor %s falhou: %s\n%s", name, exc, traceback.format_exc())
    if status == "ok" and counts.get("rejected"):
        status = "parcial"
    with connect() as c:
        finish_run(c, run_id, status, counts, "\n".join(messages[:200]))
    log.info("Coletor %s: %s %s", name, status, dict(counts))
    return {"collector": name, "status": status, **counts, "messages": messages}
