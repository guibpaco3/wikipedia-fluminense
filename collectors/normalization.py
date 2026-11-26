"""Normalização de nomes vindos das fontes.

Apenas grafia (acentos, abreviações de fonte → nome usual). Nenhum dado histórico aqui.
Novas variações podem ser cadastradas pelo painel (aliases de clubes).
"""
from __future__ import annotations

import re

from core.text import clean, norm

# Grafia usada pelo Brasileirão Dataset → nome de exibição.
TEAM_DISPLAY = {
    "america mg": "América-MG", "america rn": "América-RN", "athletico pr": "Athletico-PR",
    "atletico go": "Atlético-GO", "atletico mg": "Atlético-MG", "avai": "Avaí", "botafogo rj": "Botafogo",
    "ceara": "Ceará", "criciuma": "Criciúma", "cuiaba": "Cuiabá", "goias": "Goiás", "gremio": "Grêmio",
    "gremio prudente": "Grêmio Prudente", "nautico": "Náutico", "parana": "Paraná",
    "santo andre": "Santo André", "sao caetano": "São Caetano", "sao paulo": "São Paulo",
    "vasco": "Vasco da Gama", "vitoria": "Vitória",
    "mirassol": "Mirassol",
}


def team_display(name: str) -> str:
    name = clean(name) or ""
    return TEAM_DISPLAY.get(norm(name), name)


def stadium_display(name: str | None) -> str | None:
    """Limpa ruído de digitação (NBSP, '*(PF)', prefixos repetidos)."""
    name = clean(name)
    if not name:
        return None
    name = re.sub(r"\*\(.*?\)", "", name)
    name = name.strip(" -|")
    return name or None


def parse_int(v) -> int | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in {"-", "—"}:
        return None
    m = re.match(r"^(\d+)", s.replace(".", ""))
    return int(m.group(1)) if m else None
