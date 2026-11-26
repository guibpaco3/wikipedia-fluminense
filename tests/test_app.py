"""Executa cada página via app.py (AppTest) contra o banco de teste e verifica que não há exceções."""
import pytest
from streamlit.testing.v1 import AppTest

from tests.conftest import ROOT

PAGES = ["views/home.py", "views/search.py", "views/advanced_search.py", "views/match_list.py", "views/match.py",
         "views/history.py", "views/titles.py", "views/competitions.py", "views/players.py", "views/coaches.py",
         "views/stadiums.py", "views/referees_kits.py", "views/sources.py", "views/administration.py"]


def run(page: str, params: dict | None = None) -> AppTest:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    at.run()
    at.switch_page(page)
    for k, v in (params or {}).items():
        at.query_params[k] = v
    at.run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(sample, page):
    from modules.search import rebuild_index
    rebuild_index()
    params = {"views/match.py": {"id": "1"}, "views/search.py": {"q": "Time A"}}.get(page)
    at = run(page, params)
    assert not at.exception, at.exception


@pytest.mark.parametrize("page,qid", [("views/players.py", "1"), ("views/competitions.py", "1"),
                                      ("views/stadiums.py", "1"), ("views/coaches.py", "999"),
                                      ("views/match.py", "999")])
def test_detail_pages(sample, page, qid):
    at = run(page, {"id": qid})
    assert not at.exception, at.exception


def test_pages_with_manual_content(sample, db):
    """Ramos que só aparecem com cadastro manual: passagens, presidentes, artigos, linha do tempo, uniformes."""
    with db.connect() as c:
        pid = c.scalar("SELECT id FROM people WHERE name = 'Jogador Um'")
        c.execute("INSERT INTO player_spells (person_id, start_date, end_date) VALUES (?, '2009', '2012')", (pid,))
        c.execute("INSERT INTO coach_spells (person_id, start_date, end_date) VALUES (?, '2010', '2011')", (pid,))
        c.execute("UPDATE matches SET flu_coach_id = ?", (pid,))
        c.execute("INSERT INTO presidencies (person_id, start_date, end_date, highlights) VALUES (?, '2010', '2012', 'Teste')", (pid,))
        c.execute("INSERT INTO titles (name, season, competition_id) VALUES ('Título Teste', '2010', 1)")
        aid = c.insert("INSERT INTO articles (slug, title, category, body_md, created_at, updated_at) "
                       "VALUES ('a', 'Artigo Teste', 'historia', 'Texto', '2026-01-01', '2026-01-01')")
        c.execute("INSERT INTO timeline_events (date, title) VALUES ('1902-07-21', 'Marco teste')")
        k = c.insert("INSERT INTO kits (name, category) VALUES ('Kit Teste', 'titular')")
        c.execute("UPDATE matches SET flu_kit_id = ?, kit_status = 'confirmado' WHERE id = 1", (k,))
    for page, params in [("views/players.py", {"id": str(pid)}), ("views/coaches.py", {"id": str(pid)}),
                         ("views/coaches.py", None), ("views/history.py", None),
                         ("views/history.py", {"id": str(aid)}), ("views/titles.py", {"id": "1"}),
                         ("views/titles.py", None), ("views/referees_kits.py", None),
                         ("views/referees_kits.py", {"id": "1"}), ("views/match.py", {"id": "1"})]:
        at = run(page, params)
        assert not at.exception, (page, at.exception)


def test_admin_requires_login_and_renders_when_authenticated(sample, monkeypatch):
    from core import config
    from core.auth import hash_password
    monkeypatch.setattr(config, "ADMIN_PASSWORD_HASH", hash_password("senha-de-teste-123"))
    at = run("views/administration.py")
    assert not at.exception
    assert any(e.label == "Senha" for e in at.text_input)          # formulário de login visível
    assert not at.tabs                                              # nada do painel antes do login
    at.session_state["admin_user"] = "admin"
    at.run()
    assert not at.exception, at.exception
    assert len(at.tabs) == 6
