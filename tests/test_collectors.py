from datetime import date

from collectors import brasileirao_dataset as bd
from collectors import csv_import
from collectors.data_validation import validate_match
from collectors.http import AccessDenied, PoliteClient
from database.models import EventRecord
from tests.conftest import make


def _row(i, rnd, d, home, away, hg, ag):
    return {"ID": str(i), "rodata": str(rnd), "data": d, "hora": "16:00", "mandante": home, "visitante": away,
            "formacao_mandante": "", "formacao_visitante": "", "tecnico_mandante": "T. Mandante",
            "tecnico_visitante": "T. Visitante", "vencedor": "", "arena": "\xa0 Estádio Teste",
            "mandante_Placar": str(hg), "visitante_Placar": str(ag), "mandante_Estado": "RJ", "visitante_Estado": "SP"}


def test_seasons_follow_round_resets_not_calendar_year():
    rows = [_row(1, 1, "10/08/2020", "A", "B", 0, 0), _row(2, 38, "25/02/2021", "A", "B", 0, 0),
            _row(3, 1, "30/05/2021", "A", "B", 0, 0), _row(4, 5, "01/09/2021", "A", "B", 0, 0),
            _row(5, 3, "02/09/2021", "A", "B", 0, 0)]  # jogo adiado: pequeno recuo não abre temporada
    s = bd.assign_seasons(rows)
    assert s == {"1": "2020", "2": "2020", "3": "2021", "4": "2021", "5": "2021"}


def test_build_records_filters_fluminense_and_maps_events():
    data = {"matches": [_row(1, 1, "10/08/2020", "Fluminense", "Sao Paulo", 2, 1),
                        _row(2, 1, "10/08/2020", "Gremio", "Vasco", 1, 1)],
            "goals": [{"partida_id": "1", "clube": "Fluminense", "atleta": "Fulano", "minuto": "12", "tipo_de_gol": ""},
                      {"partida_id": "1", "clube": "Fluminense", "atleta": "Zagueiro", "minuto": "40",
                       "tipo_de_gol": "Gol Contra"},
                      {"partida_id": "1", "clube": "Sao Paulo", "atleta": "Beltrano", "minuto": "80",
                       "tipo_de_gol": "Penalty"}],
            "cards": []}
    recs = bd.build_records(data)
    assert len(recs) == 1
    r = recs[0]
    assert (r.away_team, r.stadium, r.country_status, r.season) == ("São Paulo", "Estádio Teste", "inferido", "2020")
    assert [e.event_type for e in r.events] == ["gol", "gol_contra", "gol"]
    assert validate_match(r).ok and not validate_match(r).warnings


def test_brasileirao_ingest_incremental(db):
    data = {"matches": [_row(1, 1, "10/08/2020", "Fluminense", "Sao Paulo", 2, 1)], "goals": [], "cards": []}
    assert bd.collect(data)["inserted"] == 1
    assert bd.collect(data)["unchanged"] == 1


def test_validation_rules():
    assert not validate_match(make("v", "1890-01-01", "Fluminense", "X", 1, 0)).ok
    assert not validate_match(make("v", "2999-01-01", "Fluminense", "X", 1, 0)).ok
    assert not validate_match(make("v", "2000-01-01", "A", "B", 1, 0)).ok
    assert not validate_match(make("v", "2000-01-01", "Fluminense", "X", 1, None)).ok
    bad_ht = make("v", "2000-01-01", "Fluminense", "X", 1, 0, home_goals_ht=2)
    assert not validate_match(bad_ht).ok
    w = make("v", "2000-01-01", "Fluminense", "X", 2, 0, events=[EventRecord("gol", "home", "A", 3)])
    v = validate_match(w, today=date(2026, 1, 1))
    assert v.ok and v.warnings


def test_csv_import(db):
    text = csv_import.template() + (
        "1984-05-27,,Fluminense,Rival Teste,1,0,,,Torneio Teste,nacional,1984,Final,,não,Estádio Z,Rio de Janeiro,"
        "BR,verificado,100000,Árbitro Beta,confirmado,,,mandante|Autor Teste|35,rsssf,https://exemplo.org,alta,\n"
        "1984-05-28,,Fluminense,Rival Teste,1,0,,,,,,,,,,,,,,,,,,,fonte_inexistente,,,\n"
        "data-ruim,,Fluminense,X,1,0,,,,,,,,,,,,,,,,,,,rsssf,,,\n")
    r = csv_import.import_csv(text, "teste")
    assert r["inserted"] == 1 and r["rejected"] == 2
    m = db.query_one("SELECT * FROM v_matches")
    assert (m["referee"], m["referee_status"], m["attendance"], m["stage"]) == ("Árbitro Beta", "confirmado", 100000, "Final")
    assert db.scalar("SELECT COUNT(*) FROM match_events WHERE person_id IS NOT NULL") == 1


class _Resp:
    def __init__(self, code):
        self.status_code, self.content = code, b"{}"

    def raise_for_status(self):
        pass


class _Session:
    def __init__(self, code):
        self.code = code

    def get(self, *a, **k):
        return _Resp(self.code)


def test_http_client_stops_on_403():
    import pytest
    with pytest.raises(AccessDenied):
        PoliteClient(delay=0, session=_Session(403)).get("https://exemplo.org/x")
