from database.migrations import migrate
from database.repository import merge_people, resolve_person
from tests.conftest import make
from database.repository import upsert_match


def test_migrations_idempotent(db):
    assert migrate() == []
    assert db.scalar("SELECT COUNT(*) FROM countries") > 200
    names = {r["name"] for r in db.query_all("SELECT name FROM sqlite_master")}
    assert {"matches", "field_sources", "discrepancies", "v_matches", "search_index"} <= names


def test_insert_and_incremental(db):
    r = make("x1", "2020-01-01", "Fluminense", "Rival", 2, 1, row_hash="h1")
    with db.connect() as c:
        assert upsert_match(c, r)[0] == "inserted"
        assert upsert_match(c, r)[0] == "unchanged"  # mesmo hash
    assert db.scalar("SELECT COUNT(*) FROM matches") == 1
    m = db.query_one("SELECT * FROM v_matches")
    assert (m["flu_goals"], m["opp_goals"], m["result"], m["flu_side"]) == (2, 1, "V", "mandante")


def test_away_side_and_orientation(db):
    with db.connect() as c:
        upsert_match(c, make("x2", "2020-02-01", "Rival", "Fluminense", 3, 1))
    m = db.query_one("SELECT * FROM v_matches")
    assert (m["flu_side"], m["flu_goals"], m["opp_goals"], m["result"]) == ("visitante", 1, 3, "D")


def test_duplicate_from_other_source_merges_and_flags_divergence(db):
    with db.connect() as c:
        upsert_match(c, make("a", "2020-03-01", "Fluminense", "Rival", 2, 1, stadium="Maracanã"))
        status, _ = upsert_match(c, make("b", "2020-03-01", "Fluminense", "Rival", 2, 2, source_code="rsssf",
                                         attendance=50000))
    assert status == "updated"
    assert db.scalar("SELECT COUNT(*) FROM matches") == 1
    m = db.query_one("SELECT * FROM matches")
    assert m["opp_goals"] == 1                      # valor original mantido
    assert m["attendance"] == 50000                 # campo vazio preenchido
    assert m["verification_status"] == "divergente"
    d = db.query_one("SELECT * FROM discrepancies")
    assert (d["field"], d["current_value"], d["new_value"]) == ("opp_goals", "1", "2")


def test_same_source_correction_overwrites(db):
    with db.connect() as c:
        upsert_match(c, make("a", "2020-03-01", "Fluminense", "Rival", 2, 1, row_hash="1"))
        upsert_match(c, make("a", "2020-03-01", "Fluminense", "Rival", 3, 1, row_hash="2"))
    assert db.scalar("SELECT flu_goals FROM matches") == 3
    assert db.scalar("SELECT COUNT(*) FROM discrepancies") == 0


def test_match_without_fluminense_is_rejected(db):
    import pytest
    with db.connect() as c, pytest.raises(ValueError):
        upsert_match(c, make("z", "2020-01-01", "A", "B", 1, 0))


def test_merge_people(db, sample):
    with db.connect() as c:
        full = resolve_person(c, "Jogador Um Completo", "jogador")
        short = c.scalar("SELECT id FROM people WHERE name = 'Jogador Um'")
        merge_people(c, full, short, "teste")
    assert db.scalar("SELECT COUNT(*) FROM match_events WHERE person_id = ?", (full,)) == 2
    assert db.scalar("SELECT COUNT(*) FROM people WHERE name = 'Jogador Um'") == 0
