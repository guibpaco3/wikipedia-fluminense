"""Validação de registros antes da gravação."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from core import config
from core.text import norm
from database.models import EVENT_TYPES, RELIABILITY, MatchRecord

FOUNDATION = date(1902, 7, 21)


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_match(rec: MatchRecord, today: date | None = None) -> ValidationResult:
    v = ValidationResult()
    today = today or date.today()
    try:
        d = date.fromisoformat(rec.date)
        if d < FOUNDATION:
            v.errors.append(f"Data {rec.date} anterior à fundação do clube.")
        if d > today:
            v.errors.append(f"Data {rec.date} no futuro.")
    except (TypeError, ValueError):
        v.errors.append(f"Data inválida: {rec.date!r}")

    flu = norm(config.FLUMINENSE_NAME)
    h, a = norm(rec.home_team), norm(rec.away_team)
    if not h or not a:
        v.errors.append("Mandante e visitante são obrigatórios.")
    elif h == a:
        v.errors.append("Mandante e visitante iguais.")
    elif flu not in (h, a):
        v.errors.append(f"Fluminense não participa: {rec.home_team} x {rec.away_team}.")

    for name, val in (("gols do mandante", rec.home_goals), ("gols do visitante", rec.away_goals),
                      ("gols do mandante no intervalo", rec.home_goals_ht),
                      ("gols do visitante no intervalo", rec.away_goals_ht)):
        if val is not None and (not isinstance(val, int) or val < 0 or val > 40):
            v.errors.append(f"Valor inválido em {name}: {val!r}")
    if (rec.home_goals is None) != (rec.away_goals is None):
        v.errors.append("Placar incompleto (apenas um dos lados informado).")
    if rec.home_goals_ht is not None and rec.home_goals is not None and rec.home_goals_ht > rec.home_goals:
        v.errors.append("Gols do mandante no intervalo maiores que no final.")
    if rec.away_goals_ht is not None and rec.away_goals is not None and rec.away_goals_ht > rec.away_goals:
        v.errors.append("Gols do visitante no intervalo maiores que no final.")
    if rec.reliability not in RELIABILITY:
        v.errors.append(f"Confiabilidade inválida: {rec.reliability}")
    if rec.attendance is not None and rec.attendance < 0:
        v.errors.append("Público negativo.")

    for ev in rec.events:
        if ev.event_type not in EVENT_TYPES:
            v.errors.append(f"Tipo de evento inválido: {ev.event_type}")
        if ev.minute is not None and not (0 <= ev.minute <= 130):
            v.warnings.append(f"Minuto incomum ({ev.minute}) para {ev.player_name}.")

    if rec.events and rec.home_goals is not None:
        goals = {"home": 0, "away": 0}
        for ev in rec.events:
            if ev.event_type in ("gol", "gol_penalti", "gol_contra"):
                goals[ev.side] += 1
        if (goals["home"], goals["away"]) != (rec.home_goals, rec.away_goals) and any(goals.values()):
            v.warnings.append(
                f"Gols detalhados ({goals['home']}x{goals['away']}) não batem com o placar "
                f"({rec.home_goals}x{rec.away_goals}); lista de autores possivelmente incompleta.")
    return v
