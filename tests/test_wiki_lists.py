"""Leitura das cópias da Wikipédia usadas na página inicial."""
from datetime import date

from modules import wiki_lists as w


def test_presidents():
    p = w.presidents()
    assert len(p) >= 40
    assert p[0].start == date(1902, 7, 21)
    assert p[-1].end is None                       # mandato em curso
    assert all(x.start for x in p)


def test_coaches_only_last_is_open():
    c = w.coaches()
    assert len(c) > 150
    assert [x for x in c if x.end is None] == [c[-1]]
    assert any(x.interim for x in c)


def test_main_titles_total():
    t = {x.name: x for x in w.main_titles()}
    assert t["Campeonato Carioca"].count == len(t["Campeonato Carioca"].years) == 33
    assert t["Campeonato Brasileiro"].years == [1970, 1984, 2010, 2012]
    official = sum(x.count for x in w.main_titles() if x.category not in ("Honrarias", "Total"))
    assert official == t["Conquistas oficiais"].count


def test_idols():
    i = w.idols()
    assert len(i) == 30 and i[0].name == "Castilho" and i[0].games == 704


def test_infobox_formats():
    a = "|clube1 = {{Futebol Fluminense}}\n|jogos1 = 100\n|gols1 = 10\n|clube2 = {{Futebol Fluminense}}\n|jogos2 = 5\n|gols2 = 1\n"
    assert w.infobox_flu_stats(a)["games"] == 105
    b = "|clubes = {{Futebol Santos}}<br>{{Futebol Fluminense}}\n|jogos(golos) = 10 (2)<br>{{0|00}}158 {{0|000}}(53)\n"
    r = w.infobox_flu_stats(b)
    assert (r["games"], r["goals"]) == (158, 53)
