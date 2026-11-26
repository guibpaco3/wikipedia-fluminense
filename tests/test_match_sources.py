"""Parsers RSSSF e openfootball, nomes de clubes e fusão por data próxima (sem rede)."""
from collectors.openfootball import parse as of_parse
from collectors.rsssf import split_sections
from collectors.rsssf_parser import parse_header_dates, parse_page, parse_scorers
from collectors.teams import TeamNamer, is_fluminense, split_name

BRAZ = """
Round 1
[Jan 26]
Fluminense      2-1  Santos
  [Assis, Vica; Lima]
[Jan 27]
Corinthians     2-2  Vasco da Gama
Round 2
[Jan 30]
Fluminense      2-0  Portuguesa
  [Washington, Romerito]
Second Stage
Flamengo-RJ     0-0  Fluminense
"""


def test_header_dates():
    assert parse_header_dates("Jan 17") == [(17, 1, None)]
    assert parse_header_dates("Aug 24 and 31") == [(24, 8, None), (31, 8, None)]
    assert parse_header_dates("Apr 30-May 6") == [(30, 4, None), (6, 5, None)]
    assert parse_header_dates("1. 7.1984") == [(1, 7, 1984)]
    assert parse_header_dates("14/02") == [(14, 2, None)]
    assert parse_header_dates("From Sep 1 to Oct 23") is None
    assert parse_header_dates("Assis, Vica; Lima") is None


def test_rsssf_round_format_with_scorers_and_no_stale_dates():
    r = parse_page(BRAZ, 1985)
    assert [(m.date, m.home, m.home_goals, m.away_goals, m.away) for m in r.matches] == [
        ("1985-01-26", "Fluminense", 2, 1, "Santos"), ("1985-01-30", "Fluminense", 2, 0, "Portuguesa")]
    assert r.matches[0].scorers == [("home", "Assis", None, "gol"), ("home", "Vica", None, "gol"),
                                    ("away", "Lima", None, "gol")]
    # Jogo sob novo estágio sem data própria NÃO herda a data anterior.
    assert r.undated == ["Flamengo-RJ     0-0  Fluminense"]


def test_rsssf_carioca_formats_and_venue():
    text = ("03/May - Paysandu 1-7 Fluminense (Rua Guanabara).\n"
            "23/Sep      Portuguesa 1-4 Fluminense\n"
            "[Jan 21]\nFluminense 2-1 Portuguesa [played in Moça Bonita, Rio de Janeiro-RJ]\n"
            " (Lelê 4’, Isaac 30’; Ronaldo 69’)\n")
    r = parse_page(text, 1906, "RJ")
    m1, m2, m3 = r.matches
    assert (m1.date, m1.stadium, m1.away) == ("1906-05-03", "Rua Guanabara", "Fluminense")
    assert m2.date == "1906-09-23"
    assert m3.date == "1907-01-21"              # temporada virou o ano (jan < mês inicial)
    assert (m3.stadium, m3.city) == ("Moça Bonita", "Rio de Janeiro")
    assert [(s[1], s[2]) for s in m3.scorers] == [("Lelê", 4), ("Isaac", 30), ("Ronaldo", 69)]


def test_rsssf_two_legs_conventions():
    taca = "[Aug 24 and 31]\nFonseca         0-3   0-8  Fluminense\n"
    a, b = parse_page(taca, 1960).matches
    assert (a.date, a.home, a.home_goals, a.away_goals) == ("1960-08-24", "Fonseca", 0, 3)
    assert (b.date, b.home, b.home_goals, b.away_goals, b.away) == ("1960-08-31", "Fluminense", 8, 0, "Fonseca")
    cup = ("13 Adesg (AC) - Fluminense (RJ)                 1-2 (14/02)     0-6 (28/02)\n"
           "                                                [Diego 79 ; Soares 25, Alex Dias 75]\n"
           "                                                [Alex Dias 2, Cícero 20, Thiago Neves 22, 55, "
           "Thiago Silva 41, Lenny 88]\n")
    a, b = parse_page(cup, 2007).matches
    assert (b.date, b.home, b.home_goals, b.away_goals) == ("2007-02-28", "Fluminense", 6, 0)
    assert len(b.scorers) == 6 and ("home", "Thiago Neves", 55, "gol") in b.scorers
    sula = ("(Apr 30-May 6)\n"
            "Atlético Nacional         Col  Fluminense                Bra   1-2  0-1  1-3\n"
            "  [Francisco Arrué 53; Thiago Neves 22pen, Darío Conca 72]\n  [Roger 52]\n")
    a, b = parse_page(sula, 2008).matches
    assert (a.home_country, a.date, b.date, b.home, b.home_goals) == ("CO", "2008-04-30", "2008-05-06", "Fluminense", 1)
    assert ("away", "Thiago Neves", 22, "gol_penalti") in a.scorers


def test_rsssf_dated_dash_format_and_penalty_shootout():
    t = "Feb 20: LDU Quito - Fluminense                0-0\nJul  2: Fluminense - LDU Quito    3-1 [1-3 pen]\n"
    a, b = parse_page(t, 2008).matches
    assert (a.date, a.home) == ("2008-02-20", "LDU Quito")
    assert (b.home_pens, b.away_pens) == (1, 3)


def test_scorers_mismatch_is_dropped():
    assert parse_scorers("[Fred (2), Alan]") == [[("Fred", None, "gol"), ("Fred", None, "gol"), ("Alan", None, "gol")]]
    r = parse_page("[Jan 5]\nFluminense 3-0 Bangu\n  [Fred, Alan]\n", 2010, "RJ")
    assert r.matches[0].scorers == []           # 2 nomes para 3 gols: não grava autores


def test_other_fluminenses_are_never_ours():
    assert is_fluminense("Fluminense") and is_fluminense("Fluminense-RJ") and is_fluminense("Fluminense(RJ)")
    assert is_fluminense("Fluminense RJ (BRA)") and is_fluminense("Fluminense FC")
    for other in ("Fluminense-BA", "Fluminense (BA)", "Fluminense de Feira", "Fluminense-PI"):
        assert not is_fluminense(other), other
    # Homônimo sempre qualificado: "Fluminense" sozinho é o do Rio.
    page = "[Oct 16]\nDesportiva      0-5  Fluminense-RJ\nFluminense-BA   1-0  Vitória-ES\nFluminense 1-1 Bahia\n"
    r = parse_page(page, 1977)
    assert [(m.home, m.away) for m in r.matches] == [("Desportiva", "Fluminense"), ("Fluminense", "Bahia")]
    assert not r.ambiguous


def test_homonym_introduced_as_participant_owns_its_group():
    page = ("Group C\nParticipating Teams:\nCSA (Maceió, AL)\nFluminense FC (Feira de Santana, BA)\n\n"
            "29/08\nFluminense 1x2 CSA\n\n"
            "Group D\nParticipating Teams:\nFluminense FC (Rio de Janeiro, RJ)\nSerra (Serra, ES)\n\n"
            "30/08\nFluminense 1x0 Serra\n")
    r = parse_page(page, 1999)
    assert [(m.date, m.home, m.away) for m in r.matches] == [("1999-08-30", "Fluminense", "Serra")]
    # Sem apresentação no grupo, "Fluminense" numa página com homônimo apresentado fica ambíguo.
    r = parse_page(page + "Final Phase\n[Dec 9]\nFluminense 2-1 Náutico\nGroup E\n[Dec 10]\nFluminense 0-0 CSA\n", 1999)
    assert r.ambiguous == ["Fluminense 0-0 CSA"]


def test_two_column_layout_and_three_leg_ties():
    page = ("29/08                                   19/09\n"
            "Náutico 2x0 Unibol                      Fluminense 0x1 Sergipe\n"
            "Fluminense 1x2 CSA                      Unibol 2x2 Itabaiana\n"
            "Sergipe 2x2 Itabaiana                   Náutico 2x1 CSA\n\n"
            "1/8 Finals [Nov 7, 14 and 16]\n"
            "Moto Clube (MA)   1-1 0-1 1-2 Fluminense (RJ)     [1st leg Nov 8, 2nd match in Juiz de Fora]\n"
            "[NB: first mentioned team played at home 1st leg; 2nd mentioned team\n"
            "     played at home 2nd (and 3rd) leg]\n")
    r = parse_page(page, 1999)
    got = [(m.date, m.home, m.home_goals, m.away_goals, m.away, m.city) for m in r.matches]
    assert got == [("1999-08-29", "Fluminense", 1, 2, "CSA", None),
                   ("1999-09-19", "Fluminense", 0, 1, "Sergipe", None),
                   ("1999-11-08", "Moto Clube (MA)", 1, 1, "Fluminense", None),
                   ("1999-11-14", "Fluminense", 1, 0, "Moto Clube (MA)", "Juiz de Fora"),
                   ("1999-11-16", "Fluminense", 2, 1, "Moto Clube (MA)", None)]


def test_match_sheet_date_wins_over_round_header():
    page = ("Round 7 [May 3]\nFluminense    0-0 Botafogo            [May 4]\n\n"
            "BOTAFOGO 0 x 0 FLUMINENSE\nData – 4 de maio de 1997\nLocal – Maracanã, Rio de Janeiro (RJ)\n"
            "Árbitro – Fulano de Tal\n\n[Dec 11]\nFLUMINENSE 1 x 0 FLAMENGO\nLocal: Estádio do Maracanã.\n"
            "Data: 11/12/1983.\n")
    r = parse_page(page, 1997, default_state="RJ")
    sheets = [m for m in r.matches if m.from_sheet]
    assert [(m.date, m.home, m.stadium, m.city) for m in sheets] == [
        ("1997-05-04", "Botafogo", "Maracanã", "Rio de Janeiro"),
        ("1983-12-11", "Fluminense", "Estádio do Maracanã", None)]
    assert sheets[0].referee == "Fulano de Tal"


def test_team_goals_format_and_compact_dates():
    page = "20/sep/87\n\nSANTOS 0 x PALMEIRAS 0\nFLUMINENSE 1 x BOTAFOGO 1\n[Jan 24/87]\nFluminense 2-0 Santa Cruz\n"
    r = parse_page(page, 1987)
    assert [(m.date, m.home, m.away, m.home_goals) for m in r.matches] == [
        ("1987-09-20", "Fluminense", "Botafogo", 1), ("1987-01-24", "Fluminense", "Santa Cruz", 2)]
    r = parse_page("02/Jan/1955 Madureira 1-8 Fluminense\n", 1954, default_state="RJ")
    assert [(m.date, m.away_goals) for m in r.matches] == [("1955-01-02", 8)]


def test_qualified_homonym_is_not_a_venue():
    """Carioca 1979: 'Fluminense (Nova Friburgo)' é outro clube, não 'Fluminense' jogando em Nova Friburgo."""
    page = ("06/May      Fluminense (Nova Friburgo) 0-0 Americano\n"
            "13/May      Goytacaz 1-0 Fluminense (Nova Friburgo)\n"
            "03/Jun      Fluminense 3-0 Fluminense (Nova Friburgo)\n"
            "06/May      São Cristóvão 1-8 Fluminense\n"
            "03/May - Paysandu 1-7 Fluminense (Rua Guanabara).\n")
    r = parse_page(page, 1979, "RJ")
    got = [(m.date, m.home, m.away, m.stadium) for m in r.matches]
    assert got == [("1979-06-03", "Fluminense", "Fluminense (Nova Friburgo)", None),
                   ("1979-05-06", "São Cristóvão", "Fluminense", None),
                   ("1979-05-03", "Paysandu", "Fluminense", "Rua Guanabara")]


def test_team_namer():
    n = TeamNamer({"Portuguesa": "SP", "Botafogo": "RJ", "Paysandu": "PA", "Atlético-MG": "MG"})
    assert n.canonical("Portuguesa", "RJ")[0] == "Portuguesa-RJ"
    assert n.canonical("Botafogo", "RJ")[0] == "Botafogo"
    assert n.canonical("Botafogo(SP)")[0] == "Botafogo-SP"
    assert n.canonical("Atlético MG")[0] == "Atlético-MG"
    assert n.canonical("Atlético(PR)")[0] == "Athletico-PR"
    assert n.canonical("CR Flamengo (BRA)")[0] == "Flamengo"
    assert n.canonical("Vasco", "RJ")[0] == "Vasco da Gama"
    assert n.canonical("America", "RJ")[0] == "América-RJ"
    assert n.canonical("CA Boca Juniors (ARG)") == ("CA Boca Juniors", None, "AR")
    assert split_name("Picos (PI)") == ("Picos", "PI", "BR")


def test_foreign_clubs_unified_and_homonyms_need_evidence():
    from collectors.rsssf import _canon, page_qualifiers
    n = TeamNamer({"América-MG": "MG", "Palmeiras": "SP"})
    assert n.canonical("CA Boca Juniors (ARG)", international=True) == ("Boca Juniors", None, "AR")
    assert n.canonical("Boca Juniors", international=True) == ("Boca Juniors", None, "AR")
    assert n.canonical("Olimpia Asuncion (PAR)", international=True)[0] == "Olimpia"
    assert n.canonical("Palmeiras", international=True) == ("Palmeiras", "SP", "BR")
    # Homônimo sem país: não é presumido...
    assert n.canonical("Nacional", international=True) == ("Nacional", None, None)
    # ...mas a tabela da própria página resolve ("3.Nacional (Montevideo)  6 ...").
    quals = page_qualifiers(" 1.América (Ciudad de México)      6  3  1  2   8- 7 10\n"
                            " 3.Nacional (Montevideo)           6  2  2  2   3- 3  8\n")
    assert _canon(n, "Nacional", None, None, True, quals) == ("Nacional (Uruguai)", None, "UY")
    assert _canon(n, "América", None, None, True, quals) == ("América (México)", None, "MX")


def test_sections_of_brasileiro_page():
    text = ("Brazil 1998 Championship\n[Jan 5]\nFluminense 1-0 Bahia\nBrazil 1998 Cup\n[Feb 2]\n"
            "Fluminense 2-0 Remo\nBrazil 1998 Championship Second Division\n[Aug 1]\nFluminense 3-0 Vila Nova\n")
    secs = dict(split_sections(text, "brasileiro", "Campeonato Brasileiro Série A"))
    assert set(secs) == {"Campeonato Brasileiro Série A", "Campeonato Brasileiro Série B"}
    assert "Remo" not in "".join(secs.values())            # Copa do Brasil vem das páginas próprias
    assert "Vila Nova" in secs["Campeonato Brasileiro Série B"]
    assert dict(split_sections(text, "cup_only", "Copa do Brasil de Futebol")).keys() == {"Copa do Brasil de Futebol"}


OF = """= Copa Libertadores 2023
▪ Finals, Semifinals
  Wed Oct 4
    21:30  SC Internacional (BRA)  v Fluminense FC (BRA)      1-2 (1-0)
  Thu Oct 5
    21:30  SE Palmeiras (BRA)      v CA Boca Juniors (ARG)    2-4 pen. (1-1, 0-1)
▪ Finals, Final
  Sat Nov 4
    17:00  CA Boca Juniors (ARG)   v Fluminense FC (BRA)      1-2 a.e.t. (1-1, 0-1)
"""


def test_openfootball_scores():
    ms = of_parse(OF, 2023)
    semi, pens, final = ms
    assert (semi.date, semi.home_goals, semi.away_goals, semi.ht) == ("2023-10-04", 1, 2, (1, 0))
    assert (pens.home_goals, pens.away_goals, pens.pens, pens.ht) == (1, 1, (2, 4), (0, 1))
    assert (final.home_goals, final.away_goals, final.ht, final.stage) == (1, 2, (0, 1), "Finals, Final")


def test_openfootball_collect_single_final_is_neutral(db):
    from collectors import openfootball
    files = [("south-america", "x/2023_copal.txt", "Copa Libertadores", "continental", "2023", None)]
    res = openfootball.collect(files=files, texts={"x/2023_copal.txt": OF})
    assert res["inserted"] == 2, res
    with db.connect() as c:
        final = c.one("SELECT * FROM v_matches WHERE date = '2023-11-04'")
        semi = c.one("SELECT * FROM v_matches WHERE date = '2023-10-04'")
    assert final["flu_side"] == "neutro" and final["country_iso2"] is None     # sede não informada pela fonte
    assert (final["flu_goals"], final["opp_goals"]) == (2, 1)
    assert semi["country_iso2"] == "BR" and semi["flu_side"] == "visitante"


def test_same_match_with_shifted_date_is_merged(db):
    from database.models import MatchRecord
    from database.repository import ensure_source, upsert_match
    base = dict(home_team="Fluminense", away_team="Bangu", home_goals=2, away_goals=0,
                competition="Campeonato Carioca de Futebol", season="1990")
    with db.connect() as c:
        ensure_source(c, "src_a", "A", "dataset")
        ensure_source(c, "src_b", "B", "dataset")
        s1, id1 = upsert_match(c, MatchRecord(source_code="src_a", source_ref="1", date="1990-03-04", **base))
        s2, id2 = upsert_match(c, MatchRecord(source_code="src_b", source_ref="9", date="1990-03-05", **base))
        assert (s1, s2) == ("inserted", "updated") and id1 == id2
        assert c.scalar("SELECT COUNT(*) FROM discrepancies WHERE entity_id = ? AND field = 'date'", (id1,)) == 1
