"""Fixtures: banco SQLite temporário e isolado por teste.

ATENÇÃO: as partidas criadas aqui são FICTÍCIAS e servem só para testar a lógica.
Elas nunca são gravadas no banco real (data/wikipedia.db).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collectors.sources_registry import register_sources  # noqa: E402
from database import connection  # noqa: E402
from database.migrations import migrate  # noqa: E402
from database.models import EventRecord, MatchRecord  # noqa: E402
from database.repository import upsert_match  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    previous = connection.database_url()
    connection.set_database_url(f"sqlite:///{tmp_path / 'test.db'}")
    migrate()
    with connection.connect() as c:
        register_sources(c)
    yield connection
    connection.set_database_url(previous)


def make(ref: str, d: str, home: str, away: str, hg: int, ag: int, **kw) -> MatchRecord:
    kw.setdefault("source_code", "csv_import")
    return MatchRecord(source_ref=ref, date=d, home_team=home, away_team=away, home_goals=hg, away_goals=ag, **kw)


@pytest.fixture()
def sample(db):
    """Cinco partidas fictícias com cenários variados."""
    recs = [
        make("t1", "2010-05-10", "Fluminense", "Time A", 3, 0, competition="Liga Teste", season="2010",
             competition_category="nacional", stadium="Estádio X", country_iso2="BR", country_status="verificado",
             events=[EventRecord("gol", "home", "Jogador Um", 10), EventRecord("gol", "home", "Jogador Um", 50),
                     EventRecord("gol_contra", "home", "Zagueiro Rival", 70)]),
        make("t2", "2010-08-15", "Time B", "Fluminense", 2, 1, competition="Liga Teste", season="2010",
             competition_category="nacional", stadium="Estádio Y", country_iso2="AR", country_status="verificado",
             referee="Árbitro Alfa", referee_status="confirmado"),
        make("t3", "2011-08-15", "Fluminense", "Time A", 1, 1, competition="Copa Teste", season="2011",
             competition_category="continental", referee="Árbitro Alfa", referee_status="nao_confirmado"),
        make("t4", "2012-12-15", "Fluminense", "Time C", 0, 4, competition="Copa Teste", season="2012",
             competition_category="continental", country_iso2="JP", country_status="verificado"),
        make("t5", "2012-01-20", "Time A", "Fluminense", 0, 5, competition="Liga Teste", season="2012"),
    ]
    with db.connect() as c:
        for r in recs:
            upsert_match(c, r)
    return recs
