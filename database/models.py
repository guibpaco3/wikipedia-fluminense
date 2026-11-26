"""Estruturas de dados trocadas entre coletores, validação e repositório."""
from __future__ import annotations

from dataclasses import dataclass, field

RELIABILITY = ("alta", "media", "baixa")
VERIFICATION = ("verificado", "nao_verificado", "divergente", "rejeitado")
KIT_CATEGORIES = ("titular", "reserva", "terceiro", "especial", "historico")
COMPETITION_CATEGORIES = ("nacional", "estadual", "continental", "mundial", "amistoso", "outro")
EVENT_TYPES = ("gol", "gol_penalti", "gol_contra", "amarelo", "vermelho")

LABELS = {
    "alta": "Alta", "media": "Média", "baixa": "Baixa",
    "verificado": "Verificado", "nao_verificado": "Não verificado",
    "divergente": "Divergente", "rejeitado": "Rejeitado",
    "confirmado": "Confirmado", "nao_confirmado": "Não confirmado",
    "nao_identificado": "Não identificado",
}


@dataclass
class EventRecord:
    event_type: str          # ver EVENT_TYPES
    side: str                # 'home' | 'away' — time BENEFICIADO (gols) ou PUNIDO (cartões)
    player_name: str | None
    minute: int | None = None


@dataclass
class MatchRecord:
    """Uma partida como descrita por UMA fonte, antes de ser fundida na base."""
    source_code: str
    source_ref: str
    date: str                       # AAAA-MM-DD
    home_team: str
    away_team: str
    home_goals: int | None
    away_goals: int | None
    competition: str | None = None
    competition_category: str = "outro"
    season: str | None = None
    round: str | None = None
    stage: str | None = None
    kickoff: str | None = None
    home_state: str | None = None
    away_state: str | None = None
    home_country: str | None = None
    away_country: str | None = None
    neutral: bool = False
    home_goals_ht: int | None = None
    away_goals_ht: int | None = None
    stadium: str | None = None
    city: str | None = None
    country_iso2: str | None = None
    country_status: str = "nao_verificado"
    attendance: int | None = None
    referee: str | None = None
    referee_status: str = "nao_identificado"
    home_coach: str | None = None
    away_coach: str | None = None
    home_formation: str | None = None
    away_formation: str | None = None
    url: str | None = None
    reliability: str = "media"
    events: list[EventRecord] = field(default_factory=list)
    row_hash: str | None = None
