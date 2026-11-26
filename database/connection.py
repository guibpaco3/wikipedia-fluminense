"""Camada de conexão.

Toda a aplicação usa `connect()`, `query_df()`, `query_all()` e `execute()` daqui,
nunca o driver diretamente. Isso concentra as diferenças de dialeto:

- SQLite (padrão): placeholders `?`, chaves estrangeiras ativadas por PRAGMA, WAL.
- PostgreSQL (futuro): defina DATABASE_URL=postgresql://... e instale `psycopg`.
  Os placeholders `?` são convertidos para `%s`. A busca FTS5 (modules/search.py)
  tem fallback para LIKE quando FTS5 não existe.
"""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import pandas as pd

from core import config

_url = config.DATABASE_URL


def set_database_url(url: str) -> None:
    """Troca o banco em tempo de execução (usado pelos testes)."""
    global _url
    _url = url


def database_url() -> str:
    return _url


def is_sqlite() -> bool:
    return _url.startswith("sqlite:")


def sqlite_path() -> Path:
    return Path(_url.removeprefix("sqlite:///"))


def _adapt(sql: str) -> str:
    if is_sqlite():
        return sql
    return re.sub(r"\?", "%s", sql)


def _raw_connect():
    if is_sqlite():
        path = sqlite_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn
    try:  # pragma: no cover - caminho de migração futura
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Para PostgreSQL instale 'psycopg[binary]'.") from exc
    return psycopg.connect(_url, row_factory=dict_row)  # pragma: no cover


class Conn:
    """Envoltório fino que adapta o SQL ao dialeto."""

    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql: str, params: Sequence[Any] = ()):
        return self.raw.execute(_adapt(sql), tuple(params))

    def executemany(self, sql: str, seq):
        cur = self.raw.cursor()
        cur.executemany(_adapt(sql), seq)
        return cur

    def executescript(self, sql: str):
        if is_sqlite():
            return self.raw.executescript(sql)
        return self.raw.execute(sql)  # pragma: no cover

    def commit(self) -> None:
        """Confirma o trabalho parcial (coletas longas não devem bloquear o site)."""
        self.raw.commit()

    def one(self, sql: str, params: Sequence[Any] = ()) -> dict | None:
        row = self.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def all(self, sql: str, params: Sequence[Any] = ()) -> list[dict]:
        return [dict(r) for r in self.execute(sql, params).fetchall()]

    def scalar(self, sql: str, params: Sequence[Any] = ()):
        row = self.execute(sql, params).fetchone()
        if row is None:
            return None
        return row[0] if is_sqlite() else next(iter(dict(row).values()))

    def insert(self, sql: str, params: Sequence[Any] = ()) -> int:
        cur = self.execute(sql, params)
        return cur.lastrowid


@contextmanager
def connect() -> Iterator[Conn]:
    """Abre uma conexão; faz commit ao sair sem erro e rollback em caso de exceção."""
    raw = _raw_connect()
    try:
        yield Conn(raw)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def query_df(sql: str, params: Sequence[Any] = ()) -> pd.DataFrame:
    with connect() as c:
        cur = c.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        return pd.DataFrame([tuple(r) for r in cur.fetchall()], columns=cols)


def query_all(sql: str, params: Sequence[Any] = ()) -> list[dict]:
    with connect() as c:
        return c.all(sql, params)


def query_one(sql: str, params: Sequence[Any] = ()) -> dict | None:
    with connect() as c:
        return c.one(sql, params)


def scalar(sql: str, params: Sequence[Any] = ()):
    with connect() as c:
        return c.scalar(sql, params)
