from core.auth import LoginGuard, hash_password, verify_password
from modules import coverage, globe, players, search
from modules.filters import KIT_UNIDENTIFIED, MatchFilter, fetch_matches
from modules.statistics import by_group, score_text, summarize


def opp(db, name):
    return db.scalar("SELECT id FROM teams WHERE name = ?", (name,))


def test_summary_numbers(sample, db):
    r = summarize(fetch_matches())
    assert (r.matches, r.wins, r.draws, r.losses, r.goals_for, r.goals_against) == (5, 2, 1, 2, 10, 7)
    assert round(r.points_pct, 1) == round(100 * 7 / 15, 1)
    assert (r.biggest_win["flu_goals"], r.biggest_win["opp_goals"]) == (5, 0)
    assert (r.biggest_loss["flu_goals"], r.biggest_loss["opp_goals"]) == (0, 4)
    assert r.last["date"] == "2012-12-15"


def test_combined_filters(sample, db):
    a = opp(db, "Time A")
    assert len(fetch_matches(MatchFilter(opponents=[a]))) == 3
    assert len(fetch_matches(MatchFilter(opponents=[a], year_from=2011))) == 2
    assert len(fetch_matches(MatchFilter(months=[8]))) == 2
    assert len(fetch_matches(MatchFilter(months=[8], day=15))) == 2
    assert len(fetch_matches(MatchFilter(months=[12], day=15, year_from=2012, year_to=2012))) == 1
    assert len(fetch_matches(MatchFilter(international=True))) == 2
    assert len(fetch_matches(MatchFilter(continents=["Ásia"]))) == 1
    comp = db.scalar("SELECT id FROM competitions WHERE name = 'Copa Teste'")
    assert len(fetch_matches(MatchFilter(competitions=[comp], opponents=[a]))) == 1


def test_referee_filter_only_confirmed_by_default(sample, db):
    ref = db.scalar("SELECT id FROM referees")
    assert len(fetch_matches(MatchFilter(referees=[ref]))) == 1
    assert len(fetch_matches(MatchFilter(referees=[ref], include_unconfirmed_referees=True))) == 2


def test_kit_never_presumed(sample, db):
    assert len(fetch_matches(MatchFilter(kits=[KIT_UNIDENTIFIED]))) == 5
    with db.connect() as c:
        k = c.insert("INSERT INTO kits (name, category) VALUES ('Tricolor', 'titular')")
        c.execute("UPDATE matches SET flu_kit_id = ? WHERE id = 1", (k,))  # sem confirmação
    assert len(fetch_matches(MatchFilter(kits=[k]))) == 0
    with db.connect() as c:
        c.execute("UPDATE matches SET kit_status = 'confirmado' WHERE id = 1")
    assert len(fetch_matches(MatchFilter(kits=[k]))) == 1
    assert len(fetch_matches(MatchFilter(kit_categories=["titular"]))) == 1
    assert len(fetch_matches(MatchFilter(kits=[KIT_UNIDENTIFIED]))) == 4


def test_by_group_and_score_text(sample):
    df = fetch_matches()
    g = by_group(df, "opponent", "Adversário")
    row = g[g["Adversário"] == "Time A"].iloc[0]
    assert (row["Jogos"], row["V"], row["E"], row["D"]) == (3, 2, 1, 0)
    away = df[df["flu_side"] == "visitante"].iloc[0].to_dict()
    assert score_text(away).endswith("Fluminense")


def test_globe_and_coverage(sample):
    pts = {p["iso2"]: p for p in globe.country_points()}
    assert set(pts) == {"BR", "AR", "JP"}
    wt = globe.world_totals()
    assert (wt["countries"], wt["international"], wt["unknown"]) == (3, 2, 2)
    det = globe.country_detail("AR")
    assert det["record"].losses == 1 and det["stadiums"].index.tolist() == ["Estádio Y"]
    assert "Não representa toda a história" in coverage.coverage_sentence()


def test_player_stats_exclude_own_goals(sample, db):
    pid = db.scalar("SELECT id FROM people WHERE name = 'Jogador Um'")
    assert players.stats(pid)["goals"] == 2
    assert db.scalar("SELECT COUNT(*) FROM people WHERE name = 'Zagueiro Rival'") == 0


def test_global_search_accent_insensitive(sample):
    search.rebuild_index()
    assert "stadium" in search.search("estadio x")
    assert "match" in search.search("Time C 2012")
    assert "player" in search.search("jogador um")
    assert search.search("de") == {}


def test_password_hashing_and_lockout():
    h = hash_password("senha-muito-forte")
    assert verify_password("senha-muito-forte", h) and not verify_password("errada", h)
    state = {}
    g = LoginGuard(state)
    for _ in range(5):
        assert not g.attempt("admin", "x", "admin", h)
    assert g.locked_for() > 0
    assert not g.attempt("admin", "senha-muito-forte", "admin", h)  # bloqueado mesmo com a senha certa
